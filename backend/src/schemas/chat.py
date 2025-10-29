"""Pydantic schemas for chat requests and responses."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message content")
    session_id: Optional[UUID] = Field(None, description="Existing session ID for follow-up messages")


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""

    status: str = Field(..., description="Response status: success/error/clarification_needed")
    agent: str = Field(..., description="Agent that processed the request")
    intent: str = Field(..., description="Detected user intent")
    data: Dict[str, Any] = Field(..., description="Response data (structure varies by agent)")
    format: str = Field(..., description="Output format type")
    renderer_hint: Optional[Dict[str, Any]] = Field(None, description="UI rendering hints")
    metadata: Dict[str, Any] = Field(..., description="Response metadata")


class ErrorResponse(BaseModel):
    """Error response schema."""

    status: str = Field(default="error")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")


class SessionSummary(BaseModel):
    """Session summary schema."""

    session_id: UUID
    agent_id: Optional[UUID] = None
    created_at: datetime
    last_message_at: datetime
    message_count: int


class Message(BaseModel):
    """Message schema."""

    message_id: UUID
    role: str = Field(..., description="Message role: user/assistant/system")
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class SessionDetail(BaseModel):
    """Detailed session information schema."""

    session_id: UUID
    tenant_id: UUID
    user_id: str
    agent_id: Optional[UUID] = None
    created_at: datetime
    last_message_at: datetime
    messages: List[Message]


class SessionListResponse(BaseModel):
    """Response schema for session list endpoint."""

    sessions: List[SessionSummary]
    total: int
    limit: int
    offset: int
