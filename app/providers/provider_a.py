import asyncio
import random
import uuid
from typing import Callable, Awaitable, Optional
from app.domain.enums import EventType
from app.domain.events import ProviderEvent


class MockProviderA:
    """Healthy Telecom Provider implementation: fast, reliable (~5% failure), ordered events."""

    def __init__(self, failure_rate: float = 0.05, setup_delay_range: tuple[float, float] = (0.05, 0.15)):
        self.provider_id = "Provider_A"
        self.failure_rate = failure_rate
        self.setup_delay_range = setup_delay_range
        self._listener: Optional[Callable[[ProviderEvent], Awaitable[None]]] = None

    def register_event_listener(self, listener: Callable[[ProviderEvent], Awaitable[None]]) -> None:
        self._listener = listener

    async def _emit(self, event: ProviderEvent) -> None:
        if self._listener:
            await self._listener(event)

    async def initiate_call(self, call_id: str, to_phone: str) -> str:
        provider_call_id = f"pA_{uuid.uuid4().hex[:8]}"
        asyncio.create_task(self._simulate_call_lifecycle(call_id, provider_call_id))
        return provider_call_id

    async def cancel_call(self, provider_call_id: str) -> bool:
        await self._emit(
            ProviderEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                provider_call_id=provider_call_id,
                call_id="",
                event_type=EventType.FAILED,
                error_reason="CANCELLED_BY_SYSTEM",
            )
        )
        return True

    async def _simulate_call_lifecycle(self, call_id: str, provider_call_id: str) -> None:
        delay = random.uniform(*self.setup_delay_range)
        await asyncio.sleep(delay)

        # 1. INITIATED
        await self._emit(
            ProviderEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                provider_call_id=provider_call_id,
                call_id=call_id,
                event_type=EventType.INITIATED,
            )
        )

        await asyncio.sleep(0.05)
        # 2. RINGING
        await self._emit(
            ProviderEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                provider_call_id=provider_call_id,
                call_id=call_id,
                event_type=EventType.RINGING,
            )
        )

        await asyncio.sleep(0.1)

        # Check for failure
        if random.random() < self.failure_rate:
            await self._emit(
                ProviderEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    provider_call_id=provider_call_id,
                    call_id=call_id,
                    event_type=EventType.FAILED,
                    error_reason="NO_ANSWER_OR_BUSY",
                )
            )
            return

        # 3. ANSWERED
        await self._emit(
            ProviderEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                provider_call_id=provider_call_id,
                call_id=call_id,
                event_type=EventType.ANSWERED,
            )
        )

        # Call duration simulation
        await asyncio.sleep(random.uniform(0.2, 0.5))

        # 4. COMPLETED
        await self._emit(
            ProviderEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                provider_call_id=provider_call_id,
                call_id=call_id,
                event_type=EventType.COMPLETED,
            )
        )