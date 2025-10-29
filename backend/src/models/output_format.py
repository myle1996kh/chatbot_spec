"""Output Format definitions for structured output."""
from datetime import datetime
from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class OutputFormat(Base):
    """Output Format - response format definitions for structured output."""

    __tablename__ = "output_formats"

    format_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)  # structured_json/markdown_table/chart_data/summary_text
    schema = Column(JSONB)  # JSON schema for output structure
    renderer_hint = Column(JSONB)  # UI rendering hints (type, fields)
    description = Column(Text)  # Format description
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    tool_configs = relationship("ToolConfig", back_populates="output_format")
    agent_configs = relationship("AgentConfig", back_populates="output_format")

    def __repr__(self):
        return f"<OutputFormat(name={self.name})>"
