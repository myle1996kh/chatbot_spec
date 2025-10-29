"""Base tool interface for all tool implementations."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Base interface for all tool implementations."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize base tool with configuration.

        Args:
            config: Tool configuration from database
        """
        self.config = config

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Tool execution result
        """
        pass

    def validate_input(self, input_schema: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """
        Validate input parameters against JSON schema.

        Args:
            input_schema: JSON schema for validation
            params: Input parameters

        Returns:
            True if valid, raises ValueError if invalid
        """
        # Simple validation - check required fields
        required = input_schema.get("required", [])
        for field in required:
            if field not in params:
                raise ValueError(f"Required parameter '{field}' missing")
        return True
