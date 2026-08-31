import asyncio
import uuid
from typing import Optional
from app.domain.agent import Agent
from app.domain.call import Call
from app.domain.enums import AgentState, CallState
from app.providers.base import TelecomProvider
from app.repositories.csv_repository import InMemoryRepository


class CallAllocator:
    """
    Handles atomic reservation of agents and launches calls via the configured provider.
    Ensures safe concurrent access using per-agent locks.
    """

    def __init__(self, repo: InMemoryRepository, provider: TelecomProvider):
        self.repo = repo
        self.provider = provider
        self.reservation_conflicts: int = 0

    async def reserve_and_allocate(self, agent_id: str) -> Optional[Call]:
        agent = self.repo.agents.get(agent_id)
        if not agent:
            return None

        # Atomic reservation check
        async with agent.lock:
            if agent.status != AgentState.AVAILABLE:
                self.reservation_conflicts += 1
                return None
            agent.transition_to(AgentState.RESERVED)

        # Select prioritized borrower
        borrower = self.repo.get_next_borrower()
        if not borrower:
            # Revert agent reservation if no borrowers left
            async with agent.lock:
                if agent.status == AgentState.RESERVED:
                    agent.transition_to(AgentState.AVAILABLE)
            return None

        borrower.is_contacted = True
        borrower.attempts += 1

        # Create Call object
        call_id = f"call_{uuid.uuid4().hex[:8]}"
        call = Call(id=call_id, borrower_id=borrower.id, agent_id=agent.id, status=CallState.RESERVED)
        self.repo.add_call(call)

        async with agent.lock:
            if agent.can_transition_to(AgentState.DIALING):
                agent.transition_to(AgentState.DIALING, call_id=call.id)

        call.transition_to(CallState.INITIATED)

        try:
            provider_call_id = await self.provider.initiate_call(call.id, borrower.phone)
            self.repo.map_provider_call_id(provider_call_id, call.id)
            return call
        except Exception:
            # Handle setup failure gracefully
            call.transition_to(CallState.FAILED)
            async with agent.lock:
                if agent.can_transition_to(AgentState.AVAILABLE):
                    agent.transition_to(AgentState.AVAILABLE)
            return None