from collections import deque
from app.domain.enums import ProviderHealthStatus


class ProviderHealthMonitor:
    """Tracks provider success, failure, and latency to evaluate status."""

    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self._results: deque[bool] = deque(maxlen=window_size)
        self.duplicate_count: int = 0
        self.out_of_order_count: int = 0

    def record_outcome(self, success: bool) -> None:
        self._results.append(success)

    def record_duplicate(self) -> None:
        self.duplicate_count += 1

    def record_out_of_order(self) -> None:
        self.out_of_order_count += 1

    def get_status(self) -> ProviderHealthStatus:
        if len(self._results) < 5:
            return ProviderHealthStatus.HEALTHY

        failures = sum(1 for res in self._results if not res)
        failure_rate = failures / len(self._results)

        if failure_rate >= 0.40:
            return ProviderHealthStatus.CRITICAL
        elif failure_rate >= 0.20:
            return ProviderHealthStatus.DEGRADED
        return ProviderHealthStatus.HEALTHY