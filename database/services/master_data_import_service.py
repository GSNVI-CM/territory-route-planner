"""Authoritative Master Data importer.

The TMS owns routing, cadence, rank, routability, and exclusion rules.
The Doctor Spreadsheet owns the newest factual doctor/practice/contact/referral/visit data.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import hashlib
import json
import re
import pandas as pd
from sqlalchemy import select
from database.connection import transaction, connection
from database.schema import doctors, practices, doctor_practices, referral_snapshots, visit_history, import_runs, business_events
from config import APP_DIR

SEED_DOCTOR_FILE = APP_DIR / "data" / "seed" / "Misty_Dr_Spreadsheet_CURRENT.xlsx"
SEED_TMS_FILE = APP_DIR / "data" / "seed" / "Misty_TMS_CURRENT.xlsx"

@dataclass(frozen=True)
class ImportSummary:
    doctors: int
    practices: int
    associations: int
    visits: int
    referral_rows: int
    source_doctor_file: str
    source_tms_file: str


def _text(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    value = str(value).strip()
    return value or None


def _normalize(value) -> str:
    text = _text(value) or ""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _zip(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(5) if text.isdigit() and len(text) < 5 else text


def _int(value) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _date(value) -> date | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_sources(doctor_file: Path, tms_file: Path):
    master = pd.read_excel(doctor_file, sheet_name="All Docs")
    tms_doctors = pd.read_excel(tms_file, sheet_name="Doctors")
    tms_visits = pd.read_excel(tms_file, sheet_name="Visits")
    return master, tms_doctors, tms_visits


def _master_index(master: pd.DataFrame) -> dict[tuple[str, str], dict]:
    result = {}
    for _, row in master.iterrows():
        key = (_normalize(row.get("Dr Name")), _normalize(row.get("Address")))
        if not key[0]:
            continue
        result[key] = row.to_dict()
    return result


def import_master_data(doctor_file: str | Path, tms_file: str | Path, actor_user_id: int | None = None) -> ImportSummary:
    doctor_file, tms_file = Path(doctor_file), Path(tms_file)
    master, tms_df, visits_df = _load_sources(doctor_file, tms_file)
    master_idx = _master_index(master)
    doctor_ids: dict[str, int] = {}
    practice_ids: dict[str, int] = {}
    associations = visits = referral_rows = 0

    with transaction() as conn:
        # A full authoritative refresh keeps IDs stable where natural keys still match.
        existing_doctors = {r.normalized_name: r.doctor_id for r in conn.execute(select(doctors.c.doctor_id, doctors.c.normalized_name))}
        existing_practices = {r.normalized_address: r.practice_id for r in conn.execute(select(practices.c.practice_id, practices.c.normalized_address))}

        conn.execute(doctor_practices.delete())
        conn.execute(referral_snapshots.delete())
        conn.execute(visit_history.delete())

        seen_doctors, seen_practices, referral_doctors_written = set(), set(), set()
        for _, tms in tms_df.iterrows():
            dname = _text(tms.get("Doctor Name"))
            if not dname:
                continue
            address = _text(tms.get("Practice Address")) or "Address unavailable"
            dkey, pkey = _normalize(dname), _normalize(address)
            newer = master_idx.get((dkey, pkey), {})

            practice_values = {
                "name": _text(newer.get("Practice Name")) or _text(tms.get("Practice Name")) or "Practice unavailable",
                "normalized_name": _normalize(_text(newer.get("Practice Name")) or _text(tms.get("Practice Name"))),
                "address": _text(newer.get("Address")) or address,
                "normalized_address": pkey,
                "city": _text(tms.get("City")),
                "zip_code": _zip(newer.get("Zip")) or _zip(tms.get("Zip")),
                "office_number": _text(newer.get("Office Number")) or _text(tms.get("Office Number")),
                "office_manager": _text(newer.get("Office Manager/CM Liason")) or _text(tms.get("Office Manager/CM Liaison")),
                "route_group": _text(tms.get("Correct Route Group")),
                "route_cluster": _text(tms.get("Route Cluster")),
                "routable": str(tms.get("Routable", "Yes")).strip().lower() == "yes",
                "excluded_reason": _text(tms.get("Excluded Reason")),
                "active": True,
                "updated_at": datetime.utcnow(),
            }
            if pkey in existing_practices:
                pid = existing_practices[pkey]
                conn.execute(practices.update().where(practices.c.practice_id == pid).values(**practice_values))
            else:
                pid = conn.execute(practices.insert().values(**practice_values)).inserted_primary_key[0]
                existing_practices[pkey] = pid
            practice_ids[pkey] = pid
            seen_practices.add(pkey)

            last_visit = _date(newer.get("Visit Date")) or _date(tms.get("Last Visit Date"))
            doctor_values = {
                "name": dname,
                "normalized_name": dkey,
                "referral_rank": _int(tms.get("Referral Rank")),
                "cadence_days": _int(tms.get("Cadence Days")),
                "last_visit_date": last_visit,
                "next_due_date": _date(tms.get("Next Due")),
                "due_status": _text(tms.get("Due Status")),
                "routable": str(tms.get("Routable", "Yes")).strip().lower() == "yes",
                "excluded_reason": _text(tms.get("Excluded Reason")),
                "notes": _text(tms.get("Notes")) or _text(newer.get("Unnamed: 10")),
                "active": True,
                "updated_at": datetime.utcnow(),
            }
            if dkey in existing_doctors:
                did = existing_doctors[dkey]
                conn.execute(doctors.update().where(doctors.c.doctor_id == did).values(**doctor_values))
            else:
                did = conn.execute(doctors.insert().values(**doctor_values)).inserted_primary_key[0]
                existing_doctors[dkey] = did
            doctor_ids[dkey] = did
            seen_doctors.add(dkey)

            conn.execute(doctor_practices.insert().values(doctor_id=did, practice_id=pid, active=True))
            associations += 1
            if did not in referral_doctors_written:
                for year, master_col, tms_col in ((2026,"Referred 2026","2026 referrals"),(2025,"Referred 2025","2025 referrals"),(2024,"Referred 2024","2024 referrals")):
                    count = _int(newer.get(master_col))
                    if count is None:
                        count = _int(tms.get(tms_col)) or 0
                    conn.execute(referral_snapshots.insert().values(doctor_id=did, year=year, referral_count=count, source_file=doctor_file.name))
                    referral_rows += 1
                referral_doctors_written.add(did)

        # Mark records missing from the current authoritative sources inactive rather than deleting history.
        if seen_doctors:
            conn.execute(doctors.update().where(~doctors.c.normalized_name.in_(seen_doctors)).values(active=False))
        if seen_practices:
            conn.execute(practices.update().where(~practices.c.normalized_address.in_(seen_practices)).values(active=False))

        for _, row in visits_df.iterrows():
            dkey = _normalize(row.get("Doctor Name"))
            did = doctor_ids.get(dkey)
            vdate = _date(row.get("Visit Date"))
            if not did or not vdate:
                continue
            pkey = _normalize(row.get("Practice Address"))
            pid = practice_ids.get(pkey)
            conn.execute(visit_history.insert().values(
                doctor_id=did, practice_id=pid, visit_date=vdate,
                source=_text(row.get("Source")) or tms_file.name,
                route_cluster=_text(row.get("Route Cluster")),
            ))
            visits += 1

        summary = {
            "doctors": len(seen_doctors), "practices": len(seen_practices),
            "associations": associations, "visits": visits, "referral_rows": referral_rows,
        }
        conn.execute(import_runs.insert().values(
            doctor_source_file=doctor_file.name, tms_source_file=tms_file.name,
            doctor_source_hash=_file_hash(doctor_file), tms_source_hash=_file_hash(tms_file),
            status="Completed", summary_json=json.dumps(summary), completed_at=datetime.utcnow(),
        ))
        conn.execute(business_events.insert().values(
            event_type="master_data_imported", entity_type="master_data",
            actor_user_id=actor_user_id, event_payload=json.dumps(summary),
        ))

    return ImportSummary(**summary, source_doctor_file=doctor_file.name, source_tms_file=tms_file.name)


def seed_current_master_data() -> ImportSummary:
    return import_master_data(SEED_DOCTOR_FILE, SEED_TMS_FILE)


def master_data_is_empty() -> bool:
    with connection() as conn:
        return conn.execute(select(doctors.c.doctor_id).limit(1)).first() is None
