from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime, timezone

class AgentStatus(str, Enum):
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

class AgentCapability(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"

class AgentMetadata(BaseModel):
    id: str
    name: str
    role: str = "general"
    version: str
    capabilities: List[str] = []
    topics: List[str] = []
    health_url: Optional[str] = None
    status: AgentStatus = AgentStatus.ACTIVE
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        from_attributes = True

class AgentRegistrationRequest(BaseModel):
    name: str
    role: str
    version: str = Field(default="1.0.0")
    capabilities: List[str] = []
    topics: List[str] = []
    health_url: Optional[str] = None
    dedup_key: Optional[str] = None

class AgentHeartbeat(BaseModel):
    agent_id: str
    status: AgentStatus
    load: float = 0.0
