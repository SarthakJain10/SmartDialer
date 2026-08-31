import math
from app.domain.enums import CallState
from app.repositories.csv_repository import InMemoryRepository
from app.services.provider_health import ProviderHealthMonitor


class PredictivePacingEngine:
    """
    Transparent Heuristic Pacing Engine.
    Formula:
        estimated_answer_rate = answered_calls / max(1, completed_calls) [default fallback 0.30]
        target_answers = available_capacity * utilization_target
        desired_calls = math.ceil(target_answers / estimated_answer_rate) - ringing_calls

    IMPORTANT INVARIANT: This class MUST NEVER call TelecomProvider directly.
    It returns requested dial counts to the SafetyController.
    """

    def __init__(self, repo: InMemoryRepository, health_monitor: ProviderHealthMonitor, utilization_target: float = 0.85):
        self.repo = repo
        self.health_monitor = health_monitor
        self.utilization_target = utilization_target

    def calculate_desired_calls(self) -> int:
        available_agents = len(self.repo.get_available_agents())
        if available_agents == 0:
            return 0

        # Calculate historical answer rate
        total_finished = sum(
            1 for c in self.repo.calls.values() if c.status in {CallState.COMPLETED, CallState.FAILED}
        )
        answered = sum(
            1 for c in self.repo.calls.values() if c.answered_at is not None or c.status == CallState.COMPLETED
        )

        if total_finished < 5:
            estimated_answer_rate = 0.30  # Conservative cold-start default
        else:
            estimated_answer_rate = max(0.10, answered / total_finished)

        # Count active in-flight calls currently ringing
        ringing_calls = sum(1 for c in self.repo.calls.values() if c.status == CallState.RINGING)

        target_answers = available_agents * self.utilization_target
        desired_total_calls = math.ceil(target_answers / estimated_answer_rate)

        # Net new calls needed
        desired_new_calls = max(0, desired_total_calls - ringing_calls)
        return desired_new_calls