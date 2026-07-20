"""Master Data schema migration."""
from __future__ import annotations
from sqlalchemy.engine import Connection
from database.schema import (
    doctors, practices, doctor_practices, referral_snapshots,
    visit_history, import_runs,
)

def apply_master_data_schema(connection: Connection) -> None:
    for table in (doctors, practices, doctor_practices, referral_snapshots, visit_history, import_runs):
        table.create(bind=connection, checkfirst=True)
