"""Pydantic schemas for chat requests and responses."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message content")
    user_id: str = Field(..., description="User identifier (external user ID from auth system)")
    session_id: Optional[str] = Field(None, description="Existing session UUID as string for follow-up messages")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata (e.g., jwt_token for external API calls)")


class LLMModelInfo(BaseModel):
    """LLM model information."""

    llm_model_id: str = Field(..., description="LLM model UUID")
    model_class: str = Field(..., description="LLM class name (e.g., ChatOpenAI, ChatOpenRouter)")
    model_name: str = Field(..., description="Model name (e.g., openai/gpt-4o-mini)")


class ToolCallInfo(BaseModel):
    """Tool call information."""

    tool_name: str = Field(..., description="Name of the tool that was called")
    tool_args: Dict[str, Any] = Field(..., description="Arguments passed to the tool")
    tool_id: str = Field(..., description="Unique identifier for this tool call")


class ResponseMetadata(BaseModel):
    """Extended metadata for chat responses."""

    agent_id: str = Field(..., description="Agent UUID that processed the request")
    tenant_id: str = Field(..., description="Tenant UUID")
    duration_ms: Optional[float] = Field(None, description="Request processing duration in milliseconds")
    status: Optional[str] = Field(None, description="Processing status")
    llm_model: Optional[LLMModelInfo] = Field(None, description="LLM model information")
    tool_calls: Optional[List[ToolCallInfo]] = Field(default_factory=list, description="Tools called during processing")
    extracted_entities: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Entities extracted from user message (e.g., tax_code, salesman)")


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""

    session_id: str = Field(..., description="Session UUID")
    message_id: str = Field(..., description="Message UUID")
    response: Dict[str, Any] = Field(..., description="Agent response data (structure varies by agent)")
    agent: str = Field(..., description="Agent that processed the request")
    intent: str = Field(..., description="Detected user intent")
    format: str = Field(..., description="Output format type (text/json/table)")
    renderer_hint: Dict[str, Any] = Field(default_factory=dict, description="UI rendering hints")
    metadata: ResponseMetadata = Field(..., description="Response metadata with LLM model info, tool calls, and extracted entities")


class ErrorResponse(BaseModel):
    """Error response schema."""

    status: str = Field(default="error")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")


class SessionSummary(BaseModel):
    """Session summary schema."""

    session_id: UUID
    user_id: str = Field(..., description="User identifier")
    created_at: datetime
    last_message_at: datetime
    message_count: int
    last_message_preview: Optional[str] = Field(None, description="Preview of the last message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")


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
    thread_id: Optional[str] = Field(None, description="LangGraph thread ID")
    created_at: datetime
    last_message_at: datetime
    messages: List[Dict[str, Any]] = Field(..., description="List of messages in the session")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")


class SessionListResponse(BaseModel):
    """Response schema for session list endpoint."""

    sessions: List[SessionSummary]
    total: int
    limit: int
    offset: int
