from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class MemoryBase(BaseModel):
    content: str
    type: str = Field(..., description="short-term, long-term, knowledge")
    userId: Optional[str] = None
    sessionId: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    keywords: Optional[List[str]] = []
    missionId: Optional[str] = None
    expiresAt: Optional[datetime] = None

class MemoryCreate(MemoryBase):
    pass

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    keywords: Optional[List[str]] = None
    expiresAt: Optional[datetime] = None

class MemoryResponse(MemoryBase):
    id: str
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

class MemorySearch(BaseModel):
    query: Optional[str] = None
    type: Optional[str] = None
    userId: Optional[str] = None
    sessionId: Optional[str] = None
    limit: int = 10
    offset: int = 0
