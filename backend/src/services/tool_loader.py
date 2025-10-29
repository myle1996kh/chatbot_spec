"""Tool Registry for dynamic tool creation from database configuration."""
from typing import List, Dict, Any, Callable
from pydantic import create_model, Field as PydanticField
from langchain_core.tools import StructuredTool
from sqlalchemy.orm import Session
from src.models.tool import ToolConfig
from src.models.base_tool import BaseTool as BaseToolModel
from src.tools.http import HTTPGetTool, HTTPPostTool
from src.tools.rag import RAGTool
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for creating and caching LangChain tools from database configuration."""

    def __init__(self):
        """Initialize tool registry with handler mapping."""
        self._cache: Dict[str, StructuredTool] = {}
        self._tool_handlers = {
            "tools.http.HTTPGetTool": HTTPGetTool,
            "tools.http.HTTPPostTool": HTTPPostTool,
            "tools.rag.RAGTool": RAGTool,
            # Additional handlers can be added here
            # "tools.db.DBQueryTool": DBQueryTool,
            # "tools.ocr.OCRTool": OCRTool,
        }

    def create_tool_from_db(
        self,
        db: Session,
        tool_id: str,
        tenant_id: str,
        jwt_token: str
    ) -> StructuredTool:
        """
        Create LangChain StructuredTool from database configuration.

        Args:
            db: Database session
            tool_id: Tool configuration UUID
            tenant_id: Tenant UUID (for context injection)
            jwt_token: User JWT token (for context injection)

        Returns:
            LangChain StructuredTool instance

        Raises:
            ValueError: If tool not found or handler not supported
        """
        cache_key = f"{tenant_id}:{tool_id}"

        # Check cache
        if cache_key in self._cache:
            logger.debug("tool_cache_hit", tool_id=tool_id, tenant_id=tenant_id)
            return self._cache[cache_key]

        # Load tool configuration
        tool_config = db.query(ToolConfig).filter(
            ToolConfig.tool_id == tool_id,
            ToolConfig.is_active == True
        ).first()

        if not tool_config:
            raise ValueError(f"Tool {tool_id} not found or inactive")

        # Load base tool for handler class
        base_tool = db.query(BaseToolModel).filter(
            BaseToolModel.base_tool_id == tool_config.base_tool_id
        ).first()

        if not base_tool:
            raise ValueError(f"Base tool not found for tool {tool_id}")

        # Get handler class
        handler_class = self._tool_handlers.get(base_tool.handler_class)
        if not handler_class:
            raise ValueError(f"Unsupported tool handler: {base_tool.handler_class}")

        # Create dynamic Pydantic schema from input_schema
        pydantic_schema = self._create_pydantic_schema(
            tool_config.name,
            tool_config.input_schema
        )

        # Check if this is RAGTool which has different instantiation
        if base_tool.handler_class == "tools.rag.RAGTool":
            # Use RAGTool's create_langchain_tool method
            structured_tool = handler_class.create_langchain_tool(
                name=tool_config.name,
                description=tool_config.description or f"Tool: {tool_config.name}",
                config=tool_config.config,
                input_schema=tool_config.input_schema,
                tenant_id=tenant_id,
                jwt_token=jwt_token,
            )
        else:
            # Standard tool instantiation for HTTP tools
            tool_instance = handler_class(tool_config.config)

            async def tool_executor(**kwargs) -> str:
                """Execute tool with injected context."""
                try:
                    # Inject tenant_id and jwt_token
                    result = await tool_instance.execute(
                        jwt_token=jwt_token,
                        tenant_id=tenant_id,
                        **kwargs
                    )

                    logger.info(
                        "tool_executed",
                        tool_name=tool_config.name,
                        tenant_id=tenant_id
                    )

                    return str(result)
                except Exception as e:
                    logger.error(
                        "tool_execution_error",
                        tool_name=tool_config.name,
                        tenant_id=tenant_id,
                        error=str(e)
                    )
                    raise

            # Create StructuredTool
            structured_tool = StructuredTool.from_function(
                func=tool_executor,
                name=tool_config.name,
                description=tool_config.description or f"Tool: {tool_config.name}",
                args_schema=pydantic_schema,
                coroutine=tool_executor  # For async execution
            )

        # Cache the tool
        self._cache[cache_key] = structured_tool

        logger.info(
            "tool_created",
            tool_name=tool_config.name,
            tool_id=tool_id,
            tenant_id=tenant_id
        )

        return structured_tool

    def _create_pydantic_schema(self, tool_name: str, input_schema: Dict[str, Any]):
        """
        Create Pydantic model from JSON schema.

        Args:
            tool_name: Name of the tool
            input_schema: JSON schema definition

        Returns:
            Pydantic model class
        """
        fields = {}
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        for field_name, field_spec in properties.items():
            field_type = self._map_json_type(field_spec.get("type", "string"))
            field_description = field_spec.get("description", "")
            is_required = field_name in required

            if is_required:
                fields[field_name] = (
                    field_type,
                    PydanticField(description=field_description)
                )
            else:
                fields[field_name] = (
                    field_type,
                    PydanticField(default=None, description=field_description)
                )

        return create_model(f"{tool_name}Schema", **fields)

    def _map_json_type(self, json_type: str) -> type:
        """Map JSON schema type to Python type."""
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        return type_mapping.get(json_type, str)

    def load_agent_tools(
        self,
        db: Session,
        agent_id: str,
        tenant_id: str,
        jwt_token: str,
        top_n: int = 5
    ) -> List[StructuredTool]:
        """
        Load tools for an agent with priority filtering.

        Args:
            db: Database session
            agent_id: Agent UUID
            tenant_id: Tenant UUID
            jwt_token: User JWT token
            top_n: Number of top priority tools to load (default: 5)

        Returns:
            List of LangChain StructuredTool instances
        """
        # Query agent_tools with priority filtering
        from src.models.agent import AgentTools

        agent_tools = db.query(AgentTools).filter(
            AgentTools.agent_id == agent_id
        ).order_by(AgentTools.priority.asc()).limit(top_n).all()

        tools = []
        for agent_tool in agent_tools:
            try:
                tool = self.create_tool_from_db(
                    db,
                    str(agent_tool.tool_id),
                    tenant_id,
                    jwt_token
                )
                tools.append(tool)
            except Exception as e:
                logger.error(
                    "tool_load_error",
                    tool_id=agent_tool.tool_id,
                    agent_id=agent_id,
                    error=str(e)
                )
                # Continue loading other tools

        logger.info(
            "agent_tools_loaded",
            agent_id=agent_id,
            tenant_id=tenant_id,
            tool_count=len(tools)
        )

        return tools

    def clear_cache(self, tenant_id: str = None):
        """Clear tool cache."""
        if tenant_id:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{tenant_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info("tool_cache_cleared", tenant_id=tenant_id)
        else:
            self._cache.clear()
            logger.info("tool_cache_cleared_all")


# Global tool registry instance
tool_registry = ToolRegistry()
