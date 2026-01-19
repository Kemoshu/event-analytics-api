from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Event

router = APIRouter(prefix="/analytics", tags=["analytics"])

GroupBy = Literal["event_type", "source", "user_id"]
Interval = Literal["hour", "day"]

def _apply_filters(stmt, event_type, source, user_id, since, until):
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if source:
        stmt = stmt.where(Event.source == source)
    if user_id:
        stmt = stmt.where(Event.user_id == user_id)
    if since:
        stmt = stmt.where(Event.ingested_at >= since)
    if until:
        stmt = stmt.where(Event.ingested_at < until)
    return stmt

@router.get("/counts")
def counts(
    db: Session = Depends(get_db),
    group_by: GroupBy = Query("event_type"),
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    user_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=200),
):
    col = getattr(Event, group_by)

    stmt = (
        select(col.label("key"), func.count(Event.id).label("count"))
        .group_by(col)
        .order_by(func.count(Event.id).desc())
        .limit(limit)
    )
    stmt = _apply_filters(stmt, event_type, source, user_id, since, until)

    rows = db.execute(stmt).all()
    return {
        "group_by": group_by,
        "since": since,
        "until": until,
        "results": [{"key": r.key, "count": int(r.count)} for r in rows],
    }

@router.get("/timeseries")
def timeseries(
    db: Session = Depends(get_db),
    interval: Interval = Query("day"),
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    user_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
):
    # Postgres date_trunc
    bucket = func.date_trunc(interval, Event.ingested_at).label("bucket")

    stmt = (
        select(bucket, func.count(Event.id).label("count"))
        .group_by(bucket)
        .order_by(bucket.asc())
    )
    stmt = _apply_filters(stmt, event_type, source, user_id, since, until)

    rows = db.execute(stmt).all()
    return {
        "interval": interval,
        "since": since,
        "until": until,
        "results": [{"bucket": r.bucket.isoformat(), "count": int(r.count)} for r in rows],
    }
