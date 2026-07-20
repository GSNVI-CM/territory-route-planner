from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Practice:
    practice_id: int
    name: str
    address: str
    city: str | None = None
    zip_code: str | None = None
    office_number: str | None = None
    office_manager: str | None = None
    route_group: str | None = None
    route_cluster: str | None = None
    routable: bool = True
    excluded_reason: str | None = None
