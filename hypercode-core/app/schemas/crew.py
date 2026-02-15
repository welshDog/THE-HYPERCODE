from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid

class AgentProfile(BaseModel):
    name: str
    role: str
    version: str = "1.0.0"
    description: Optional[str] = None
    tools: List[str] = []
    env_vars: Dict[str, str] = {}
    config_overrides: Dict[str, Any] = {}

class NetworkConfig(BaseModel):
    shared_context: bool = True
    redis_bus: bool = True
    vector_store_namespace: Optional[str] = None

class CrewManifest(BaseModel):
    crew_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    agents: List[AgentProfile]
    network_config: NetworkConfig = Field(default_factory=NetworkConfig)

class CrewStatus(str, Enum):
    ASSEMBLING = "assembling"
    READY = "ready"
    ACTIVE = "active"
    FAILED = "failed"
    DISBANDED = "disbanded"

class CrewAssemblyResponse(BaseModel):
    crew_id: str
    status: CrewStatus
    endpoints: Dict[str, str] = {} # agent_name -> endpoint_url
    message: Optional[str] = None
