"""LLM Model representing available language models from various providers."""
from datetime import datetime
from sqlalchemy import Column, String, Integer, TIMESTAMP, Boolean, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class LLMModel(Base):
    """LLM Model - available language models from various providers."""

    __tablename__ = "llm_models"

    llm_model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)  # openai/gemini/anthropic/openrouter
    model_name = Column(String(100), nullable=False)  # e.g., "gpt-4o", "gemini-pro"
    context_window = Column(Integer, nullable=False)  # Max context window in tokens
    cost_per_1k_input_tokens = Column(DECIMAL(10, 6), nullable=False)  # Input token cost (USD)
    cost_per_1k_output_tokens = Column(DECIMAL(10, 6), nullable=False)  # Output token cost (USD)
    is_active = Column(Boolean, nullable=False, default=True)  # Model availability
    capabilities = Column(JSONB)  # Model capabilities (e.g., {"vision": true})
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    tenant_configs = relationship("TenantLLMConfig", back_populates="llm_model")
    agent_configs = relationship("AgentConfig", back_populates="llm_model")

    def __repr__(self):
        return f"<LLMModel(provider={self.provider}, model_name={self.model_name})>"
