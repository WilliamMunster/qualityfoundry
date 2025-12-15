from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Requirement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    text: str
    domain: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CaseRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    requirement_id: int = Field(index=True)
    objective_id: str
    title: str
    payload_json: str  # serialized TestCase JSON
    created_at: datetime = Field(default_factory=datetime.utcnow)
