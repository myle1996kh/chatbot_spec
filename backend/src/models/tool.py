"""Tool configuration representing specific tool instances."""
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class ToolConfig(Base):
    """Tool Config - specific tool instances configured from base tools."""

    __tablename__ = "tool_configs"

    tool_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)  # Tool name (e.g., "get_customer_debt")
    base_tool_id = Column(UUID(as_uuid=True), ForeignKey("base_tools.base_tool_id"), nullable=False)
    config = Column(JSONB, nullable=False)  # Tool-specific config (endpoint, method, headers)
    input_schema = Column(JSONB, nullable=False)  # JSON schema for tool parameters
    output_format_id = Column(UUID(as_uuid=True), ForeignKey("output_formats.format_id"))
    description = Column(Text)  # Tool description for LLM
    is_active = Column(Boolean, nullable=False, default=True)  # Tool availability
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    base_tool = relationship("BaseTool", back_populates="tool_configs")
    output_format = relationship("OutputFormat", back_populates="tool_configs")
    agent_tools = relationship("AgentTools", back_populates="tool")
    tenant_tool_permissions = relationship("TenantToolPermission", back_populates="tool")

    def __repr__(self):
        return f"<ToolConfig(name={self.name}, base_tool_id={self.base_tool_id})>"
