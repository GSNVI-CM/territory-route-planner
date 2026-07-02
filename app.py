
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
    "Encinitas Split Review": ["north encinitas", "leucadia", "encinitas"],
    "Del Mar / Solana / South Encinitas": ["south encinitas", "del mar", "carmel valley"],
    "Solana Beach / Rancho Santa Fe / Fallbrook": ["solana beach", "rancho santa fe", "rsf", "fallbrook"],
    "Escondido / San Marcos": ["san marcos", "escondido"],
    "Poway / Ramona": ["poway", "ramona"],
    "CM / 4S / Scripps / RB": ["carmel mountain", "4s", "scripps", "rancho bernardo", "rb"],
    "Mira Mesa": ["mira mesa"],
    "Mission Valley / Kearny Mesa / Clairemont": ["mission valley", "kearny", "clairemont", "serra mesa"],
    "UTC / La Jolla / Sorrento Valley": ["la jolla", "utc", "university city", "sorrento valley"],
    "Downtown / Coronado / Hillcrest": ["downtown", "coronado", "hillcrest", "north park", "mission hills", "bankers hill", "92101"],
    "Sports Arena / Point Loma / Bay Park": ["sports arena", "point loma", "bay park", "92110"],
    "Chula Vista / National City": ["chula vista", "national city", "south bay"],
    "Eastlake / Otay": ["eastlake", "otay"],
    "Bonita / Rancho del Rey": ["bonita", "rancho del rey"],
    "El Cajon / Rancho San Diego": ["el cajon", "rancho san diego"],
    "La Mesa / Lemon Grove / Spring Valley": ["la mesa", "lemon grove", "spring valley"],
    "Santee / Tierrasanta": ["santee", "tierrasanta"],
}

ROUTE_ORDER = [
    'Rancho Bernardo',
    '4S',
    'Carmel Mountain',
    'Poway',
    'Mira Mesa',
    'Scripps Ranch',
    'Point Loma',
    'Ocean Beach',
    'Pacific Beach',
    'Sports Arena',
    'Mission Valley',
    'Linda Vista',
    'Clairemont',
    'Kearny Mesa',
    'College Area',
    'UTC',
    'La Jolla',
    'Sorrento Valley',
    'Del Mar',
    'Solana Beach',
    'Rancho Santa Fe',
    'Encinitas',
    'Fallbrook',
    'Carlsbad',
    'Oceanside / Vista',
    'Escondido / San Marcos',
    'Santee',
    'La Mesa',
    'Lemon Grove',
    'Spring Valley',
    'Chula Vista / National City',
    'Eastlake / Otay',
    'Bonita / Rancho del Rey',
    'El Cajon / Rancho San Diego',
    'Downtown / Coronado / Hillcrest',
    'Do Not Route',
    'Needs Review',
    'Out of Territory',
    'Unassigned',
]

ROUTE_ALIASES = {
    'rancho bernardo / 4s / carmel mountain / mira mesa': 'CM / 4S / Scripps / RB',
    'carmel mountain / 4s / scripps / rb': 'CM / 4S / Scripps / RB',
    'cm / 4s / scripps / rb': 'CM / 4S / Scripps / RB',
    'kearny mesa / clairemont / serra mesa': 'Mission Valley / Kearny Mesa / Clairemont',
    'la jolla / utc': 'UTC / La Jolla / Sorrento Valley',
    'coronado / downtown': 'Downtown / Coronado / Hillcrest',
    'hillcrest / north park / central': 'Downtown / Coronado / Hillcrest',
    'chula vista / south bay': 'Chula Vista / National City',
    'san marcos / escondido': 'Escondido / San Marcos',
    'encinitas south / del mar / solana / rsf': 'Del Mar / Solana / South Encinitas',
    'rancho bernardo': 'Rancho Bernardo',
    '4s': '4S',
    'carmel mountain': 'Carmel Mountain',
    'poway': 'Poway',
    'mira mesa': 'Mira Mesa',
    'scripps ranch': 'Scripps Ranch',
    'point loma': 'Point Loma',
    'ocean beach': 'Ocean Beach',
    'pacific beach': 'Pacific Beach',
    'sports arena': 'Sports Arena',
    'mission valley': 'Mission Valley',
    'linda vista': 'Linda Vista',
    'clairemont': 'Clairemont',
    'kearny mesa': 'Kearny Mesa',
    'college area': 'College Area',
    'utc': 'UTC',
    'la jolla': 'La Jolla',
    'sorrento valley': 'Sorrento Valley',
    'del mar': 'Del Mar',
    'solana beach': 'Solana Beach',
    'rancho santa fe': 'Rancho Santa Fe',
    'encinitas': 'Encinitas',
    'fallbrook': 'Fallbrook',
    'carlsbad': 'Carlsbad',
    'oceanside / vista': 'Oceanside / Vista',
    'escondido / san marcos': 'Escondido / San Marcos',
    'santee': 'Santee',
    'la mesa': 'La Mesa',
    'lemon grove': 'Lemon Grove',
    'spring valley': 'Spring Valley',
    'chula vista / national city': 'Chula Vista / National City',
    'eastlake / otay': 'Eastlake / Otay',
    'bonita / rancho del rey': 'Bonita / Rancho del Rey',
    'el cajon / rancho san diego': 'El Cajon / Rancho San Diego',
    'downtown / coronado / hillcrest': 'Downtown / Coronado / Hillcrest',
    'do not route': 'Do Not Route',
    'needs review': 'Needs Review',
    'out of territory': 'Out of Territory',
    'unassigned': 'Unassigned',
}

DOCTOR_ROUTE_OVERRIDES = {
    'Abbott, Christopher'.lower(): 'Santee',
    'Albers, Harry'.lower(): 'UTC',
    'Apostolides, John'.lower(): 'Point Loma',
    'Austin, Scott'.lower(): 'Sports Arena',
    'Bajpai, Abishek'.lower(): 'Mission Valley',
    'Bende, Lori'.lower(): 'UTC',
    'Berkowitz, Carla'.lower(): 'Sorrento Valley',
    'Boeck, Carl'.lower(): 'Kearny Mesa',
    'Camen, Jesse'.lower(): 'Mission Valley',
    'Cao, Duyen'.lower(): 'Carlsbad',
    'Cauchi, Caroline'.lower(): 'La Mesa',
    'Chen, Edwin S'.lower(): 'College Area',
    'Chen, Oliver'.lower(): 'Carlsbad',
    'Cheng, Patty'.lower(): 'Rancho Bernardo',
    'Chisholm, Karen'.lower(): 'Point Loma',
    'Chung, Allen'.lower(): 'Mira Mesa',
    'Coden, Daniel'.lower(): 'Do Not Route',
    'Coleman, Brooke'.lower(): '4S',
    'Cooper, Michael'.lower(): '4S',
    'Cullins ( Monaco), Rosina'.lower(): 'College Area',
    'Darrow, Irina'.lower(): 'Mission Valley',
    'Dexter, Amanda'.lower(): 'Del Mar',
    'Diaz, Yvette'.lower(): 'Santee',
    'Dr. Denis Iwamoto'.lower(): 'Mira Mesa',
    'Dr. Eli Ben-Moshe'.lower(): 'Ocean Beach',
    'Dr. Shervin Alborzian'.lower(): 'UTC',
    'Dr. Victoria Voung'.lower(): 'Santee',
    'Dr. Viet Nguyen'.lower(): 'College Area',
    'Eck, Thomas'.lower(): 'Sports Arena',
    'Fitzpatrick, Michelle'.lower(): 'Carmel Mountain',
    'Fleming, John C'.lower(): 'Spring Valley',
    'Gentile, Matthew'.lower(): 'UTC',
    'Giang, Steven'.lower(): 'Sports Arena',
    'Goode, Korrin'.lower(): 'Rancho Bernardo',
    'Grazian, Robert'.lower(): 'Santee',
    'Guarneri, Erminia Mimi'.lower(): 'La Jolla',
    'Hayes, Greg'.lower(): 'Rancho Bernardo',
    'Hirmiz, Austin'.lower(): 'UTC',
    'Homesley, Susan'.lower(): 'Poway',
    'Hosn, Ryan'.lower(): 'La Mesa',
    'Huang, Flora'.lower(): 'Lemon Grove',
    'Huynh, Chi'.lower(): 'Mira Mesa',
    'Kartsonis, Louis'.lower(): 'Pacific Beach',
    'Kasanoff, David'.lower(): 'La Mesa',
    'Kashak, Vanessa'.lower(): 'Carlsbad',
    'Kavanagh, Cecilia'.lower(): 'Carlsbad',
    'Kim, Joanne'.lower(): 'Clairemont',
    'Kirk, Matthew'.lower(): 'Do Not Route',
    'Kolodzey, Elizabeth'.lower(): 'Point Loma',
    'Langford, Matthew'.lower(): 'Clairemont',
    'Langford, Melanie'.lower(): 'Clairemont',
    'Lee, Joyce'.lower(): 'Sports Arena',
    'Lee, Nathan'.lower(): 'Clairemont',
    'Li, Natalie'.lower(): '4S',
    'Liu, Ying'.lower(): 'UTC',
    'Luna, Fabian'.lower(): 'Mira Mesa',
    'Luskin, Stephen'.lower(): 'Carlsbad',
    'Ma, Shan'.lower(): 'Mira Mesa',
    'Makor, Monvelea'.lower(): 'Santee',
    'Mallari, Janel'.lower(): 'Del Mar',
    'Marbun, Riolan'.lower(): 'Kearny Mesa',
    'Markson, Anna'.lower(): 'UTC',
    'Mashouf, Jay'.lower(): 'Poway',
    'Master, Ramona'.lower(): 'UTC',
    'Monck, Tammy'.lower(): 'Clairemont',
    'Morgan, Hunter'.lower(): 'Carlsbad',
    'Moss, Jason'.lower(): 'College Area',
    'Nahl, Angela'.lower(): 'Do Not Route',
    'Nakamura, Yuki'.lower(): 'Carlsbad',
    'Nguyen, Theresa'.lower(): 'Spring Valley',
    'Nguyen, Thu'.lower(): 'Mira Mesa',
    'Niskanen, Rachel'.lower(): 'Carlsbad',
    'Patel, Smit'.lower(): 'Santee',
    'Perey, Dave'.lower(): 'La Mesa',
    'Perry, Arthur'.lower(): 'Do Not Route',
    'Peters, Jamie Starr'.lower(): 'La Mesa',
    'Peterson-Salgado, Kristin'.lower(): 'Solana Beach',
    'Ramolia, Anika'.lower(): 'Carlsbad',
    'Ramos, Eric'.lower(): 'Fallbrook',
    'Reeder, Kevin'.lower(): 'Carmel Mountain',
    'Riggs, John'.lower(): 'Encinitas',
    'Riggs, Kevin'.lower(): 'La Mesa',
    'Ritchken, Simion'.lower(): 'Clairemont',
    'Samuels, Marianna'.lower(): 'Poway',
    'Sandler, Earl'.lower(): 'Carmel Mountain',
    'Sandoc, Emily'.lower(): 'Mission Valley',
    'Shapiro, Elliot'.lower(): 'UTC',
    'Shulkin, Mitchell'.lower(): 'Rancho Bernardo',
    'Solis, Kevin'.lower(): 'Kearny Mesa',
    'Starkey, Elesha'.lower(): 'Carmel Mountain',
    'Sung, Ann'.lower(): 'Poway',
    'Tang, Ashley'.lower(): 'Sports Arena',
    'Tavakoli, Melody'.lower(): 'Pacific Beach',
    'Tayman, Steven'.lower(): 'UTC',
    'Thai, Amanda'.lower(): 'Kearny Mesa',
    'Thiem, Christine'.lower(): 'Sports Arena',
    'Tran, Linda'.lower(): '4S',
    'Tran, Michael'.lower(): 'Poway',
    'Trang, Chau'.lower(): 'Linda Vista',
    'Tu, Jason'.lower(): 'Carmel Mountain',
    'Val, Isabel'.lower(): 'Clairemont',
    'Van Der Linde, Harrison'.lower(): 'Ocean Beach',
    'Van Hoose, Marc'.lower(): 'Kearny Mesa',
    'Varghese, Ashley'.lower(): 'Do Not Route',
    'Wan, Keith'.lower(): 'Poway',
    'Wang, Dorothy'.lower(): 'Carmel Mountain',
    'Wang, Howard'.lower(): 'Carlsbad',
    'Weiss, Lisa'.lower(): 'Rancho Santa Fe',
    'Wesling, Paul'.lower(): 'Lemon Grove',
    'White, Eric'.lower(): 'Kearny Mesa',
    'White, Renee'.lower(): 'Sorrento Valley',
    'Willey, Melissa'.lower(): 'Carlsbad',
    'Wong, Gordon'.lower(): 'La Jolla',
    'Wynnshang, Sun'.lower(): 'UTC',
    'Yang, Diane'.lower(): 'Poway',
    'Yeghiazarian, Mark'.lower(): 'La Mesa',
    'Zarkhina, Darya'.lower(): 'Mission Valley',
}

ROUTE_SEQUENCE = {route: i for i, route in enumerate(ROUTE_ORDER)}

def normalize_route_name(route):
    val = str(route).strip()
    if not val or val.lower() in ["nan", "none"]:
        return "Unassigned"
    return ROUTE_ALIASES.get(val.lower(), val)

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
    "92024": "Encinitas Split Review",
    "92130": "Del Mar / Solana / South Encinitas",
    "92075": "Solana Beach / Rancho Santa Fe / Fallbrook",
    "92091": "Solana Beach / Rancho Santa Fe / Fallbrook",
    "92067": "Solana Beach / Rancho Santa Fe / Fallbrook",
    "92028": "Solana Beach / Rancho Santa Fe / Fallbrook",
    "92069": "Escondido / San Marcos",
    "92078": "Escondido / San Marcos",
    "92025": "Escondido / San Marcos",
    "92026": "Escondido / San Marcos",
    "92027": "Escondido / San Marcos",
    "92029": "Escondido / San Marcos",
    "92064": "Poway / Ramona",
    "92065": "Poway / Ramona",
    "92127": "CM / 4S / Scripps / RB",
    "92128": "CM / 4S / Scripps / RB",
    "92129": "CM / 4S / Scripps / RB",
    "92131": "CM / 4S / Scripps / RB",
    "92126": "Mira Mesa",
    "92123": "Mission Valley / Kearny Mesa / Clairemont",
    "92111": "Mission Valley / Kearny Mesa / Clairemont",
    "92117": "Mission Valley / Kearny Mesa / Clairemont",
    "92108": "Mission Valley / Kearny Mesa / Clairemont",
    "92122": "UTC / La Jolla / Sorrento Valley",
    "92037": "UTC / La Jolla / Sorrento Valley",
    "92093": "UTC / La Jolla / Sorrento Valley",
    "92121": "UTC / La Jolla / Sorrento Valley",
    "92103": "Downtown / Coronado / Hillcrest",
    "92104": "Downtown / Coronado / Hillcrest",
    "92116": "Downtown / Coronado / Hillcrest",
    "92101": "Downtown / Coronado / Hillcrest",
    "92118": "Downtown / Coronado / Hillcrest",
    "92110": "Sports Arena / Point Loma / Bay Park",
    "92106": "Sports Arena / Point Loma / Bay Park",
    "91910": "Chula Vista / National City",
    "91911": "Chula Vista / National City",
    "91950": "Chula Vista / National City",
    "91913": "Eastlake / Otay",
    "91914": "Eastlake / Otay",
    "91915": "Eastlake / Otay",
    "91902": "Bonita / Rancho del Rey",
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
    "encinitas": "Encinitas Split Review",
    "del mar": "Del Mar / Solana / South Encinitas",
    "solana beach": "Solana Beach / Rancho Santa Fe / Fallbrook",
    "rancho santa fe": "Solana Beach / Rancho Santa Fe / Fallbrook",
    "fallbrook": "Solana Beach / Rancho Santa Fe / Fallbrook",
    "san marcos": "Escondido / San Marcos",
    "escondido": "Escondido / San Marcos",
    "poway": "Poway / Ramona",
    "ramona": "Poway / Ramona",
    "rancho bernardo": "CM / 4S / Scripps / RB",
    "scripps ranch": "CM / 4S / Scripps / RB",
    "mira mesa": "Mira Mesa",
    "la jolla": "UTC / La Jolla / Sorrento Valley",
    "university city": "UTC / La Jolla / Sorrento Valley",
    "utc": "UTC / La Jolla / Sorrento Valley",
    "sorrento valley": "UTC / La Jolla / Sorrento Valley",
    "mission valley": "Mission Valley / Kearny Mesa / Clairemont",
    "kearny mesa": "Mission Valley / Kearny Mesa / Clairemont",
    "clairemont": "Mission Valley / Kearny Mesa / Clairemont",
    "sports arena": "Sports Arena / Point Loma / Bay Park",
    "point loma": "Sports Arena / Point Loma / Bay Park",
    "bay park": "Sports Arena / Point Loma / Bay Park",
    "hillcrest": "Downtown / Coronado / Hillcrest",
    "north park": "Downtown / Coronado / Hillcrest",
    "downtown": "Downtown / Coronado / Hillcrest",
    "coronado": "Downtown / Coronado / Hillcrest",
    "chula vista": "Chula Vista / National City",
    "national city": "Chula Vista / National City",
    "eastlake": "Eastlake / Otay",
    "otay": "Eastlake / Otay",
    "bonita": "Bonita / Rancho del Rey",
    "rancho del rey": "Bonita / Rancho del Rey",
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
            return normalize_route_name(val)

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
    return ROUTE_SEQUENCE.get(normalize_route_name(route), 999)

def route_direction_label(route):
    route = normalize_route_name(route)
    directions = {
        "Rancho Bernardo": "Rancho Bernardo working route.",
        "4S": "4S working route.",
        "Carmel Mountain": "Carmel Mountain working route.",
        "Poway": "Poway working route.",
        "Mira Mesa": "Mira Mesa working route.",
        "Scripps Ranch": "Scripps Ranch working route.",
        "Point Loma": "Point Loma working route.",
        "Ocean Beach": "Ocean Beach working route.",
        "Pacific Beach": "Pacific Beach working route.",
        "Sports Arena": "Sports Arena working route.",
        "Mission Valley": "Mission Valley working route.",
        "Linda Vista": "Linda Vista working route.",
        "Clairemont": "Clairemont working route.",
        "Kearny Mesa": "Kearny Mesa working route.",
        "College Area": "College Area working route.",
        "UTC": "UTC working route.",
        "La Jolla": "La Jolla working route.",
        "Sorrento Valley": "Sorrento Valley working route.",
        "Del Mar": "Del Mar working route.",
        "Solana Beach": "Solana Beach working route.",
        "Rancho Santa Fe": "Rancho Santa Fe working route.",
        "Encinitas": "Encinitas working route.",
        "Fallbrook": "Fallbrook working route.",
        "Santee": "Santee working route.",
        "La Mesa": "La Mesa working route.",
        "Lemon Grove": "Lemon Grove working route.",
        "Spring Valley": "Spring Valley working route.",
        "Carlsbad": "Carlsbad route. Keep separate from Oceanside/Vista unless intentionally filling a day.",
        "Oceanside / Vista": "Oceanside and Vista route. Do not mix with Carlsbad by default.",
        "Encinitas Split Review": "Encinitas needs review; split north/south when possible.",
        "Del Mar / Solana / South Encinitas": "Del Mar, Solana, and South Encinitas route.",
        "Solana Beach / Rancho Santa Fe / Fallbrook": "Solana Beach, Rancho Santa Fe, and Fallbrook route.",
        "Escondido / San Marcos": "North inland route for Escondido and San Marcos.",
        "Poway / Ramona": "Poway route; Ramona is quarterly and should stay with Poway.",
        "CM / 4S / Scripps / RB": "Carmel Mountain, 4S, Scripps Ranch, Rancho Bernardo route.",
        "Mira Mesa": "Mira Mesa route; good fill-in with nearby central/north routes when needed.",
        "Mission Valley / Kearny Mesa / Clairemont": "Central route with Mission Valley, Kearny Mesa, and Clairemont.",
        "UTC / La Jolla / Sorrento Valley": "UTC, La Jolla, and Sorrento Valley route.",
        "Sports Arena / Point Loma / Bay Park": "Sports Arena, Point Loma, Bay Park route.",
        "Downtown / Coronado / Hillcrest": "Central/Downtown route including Coronado and Hillcrest.",
        "Chula Vista / National City": "South Bay route for Chula Vista and National City.",
        "Eastlake / Otay": "Eastlake and Otay route.",
        "Bonita / Rancho del Rey": "Bonita and Rancho del Rey route.",
        "El Cajon / Rancho San Diego": "East County route; pairs El Cajon with Rancho San Diego.",
        "La Mesa / Lemon Grove / Spring Valley": "La Mesa, Lemon Grove, and Spring Valley route.",
        "Santee / Tierrasanta": "Santee pairs with Tierrasanta.",
        "Needs Review": "Needs review before routing.",
        "Out of Territory": "Out of territory; should not be scheduled.",
        "Unassigned": "Needs route assignment before routing.",
    }
    return directions.get(route, "Needs review; app could not confidently assign a route cluster.")

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
    correct_route_col = find_col(doctors, ["Correct Route Group", "Correct Route", "Misty Route Group", "Working Route Group"])

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

    out["_Route Cluster"] = out.apply(lambda r: normalize_route_name(infer_route(r, route_col, address_col, city_col, zip_col)), axis=1)

    # User-taught routing: prefer Misty's working route group when present,
    # otherwise use doctor-specific route rules learned from the July schedule corrections.
    if correct_route_col:
        mask = out[correct_route_col].notna() & out[correct_route_col].astype(str).str.strip().ne("")
        out.loc[mask, "_Route Cluster"] = out.loc[mask, correct_route_col].astype(str).str.strip().apply(normalize_route_name)

    out["_Doctor Key"] = out["_Doctor Name"].astype(str).str.strip().str.lower()
    override_mask = out["_Doctor Key"].isin(DOCTOR_ROUTE_OVERRIDES)
    out.loc[override_mask, "_Route Cluster"] = out.loc[override_mask, "_Doctor Key"].map(DOCTOR_ROUTE_OVERRIDES)

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
    out.loc[out["_Route Cluster"].astype(str).str.lower().eq("do not route"), "_Excluded Reason"] = "Misty route group: Do Not Route"
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

def parse_day_limits(text):
    limits = {}
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        raw_date, raw_count = line.split("=", 1)
        try:
            dt = pd.to_datetime(raw_date.strip()).date()
            count = int(re.search(r"\d+", raw_count).group(0))
            if count >= 0:
                limits[dt] = count
        except Exception:
            pass
    return limits

def parse_route_preferences(text):
    preferences = {}
    route_names = list(ROUTE_ORDER)
    city_aliases = {
        "carmel mountain": "Carmel Mountain",
        "4s": "4S",
        "rancho bernardo": "Rancho Bernardo",
        "rb": "Rancho Bernardo",
        "poway": "Poway",
        "mira mesa": "Mira Mesa",
        "sorrento valley": "Sorrento Valley",
        "utc": "UTC",
        "la jolla": "La Jolla",
        "del mar": "Del Mar",
        "solana beach": "Solana Beach",
        "rancho santa fe": "Rancho Santa Fe",
        "sports arena": "Sports Arena",
        "point loma": "Point Loma",
        "ocean beach": "Ocean Beach",
        "pacific beach": "Pacific Beach",
        "carlsbad": "Carlsbad",
        "oceanside": "Oceanside / Vista",
        "vista": "Oceanside / Vista",
        "escondido": "Escondido / San Marcos",
        "san marcos": "Escondido / San Marcos",
        "eastlake": "Eastlake / Otay",
        "otay": "Eastlake / Otay",
        "chula vista": "Chula Vista / National City",
        "national city": "Chula Vista / National City",
        "la mesa": "La Mesa",
        "lemon grove": "Lemon Grove",
        "spring valley": "Spring Valley",
        "santee": "Santee",
        "el cajon": "El Cajon / Rancho San Diego",
        "rancho san diego": "El Cajon / Rancho San Diego",
    }
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        raw_date, raw_routes = line.split("=", 1)
        try:
            dt = pd.to_datetime(raw_date.strip()).date()
        except Exception:
            continue
        txt = raw_routes.lower()
        found = []
        for route in route_names:
            if route.lower() in txt and route not in found:
                found.append(route)
        for key, route in city_aliases.items():
            if key in txt and route not in found:
                found.append(route)
        if found:
            preferences[dt] = found
    return preferences

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
    route_cluster = normalize_route_name(row["_Route Cluster"])
    return {
        "Date": visit_date,
        "Day": visit_date.strftime("%A"),
        "Stop #": "",
        "Doctor Name": row["_Doctor Name"],
        "Practice Name": row["_Practice Name"],
        "Practice Address": row["_Practice Address"],
        "City": row["_City"],
        "Zip": row["_Zip"],
        "Route Cluster": route_cluster,
        "Route Sort": route_sort_value(route_cluster),
        "Route Guidance": route_direction_label(route_cluster),
        "Priority Rank": int(row["_Priority Rank"]) if pd.notna(row["_Priority Rank"]) else "",
        "Last Visit": last_visit.date() if pd.notna(last_visit) else "",
        "Next Due": next_due.date() if pd.notna(next_due) else "",
        "Due Status": row["_Due Status"],
        "Planner Note": note,
        "Visit Completed": "",
        "Updated Notes": "",
    }

def generate_month(doctors, year, month, blocked_dates, locks, max_per_day, monday_office_day=True, target_per_day=None, day_route_preferences=None, day_max_overrides=None):
    target_per_day = target_per_day or RULES["target_offices_per_day"]
    min_per_day = RULES["min_offices_per_day"]
    day_route_preferences = day_route_preferences or {}
    day_max_overrides = day_max_overrides or {}

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

        day_limit = day_max_overrides.get(dt, max_per_day)
        available = min(available, day_limit)
        if available <= 0:
            continue

        target_for_day = min(target_per_day, available)
        preferred_routes = day_route_preferences.get(dt, [])

        if preferred_routes:
            preferred = remaining[remaining["_Route Cluster"].isin(preferred_routes)]
            take_indexes = list(preferred.index[:target_for_day])
            # Event days stay intentionally lighter and close to the event. Do not top off with far-away routes.
            note = "Built around calendar event / preferred route"
            if not take_indexes:
                take_indexes = list(remaining.index[:min(target_for_day, len(remaining))])
                note = "No preferred-route doctors due; filled with next due doctors"
        elif len(remaining) <= target_for_day:
            take_indexes = list(remaining.index)
            note = "Smart grouped by route/priority"
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
            day_rows_preview = remaining.loc[take_indexes]
            route_count_preview = day_rows_preview["_Route Cluster"].nunique()
            note = "Smart grouped by route/priority" if route_count_preview == 1 else "Route topped off to avoid a light day"

        day_rows = remaining.loc[take_indexes]
        route_count = day_rows["_Route Cluster"].nunique()

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

def workdays_for_range(start_date, end_date, blocked_dates):
    days = []
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current not in blocked_dates:
            days.append(current)
        current += timedelta(days=1)
    return days

def first_nonempty(series, default=""):
    try:
        cleaned = series.dropna().astype(str).str.strip()
        cleaned = cleaned[cleaned.ne("") & cleaned.str.lower().ne("nan")]
        if len(cleaned):
            return cleaned.iloc[0]
    except Exception:
        pass
    return default

def build_offices(doctors, range_start, range_end, locks=None):
    d = doctors[doctors["_Routable"]].copy()
    if d.empty:
        return pd.DataFrame()

    locks = locks or {}
    start_dt = pd.to_datetime(range_start).date()
    end_dt = pd.to_datetime(range_end).date()

    # If a doctor/office is locked to a future date outside this selected range,
    # remove that whole office from this range so it cannot be scheduled early.
    # If the locked date is inside the selected range, the scheduler will place
    # that office on the locked date first and then remove it from the regular pool.
    def locked_date_for_group(group):
        names = " | ".join(group.get("_Doctor Name", pd.Series(dtype=str)).dropna().astype(str).str.lower().tolist())
        practice = " | ".join(group.get("_Practice Name", pd.Series(dtype=str)).dropna().astype(str).str.lower().tolist())
        combined = names + " | " + practice
        for key, lock_date in locks.items():
            if key and key.lower() in combined:
                return lock_date
        return None

    for col in ["_Practice Name", "_Practice Address", "_City", "_Zip", "_Route Cluster"]:
        if col not in d.columns:
            d[col] = ""

    d["_Office Key"] = (
        d["_Practice Name"].fillna("").astype(str).str.strip().str.lower() + "|" +
        d["_Practice Address"].fillna("").astype(str).str.strip().str.lower() + "|" +
        d["_City"].fillna("").astype(str).str.strip().str.lower() + "|" +
        d["_Zip"].fillna("").astype(str).str.strip().str.lower()
    )

    rows = []
    start_ts = pd.Timestamp(range_start)
    end_ts = pd.Timestamp(range_end)
    pull_ahead_end = end_ts + pd.Timedelta(days=21)

    for _, g in d.groupby("_Office Key", dropna=False):
        g = g.copy()
        locked_date = locked_date_for_group(g)
        if locked_date is not None and not (start_dt <= locked_date <= end_dt):
            # Save it for the locked date later; do not schedule it early.
            continue
        route = normalize_route_name(first_nonempty(g["_Route Cluster"], "Unassigned")) if len(g) else "Unassigned"
        last_visits = pd.to_datetime(g["_Last Visit"], errors="coerce")
        next_dues = pd.to_datetime(g["_Next Due"], errors="coerce")

        last_office_visit = last_visits.max()
        next_office_due = next_dues.min()

        if pd.isna(next_office_due):
            due_status = "No Visit History"
        elif next_office_due < start_ts:
            due_status = "Overdue"
        elif next_office_due <= end_ts:
            due_status = "Due During Range"
        elif next_office_due <= pull_ahead_end and (pd.isna(last_office_visit) or last_office_visit <= start_ts - pd.Timedelta(days=28)):
            due_status = "Pull Ahead"
        else:
            due_status = "Not Due"

        if due_status == "Not Due":
            continue

        priority_rank = pd.to_numeric(g["_Priority Rank"], errors="coerce").min()
        if pd.isna(priority_rank):
            priority_rank = 9999

        days_overdue = (start_ts - next_office_due).days if pd.notna(next_office_due) else 999

        rows.append({
            "_Office Key": g["_Office Key"].iloc[0],
            "Practice Name": first_nonempty(g["_Practice Name"], "Unnamed Office"),
            "Practice Address": first_nonempty(g["_Practice Address"], ""),
            "City": first_nonempty(g["_City"], ""),
            "Zip": first_nonempty(g["_Zip"], ""),
            "Doctors": ", ".join(sorted(g["_Doctor Name"].dropna().astype(str).unique())),
            "Doctor Count": int(g["_Doctor Name"].nunique()),
            "Route Cluster": route,
            "Route Sort": route_sort_value(route),
            "Route Guidance": route_direction_label(route),
            "Priority Rank": int(priority_rank),
            "Last Office Visit": last_office_visit.date() if pd.notna(last_office_visit) else "",
            "Next Office Due": next_office_due.date() if pd.notna(next_office_due) else "",
            "Due Status": due_status,
            "Locked Date": locked_date if locked_date is not None else "",
            "_Days Overdue": days_overdue,
        })

    offices = pd.DataFrame(rows)
    if offices.empty:
        return offices

    status_order = {"Overdue": 0, "No Visit History": 1, "Due During Range": 2, "Pull Ahead": 3}
    offices["_Status Sort"] = offices["Due Status"].map(status_order).fillna(9)
    offices = offices.sort_values(
        ["_Status Sort", "Route Sort", "Priority Rank", "_Days Overdue", "Practice Name"],
        ascending=[True, True, True, False, True]
    ).reset_index(drop=True)
    return offices

def office_schedule_row(row, visit_date, note=""):
    return {
        "Date": visit_date,
        "Day": visit_date.strftime("%A"),
        "Stop #": "",
        "Practice Name": row["Practice Name"],
        "Practice Address": row["Practice Address"],
        "City": row["City"],
        "Zip": row["Zip"],
        "Doctors Credited": row["Doctors"],
        "Doctor Count": row["Doctor Count"],
        "Route Cluster": row["Route Cluster"],
        "Route Sort": row["Route Sort"],
        "Route Guidance": row["Route Guidance"],
        "Priority Rank": row["Priority Rank"],
        "Last Office Visit": row["Last Office Visit"],
        "Next Office Due": row["Next Office Due"],
        "Due Status": row["Due Status"],
        "Planner Note": note,
        "Visit Completed": "",
        "Updated Notes": "",
    }

def assign_office_stop_order(day_df):
    if day_df.empty:
        return day_df
    ordered = day_df.copy()
    ordered["_Local Sort"] = ordered["Zip"].apply(clean_zip)
    ordered = ordered.sort_values(["Route Sort", "_Local Sort", "Priority Rank", "Practice Name"], ascending=[True, True, True, True])
    ordered["Stop #"] = range(1, len(ordered) + 1)
    return ordered.drop(columns=["_Local Sort"], errors="ignore")

def generate_date_range_offices(doctors, start_date, end_date, blocked_dates, max_per_day, target_per_day=7, day_route_preferences=None, day_max_overrides=None, locks=None):
    day_route_preferences = day_route_preferences or {}
    day_max_overrides = day_max_overrides or {}

    offices = build_offices(doctors, start_date, end_date, locks=locks)
    rows = []
    if offices.empty:
        return pd.DataFrame(), offices

    remaining = offices.copy()
    days = workdays_for_range(start_date, end_date, blocked_dates)

    # Place locked offices first on their exact locked date.
    if "Locked Date" in remaining.columns:
        locked_mask = remaining["Locked Date"].astype(str).str.strip().ne("")
        locked_rows = remaining[locked_mask].copy()
        for _, r in locked_rows.iterrows():
            lock_dt = pd.to_datetime(r["Locked Date"]).date()
            if lock_dt in days:
                rows.append(office_schedule_row(r, lock_dt, "Locked by user / calendar event"))
        remaining = remaining[~locked_mask].copy()

    for dt in days:
        if remaining.empty:
            break

        already_scheduled = sum(1 for r in rows if r.get("Date") == dt)
        day_limit = min(int(max_per_day), int(day_max_overrides.get(dt, target_per_day)))
        target = min(int(target_per_day), max(day_limit - already_scheduled, 0), len(remaining))
        if target <= 0:
            continue

        preferred_routes = day_route_preferences.get(dt, [])
        if preferred_routes:
            preferred = remaining[remaining["Route Cluster"].isin(preferred_routes)]
            chosen_idx = list(preferred.index[:target])
            note = "Built around calendar event / preferred route"
            if not chosen_idx:
                chosen_idx = list(remaining.index[:target])
                note = "No preferred-route offices due; filled with next due offices"
        else:
            first_route = remaining.iloc[0]["Route Cluster"]
            same_route = list(remaining[remaining["Route Cluster"] == first_route].index[:target])
            chosen_idx = same_route
            if len(chosen_idx) < min(target, 4):
                for idx in remaining.index:
                    if idx not in chosen_idx:
                        chosen_idx.append(idx)
                    if len(chosen_idx) >= target:
                        break
            route_count = remaining.loc[chosen_idx]["Route Cluster"].nunique()
            note = "Office-based route group" if route_count == 1 else "Route topped off with next due offices"

        for _, r in remaining.loc[chosen_idx].iterrows():
            rows.append(office_schedule_row(r, dt, note))

        remaining = remaining.drop(index=chosen_idx, errors="ignore")

    schedule = pd.DataFrame(rows)
    if not schedule.empty:
        ordered_days = []
        for _, day_df in schedule.groupby("Date", sort=True):
            ordered_days.append(assign_office_stop_order(day_df))
        schedule = pd.concat(ordered_days, ignore_index=True)
        schedule["_Stop Sort"] = pd.to_numeric(schedule["Stop #"], errors="coerce").fillna(0)
        schedule = schedule.sort_values(["Date", "_Stop Sort", "Route Sort", "Priority Rank", "Practice Name"], na_position="last").drop(columns=["_Stop Sort"]).reset_index(drop=True)

    return schedule, offices

def export_office_excel(schedule, offices, excluded):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        schedule.to_excel(writer, sheet_name="Office Schedule", index=False)
        offices.to_excel(writer, sheet_name="Due Offices", index=False)
        excluded.to_excel(writer, sheet_name="Excluded", index=False)

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for row in ws.iter_rows():
                for cell in row:
                    cell.alignment = cell.alignment.copy(wrap_text=True, vertical="top")
            for col in ws.columns:
                letter = col[0].column_letter
                max_len = max([len(str(c.value)) if c.value is not None else 0 for c in col] + [8])
                ws.column_dimensions[letter].width = min(max(max_len + 2, 10), 45)

    output.seek(0)
    return output

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
st.caption("Upload visit reports, plan a custom date range by office stop, and export Excel.")

with st.sidebar:
    st.header("Date Range Setup")
    today = date.today()
    selected_start_date = st.date_input("Start date", value=date(2026, 7, 7))
    selected_end_date = st.date_input("End date", value=date(2026, 7, 10))

    st.header("July calendar")
    st.caption("Edit these July commitments before generating the schedule.")
    july_events_text = st.text_area(
        "July event notes",
        value=(
            "2026-07-01 5:00 PM - Alcon dinner at Amalfi Llama\n"
            "2026-07-03 - Office closed\n"
            "2026-07-13 - Field day\n"
            "2026-07-14 - Office day\n"
            "2026-07-16 - SDCOS meeting at WestPac near Sorrento Valley/Mira Mesa\n"
            "2026-07-28 - Epioxa Dinner at California English in Sorrento Valley\n"
            "2026-07-31 - Lunch & Learn with Dorothy Wang's office"
        ),
        height=160,
    )

    st.header("Calendar Control")
    blocked_text = st.text_area(
        "Blocked full days",
        value="2026-07-03\n2026-07-14",
        placeholder="One per line:\n2026-07-03\n2026-07-14",
        help="Use this for office closed, office days, PTO, or days you do not want field visits."
    )
    lock_text = st.text_area(
        "Doctor/date locks",
        value="Dorothy Wang = 2026-07-31",
        placeholder="One per line:\nDorothy Wang = 2026-07-31\nClarke = 2026-07-08",
        help="Use any searchable part of the doctor's name."
    )
    preferred_routes_text = st.text_area(
        "Preferred route days",
        value="2026-07-01 = UTC / La Jolla / Sorrento Valley\n2026-07-16 = Sorrento Valley / Mira Mesa\n2026-07-28 = Sorrento Valley / Mira Mesa\n2026-07-31 = Carmel Mountain",
        help="Use this for event days where you want the field route to stay near the event location."
    )
    day_limits_text = st.text_area(
        "Lighter days / max stops",
        value="2026-07-01 = 5\n2026-07-16 = 5\n2026-07-28 = 5\n2026-07-31 = 4",
        help="Use this for dinners, meetings, and lunch & learns. Lunch & Learn default is 4 total stops including the meeting office."
    )
    max_per_day = st.slider("Max office stops per field day", 6, 10, 10)

    st.header("Rules")
    st.write(f"Start/end base: **{RULES['home_base']}**")
    st.write("Top 20: monthly")
    st.write("Rank 21–60: every 6 weeks")
    st.write("Remaining: quarterly")
    monday_office_day = st.checkbox("Auto-block every Monday as La Jolla office day", value=False)
    st.caption("July defaults: 7/3 and 7/14 are blocked. 7/13 is available as a field day.")

tab_upload, tab_plan, tab_history, tab_rules = st.tabs(["Upload", "Plan Date Range", "Upload History", "Rules"])

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
        day_route_preferences = parse_route_preferences(preferred_routes_text)
        day_max_overrides = parse_day_limits(day_limits_text)

        st.subheader("Plan Date Range")
        st.caption("This schedules office stops, not individual doctors. All doctors at the same office receive visit credit for one physical stop.")
        st.write(f"Planning: **{selected_start_date}** through **{selected_end_date}**")

        if selected_end_date < selected_start_date:
            st.error("End date must be after start date.")
        elif st.button("Build office schedule", type="primary"):
            schedule, offices = generate_date_range_offices(
                doctors,
                selected_start_date,
                selected_end_date,
                blocked_dates,
                int(max_per_day),
                target_per_day=7,
                day_route_preferences=day_route_preferences,
                day_max_overrides=day_max_overrides,
                locks=locks,
            )
            st.session_state["schedule"] = schedule
            st.session_state["due_offices"] = offices

        if "schedule" in st.session_state:
            schedule = st.session_state["schedule"]
            due_offices = st.session_state.get("due_offices", pd.DataFrame())
            excluded = doctors[~doctors["_Routable"]].copy()

            if schedule.empty:
                st.warning("No due offices found for the selected date range/rules.")
            else:
                st.subheader("Editable office schedule")
                st.caption("Each row is one physical office stop. The Doctors Credited column shows everyone who receives visit credit.")
                edited = st.data_editor(schedule, use_container_width=True, num_rows="dynamic", key="schedule_editor")

                st.subheader("Daily stop counts")
                counts = edited.groupby(["Date", "Day"]).size().reset_index(name="Office Stop Count")
                st.dataframe(counts, use_container_width=True, hide_index=True)

                export = export_office_excel(
                    edited,
                    due_offices,
                    excluded[["_Doctor Name", "_Practice Name", "_Practice Address", "_City", "_Zip", "_Route Cluster", "_Route Guidance", "_Excluded Reason", "_Notes"]],
                )
                file_name = f"territory_office_schedule_{selected_start_date}_to_{selected_end_date}.xlsx"
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

    st.subheader("Doctor-specific route overrides")
    st.json(DOCTOR_ROUTE_OVERRIDES)

    st.caption("These rules are code-based so they do not drift between uploads.")
