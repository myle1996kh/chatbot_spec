"""Output formatting utilities for agent responses."""
import json
from typing import Dict, Any, Literal
from langchain_core.output_parsers import BaseOutputParser
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AgentHubOutputParser(BaseOutputParser[Dict[str, Any]]):
    """Custom output parser for AgentHub responses."""

    format_type: Literal["structured_json", "markdown_table", "chart_data", "summary_text"] = "structured_json"

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse agent output into structured format.

        Args:
            text: Raw agent output

        Returns:
            Formatted output dictionary
        """
        if self.format_type == "structured_json":
            return self._parse_json(text)
        elif self.format_type == "markdown_table":
            return self._parse_table(text)
        elif self.format_type == "chart_data":
            return self._parse_chart(text)
        else:  # summary_text
            return {"content": text, "format": "text"}

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON output."""
        try:
            # Try to extract JSON from text
            if "```json" in text:
                # Extract JSON from markdown code block
                start = text.find("```json") + 7
                end = text.find("```", start)
                json_str = text[start:end].strip()
            elif "{" in text and "}" in text:
                # Extract JSON object
                start = text.find("{")
                end = text.rfind("}") + 1
                json_str = text[start:end]
            else:
                # Return as plain text
                return {"content": text, "format": "text"}

            data = json.loads(json_str)
            return {
                "content": data,
                "format": "structured_json"
            }
        except json.JSONDecodeError as e:
            logger.warning("json_parse_error", error=str(e), text=text[:200])
            return {"content": text, "format": "text"}

    def _parse_table(self, text: str) -> Dict[str, Any]:
        """Parse markdown table output."""
        return {
            "content": text,
            "format": "markdown_table"
        }

    def _parse_chart(self, text: str) -> Dict[str, Any]:
        """Parse chart data output."""
        try:
            # Try to extract chart data
            data = json.loads(text) if "{" in text else {"values": []}
            return {
                "content": data,
                "format": "chart_data"
            }
        except json.JSONDecodeError:
            return {"content": text, "format": "text"}

    def get_format_instructions(self) -> str:
        """Get format instructions for LLM prompt."""
        if self.format_type == "structured_json":
            return """Format your response as valid JSON with this structure:
{
  "field1": "value1",
  "field2": "value2"
}"""
        elif self.format_type == "markdown_table":
            return """Format your response as a markdown table:
| Column1 | Column2 |
|---------|---------|
| Value1  | Value2  |"""
        elif self.format_type == "chart_data":
            return """Format your response as JSON for chart rendering:
{
  "labels": ["A", "B", "C"],
  "values": [10, 20, 30]
}"""
        else:
            return "Provide a clear, concise summary."

    @property
    def _type(self) -> str:
        """Return the type key."""
        return "agenthub_output_parser"


def format_agent_response(
    agent_name: str,
    intent: str,
    data: Any,
    format_type: str = "structured_json",
    renderer_hint: Dict[str, Any] = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Format agent response into standardized structure.

    Args:
        agent_name: Name of the agent that generated the response
        intent: Detected user intent
        data: Response data
        format_type: Output format type
        renderer_hint: UI rendering hints
        metadata: Additional metadata

    Returns:
        Standardized response dictionary
    """
    return {
        "status": "success",
        "agent": agent_name,
        "intent": intent,
        "data": data,
        "format": format_type,
        "renderer_hint": renderer_hint or {"type": "json"},
        "metadata": metadata or {}
    }


def format_error_response(
    agent_name: str,
    intent: str,
    error_message: str,
    error_code: str = None
) -> Dict[str, Any]:
    """
    Format error response.

    Args:
        agent_name: Name of the agent
        intent: Detected intent
        error_message: Error message
        error_code: Optional error code

    Returns:
        Error response dictionary
    """
    return {
        "status": "error",
        "agent": agent_name,
        "intent": intent,
        "data": {
            "message": error_message,
            "code": error_code
        },
        "format": "text",
        "renderer_hint": {"type": "error"},
        "metadata": {}
    }


def format_clarification_response(
    detected_intents: list,
    message: str = None
) -> Dict[str, Any]:
    """
    Format multi-intent clarification response.

    Args:
        detected_intents: List of detected intents
        message: Clarification message

    Returns:
        Clarification response dictionary
    """
    default_message = (
        "I detected multiple questions. Please ask about one topic at a time "
        "so I can help you better."
    )

    return {
        "status": "clarification_needed",
        "agent": "SupervisorAgent",
        "intent": "multi_intent_detected",
        "data": {
            "message": message or default_message,
            "detected_intents": detected_intents
        },
        "format": "text",
        "renderer_hint": {"type": "text"},
        "metadata": {}
    }
