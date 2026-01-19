from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from ..db import get_db
from ..models import Event
from ..schemas import EventCreate, EventOut

router = APIRouter(prefix="/events", tags=["events"])

@router.post("", response_model=EventOut, status_code=201)
def create_event(body: EventCreate, db: Session = Depends(get_db)):
    ev = Event(
        event_type=body.event_type,
        source=body.source,
        user_id=body.user_id,
        occurred_at=body.occurred_at,
        payload=body.payload,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev

@router.get("", response_model=list[EventOut])
def list_events(
    db: Session = Depends(get_db),
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(Event)

    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if source:
        stmt = stmt.where(Event.source == source)
    if user_id:
        stmt = stmt.where(Event.user_id == user_id)

    stmt = stmt.order_by(desc(Event.ingested_at)).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()
