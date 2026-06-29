
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime, timedelta
import calendar
import re
import sqlite3
import hashlib
import io
import json

APP_TITLE = "Territory Route Planner"
APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "app_history.sqlite"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title=APP_TITLE, layout="wide")

RULES = {
    "home_base": "North Park",
    "min_offices_per_day": 6,
    "target_offices_per_day": 8,
    "max_offices_per_day": 10,
    "top_20_cadence_days": 35,
    "rank_21_60_cadence_days": 49,
    "remaining_cadence_days": 95,
    "due_lookahead_days": 31,
    "excluded_keywords": [
        "won't visit", "wont visit", "do not visit", "do not route", "never visit",
        "not routable", "out of territory", "retired", "rady", "hospital",
        "nvision", "nv vision", "acuity eye group", "angelique pilar"
    ],
}

ROUTE_KEYWORDS = {
    "Carlsbad": ["carlsbad"],
    "Oceanside / Vista": ["oceanside", "vista"],
    "Encinitas North / Carlsbad Fill-in": ["north encinitas", "leucadia"],
    "Encinitas South / Del Mar / Solana / RSF": ["south encinitas", "encinitas", "del mar", "solana beach", "rancho santa fe", "rsf"],
    "San Marcos / Escondido": ["san marcos", "escondido"],
    "Poway / Ramona": ["poway", "ramona"],
    "Rancho Bernardo / 4S / Carmel Mountain / Mira Mesa": ["rancho bernardo", "4s", "carmel mountain", "mira mesa"],
    "Kearny Mesa / Clairemont / Serra Mesa": ["kearny", "clairemont", "serra mesa"],
    "La Mesa / Lemon Grove / Spring Valley": ["la mesa", "lemon grove", "spring valley"],
    "El Cajon / Rancho San Diego": ["el cajon", "rancho san diego"],
    "Santee / Tierrasanta": ["santee", "tierrasanta"],
    "Coronado / Downtown": ["coronado", "downtown", "92101"],
    "Chula Vista / South Bay": ["chula vista", "national city", "bonita", "eastlake", "south bay"],
    "La Jolla / UTC": ["la jolla", "utc", "university city"],
    "Hillcrest / North Park / Central": ["hillcrest", "north park", "mission hills", "bankers hill"],
}


ROUTE_ORDER = [
    "Carlsbad",
    "Oceanside / Vista",
    "Encinitas North / Carlsbad Fill-in",
    "Encinitas South / Del Mar / Solana / RSF",
    "San Marcos / Escondido",
    "Poway / Ramona",
    "Rancho Bernardo / 4S / Carmel Mountain / Mira Mesa",
    "Kearny Mesa / Clairemont / Serra Mesa",
    "La Jolla / UTC",
    "Hillcrest / North Park / Central",
    "Coronado / Downtown",
    "Chula Vista / South Bay",
    "El Cajon / Rancho San Diego",
    "La Mesa / Lemon Grove / Spring Valley",
    "Santee / Tierrasanta",
    "Unassigned",
]

ROUTE_SEQUENCE = {route: i for i, route in enumerate(ROUTE_ORDER)}

ZIP_ROUTE_OVERRIDES = {
    "92008": "Carlsbad",
    "92009": "Carlsbad",
    "92010": "Carlsbad",
    "92011": "Carlsbad",
    "92054": "Oceanside / Vista",
    "92056": "Oceanside / Vista",
    "92057": "Oceanside / Vista",
    "92058": "Oceanside / Vista",
    "92081": "Oceanside / Vista",
    "92083": "Oceanside / Vista",
    "92084": "Oceanside / Vista",
    "92024": "Encinitas South / Del Mar / Solana / RSF",
    "92075": "Encinitas South / Del Mar / Solana / RSF",
    "92091": "Encinitas South / Del Mar / Solana / RSF",
    "92067": "Encinitas South / Del Mar / Solana / RSF",
    "92069": "San Marcos / Escondido",
    "92078": "San Marcos / Escondido",
    "92025": "San Marcos / Escondido",
    "92026": "San Marcos / Escondido",
    "92027": "San Marcos / Escondido",
    "92029": "San Marcos / Escondido",
    "92064": "Poway / Ramona",
    "92065": "Poway / Ramona",
    "92127": "Rancho Bernardo / 4S / Carmel Mountain / Mira Mesa",
    "92128": "Rancho Bernardo / 4S / Carmel Mountain / Mira Mesa",
    "92129": "Rancho Bernardo / 4S / Carmel Mountain / Mira Mesa",
    "92126": "Rancho Bernardo / 4S / Carmel Mountain / Mira Mesa",
    "92123": "Kearny Mesa / Clairemont / Serra Mesa",
    "92111": "Kearny Mesa / Clairemont / Serra Mesa",
    "92117": "Kearny Mesa / Clairemont / Serra Mesa",
    "92110": "Kearny Mesa / Clairemont / Serra Mesa",
    "92109": "Kearny Mesa / Clairemont / Serra Mesa",
    "92122": "La Jolla / UTC",
    "92037": "La Jolla / UTC",
    "92093": "La Jolla / UTC",
    "92103": "Hillcrest / North Park / Central",
    "92104": "Hillcrest / North Park / Central",
    "92116": "Hillcrest / North Park / Central",
    "92101": "Coronado / Downtown",
    "92118": "Coronado / Downtown",
    "91910": "Chula Vista / South Bay",
    "91911": "Chula Vista / South Bay",
    "91913": "Chula Vista / South Bay",
    "91914": "Chula Vista / South Bay",
    "91915": "Chula Vista / South Bay",
    "91902": "Chula Vista / South Bay",
    "91950": "Chula Vista / South Bay",
    "92020": "El Cajon / Rancho San Diego",
    "92019": "El Cajon / Rancho San Diego",
    "91941": "La Mesa / Lemon Grove / Spring Valley",
    "91942": "La Mesa / Lemon Grove / Spring Valley",
    "91945": "La Mesa / Lemon Grove / Spring Valley",
    "91977": "La Mesa / Lemon Grove / Spring Valley",
    "92071": "Santee / Tierrasanta",
    "92124": "Santee / Tierrasanta",
}

CITY_ROUTE_OVERRIDES = {
    "carlsbad": "Carlsbad",
    "oceanside": "Oceanside / Vista",
    "vista": "Oceanside / Vista",
    "del mar": "Encinitas South / Del Mar / Solana / RSF",
    "solana beach": "Encinitas South / Del Mar / Solana / RSF",
    "rancho santa fe": "Encinitas South / Del Mar / Solana / RSF",
    "san marcos": "San Marcos / Escondido",
    "escondido": "San Marcos / Escondido",
    "poway": "Poway / Ramona",
    "ramona": "Poway / Ramona",
    "rancho bernardo": "Rancho Bernardo / 4S / Carmel Mountain / Mira Mesa",
    "mira mesa": "Rancho Bernardo / 4S / Carmel Mountain / Mira Mesa",
    "la jolla": "La Jolla / UTC",
    "university city": "La Jolla / UTC",
    "utc": "La Jolla / UTC",
    "hillcrest": "Hillcrest / North Park / Central",
    "north park": "Hillcrest / North Park / Central",
    "downtown": "Coronado / Downtown",
    "coronado": "Coronado / Downtown",
    "chula vista": "Chula Vista / South Bay",
    "national city": "Chula Vista / South Bay",
    "bonita": "Chula Vista / South Bay",
    "el cajon": "El Cajon / Rancho San Diego",
    "rancho san diego": "El Cajon / Rancho San Diego",
    "la mesa": "La Mesa / Lemon Grove / Spring Valley",
    "lemon grove": "La Mesa / Lemon Grove / Spring Valley",
    "spring valley": "La Mesa / Lemon Grove / Spring Valley",
    "santee": "Santee / Tierrasanta",
    "tierrasanta": "Santee / Tierrasanta",
}

SYSTEM_SHEETS = ["Doctors", "Visits", "Routes", "Settings", "Route Builder", "Cleanup", "Import Review"]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uploaded_at TEXT NOT NULL,
            file_name TEXT NOT NULL,
            saved_path TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            notes TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exported_at TEXT NOT NULL,
            file_name TEXT NOT NULL,
            row_count INTEGER NOT NULL
        )"""
    )
    conn.commit()
    return conn

def save_upload(uploaded_file):
    raw = uploaded_file.getvalue()
    file_hash = hashlib.sha256(raw).hexdigest()[:16]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^A-Za-z0-9_. -]", "_", uploaded_file.name)
    path = UPLOAD_DIR / f"{stamp}_{file_hash}_{safe_name}"
    path.write_bytes(raw)
    conn = db()
    conn.execute(
        "INSERT INTO uploads (uploaded_at, file_name, saved_path, file_hash, notes) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), uploaded_file.name, str(path), file_hash, "")
    )
    conn.commit()
    conn.close()
    return path

def history_df():
    conn = db()
    df = pd.read_sql_query("SELECT uploaded_at, file_name, file_hash, saved_path FROM uploads ORDER BY id DESC", conn)
    conn.close()
    return df

def normalize_col(c):
    return str(c).strip()

def read_workbook(path):
    xl = pd.ExcelFile(path)
    sheets = {}
    for s in xl.sheet_names:
        try:
            df = pd.read_excel(path, sheet_name=s)
            df.columns = [normalize_col(c) for c in df.columns]
            sheets[s] = df
        except Exception:
            sheets[s] = pd.DataFrame()
    return sheets

def find_sheet(sheets, names):
    lookup = {k.lower().strip(): k for k in sheets.keys()}
    for n in names:
        if n.lower().strip() in lookup:
            return lookup[n.lower().strip()]
    for k in sheets.keys():
        kl = k.lower()
        if any(n.lower() in kl for n in names):
            return k
    return None

def find_col(df, names):
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    exact = {str(c).lower().strip(): c for c in cols}
    for n in names:
        if n.lower().strip() in exact:
            return exact[n.lower().strip()]
    for c in cols:
        cl = str(c).lower().strip()
        for n in names:
            if n.lower().strip() in cl:
                return c
    return None

def row_text(row):
    return " ".join([str(v).lower() for v in row.values if pd.notna(v)])

def cadence_from_rank(rank):
    try:
        r = int(float(rank))
        if r <= 20:
            return RULES["top_20_cadence_days"]
        if r <= 60:
            return RULES["rank_21_60_cadence_days"]
    except Exception:
        pass
    return RULES["remaining_cadence_days"]

def clean_zip(value):
    if value is None or pd.isna(value):
        return ""
    match = re.search(r"\b(\d{5})\b", str(value))
    return match.group(1) if match else ""

def infer_route(row, route_col, address_col, city_col, zip_col):
    # Keep an explicit route/pod when the spreadsheet already has one.
    if route_col and pd.notna(row.get(route_col)) and str(row.get(route_col)).strip():
        val = str(row.get(route_col)).strip()
        if val.lower() not in ["nan", "none", "unassigned"]:
            return val

    zip_value = clean_zip(row.get(zip_col)) if zip_col else ""
    if zip_value in ZIP_ROUTE_OVERRIDES:
        return ZIP_ROUTE_OVERRIDES[zip_value]

    city_text = str(row.get(city_col, "")).lower().strip() if city_col else ""
    for city_key, route in CITY_ROUTE_OVERRIDES.items():
        if city_key in city_text:
            return route

    text = " ".join(str(row.get(c, "")) for c in [address_col, city_col, zip_col] if c).lower()
    for route, words in ROUTE_KEYWORDS.items():
        if any(w in text for w in words):
            return route
    return "Unassigned"

def route_sort_value(route):
    return ROUTE_SEQUENCE.get(str(route), 999)

def route_direction_label(route):
    directions = {
        "Carlsbad": "North County coastal. Keep separate from Oceanside/Vista unless needed.",
        "Oceanside / Vista": "North County inland/coastal. Do not mix with Carlsbad by default.",
        "Encinitas North / Carlsbad Fill-in": "Use as Carlsbad fill-in when needed.",
        "Encinitas South / Del Mar / Solana / RSF": "South Encinitas, Del Mar, Solana Beach, Rancho Santa Fe.",
        "San Marcos / Escondido": "North inland route.",
        "Poway / Ramona": "Poway route; Ramona quarterly and never grouped with Pod 4.",
        "Rancho Bernardo / 4S / Carmel Mountain / Mira Mesa": "Fill-in route between 4S, Poway, Carmel Mountain, and Mira Mesa.",
        "Kearny Mesa / Clairemont / Serra Mesa": "Central cluster with many offices; good filler route from North Park.",
        "La Jolla / UTC": "Office/UTC route.",
        "Hillcrest / North Park / Central": "Closest-to-home central route.",
        "Coronado / Downtown": "Downtown/Coronado route.",
        "Chula Vista / South Bay": "South Bay route.",
        "El Cajon / Rancho San Diego": "East County route; pairs El Cajon with Rancho San Diego.",
        "La Mesa / Lemon Grove / Spring Valley": "East/Central route; do not mix with Santee by default.",
        "Santee / Tierrasanta": "Santee pairs with Tierrasanta.",
    }
    return directions.get(str(route), "Needs review; app could not confidently assign a route cluster.")

def score_from_referrals(row, cols):
    total = 0
    for c in cols:
        if c and pd.notna(row.get(c)):
            try:
                total += float(row.get(c))
            except Exception:
                pass
    return total

def prepare_data(sheets):
    doctor_sheet = find_sheet(sheets, ["Doctors", "Doctor", "Master", "Master Report"])
    visit_sheet = find_sheet(sheets, ["Visits", "Visit", "Activity", "Activities"])

    if not doctor_sheet:
        raise ValueError("No Doctors sheet found. The upload needs a Doctors/Master sheet.")

    doctors = sheets[doctor_sheet].copy()
    visits = sheets.get(visit_sheet, pd.DataFrame()).copy() if visit_sheet else pd.DataFrame()

    name_col = find_col(doctors, ["Doctor Name", "Provider Name", "Doctor", "Provider", "Name"])
    practice_col = find_col(doctors, ["Practice Name", "Practice", "Account Name", "Office"])
    address_col = find_col(doctors, ["Practice Address", "Address", "Street Address", "Location"])
    city_col = find_col(doctors, ["City"])
    zip_col = find_col(doctors, ["Zip", "Zip Code", "Postal Code"])
    notes_col = find_col(doctors, ["Notes", "Note", "Visit Notes", "Account Notes"])
    route_col = find_col(doctors, ["Route Cluster", "Route", "Territory", "Pod", "Area"])
    rank_col = find_col(doctors, ["Referral Rank", "Rank", "2026 Rank", "Ref Rank"])
    last_visit_col = find_col(doctors, ["Last Visit Date", "Last Visit", "Most Recent Visit", "Last Activity"])
    ref2026_col = find_col(doctors, ["2026 referrals", "2026 Referrals", "2026", "YTD Referrals", "Current Year Referrals"])
    ref2025_col = find_col(doctors, ["2025 referrals", "2025 Referrals", "2025", "Prior Year Referrals"])
    routable_col = find_col(doctors, ["Routable", "Routable?", "Visit", "Visit?", "Active"])

    if not name_col:
        raise ValueError("Could not find the doctor/provider name column.")

    out = doctors.copy()
    out["_Doctor Name"] = out[name_col].astype(str).str.strip()
    out["_Practice Name"] = out[practice_col].astype(str).str.strip() if practice_col else ""
    out["_Practice Address"] = out[address_col].astype(str).str.strip() if address_col else ""
    out["_City"] = out[city_col].astype(str).str.strip() if city_col else ""
    out["_Zip"] = out[zip_col].astype(str).str.strip() if zip_col else ""
    out["_Notes"] = out[notes_col].astype(str) if notes_col else ""

    if rank_col:
        out["_Priority Rank"] = pd.to_numeric(out[rank_col], errors="coerce").fillna(9999).astype(int)
    else:
        out["_Referral Score"] = out.apply(lambda r: score_from_referrals(r, [ref2026_col, ref2025_col]), axis=1)
        out["_Priority Rank"] = out["_Referral Score"].rank(method="first", ascending=False).astype(int)

    out["_Route Cluster"] = out.apply(lambda r: infer_route(r, route_col, address_col, city_col, zip_col), axis=1)
    out["_Route Sort"] = out["_Route Cluster"].apply(route_sort_value)
    out["_Route Guidance"] = out["_Route Cluster"].apply(route_direction_label)

    out["_Last Visit"] = pd.NaT
    if last_visit_col:
        out["_Last Visit"] = pd.to_datetime(out[last_visit_col], errors="coerce")

    if not visits.empty:
        v_name = find_col(visits, ["Doctor Name", "Provider Name", "Doctor", "Provider", "Name"])
        v_date = find_col(visits, ["Visit Date", "Date", "Activity Date", "Last Visit"])
        if v_name and v_date:
            temp = visits[[v_name, v_date]].copy()
            temp[v_date] = pd.to_datetime(temp[v_date], errors="coerce")
            latest = temp.dropna(subset=[v_date]).groupby(temp[v_name].astype(str).str.strip())[v_date].max()
            mapped = out["_Doctor Name"].map(latest)
            out.loc[mapped.notna(), "_Last Visit"] = mapped[mapped.notna()]

    all_text = out.apply(row_text, axis=1)
    out["_Excluded Reason"] = ""
    for kw in RULES["excluded_keywords"]:
        mask = all_text.str.contains(re.escape(kw), na=False)
        out.loc[mask & (out["_Excluded Reason"] == ""), "_Excluded Reason"] = kw

    if routable_col:
        no_mask = out[routable_col].astype(str).str.lower().str.strip().isin(["no", "n", "false", "0", "not routable", "do not visit"])
        out.loc[no_mask & (out["_Excluded Reason"] == ""), "_Excluded Reason"] = "marked not routable"

    out["_Routable"] = out["_Excluded Reason"].eq("")
    out["_Cadence Days"] = out["_Priority Rank"].apply(cadence_from_rank)

    today = pd.Timestamp(date.today())
    out["_Next Due"] = out["_Last Visit"] + pd.to_timedelta(out["_Cadence Days"], unit="D")
    out.loc[out["_Last Visit"].isna(), "_Next Due"] = today
    out["_Days Overdue"] = (today - out["_Next Due"]).dt.days

    out["_Due Status"] = "Not Due"
    out.loc[out["_Next Due"] <= today + pd.Timedelta(days=RULES["due_lookahead_days"]), "_Due Status"] = "Due Soon"
    out.loc[out["_Next Due"] <= today, "_Due Status"] = "Overdue"
    out.loc[out["_Last Visit"].isna(), "_Due Status"] = "No Visit History"

    return out

def parse_dates(text):
    dates = set()
    for part in re.split(r"[,\n;]+", text or ""):
        part = part.strip()
        if not part:
            continue
        try:
            dates.add(pd.to_datetime(part).date())
        except Exception:
            pass
    return dates

def parse_locks(text):
    locks = {}
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        name, raw_date = line.split("=", 1)
        try:
            locks[name.strip().lower()] = pd.to_datetime(raw_date.strip()).date()
        except Exception:
            pass
    return locks

def workdays_for_month(year, month, blocked_dates):
    days = []
    _, last = calendar.monthrange(year, month)
    for d in range(1, last + 1):
        dt = date(year, month, d)
        if dt.weekday() < 5 and dt not in blocked_dates:
            days.append(dt)
    return days

def assign_stop_order(day_df):
    if day_df.empty:
        return day_df
    ordered = day_df.copy()
    ordered["_Local Sort"] = ordered["Zip"].apply(clean_zip)
    ordered = ordered.sort_values(["Route Sort", "_Local Sort", "Priority Rank", "Doctor Name"], ascending=[True, True, True, True])
    ordered["Stop #"] = range(1, len(ordered) + 1)
    return ordered.drop(columns=["_Local Sort"], errors="ignore")

def office_day_row(visit_date):
    return {
        "Date": visit_date,
        "Day": visit_date.strftime("%A"),
        "Stop #": "",
        "Doctor Name": "OFFICE DAY",
        "Practice Name": "Gordon Schanzlin New Vision Institute",
        "Practice Address": "",
        "City": "La Jolla",
        "Zip": "",
        "Route Cluster": "La Jolla / UTC",
        "Route Sort": route_sort_value("La Jolla / UTC"),
        "Route Guidance": "Office/admin day; no field route scheduled unless you manually add one.",
        "Priority Rank": "",
        "Last Visit": "",
        "Next Due": "",
        "Due Status": "Office Day",
        "Planner Note": "Auto-added Monday office day",
        "Visit Completed": "",
        "Updated Notes": "",
    }

def schedule_row(row, visit_date, note=""):
    last_visit = row["_Last Visit"]
    next_due = row["_Next Due"]
    return {
        "Date": visit_date,
        "Day": visit_date.strftime("%A"),
        "Stop #": "",
        "Doctor Name": row["_Doctor Name"],
        "Practice Name": row["_Practice Name"],
        "Practice Address": row["_Practice Address"],
        "City": row["_City"],
        "Zip": row["_Zip"],
        "Route Cluster": row["_Route Cluster"],
        "Route Sort": int(row["_Route Sort"]) if pd.notna(row["_Route Sort"]) else 999,
        "Route Guidance": row.get("_Route Guidance", route_direction_label(row["_Route Cluster"])),
        "Priority Rank": int(row["_Priority Rank"]) if pd.notna(row["_Priority Rank"]) else "",
        "Last Visit": last_visit.date() if pd.notna(last_visit) else "",
        "Next Due": next_due.date() if pd.notna(next_due) else "",
        "Due Status": row["_Due Status"],
        "Planner Note": note,
        "Visit Completed": "",
        "Updated Notes": "",
    }

def generate_month(doctors, year, month, blocked_dates, locks, max_per_day, monday_office_day=True, target_per_day=None):
    target_per_day = target_per_day or RULES["target_offices_per_day"]
    min_per_day = RULES["min_offices_per_day"]

    due = doctors[
        doctors["_Routable"] &
        doctors["_Due Status"].isin(["Overdue", "Due Soon", "No Visit History"])
    ].copy()

    due["_Sort Overdue"] = pd.to_numeric(due.get("_Days Overdue", 0), errors="coerce").fillna(-9999)
    due = due.sort_values(
        ["_Route Sort", "_Priority Rank", "_Sort Overdue", "_Doctor Name"],
        ascending=[True, True, False, True]
    )

    rows = []
    scheduled_names = set()

    days = workdays_for_month(year, month, blocked_dates)
    if monday_office_day:
        for dt in days:
            if dt.weekday() == 0:
                rows.append(office_day_row(dt))

    field_days = [dt for dt in days if not (monday_office_day and dt.weekday() == 0)]

    # Apply doctor/date locks first.
    for key, lock_date in locks.items():
        matches = due[due["_Doctor Name"].str.lower().str.contains(re.escape(key), na=False)]
        for _, r in matches.iterrows():
            nm = r["_Doctor Name"]
            if nm not in scheduled_names:
                rows.append(schedule_row(r, lock_date, "Locked by user"))
                scheduled_names.add(nm)

    remaining = due[~due["_Doctor Name"].isin(scheduled_names)].copy()

    locked_counts = {}
    for r in rows:
        if r["Doctor Name"] != "OFFICE DAY":
            locked_counts[r["Date"]] = locked_counts.get(r["Date"], 0) + 1

    # Fill each field day to a usable count. Stay in the same route pod when possible,
    # but do not leave a day with only 1-2 stops when other due doctors are available.
    for dt in field_days:
        if remaining.empty:
            break

        already_on_day = locked_counts.get(dt, 0)
        available = max_per_day - already_on_day
        if available <= 0:
            continue

        target_for_day = min(target_per_day, available)
        if len(remaining) <= target_for_day:
            take_indexes = list(remaining.index)
        else:
            primary_route = remaining.iloc[0]["_Route Cluster"]
            same_route = list(remaining[remaining["_Route Cluster"] == primary_route].index[:target_for_day])
            take_indexes = same_route

            # If a pod only has a few due offices, top off the day with the next best nearby/priority offices.
            desired_min = min(min_per_day, target_for_day, len(remaining))
            if len(take_indexes) < desired_min:
                for idx in remaining.index:
                    if idx not in take_indexes:
                        take_indexes.append(idx)
                    if len(take_indexes) >= target_for_day:
                        break

        day_rows = remaining.loc[take_indexes]
        route_count = day_rows["_Route Cluster"].nunique()
        note = "Smart grouped by route/priority" if route_count == 1 else "Route topped off to avoid a light day"

        for _, rr in day_rows.iterrows():
            rows.append(schedule_row(rr, dt, note))
            scheduled_names.add(rr["_Doctor Name"])

        remaining = remaining.drop(index=take_indexes, errors="ignore")

    schedule = pd.DataFrame(rows)
    if not schedule.empty:
        ordered_days = []
        for _, day_df in schedule.groupby("Date", sort=True):
            if (day_df["Doctor Name"] == "OFFICE DAY").all():
                ordered_days.append(day_df)
            else:
                ordered_days.append(assign_stop_order(day_df))
        schedule = pd.concat(ordered_days, ignore_index=True)
        schedule["_Stop Sort"] = pd.to_numeric(schedule["Stop #"], errors="coerce").fillna(0)
        schedule = schedule.sort_values(["Date", "_Stop Sort", "Route Sort", "Priority Rank", "Doctor Name"], na_position="last").drop(columns=["_Stop Sort"]).reset_index(drop=True)

    return schedule, due

def export_excel(schedule, due, excluded):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        schedule.to_excel(writer, sheet_name="Monthly Schedule", index=False)
        due.to_excel(writer, sheet_name="Due Doctors", index=False)
        excluded.to_excel(writer, sheet_name="Excluded", index=False)

        # Plain, clean Excel output. No color formatting.
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for row in ws.iter_rows():
                for cell in row:
                    cell.alignment = cell.alignment.copy(wrap_text=True, vertical="top")
            for col in ws.columns:
                letter = col[0].column_letter
                max_len = max([len(str(c.value)) if c.value is not None else 0 for c in col] + [8])
                ws.column_dimensions[letter].width = min(max(max_len + 2, 10), 38)

    output.seek(0)
    return output

def downloadable_history_zip():
    # Lightweight backup of uploaded files + sqlite db, when available.
    import zipfile
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        if DB_PATH.exists():
            z.write(DB_PATH, "app_history.sqlite")
        for p in UPLOAD_DIR.glob("*"):
            z.write(p, f"uploads/{p.name}")
    output.seek(0)
    return output

def public_site_warning():
    st.info(
        "This is built for free website hosting. On free Streamlit hosting, uploads are saved for app use, "
        "but free cloud storage can reset. Use the backup download if you want to preserve upload history outside the site."
    )

st.title(APP_TITLE)
st.caption("Upload visit reports, enforce visit rules, generate a full-month territory schedule, and export Excel.")

with st.sidebar:
    st.header("Month Setup")
    today = date.today()
    selected_year = st.number_input("Year", min_value=2024, max_value=2035, value=today.year, step=1)
    selected_month = st.selectbox(
        "Month",
        options=list(range(1, 13)),
        index=today.month - 1,
        format_func=lambda m: calendar.month_name[m],
    )

    st.header("Calendar Control")
    blocked_text = st.text_area(
        "Blocked dates",
        placeholder="One per line:\n2026-07-03\n2026-07-14",
        help="Use this for office days, PTO, CE events, or days you do not want field visits."
    )
    lock_text = st.text_area(
        "Doctor/date locks",
        placeholder="One per line:\nDorothy Wang = 2026-07-31\nClarke = 2026-07-08",
        help="Use any searchable part of the doctor's name."
    )
    max_per_day = st.slider("Max offices per field day", 6, 10, RULES["target_offices_per_day"])

    st.header("Rules")
    st.write(f"Start/end base: **{RULES['home_base']}**")
    st.write("Top 20: monthly")
    st.write("Rank 21–60: every 6 weeks")
    st.write("Remaining: quarterly")
    monday_office_day = st.checkbox("Auto-block Mondays as La Jolla office days", value=True)
    st.caption("v2 adds smarter San Diego route pods and suggested stop order. Maps come next.")

tab_upload, tab_plan, tab_history, tab_rules = st.tabs(["Upload", "Plan Month", "Upload History", "Rules"])

with tab_upload:
    public_site_warning()
    uploaded = st.file_uploader("Upload current visit report Excel file", type=["xlsx", "xlsm", "xls"])

    if uploaded:
        try:
            saved_path = save_upload(uploaded)
            sheets = read_workbook(saved_path)
            doctors = prepare_data(sheets)
            st.session_state["sheets"] = sheets
            st.session_state["doctors"] = doctors
            st.session_state["latest_upload_path"] = str(saved_path)

            st.success("Upload read successfully.")

            summary = pd.DataFrame(
                [{"Sheet": name, "Rows": len(df), "Columns": len(df.columns)} for name, df in sheets.items()]
            )
            st.subheader("Workbook tabs found")
            st.dataframe(summary, use_container_width=True, hide_index=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total rows", len(doctors))
            c2.metric("Routable", int(doctors["_Routable"].sum()))
            c3.metric("Excluded", int((~doctors["_Routable"]).sum()))
            c4.metric("Due / overdue", int((doctors["_Routable"] & doctors["_Due Status"].isin(["Overdue", "Due Soon", "No Visit History"])).sum()))

            st.subheader("Preview")
            preview_cols = ["_Doctor Name", "_Practice Name", "_Practice Address", "_City", "_Zip", "_Route Cluster", "_Route Guidance", "_Priority Rank", "_Last Visit", "_Next Due", "_Due Status", "_Routable", "_Excluded Reason"]
            st.dataframe(doctors[preview_cols].head(100), use_container_width=True)

        except Exception as e:
            st.error(f"Could not process this workbook: {e}")

with tab_plan:
    if "doctors" not in st.session_state:
        st.warning("Upload a visit report first.")
    else:
        doctors = st.session_state["doctors"]
        blocked_dates = parse_dates(blocked_text)
        locks = parse_locks(lock_text)

        if st.button("Generate full-month schedule", type="primary"):
            schedule, due = generate_month(doctors, int(selected_year), int(selected_month), blocked_dates, locks, int(max_per_day), monday_office_day=monday_office_day)
            st.session_state["schedule"] = schedule
            st.session_state["due"] = due

        if "schedule" in st.session_state:
            schedule = st.session_state["schedule"]
            due = st.session_state["due"]
            excluded = doctors[~doctors["_Routable"]].copy()

            if schedule.empty:
                st.warning("No due doctors found for the selected month/rules.")
            else:
                st.subheader("Editable monthly schedule")
                st.caption("Make changes here before exporting. The exported Excel has blank columns for visit completion and updated notes.")
                edited = st.data_editor(schedule, use_container_width=True, num_rows="dynamic", key="schedule_editor")

                st.subheader("Daily counts")
                counts = edited.groupby(["Date", "Day"]).size().reset_index(name="Office Count")
                st.dataframe(counts, use_container_width=True, hide_index=True)

                export = export_excel(
                    edited,
                    due[["_Doctor Name", "_Practice Name", "_Practice Address", "_City", "_Zip", "_Route Cluster", "_Route Guidance", "_Priority Rank", "_Last Visit", "_Next Due", "_Due Status", "_Days Overdue", "_Notes"]],
                    excluded[["_Doctor Name", "_Practice Name", "_Practice Address", "_City", "_Zip", "_Route Cluster", "_Route Guidance", "_Excluded Reason", "_Notes"]],
                )
                file_name = f"territory_monthly_schedule_{selected_year}_{int(selected_month):02d}.xlsx"
                st.download_button(
                    "Download Excel schedule",
                    data=export,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

with tab_history:
    st.subheader("Saved uploads")
    hist = history_df()
    if hist.empty:
        st.caption("No upload history yet.")
    else:
        st.dataframe(hist[["uploaded_at", "file_name", "file_hash"]], use_container_width=True, hide_index=True)
        backup = downloadable_history_zip()
        st.download_button(
            "Download upload-history backup",
            data=backup,
            file_name="territory_route_planner_upload_history_backup.zip",
            mime="application/zip"
        )

with tab_rules:
    st.subheader("Current rules in this app")
    st.json(RULES)

    st.subheader("Route order")
    st.json(ROUTE_ORDER)

    st.subheader("Route grouping keywords")
    st.json(ROUTE_KEYWORDS)

    st.subheader("ZIP route overrides")
    st.json(ZIP_ROUTE_OVERRIDES)

    st.caption("These rules are code-based so they do not drift between uploads.")
