from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.domain.enums import CallState


class Call(BaseModel):
    id: str
    borrower_id: str
    agent_id: str
    provider_call_id: Optional[str] = None
    provider_id: Optional[str] = None
    status: CallState = CallState.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Timestamps for metrics
    initiated_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    TERMINAL_STATES: set[CallState] = {
        CallState.COMPLETED,
        CallState.FAILED,
        CallState.CANCELLED,
    }

    _ALLOWED_TRANSITIONS: dict[CallState, set[CallState]] = {
        CallState.QUEUED: {CallState.RESERVED, CallState.CANCELLED},
        CallState.RESERVED: {CallState.INITIATED, CallState.FAILED, CallState.CANCELLED},
        CallState.INITIATED: {CallState.RINGING, CallState.FAILED, CallState.CANCELLED},
        CallState.RINGING: {CallState.ANSWERED, CallState.FAILED, CallState.CANCELLED, CallState.COMPLETED},
        CallState.ANSWERED: {CallState.CONNECTED, CallState.COMPLETED, CallState.FAILED},
        CallState.CONNECTED: {CallState.COMPLETED, CallState.FAILED},
        CallState.COMPLETED: set(),
        CallState.FAILED: set(),
        CallState.CANCELLED: set(),
    }

    def is_terminal(self) -> bool:
        return self.status in self.TERMINAL_STATES

    def can_transition_to(self, target: CallState) -> bool:
        if self.is_terminal():
            return False
        return target in self._ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, target: CallState) -> bool:
        if self.is_terminal():
            # Invariant: Terminal calls cannot revert or change states
            return False
        if not self.can_transition_to(target):
            return False

        now = datetime.now(timezone.utc)
        self.status = target
        self.updated_at = now

        if target == CallState.INITIATED and not self.initiated_at:
            self.initiated_at = now
        elif target == CallState.ANSWERED and not self.answered_at:
            self.answered_at = now
        elif target in self.TERMINAL_STATES and not self.completed_at:
            self.completed_at = now

        return True