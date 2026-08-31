from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.domain.enums import EventType


class ProviderEvent(BaseModel):
    event_id: str
    provider_call_id: str
    call_id: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_reason: Optional[str] = None