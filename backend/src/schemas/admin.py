

"""Pydantic schemas for admin API."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Agent Management Schemas

class AgentCreateRequest(BaseModel):
    """Request to create a new agent."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    prompt_template: str = Field(..., min_length=1)
    llm_model_id: str = Field(..., description="UUID of LLM model to use")
    tool_ids: List[str] = Field(default_factory=list, description="List of tool UUIDs")
    is_active: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    """Request to update an existing agent."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    prompt_template: Optional[str] = Field(None, min_length=1)
    llm_model_id: Optional[str] = None
    tool_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Response for agent details."""
    agent_id: str
    name: str
    description: Optional[str]
    prompt_template: str
    llm_model_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentListResponse(BaseModel):
    """Response for list of agents."""
    agents: List[AgentResponse]
    total: int


# Tool Management Schemas

class ToolCreateRequest(BaseModel):
    """Request to create a new tool."""
    base_tool_id: str = Field(..., description="UUID of base tool template")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    config: Dict[str, Any] = Field(..., description="Tool-specific configuration (e.g., URL, method, headers)")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema for tool inputs")
    is_active: bool = Field(default=True)


class ToolUpdateRequest(BaseModel):
    """Request to update an existing tool."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    config: Optional[Dict[str, Any]] = None
    input_schema: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ToolResponse(BaseModel):
    """Response for tool details."""
    tool_id: str
    base_tool_id: str
    name: str
    description: Optional[str]
    config: Dict[str, Any]
    input_schema: Dict[str, Any]
    is_active: bool
    created_at: datetime
    base_tool: Optional[Dict[str, Any]] = None


class ToolListResponse(BaseModel):
    """Response for list of tools."""
    tools: List[ToolResponse]
    total: int


# Tenant Permission Schemas

class TenantPermissionsResponse(BaseModel):
    """Response for tenant permissions."""
    tenant_id: str
    enabled_agents: List[Dict[str, Any]] = Field(default_factory=list)
    enabled_tools: List[Dict[str, Any]] = Field(default_factory=list)


class PermissionUpdateRequest(BaseModel):
    """Request to update tenant permissions."""
    agent_permissions: Optional[List[Dict[str, bool]]] = Field(
        None,
        description="List of {agent_id: str, enabled: bool}"
    )
    tool_permissions: Optional[List[Dict[str, bool]]] = Field(
        None,
        description="List of {tool_id: str, enabled: bool}"
    )


# Knowledge Base Schemas

class DocumentIngestRequest(BaseModel):
    """Request to ingest documents into knowledge base."""
    documents: List[str] = Field(..., min_items=1, description="List of document texts to ingest")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="Optional metadata for each document")


class DocumentIngestResponse(BaseModel):
    """Response for document ingestion."""
    success: bool
    tenant_id: str
    collection_name: str
    document_count: int
    document_ids: List[str]


class KnowledgeBaseStatsResponse(BaseModel):
    """Response for knowledge base statistics."""
    success: bool
    tenant_id: str
    collection_name: str
    document_count: int


# Common Response Schemas

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
