import pytest
from app.domain.enums import ProviderHealthStatus
from app.providers.provider_a import MockProviderA
from app.repositories.csv_repository import InMemoryRepository
from app.services.call_allocator import CallAllocator
from app.services.provider_health import ProviderHealthMonitor
from app.services.safety_controller import SafetyController
from simulation.scenarios import setup_demo_csv_files


@pytest.mark.asyncio
async def test_safety_controller_clamps_overdialing():
    agents_csv, borrowers_csv = setup_demo_csv_files(3, 20)
    repo = InMemoryRepository()
    repo.load_from_csv(agents_csv, borrowers_csv)

    provider = MockProviderA()
    health_monitor = ProviderHealthMonitor()
    allocator = CallAllocator(repo, provider)
    safety_controller = SafetyController(allocator, health_monitor, max_dial_ahead_ratio=1.5)

    # Requested 10 calls, but only 3 available agents with 1.5 ratio -> max allowed math.ceil(3*1.5)=5, clamped to 3 available agents
    calls = await safety_controller.request_dialing(10)
    assert len(calls) <= 3