from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Borrower(BaseModel):
    id: str
    name: str
    phone: str
    priority: int = 1  # Higher numerical value means higher priority
    last_attempted_at: Optional[datetime] = None
    attempts: int = 0
    is_contacted: bool = False