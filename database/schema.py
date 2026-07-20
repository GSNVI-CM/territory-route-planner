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
