import asyncio
import logging
from typing import Set
from app.domain.enums import AgentState, CallState, EventType
from app.domain.events import ProviderEvent
from app.repositories.csv_repository import InMemoryRepository
from app.services.provider_health import ProviderHealthMonitor

logger = logging.getLogger(__name__)


class EventProcessor:
    """
    Handles telecom events asynchronously.
    Guarantees idempotency and protects terminal call/agent state invariants.
    """

    def __init__(self, repo: InMemoryRepository, health_monitor: ProviderHealthMonitor):
        self.repo = repo
        self.health_monitor = health_monitor
        self._processed_event_ids: Set[str] = set()
        self._lock = asyncio.Lock()

        # Metrics
        self.duplicate_events_count = 0
        self.out_of_order_events_count = 0

    async def process_event(self, event: ProviderEvent) -> None:
        async with self._lock:
            # 1. Idempotency Check
            if event.event_id in self._processed_event_ids:
                self.duplicate_events_count += 1
                self.health_monitor.record_duplicate()
                return

            self._processed_event_ids.add(event.event_id)

            # 2. Match Call
            call = self.repo.calls.get(event.call_id) or self.repo.get_call_by_provider_id(event.provider_call_id)
            if not call:
                return

            agent = self.repo.agents.get(call.agent_id)

            # 3. Handle Terminal Call Guard / Out-Of-Order Event
            if call.is_terminal():
                self.out_of_order_events_count += 1
                self.health_monitor.record_out_of_order()
                return

            # Map EventType to CallState
            target_call_state = self._map_event_to_call_state(event.event_type)
            if not target_call_state:
                return

            # Execute Call Transition
            success = call.transition_to(target_call_state)
            if not success:
                self.out_of_order_events_count += 1
                self.health_monitor.record_out_of_order()
                return

            # 4. Synchronize Agent State Machine
            if agent:
                await self._update_agent_state(agent, target_call_state, call.id)

            # 5. Record Health Metrics
            if target_call_state in {CallState.COMPLETED, CallState.ANSWERED, CallState.CONNECTED}:
                self.health_monitor.record_outcome(success=True)
            elif target_call_state == CallState.FAILED:
                self.health_monitor.record_outcome(success=False)

    def _map_event_to_call_state(self, event_type: EventType) -> CallState:
        mapping = {
            EventType.INITIATED: CallState.INITIATED,
            EventType.RINGING: CallState.RINGING,
            EventType.ANSWERED: CallState.ANSWERED,
            EventType.COMPLETED: CallState.COMPLETED,
            EventType.FAILED: CallState.FAILED,
        }
        return mapping.get(event_type)

    async def _update_agent_state(self, agent, target_call_state: CallState, call_id: str) -> None:
        async with agent.lock:
            if target_call_state in {CallState.ANSWERED, CallState.CONNECTED}:
                if agent.can_transition_to(AgentState.CONNECTED):
                    agent.transition_to(AgentState.CONNECTED, call_id=call_id)
            elif target_call_state in {CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED}:
                if agent.can_transition_to(AgentState.WRAP_UP):
                    agent.transition_to(AgentState.WRAP_UP)
                    # Instant wrap up to AVAILABLE for simulation simplicity
                    if agent.can_transition_to(AgentState.AVAILABLE):
                        agent.transition_to(AgentState.AVAILABLE)
                elif agent.can_transition_to(AgentState.AVAILABLE):
                    agent.transition_to(AgentState.AVAILABLE)