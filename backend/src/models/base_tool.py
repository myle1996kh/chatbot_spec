"""Base Tool template for tool types (HTTP, RAG, DB, OCR)."""
from datetime import datetime
from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class BaseTool(Base):
    """Base Tool - template for tool types (HTTP_GET, HTTP_POST, RAG, DB_QUERY, OCR)."""

    __tablename__ = "base_tools"

    base_tool_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False, unique=True)  # HTTP_GET/HTTP_POST/RAG/DB_QUERY/OCR
    handler_class = Column(String(255), nullable=False)  # Python class path
    description = Column(Text)  # Tool type description
    default_config_schema = Column(JSONB)  # JSON schema for config validation
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    tool_configs = relationship("ToolConfig", back_populates="base_tool")

    def __repr__(self):
        return f"<BaseTool(type={self.type}, handler_class={self.handler_class})>"
