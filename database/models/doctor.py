from __future__ import annotations
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class Doctor:
    doctor_id: int
    name: str
    referral_rank: int | None = None
    cadence_days: int | None = None
    last_visit_date: date | None = None
    next_due_date: date | None = None
    due_status: str | None = None
    routable: bool = True
    excluded_reason: str | None = None
    notes: str | None = None
