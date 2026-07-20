"""Application configuration for the Professional Relations Platform.

Secrets are read from Streamlit secrets first and then environment variables.
No secret values should be committed to source control.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
LOCAL_DATABASE_PATH = DATA_DIR / "professional_relations_platform.sqlite"

for directory in (DATA_DIR, UPLOAD_DIR, EXPORT_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def _secret(name: str, default: Any = None) -> Any:
    """Read a value without failing when Streamlit secrets are unavailable."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    app_title: str = "Professional Relations Platform"
    app_environment: str = str(_secret("APP_ENV", "development"))
    database_url: str = str(
        _secret("DATABASE_URL", f"sqlite:///{LOCAL_DATABASE_PATH.as_posix()}")
    )
    session_timeout_minutes: int = int(_secret("SESSION_TIMEOUT_MINUTES", 480))

    @property
    def uses_hosted_database(self) -> bool:
        return not self.database_url.startswith("sqlite")


settings = Settings()
