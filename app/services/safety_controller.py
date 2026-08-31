import logging
import math
from typing import List
from app.domain.call import Call
from app.domain.enums import ProviderHealthStatus
from app.services.call_allocator import CallAllocator
from app.services.provider_health import ProviderHealthMonitor

logger = logging.getLogger(__name__)


class SafetyController:
    """
    Mandatory Safety Controller: Acts as the absolute gatekeeper between Predictive Pacing
    and Call Allocation. Ensures agent capacity is never violated and handles fallback.
    """

    def __init__(
        self,
        allocator: CallAllocator,
        health_monitor: ProviderHealthMonitor,
        max_dial_ahead_ratio: float = 2.0,
    ):
        self.allocator = allocator
        self.health_monitor = health_monitor
        self.max_dial_ahead_ratio = max_dial_ahead_ratio
        self.safety_violations_prevented: int = 0
        self.fallback_triggers_count: int = 0

    async def request_dialing(self, requested_calls: int) -> List[Call]:
        available_agents = self.allocator.repo.get_available_agents()
        num_available = len(available_agents)

        if num_available == 0:
            return []

        provider_status = self.health_monitor.get_status()

        # Rule 1: Progressive Fallback on Provider Degradation/Critical state
        if provider_status in {ProviderHealthStatus.CRITICAL, ProviderHealthStatus.UNAVAILABLE}:
            self.fallback_triggers_count += 1
            approved_calls = min(requested_calls, num_available)  # 1:1 Fallback
        elif provider_status == ProviderHealthStatus.DEGRADED:
            # Dampen aggressiveness
            max_allowed = math.ceil(num_available * 1.2)
            approved_calls = min(requested_calls, max_allowed)
        else:
            # Rule 2: Normal Safety Invariant Clamp
            max_allowed = math.ceil(num_available * self.max_dial_ahead_ratio)
            approved_calls = min(requested_calls, max_allowed)

        if approved_calls < requested_calls:
            self.safety_violations_prevented += (requested_calls - approved_calls)

        # Execute allocations up to approved count
        initiated_calls: List[Call] = []
        for agent in available_agents[:approved_calls]:
            call = await self.allocator.reserve_and_allocate(agent.id)
            if call:
                initiated_calls.append(call)

        return initiated_calls