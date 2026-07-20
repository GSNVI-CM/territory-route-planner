"""Small, dependency-light migration runner for Version 1."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy import inspect, select
from sqlalchemy.engine import Connection

from database.connection import engine, transaction
from database.schema import metadata, schema_migrations
from database.master_data_migration import apply_master_data_schema


@dataclass(frozen=True)
class Migration:
    migration_id: str
    apply: Callable[[Connection], None]


def _foundation_schema(connection: Connection) -> None:
    metadata.create_all(bind=connection)


MIGRATIONS = [
    Migration("001_foundation_schema", _foundation_schema),
    Migration("002_master_data_schema", apply_master_data_schema),
]


def initialize_database() -> None:
    """Apply unapplied migrations in order and record each one atomically."""
    # Ensure the migration table itself exists before querying it.
    schema_migrations.create(bind=engine, checkfirst=True)

    with transaction() as db_connection:
        applied = {
            row[0]
            for row in db_connection.execute(
                select(schema_migrations.c.migration_id)
            ).all()
        }
        for migration in MIGRATIONS:
            if migration.migration_id in applied:
                continue
            migration.apply(db_connection)
            db_connection.execute(
                schema_migrations.insert().values(migration_id=migration.migration_id)
            )


def migration_status() -> dict[str, bool]:
    inspector = inspect(engine)
    return {
        "schema_migrations": inspector.has_table("schema_migrations"),
        "app_users": inspector.has_table("app_users"),
        "business_events": inspector.has_table("business_events"),
        "doctors": inspector.has_table("doctors"),
        "practices": inspector.has_table("practices"),
        "doctor_practices": inspector.has_table("doctor_practices"),
    }
