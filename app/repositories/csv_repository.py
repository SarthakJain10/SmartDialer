import csv
import os
from datetime import datetime
from typing import Dict, List, Optional
from app.domain.agent import Agent
from app.domain.borrower import Borrower
from app.domain.call import Call
from app.domain.enums import AgentState


class InMemoryRepository:
    """
    CSV Initializer + In-Memory Repository.
    Design Choice: CSV files serve strictly as the initial dataset loader.
    All runtime state management is handled in memory.
    In production, this layer would be replaced by a Persistent database layer.
    """

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.borrowers: Dict[str, Borrower] = {}
        self.calls: Dict[str, Call] = {}
        self.call_by_provider_id: Dict[str, str] = {}  # provider_call_id -> call_id

    def load_from_csv(self, agents_csv: str, borrowers_csv: str) -> None:
        self.agents.clear()
        self.borrowers.clear()
        self.calls.clear()
        self.call_by_provider_id.clear()

        if os.path.exists(agents_csv):
            with open(agents_csv, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = AgentState(row.get("status", "AVAILABLE"))
                    agent = Agent(id=row["id"], name=row["name"], status=status)
                    self.agents[agent.id] = agent

        if os.path.exists(borrowers_csv):
            with open(borrowers_csv, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    borrower = Borrower(
                        id=row["id"],
                        name=row["name"],
                        phone=row["phone"],
                        priority=int(row.get("priority", 1)),
                    )
                    self.borrowers[borrower.id] = borrower

    def get_available_agents(self) -> List[Agent]:
        return [a for a in self.agents.values() if a.status == AgentState.AVAILABLE]

    def get_next_borrower(self) -> Optional[Borrower]:
        """Priority DESC, then least attempted first."""
        eligible = [b for b in self.borrowers.values() if not b.is_contacted]
        if not eligible:
            return None
        eligible.sort(key=lambda b: (-b.priority, b.attempts, b.last_attempted_at or datetime.min))
        return eligible[0]

    def add_call(self, call: Call) -> None:
        self.calls[call.id] = call
        if call.provider_call_id:
            self.call_by_provider_id[call.provider_call_id] = call.id

    def map_provider_call_id(self, provider_call_id: str, call_id: str) -> None:
        self.call_by_provider_id[provider_call_id] = call_id
        if call_id in self.calls:
            self.calls[call_id].provider_call_id = provider_call_id

    def get_call_by_provider_id(self, provider_call_id: str) -> Optional[Call]:
        call_id = self.call_by_provider_id.get(provider_call_id)
        if call_id:
            return self.calls.get(call_id)
        return None