"""Agent configuration and agent-tool junction models."""
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, TIMESTAMP, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class AgentConfig(Base):
    """Agent Config - domain-specific agent configurations."""

    __tablename__ = "agent_configs"

    agent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)  # Agent name (e.g., "AgentDebt")
    prompt_template = Column(Text, nullable=False)  # Agent system prompt template
    llm_model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.llm_model_id"), nullable=False)
    default_output_format_id = Column(UUID(as_uuid=True), ForeignKey("output_formats.format_id"))
    description = Column(Text)  # Agent description
    is_active = Column(Boolean, nullable=False, default=True)  # Agent availability
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    llm_model = relationship("LLMModel", back_populates="agent_configs")
    output_format = relationship("OutputFormat", back_populates="agent_configs")
    agent_tools = relationship("AgentTools", back_populates="agent")
    tenant_permissions = relationship("TenantAgentPermission", back_populates="agent")

    def __repr__(self):
        return f"<AgentConfig(name={self.name}, llm_model_id={self.llm_model_id})>"


class AgentTools(Base):
    """Agent Tools - many-to-many relationship between agents and tools with priority."""

    __tablename__ = "agent_tools"
    __table_args__ = (
        PrimaryKeyConstraint('agent_id', 'tool_id'),
    )

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.agent_id"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tool_configs.tool_id"), nullable=False)
    priority = Column(Integer, nullable=False)  # Tool priority (1=highest) for pre-filtering
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    agent = relationship("AgentConfig", back_populates="agent_tools")
    tool = relationship("ToolConfig", back_populates="agent_tools")

    def __repr__(self):
        return f"<AgentTools(agent_id={self.agent_id}, tool_id={self.tool_id}, priority={self.priority})>"
