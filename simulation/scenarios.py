import asyncio
import os
import random
from app.domain.enums import AgentState, CallState
from app.providers.provider_a import MockProviderA
from app.providers.provider_b import MockProviderB
from app.repositories.csv_repository import InMemoryRepository
from app.services.call_allocator import CallAllocator
from app.services.event_processor import EventProcessor
from app.services.predictive_pacing import PredictivePacingEngine
from app.services.progressive_dialer import ProgressiveDialer
from app.services.provider_health import ProviderHealthMonitor
from app.services.safety_controller import SafetyController
from simulation.metrics import SimulationMetrics


def setup_demo_csv_files(agents_count: int, borrowers_count: int) -> tuple[str, str]:
    os.makedirs("data", exist_ok=True)
    agents_path = "data/agents.csv"
    borrowers_path = "data/borrowers.csv"

    with open(agents_path, "w", encoding="utf-8") as f:
        f.write("id,name,status\n")
        for i in range(1, agents_count + 1):
            f.write(f"A{i},Agent {i},AVAILABLE\n")

    with open(borrowers_path, "w", encoding="utf-8") as f:
        f.write("id,name,phone,priority\n")
        for i in range(1, borrowers_count + 1):
            priority = random.randint(1, 3)
            f.write(f"B{i},Borrower {i},99999{i:05d},{priority}\n")

    return agents_path, borrowers_path


async def run_simulation_engine(
    mode: str = "predictive",
    provider_type: str = "A",
    agents_count: int = 20,
    borrowers_count: int = 100,
    duration: float = 5.0,
    seed: int = 42,
) -> SimulationMetrics:
    random.seed(seed)
    agents_csv, borrowers_csv = setup_demo_csv_files(agents_count, borrowers_count)

    repo = InMemoryRepository()
    repo.load_from_csv(agents_csv, borrowers_csv)

    health_monitor = ProviderHealthMonitor()
    event_processor = EventProcessor(repo, health_monitor)

    if provider_type.upper() == "B":
        provider = MockProviderB()
    else:
        provider = MockProviderA()

    provider.register_event_listener(event_processor.process_event)

    allocator = CallAllocator(repo, provider)
    safety_controller = SafetyController(allocator, health_monitor)
    pacing_engine = PredictivePacingEngine(repo, health_monitor)
    progressive_dialer = ProgressiveDialer(allocator)

    start_time = asyncio.get_event_loop().time()
    end_time = start_time + duration

    peak_ringing = 0
    peak_connected = 0
    busy_ticks = 0
    total_ticks = 0

    while asyncio.get_event_loop().time() < end_time:
        total_ticks += 1

        if mode.lower() == "progressive":
            await progressive_dialer.execute_step()
        else:
            requested = pacing_engine.calculate_desired_calls()
            await safety_controller.request_dialing(requested)

        # Track metrics
        current_ringing = sum(1 for c in repo.calls.values() if c.status == CallState.RINGING)
        current_connected = sum(1 for c in repo.calls.values() if c.status == CallState.CONNECTED)
        busy_agents = sum(1 for a in repo.agents.values() if a.status != AgentState.AVAILABLE)

        peak_ringing = max(peak_ringing, current_ringing)
        peak_connected = max(peak_connected, current_connected)
        busy_ticks += busy_agents

        await asyncio.sleep(0.05)

    elapsed = asyncio.get_event_loop().time() - start_time
    utilization = (busy_ticks / max(1, total_ticks * agents_count)) * 100.0

    metrics = SimulationMetrics(
        mode=mode,
        provider=provider.provider_id,
        agents_count=agents_count,
        borrowers_count=borrowers_count,
        duration_seconds=elapsed,
        calls_attempted=len(repo.calls),
        calls_answered=sum(1 for c in repo.calls.values() if c.answered_at is not None),
        calls_completed=sum(1 for c in repo.calls.values() if c.status == CallState.COMPLETED),
        calls_failed=sum(1 for c in repo.calls.values() if c.status == CallState.FAILED),
        peak_ringing_calls=peak_ringing,
        peak_connected_calls=peak_connected,
        duplicate_events=event_processor.duplicate_events_count,
        out_of_order_events=event_processor.out_of_order_events_count,
        reservation_conflicts=allocator.reservation_conflicts,
        safety_violations_prevented=safety_controller.safety_violations_prevented,
        agent_utilization_pct=utilization,
    )
    return metrics