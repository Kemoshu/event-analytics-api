from sqlalchemy import Column, DateTime, Integer, String, JSON, Index
from sqlalchemy.sql import func
from .db import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(80), index=True, nullable=False)
    source = Column(String(120), index=True, nullable=False)
    user_id = Column(String(120), index=True, nullable=True)

    # Arbitrary event data
    payload = Column(JSON, nullable=False)

    # When the event happened (client), optional
    occurred_at = Column(DateTime(timezone=True), nullable=True)

    # When we ingested it (server)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

Index("ix_events_type_source_time", Event.event_type, Event.source, Event.ingested_at)
