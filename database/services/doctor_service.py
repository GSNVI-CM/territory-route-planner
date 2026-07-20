from __future__ import annotations
from sqlalchemy import select
from database.connection import connection
from database.schema import doctors, doctor_practices, practices, referral_snapshots


def list_doctors(search: str = "", routable_only: bool = False) -> list[dict]:
    stmt = select(
        doctors.c.doctor_id,
        doctors.c.name.label("Doctor Name"),
        doctors.c.referral_rank.label("Referral Rank"),
        doctors.c.last_visit_date.label("Last Visit"),
        doctors.c.next_due_date.label("Next Due"),
        doctors.c.due_status.label("Due Status"),
        doctors.c.routable.label("Routable"),
        doctors.c.excluded_reason.label("Excluded Reason"),
        practices.c.name.label("Practice Name"),
        practices.c.city.label("City"),
        practices.c.route_cluster.label("Route Cluster"),
    ).select_from(
        doctors.outerjoin(doctor_practices, doctors.c.doctor_id == doctor_practices.c.doctor_id)
        .outerjoin(practices, doctor_practices.c.practice_id == practices.c.practice_id)
    )
    if search.strip():
        stmt = stmt.where(doctors.c.normalized_name.like(f"%{search.strip().lower()}%"))
    if routable_only:
        stmt = stmt.where(doctors.c.routable.is_(True))
    stmt = stmt.order_by(doctors.c.referral_rank.asc().nullslast(), doctors.c.name.asc())
    with connection() as conn:
        return [dict(row._mapping) for row in conn.execute(stmt).all()]


def doctor_counts() -> dict[str, int]:
    rows = list_doctors()
    unique = {row["doctor_id"]: row for row in rows}
    return {
        "total": len(unique),
        "routable": sum(1 for row in unique.values() if row["Routable"]),
        "excluded": sum(1 for row in unique.values() if not row["Routable"]),
        "due": sum(1 for row in unique.values() if row["Due Status"] in {"Overdue", "Due Soon", "No Visit History"}),
    }
