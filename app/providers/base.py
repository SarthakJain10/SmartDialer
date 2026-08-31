from typing import Protocol, Callable, Awaitable
from app.domain.events import ProviderEvent


class TelecomProvider(Protocol):
    provider_id: str

    async def initiate_call(self, call_id: str, to_phone: str) -> str:
        """Initiates call and returns a provider_call_id."""
        ...

    async def cancel_call(self, provider_call_id: str) -> bool:
        """Cancels an ongoing outbound call attempt."""
        ...

    def register_event_listener(self, listener: Callable[[ProviderEvent], Awaitable[None]]) -> None:
        """Registers callback for receiving async telecommunication events."""
        ...