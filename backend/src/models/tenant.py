"""Tenant model representing organizations using the system."""
from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class Tenant(Base):
    """Tenant model - represents a company/organization using AgentHub."""

    __tablename__ = "tenants"

    tenant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    sessions = relationship("Session", back_populates="tenant")
    agent_permissions = relationship("TenantAgentPermission", back_populates="tenant")
    tool_permissions = relationship("TenantToolPermission", back_populates="tenant")
    llm_config = relationship("TenantLLMConfig", back_populates="tenant", uselist=False)

    def __repr__(self):
        return f"<Tenant(tenant_id={self.tenant_id}, name={self.name}, status={self.status})>"
