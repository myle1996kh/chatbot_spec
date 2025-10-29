"""Session model for tracking conversation sessions."""
from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class ChatSession(Base):
    """ChatSession - conversation sessions for tracking multi-turn interactions."""

    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False)
    user_id = Column(String(255), nullable=False)  # User identifier from JWT
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.agent_id"))
    thread_id = Column(String(500))  # LangGraph thread ID
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    last_message_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    session_metadata = Column("metadata", JSONB)  # Additional session metadata (mapped to "metadata" column)

    # Relationships
    tenant = relationship("Tenant", back_populates="sessions")
    agent = relationship("AgentConfig")
    messages = relationship("Message", back_populates="session")

    def __repr__(self):
        return f"<ChatSession(session_id={self.session_id}, tenant_id={self.tenant_id}, user_id={self.user_id})>"
