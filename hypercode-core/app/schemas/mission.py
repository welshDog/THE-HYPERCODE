from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class MissionState(str, Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    DEFERRED = "deferred"

class MissionRequest(BaseModel):
    title: str
    priority: int = Field(default=50, ge=0, le=100)
    payload: Dict[str, Any] = Field(default_factory=dict)
    dependencies: Optional[list[str]] = None

class MissionStatus(BaseModel):
    id: str
    title: str
    state: MissionState
    priority: int
    agent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
