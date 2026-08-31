from pydantic import BaseModel


class SimulationMetrics(BaseModel):
    mode: str
    provider: str
    agents_count: int
    borrowers_count: int
    duration_seconds: float
    
    calls_attempted: int = 0
    calls_answered: int = 0
    calls_completed: int = 0
    calls_failed: int = 0
    
    peak_ringing_calls: int = 0
    peak_connected_calls: int = 0
    
    duplicate_events: int = 0
    out_of_order_events: int = 0
    reservation_conflicts: int = 0
    abandoned_calls: int = 0
    safety_violations_prevented: int = 0
    
    agent_utilization_pct: float = 0.0

    def print_summary(self) -> None:
        print("\n" + "=" * 50)
        print("      SMART DIALER SIMULATION SUMMARY      ")
        print("=" * 50)
        print(f"Mode:                        {self.mode}")
        print(f"Provider:                    {self.provider}")
        print(f"Agents:                      {self.agents_count}")
        print(f"Borrowers:                   {self.borrowers_count}")
        print(f"Duration:                    {self.duration_seconds:.2f}s")
        print("-" * 50)
        print(f"Calls Attempted:             {self.calls_attempted}")
        print(f"Calls Answered:              {self.calls_answered}")
        print(f"Calls Completed:             {self.calls_completed}")
        print(f"Calls Failed:                {self.calls_failed}")
        print("-" * 50)
        print(f"Peak Ringing Calls:          {self.peak_ringing_calls}")
        print(f"Peak Connected Calls:        {self.peak_connected_calls}")
        print(f"Agent Utilization:           {self.agent_utilization_pct:.1f}%")
        print("-" * 50)
        print(f"Duplicate Events Handled:    {self.duplicate_events}")
        print(f"Out-of-Order Events Handled: {self.out_of_order_events}")
        print(f"Reservation Conflicts:       {self.reservation_conflicts}")
        print(f"Safety Violations Prevented: {self.safety_violations_prevented}")
        print(f"Abandoned Calls:             {self.abandoned_calls}")
        print("=" * 50 + "\n")