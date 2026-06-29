
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
    "Encinitas / Del Mar / Solana / RSF": ["encinitas", "del mar", "solana beach", "rancho santa fe", "rsf"],
    "San Marcos / Escondido": ["san marcos", "escondido"],
    "Poway / Ramona": ["poway", "ramona"],
    "Rancho Bernardo / 4S / Mira Mesa": ["rancho bernardo", "4s", "carmel mountain", "mira mesa"],
    "Kearny Mesa / Clairemont / Serra Mesa": ["kearny", "clairemont", "serra mesa"],
    "La Mesa / Lemon Grove / Spring Valley": ["la mesa", "lemon grove", "spring valley"],
    "El Cajon / Rancho San Diego": ["el cajon", "rancho san diego"],
    "Santee / Tierrasanta": ["santee", "tierrasanta"],
    "Coronado / Downtown": ["coronado", "downtown", "92101"],
    "Chula Vista / South Bay": ["chula vista", "national city", "bonita", "eastlake", "south bay"],
    "La Jolla / UTC": ["la jolla", "utc", "university city"],
    "Hillcrest / North Park / Central": ["hillcrest", "north park", "mission hills", "bankers hill"],
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

def infer_route(row, route_col, address_col, city_col, zip_col):
    if route_col and pd.notna(row.get(route_col)) and str(row.get(route_col)).strip():
        val = str(row.get(route_col)).strip()
        if val.lower() not in ["nan", "none", "unassigned"]:
            return val
    text = " ".join(str(row.get(c, "")) for c in [address_col, city_col, zip_col] if c).lower()
    for route, words in ROUTE_KEYWORDS.items():
        if any(w in text for w in words):
            return route
    return "Unassigned"

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

def schedule_row(row, visit_date, note=""):
    last_visit = row["_Last Visit"]
    next_due = row["_Next Due"]
    return {
        "Date": visit_date,
        "Day": visit_date.strftime("%A"),
        "Doctor Name": row["_Doctor Name"],
        "Practice Name": row["_Practice Name"],
        "Practice Address": row["_Practice Address"],
        "City": row["_City"],
        "Zip": row["_Zip"],
        "Route Cluster": row["_Route Cluster"],
        "Priority Rank": int(row["_Priority Rank"]) if pd.notna(row["_Priority Rank"]) else "",
        "Last Visit": last_visit.date() if pd.notna(last_visit) else "",
        "Next Due": next_due.date() if pd.notna(next_due) else "",
        "Due Status": row["_Due Status"],
        "Planner Note": note,
        "Visit Completed": "",
        "Updated Notes": "",
    }

def generate_month(doctors, year, month, blocked_dates, locks, max_per_day):
    due = doctors[
        doctors["_Routable"] &
        doctors["_Due Status"].isin(["Overdue", "Due Soon", "No Visit History"])
    ].copy()

    if due.empty:
        return pd.DataFrame(), due

    due["_Sort Overdue"] = pd.to_numeric(due["_Days Overdue"], errors="coerce").fillna(-9999)
    due = due.sort_values(
        ["_Priority Rank", "_Sort Overdue", "_Route Cluster", "_Doctor Name"],
        ascending=[True, False, True, True]
    )

    rows = []
    scheduled_names = set()

    # Apply doctor/date locks first.
    for key, lock_date in locks.items():
        matches = due[due["_Doctor Name"].str.lower().str.contains(re.escape(key), na=False)]
        for _, r in matches.iterrows():
            nm = r["_Doctor Name"]
            if nm not in scheduled_names:
                rows.append(schedule_row(r, lock_date, "Locked by user"))
                scheduled_names.add(nm)

    remaining = due[~due["_Doctor Name"].isin(scheduled_names)].copy()

    days = workdays_for_month(year, month, blocked_dates)
    # Avoid days already filled by locks when possible.
    locked_counts = {}
    for r in rows:
        locked_counts[r["Date"]] = locked_counts.get(r["Date"], 0) + 1

    day_idx = 0
    grouped = remaining.groupby("_Route Cluster", sort=True)

    for route, group in grouped:
        group = group.sort_values(["_Priority Rank", "_Sort Overdue"], ascending=[True, False])
        chunk = []
        for _, r in group.iterrows():
            chunk.append(r)
            if len(chunk) >= max_per_day:
                while day_idx < len(days) and locked_counts.get(days[day_idx], 0) >= max_per_day:
                    day_idx += 1
                if day_idx >= len(days):
                    break
                dt = days[day_idx]
                for rr in chunk:
                    rows.append(schedule_row(rr, dt, "Smart grouped by route/priority"))
                day_idx += 1
                chunk = []
        if chunk:
            while day_idx < len(days) and locked_counts.get(days[day_idx], 0) >= max_per_day:
                day_idx += 1
            if day_idx < len(days):
                dt = days[day_idx]
                for rr in chunk:
                    rows.append(schedule_row(rr, dt, "Smart grouped by route/priority"))
                day_idx += 1

        if day_idx >= len(days):
            break

    schedule = pd.DataFrame(rows)
    if not schedule.empty:
        schedule = schedule.sort_values(["Date", "Route Cluster", "Priority Rank", "Doctor Name"]).reset_index(drop=True)

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
    st.write("No maps/driving order in this version")

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
            preview_cols = ["_Doctor Name", "_Practice Name", "_Practice Address", "_City", "_Zip", "_Route Cluster", "_Priority Rank", "_Last Visit", "_Next Due", "_Due Status", "_Routable", "_Excluded Reason"]
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
            schedule, due = generate_month(doctors, int(selected_year), int(selected_month), blocked_dates, locks, int(max_per_day))
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
                edited = st.data_editor(schedule, use_container_width=True, num_rows="dynamic", key="edited_schedule")
                st.session_state["edited_schedule"] = edited

                st.subheader("Daily counts")
                counts = edited.groupby(["Date", "Day"]).size().reset_index(name="Office Count")
                st.dataframe(counts, use_container_width=True, hide_index=True)

                export = export_excel(
                    edited,
                    due[["_Doctor Name", "_Practice Name", "_Practice Address", "_City", "_Zip", "_Route Cluster", "_Priority Rank", "_Last Visit", "_Next Due", "_Due Status", "_Days Overdue", "_Notes"]],
                    excluded[["_Doctor Name", "_Practice Name", "_Practice Address", "_City", "_Zip", "_Route Cluster", "_Excluded Reason", "_Notes"]],
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

    st.subheader("Route grouping keywords")
    st.json(ROUTE_KEYWORDS)

    st.caption("These rules are code-based for this first version so they do not drift between uploads.")
