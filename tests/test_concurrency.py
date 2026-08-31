import asyncio
import pytest
from app.providers.provider_a import MockProviderA
from app.repositories.csv_repository import InMemoryRepository
from app.services.call_allocator import CallAllocator
from simulation.scenarios import setup_demo_csv_files


@pytest.mark.asyncio
async def test_concurrent_agent_reservation():
    agents_csv, borrowers_csv = setup_demo_csv_files(1, 10)
    repo = InMemoryRepository()
    repo.load_from_csv(agents_csv, borrowers_csv)

    provider = MockProviderA()
    allocator = CallAllocator(repo, provider)

    # Launch 5 concurrent workers attempting to reserve Agent A1 simultaneously
    tasks = [allocator.reserve_and_allocate("A1") for _ in range(5)]
    results = await asyncio.gather(*tasks)

    successful_allocations = [r for r in results if r is not None]
    
    # Invariant: Exactly one worker wins reservation
    assert len(successful_allocations) == 1
    assert allocator.reservation_conflicts == 4