"""Tenant-specific LLM configuration with encrypted API keys."""
from datetime import datetime
from sqlalchemy import Column, Text, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class TenantLLMConfig(Base):
    """Tenant LLM Config - tenant-specific LLM settings and encrypted API keys."""

    __tablename__ = "tenant_llm_configs"

    config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, unique=True)
    llm_model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.llm_model_id"), nullable=False)
    encrypted_api_key = Column(Text, nullable=False)  # Fernet-encrypted API key
    rate_limit_rpm = Column(Integer, default=60)  # Requests per minute limit
    rate_limit_tpm = Column(Integer, default=10000)  # Tokens per minute limit
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="llm_config")
    llm_model = relationship("LLMModel", back_populates="tenant_configs")

    def __repr__(self):
        return f"<TenantLLMConfig(tenant_id={self.tenant_id}, llm_model_id={self.llm_model_id})>"
