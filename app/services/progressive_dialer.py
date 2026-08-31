import asyncio
from typing import List
from app.domain.call import Call
from app.services.call_allocator import CallAllocator


class ProgressiveDialer:
    """
    Progressive Dialer strategy: 1 Available Agent -> 1 Outbound Call Max.
    Completely avoids over-dialing or abandoned call risk.
    """

    def __init__(self, allocator: CallAllocator):
        self.allocator = allocator

    async def execute_step(self) -> List[Call]:
        available_agents = self.allocator.repo.get_available_agents()
        initiated_calls: List[Call] = []

        for agent in available_agents:
            call = await self.allocator.reserve_and_allocate(agent.id)
            if call:
                initiated_calls.append(call)
        return initiated_calls