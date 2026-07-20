from __future__ import annotations
from sqlalchemy import select, func
from database.connection import connection
from database.schema import practices, doctor_practices


def list_practices(search: str = "") -> list[dict]:
    stmt = select(
        practices.c.practice_id,
        practices.c.name.label("Practice Name"),
        practices.c.address.label("Address"),
        practices.c.city.label("City"),
        practices.c.zip_code.label("Zip"),
        practices.c.office_number.label("Office Number"),
        practices.c.office_manager.label("Office Manager/CM Liaison"),
        practices.c.route_group.label("Correct Route Group"),
        practices.c.route_cluster.label("Route Cluster"),
        practices.c.routable.label("Routable"),
        practices.c.excluded_reason.label("Excluded Reason"),
        func.count(doctor_practices.c.doctor_id).label("Doctors"),
    ).select_from(practices.outerjoin(doctor_practices, practices.c.practice_id == doctor_practices.c.practice_id))
    if search.strip():
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            practices.c.normalized_name.like(pattern) |
            practices.c.normalized_address.like(pattern) |
            func.lower(practices.c.city).like(pattern)
        )
    stmt = stmt.group_by(practices.c.practice_id).order_by(practices.c.route_cluster.asc(), practices.c.name.asc())
    with connection() as conn:
        return [dict(row._mapping) for row in conn.execute(stmt).all()]
