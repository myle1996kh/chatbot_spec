"""Tenant permission models for agents and tools."""
from datetime import datetime
from sqlalchemy import Column, Boolean, TIMESTAMP, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class TenantAgentPermission(Base):
    """Tenant Agent Permission - enables agents for specific tenants with optional overrides."""

    __tablename__ = "tenant_agent_permissions"
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'agent_id'),
    )

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.agent_id"), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)  # Permission status
    output_override_id = Column(UUID(as_uuid=True), ForeignKey("output_formats.format_id"))
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="agent_permissions")
    agent = relationship("AgentConfig", back_populates="tenant_permissions")
    output_format = relationship("OutputFormat")

    def __repr__(self):
        return f"<TenantAgentPermission(tenant_id={self.tenant_id}, agent_id={self.agent_id}, enabled={self.enabled})>"


class TenantToolPermission(Base):
    """Tenant Tool Permission - enables tools for specific tenants."""

    __tablename__ = "tenant_tool_permissions"
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'tool_id'),
    )

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tool_configs.tool_id"), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)  # Permission status
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="tool_permissions")
    tool = relationship("ToolConfig", back_populates="tenant_tool_permissions")

    def __repr__(self):
        return f"<TenantToolPermission(tenant_id={self.tenant_id}, tool_id={self.tool_id}, enabled={self.enabled})>"
