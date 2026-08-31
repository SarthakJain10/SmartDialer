import asyncio
import random
import uuid
from typing import Callable, Awaitable, Optional
from app.domain.enums import EventType
from app.domain.events import ProviderEvent


class MockProviderB:
    """
    Unreliable Telecom Provider: slower setup, higher failure rate (~20%),
    generates duplicate events (~10%) and out-of-order events (~15%).
    """

    def __init__(
        self,
        failure_rate: float = 0.20,
        duplicate_prob: float = 0.10,
        out_of_order_prob: float = 0.15,
        setup_delay_range: tuple[float, float] = (0.2, 0.5),
    ):
        self.provider_id = "Provider_B"
        self.failure_rate = failure_rate
        self.duplicate_prob = duplicate_prob
        self.out_of_order_prob = out_of_order_prob
        self.setup_delay_range = setup_delay_range
        self._listener: Optional[Callable[[ProviderEvent], Awaitable[None]]] = None

    def register_event_listener(self, listener: Callable[[ProviderEvent], Awaitable[None]]) -> None:
        self._listener = listener

    async def _emit(self, event: ProviderEvent, duplicate: bool = False) -> None:
        if self._listener:
            await self._listener(event)
            if duplicate or (random.random() < self.duplicate_prob):
                # Emit identical event again immediately or shortly after
                await asyncio.sleep(0.01)
                await self._listener(event)

    async def initiate_call(self, call_id: str, to_phone: str) -> str:
        provider_call_id = f"pB_{uuid.uuid4().hex[:8]}"
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
        await asyncio.sleep(random.uniform(*self.setup_delay_range))

        init_evt = ProviderEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            provider_call_id=provider_call_id,
            call_id=call_id,
            event_type=EventType.INITIATED,
        )
        await self._emit(init_evt)

        await asyncio.sleep(0.1)

        ring_evt = ProviderEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            provider_call_id=provider_call_id,
            call_id=call_id,
            event_type=EventType.RINGING,
        )
        await self._emit(ring_evt)

        if random.random() < self.failure_rate:
            await self._emit(
                ProviderEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    provider_call_id=provider_call_id,
                    call_id=call_id,
                    event_type=EventType.FAILED,
                    error_reason="PROVIDER_NETWORK_ERROR",
                )
            )
            return

        ans_evt = ProviderEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            provider_call_id=provider_call_id,
            call_id=call_id,
            event_type=EventType.ANSWERED,
        )
        comp_evt = ProviderEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            provider_call_id=provider_call_id,
            call_id=call_id,
            event_type=EventType.COMPLETED,
        )

        # Out of order simulation: emit COMPLETED before ANSWERED
        if random.random() < self.out_of_order_prob:
            await self._emit(comp_evt)
            await asyncio.sleep(0.05)
            await self._emit(ans_evt)  # Stale event attempt
        else:
            await self._emit(ans_evt)
            await asyncio.sleep(0.2)
            await self._emit(comp_evt)