from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DoctorPractice:
    doctor_practice_id: int
    doctor_id: int
    practice_id: int
    active: bool = True
