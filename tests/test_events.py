import pytest
from app.domain.enums import CallState, EventType
from app.domain.events import ProviderEvent
from app.repositories.csv_repository import InMemoryRepository
from app.services.event_processor import EventProcessor
from app.services.provider_health import ProviderHealthMonitor
from simulation.scenarios import setup_demo_csv_files


@pytest.mark.asyncio
async def test_event_processor_idempotency_and_out_of_order():
    agents_csv, borrowers_csv = setup_demo_csv_files(1, 5)
    repo = InMemoryRepository()
    repo.load_from_csv(agents_csv, borrowers_csv)
    health = ProviderHealthMonitor()
    processor = EventProcessor(repo, health)

    # Create dummy call
    from app.domain.call import Call
    call = Call(id="call_test", borrower_id="B1", agent_id="A1", status=CallState.INITIATED)
    repo.add_call(call)

    evt = ProviderEvent(event_id="evt_1", provider_call_id="", call_id="call_test", event_type=EventType.RINGING)

    # Process first time
    await processor.process_event(evt)
    assert call.status == CallState.RINGING

    # Process duplicate event
    await processor.process_event(evt)
    assert processor.duplicate_events_count == 1