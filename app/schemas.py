from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=120)
    user_id: Optional[str] = Field(default=None, max_length=120)
    occurred_at: Optional[datetime] = None
    payload: Dict[str, Any]


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    source: str
    user_id: Optional[str] = None
    occurred_at: Optional[datetime] = None
    ingested_at: datetime
    payload: Dict[str, Any]
