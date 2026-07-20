"""Shared database connection layer.

All new Version 1 modules should use this module rather than opening database
connections directly. PostgreSQL is supported for hosted deployment and SQLite
is retained only as a local-development fallback.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

from config import settings


def _create_engine() -> Engine:
    kwargs: dict = {"future": True, "pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # NullPool avoids stale pooled connections when Streamlit apps sleep/wake.
        kwargs["poolclass"] = NullPool
    return create_engine(settings.database_url, **kwargs)


engine = _create_engine()


@contextmanager
def transaction() -> Iterator[Connection]:
    """Provide an atomic transaction that rolls back automatically on failure."""
    with engine.begin() as connection:
        yield connection


@contextmanager
def connection() -> Iterator[Connection]:
    """Provide a read connection without starting a write transaction."""
    with engine.connect() as db_connection:
        yield db_connection


def database_healthcheck() -> bool:
    try:
        with connection() as db_connection:
            db_connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
