"""Message model for individual chat messages within sessions."""
from datetime import datetime
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class Message(Base):
    """Message - individual chat messages within sessions."""

    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False)
    role = Column(String(50), nullable=False)  # user/assistant/system
    content = Column(Text, nullable=False)  # Message content
    created_at = Column("timestamp", TIMESTAMP, nullable=False, default=datetime.utcnow)  # Mapped to "timestamp" column
    message_metadata = Column("metadata", JSONB)  # Additional metadata (intent, tool_calls, tokens)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<Message(message_id={self.message_id}, session_id={self.session_id}, role={self.role})>"
