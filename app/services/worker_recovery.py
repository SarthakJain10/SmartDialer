from datetime import datetime, timezone, timedelta
from app.domain.enums import AgentState, CallState
from app.repositories.csv_repository import InMemoryRepository


class WorkerCrashRecovery:
    """Simulates stale task cleanup and orphan reservation recovery."""

    def __init__(self, repo: InMemoryRepository, stale_timeout_seconds: float = 5.0):
        self.repo = repo
        self.stale_timeout_seconds = stale_timeout_seconds
        self.recovered_agents_count: int = 0

    async def cleanup_stale_reservations(self) -> int:
        now = datetime.now(timezone.utc)
        recovered = 0

        for agent in list(self.repo.agents.values()):
            async with agent.lock:
                if agent.status in {AgentState.RESERVED, AgentState.DIALING}:
                    elapsed = (now - agent.last_state_change).total_seconds()
                    if elapsed > self.stale_timeout_seconds:
                        # Clean up associated call if stranded
                        if agent.current_call_id and agent.current_call_id in self.repo.calls:
                            call = self.repo.calls[agent.current_call_id]
                            call.transition_to(CallState.FAILED)
                        
                        agent.transition_to(AgentState.AVAILABLE)
                        recovered += 1

        self.recovered_agents_count += recovered
        return recovered