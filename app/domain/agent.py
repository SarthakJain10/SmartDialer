import asyncio
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from app.domain.enums import AgentState


class Agent(BaseModel):
    id: str
    name: str
    status: AgentState = AgentState.OFFLINE
    last_state_change: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_call_id: Optional[str] = None
    
    # Internal lock for thread/async safety (excluded from serialization)
    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    # Valid transitions mapping
    _ALLOWED_TRANSITIONS: dict[AgentState, set[AgentState]] = {
        AgentState.OFFLINE: {AgentState.AVAILABLE},
        AgentState.AVAILABLE: {AgentState.RESERVED, AgentState.PAUSED, AgentState.OFFLINE},
        AgentState.RESERVED: {AgentState.DIALING, AgentState.AVAILABLE, AgentState.OFFLINE},
        AgentState.DIALING: {AgentState.CONNECTED, AgentState.WRAP_UP, AgentState.AVAILABLE},
        AgentState.CONNECTED: {AgentState.WRAP_UP},
        AgentState.WRAP_UP: {AgentState.AVAILABLE, AgentState.PAUSED},
        AgentState.PAUSED: {AgentState.AVAILABLE, AgentState.OFFLINE},
    }

    def can_transition_to(self, target: AgentState) -> bool:
        return target in self._ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, target: AgentState, call_id: Optional[str] = None) -> None:
        if not self.can_transition_to(target):
            raise ValueError(
                f"Invalid Agent state transition for {self.id}: {self.status.value} -> {target.value}"
            )
        self.status = target
        self.last_state_change = datetime.now(timezone.utc)
        if target in {AgentState.AVAILABLE, AgentState.OFFLINE, AgentState.PAUSED}:
            self.current_call_id = None
        elif call_id is not None:
            self.current_call_id = call_id