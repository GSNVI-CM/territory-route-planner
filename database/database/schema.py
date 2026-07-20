"""Foundation database schema.

Domain tables are added by later modules. This foundation establishes migration
tracking, authenticated users, and meaningful business-event history.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    ForeignKey,
    Date,
    func,
)

metadata = MetaData()

schema_migrations = Table(
    "schema_migrations",
    metadata,
    Column("migration_id", String(100), primary_key=True),
    Column("applied_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

app_users = Table(
    "app_users",
    metadata,
    Column("user_id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(255), nullable=False),
    Column("display_name", String(255), nullable=False),
    Column("role", String(30), nullable=False),
    Column("password_hash", String(255), nullable=True),
    Column("active", Boolean, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("email", name="uq_app_users_email"),
)

business_events = Table(
    "business_events",
    metadata,
    Column("event_id", Integer, primary_key=True, autoincrement=True),
    Column("event_type", String(100), nullable=False),
    Column("entity_type", String(100), nullable=True),
    Column("entity_id", String(100), nullable=True),
    Column("actor_user_id", Integer, nullable=True),
    Column("event_payload", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


# Master Data module
doctors = Table(
    "doctors", metadata,
    Column("doctor_id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("normalized_name", String(255), nullable=False),
    Column("referral_rank", Integer, nullable=True),
    Column("cadence_days", Integer, nullable=True),
    Column("last_visit_date", Date, nullable=True),
    Column("next_due_date", Date, nullable=True),
    Column("due_status", String(50), nullable=True),
    Column("routable", Boolean, nullable=False, server_default="1"),
    Column("excluded_reason", Text, nullable=True),
    Column("notes", Text, nullable=True),
    Column("active", Boolean, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("normalized_name", name="uq_doctors_normalized_name"),
)

practices = Table(
    "practices", metadata,
    Column("practice_id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("normalized_name", String(255), nullable=False),
    Column("address", String(500), nullable=False),
    Column("normalized_address", String(500), nullable=False),
    Column("city", String(150), nullable=True),
    Column("zip_code", String(20), nullable=True),
    Column("office_number", String(100), nullable=True),
    Column("office_manager", String(255), nullable=True),
    Column("route_group", String(255), nullable=True),
    Column("route_cluster", String(255), nullable=True),
    Column("routable", Boolean, nullable=False, server_default="1"),
    Column("excluded_reason", Text, nullable=True),
    Column("active", Boolean, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("normalized_address", name="uq_practices_normalized_address"),
)

doctor_practices = Table(
    "doctor_practices", metadata,
    Column("doctor_practice_id", Integer, primary_key=True, autoincrement=True),
    Column("doctor_id", Integer, ForeignKey("doctors.doctor_id"), nullable=False),
    Column("practice_id", Integer, ForeignKey("practices.practice_id"), nullable=False),
    Column("active", Boolean, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("doctor_id", "practice_id", name="uq_doctor_practice"),
)

referral_snapshots = Table(
    "referral_snapshots", metadata,
    Column("referral_snapshot_id", Integer, primary_key=True, autoincrement=True),
    Column("doctor_id", Integer, ForeignKey("doctors.doctor_id"), nullable=False),
    Column("year", Integer, nullable=False),
    Column("referral_count", Integer, nullable=False, server_default="0"),
    Column("source_file", String(500), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("doctor_id", "year", name="uq_referral_doctor_year"),
)

visit_history = Table(
    "visit_history", metadata,
    Column("visit_history_id", Integer, primary_key=True, autoincrement=True),
    Column("doctor_id", Integer, ForeignKey("doctors.doctor_id"), nullable=False),
    Column("practice_id", Integer, ForeignKey("practices.practice_id"), nullable=True),
    Column("visit_date", Date, nullable=False),
    Column("route_cluster", String(255), nullable=True),
    Column("source", String(500), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

import_runs = Table(
    "import_runs", metadata,
    Column("import_run_id", Integer, primary_key=True, autoincrement=True),
    Column("doctor_source_file", String(500), nullable=False),
    Column("tms_source_file", String(500), nullable=False),
    Column("doctor_source_hash", String(64), nullable=False),
    Column("tms_source_hash", String(64), nullable=False),
    Column("status", String(50), nullable=False),
    Column("summary_json", Text, nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("completed_at", DateTime(timezone=True), nullable=True),
)
