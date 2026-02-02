
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime

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
    description: str
    version: str
    capabilities: List[AgentCapability] = []
    endpoint: str
    status: AgentStatus = AgentStatus.ACTIVE
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = []

class AgentRegistrationRequest(BaseModel):
    name: str
    description: str
    version: str
    capabilities: List[AgentCapability] = []
    endpoint: str
    tags: List[str] = []

class AgentHeartbeat(BaseModel):
    agent_id: str
    status: AgentStatus
    load: float = 0.0  # 0.0 to 1.0
