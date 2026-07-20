from __future__ import annotations
from pathlib import Path
import tempfile
import pandas as pd
import streamlit as st
from services.doctor_service import doctor_counts, list_doctors
from services.practice_service import list_practices
from services.master_data_import_service import import_master_data, seed_current_master_data, master_data_is_empty


def _save_upload(uploaded, suffix: str) -> Path:
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.write(uploaded.getbuffer())
    temp.close()
    return Path(temp.name)


def render_master_data_page() -> None:
    st.subheader("Master Data")
    st.caption("Doctors, physical practice locations, routing assignments, referral tier, cadence, and visit history.")

    if master_data_is_empty():
        st.warning("The Master Data database is empty.")
        if st.button("Load the current approved Doctor Spreadsheet and TMS", type="primary"):
            with st.spinner("Loading current authoritative data..."):
                result = seed_current_master_data()
            st.success(f"Loaded {result.doctors} doctors and {result.practices} physical practice locations.")
            st.rerun()

    counts = doctor_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Doctors", counts["total"])
    c2.metric("Routable", counts["routable"])
    c3.metric("Excluded", counts["excluded"])
    c4.metric("Due / overdue", counts["due"])

    doctors_tab, practices_tab, import_tab = st.tabs(["Doctors", "Practices", "Authoritative Import"])
    with doctors_tab:
        c1, c2 = st.columns([3, 1])
        search = c1.text_input("Search doctors", placeholder="Doctor name")
        routable_only = c2.checkbox("Routable only")
        rows = list_doctors(search=search, routable_only=routable_only)
        frame = pd.DataFrame(rows)
        if not frame.empty:
            frame = frame.drop(columns=["doctor_id"], errors="ignore")
        st.dataframe(frame, use_container_width=True, hide_index=True)

    with practices_tab:
        search = st.text_input("Search practices", placeholder="Practice, address, or city")
        frame = pd.DataFrame(list_practices(search=search))
        if not frame.empty:
            frame = frame.drop(columns=["practice_id"], errors="ignore")
        st.dataframe(frame, use_container_width=True, hide_index=True)

    with import_tab:
        st.info("TMS rules remain authoritative for route, cadence, rank, routability, and exclusions. The Doctor Spreadsheet refreshes factual doctor, practice, contact, referral, and visit information.")
        doctor_upload = st.file_uploader("Current Misty Doctor Spreadsheet", type=["xlsx"], key="master_doctor_upload")
        tms_upload = st.file_uploader("Current TMS", type=["xlsx"], key="master_tms_upload")
        if st.button("Import both files", disabled=not (doctor_upload and tms_upload), type="primary"):
            doctor_path = _save_upload(doctor_upload, ".xlsx")
            tms_path = _save_upload(tms_upload, ".xlsx")
            try:
                with st.spinner("Refreshing Master Data..."):
                    result = import_master_data(doctor_path, tms_path)
                st.success(f"Import completed: {result.doctors} doctors, {result.practices} practices, {result.visits} visit-history rows.")
                st.rerun()
            finally:
                doctor_path.unlink(missing_ok=True)
                tms_path.unlink(missing_ok=True)
