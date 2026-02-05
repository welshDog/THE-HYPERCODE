from pydantic import BaseModel, Field
from typing import Any, Optional, Dict
from datetime import datetime, timezone
import uuid

class MessageEnvelope(BaseModel):
    """
    Standard envelope for all agent-to-agent and system communications.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sender_id: str
    recipient_id: Optional[str] = None  # None implies broadcast or specific topic
    message_type: str  # e.g., "task_request", "task_response", "system_event"
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None  # To link request/response pairs
