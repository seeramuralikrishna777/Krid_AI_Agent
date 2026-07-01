from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

# Media Library Item
class MediaItem(BaseModel):
    url: str
    type: str  # "image" or "document"
    filename: Optional[str] = None

# Tenant Configuration
class Tenant(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    system_prompt: str
    media_library: Dict[str, MediaItem] = Field(default_factory=dict)

    class Config:
        populate_by_name = True

# Session Model
class ChatSession(BaseModel):
    id: str = Field(..., alias="_id") # format: {tenant_id}_{customer_phone}
    customer_phone: str
    tenant_id: str
    status: str = "WAITING_FOR_BOT"  # WAITING_FOR_BOT, AGENT_RESPONDING, RESOLVED, NEEDS_HUMAN
    sentiment_score: float = 3.0     # 1 to 5 scale (default neutral 3.0)
    context_variables: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True

# Message Audit Log Model
class MessageLog(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    session_id: str
    tenant_id: str
    customer_phone: str
    direction: str  # "inbound" or "outbound"
    type: str       # "text", "image", "document"
    content: str
    media_url: Optional[str] = None
    mime_type: Optional[str] = None
    filename: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True

# Broadcast campaign request
class BroadcastRequest(BaseModel):
    tenant_id: str
    numbers: List[str]
    template_name: str  # e.g., "new_catalog_promo" or "service_reminder"
    custom_message: Optional[str] = None

# Simulator input schema
class SimulatedMessageInput(BaseModel):
    tenant_id: str
    customer_phone: str
    content: str
    type: str = "text" # "text", "image", "document"
    media_url: Optional[str] = None
    mime_type: Optional[str] = None
    filename: Optional[str] = None
