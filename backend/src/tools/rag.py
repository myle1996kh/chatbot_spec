"""RAG Tool for ChromaDB knowledge base retrieval."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, create_model
import chromadb
from chromadb.config import Settings as ChromaSettings
from src.tools.base import BaseTool
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RAGToolConfig(BaseModel):
    """Configuration for RAG tool."""
    collection_name: str = Field(..., description="ChromaDB collection name")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of documents to retrieve")
    chromadb_host: str = Field(default="localhost", description="ChromaDB host")
    chromadb_port: int = Field(default=8001, description="ChromaDB port")


class RAGTool(BaseTool):
    """Tool for retrieving relevant documents from ChromaDB knowledge base."""

    def __init__(
        self,
        config: Dict[str, Any],
        input_schema: Dict[str, Any],
        tenant_id: str,
        jwt_token: Optional[str] = None,
    ):
        """
        Initialize RAG Tool.

        Args:
            config: Tool configuration (collection_name, top_k, chromadb_host, chromadb_port)
            input_schema: JSON schema for tool inputs (query field)
            tenant_id: Tenant UUID for isolation
            jwt_token: Optional JWT token (not used for ChromaDB)
        """
        super().__init__(config, input_schema, tenant_id, jwt_token)

        # Parse config
        self.rag_config = RAGToolConfig(**config)

        # Initialize ChromaDB client
        try:
            self.client = chromadb.HttpClient(
                host=self.rag_config.chromadb_host,
                port=self.rag_config.chromadb_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                ),
            )

            # Get or create collection (tenant-specific)
            self.collection = self.client.get_or_create_collection(
                name=self.rag_config.collection_name,
                metadata={"tenant_id": tenant_id}
            )

            logger.info(
                "rag_tool_initialized",
                tenant_id=tenant_id,
                collection=self.rag_config.collection_name,
                top_k=self.rag_config.top_k,
            )
        except Exception as e:
            logger.error(
                "rag_tool_init_failed",
                tenant_id=tenant_id,
                error=str(e)
            )
            raise

    def _execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute RAG retrieval.

        Args:
            query: Search query string

        Returns:
            Dictionary with retrieved documents and metadata
        """
        query = kwargs.get("query", "")

        if not query:
            logger.warning(
                "rag_tool_empty_query",
                tenant_id=self.tenant_id,
            )
            return {
                "success": False,
                "error": "Query parameter is required",
                "documents": [],
            }

        try:
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=self.rag_config.top_k,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            documents = []
            if results and results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    documents.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "rank": i + 1,
                    })

            logger.info(
                "rag_tool_executed",
                tenant_id=self.tenant_id,
                collection=self.rag_config.collection_name,
                query_length=len(query),
                results_count=len(documents),
            )

            return {
                "success": True,
                "query": query,
                "documents": documents,
                "total_results": len(documents),
            }

        except Exception as e:
            logger.error(
                "rag_tool_execution_failed",
                tenant_id=self.tenant_id,
                collection=self.rag_config.collection_name,
                error=str(e)
            )
            return {
                "success": False,
                "error": f"RAG retrieval failed: {str(e)}",
                "documents": [],
            }

    @staticmethod
    def create_langchain_tool(
        name: str,
        description: str,
        config: Dict[str, Any],
        input_schema: Dict[str, Any],
        tenant_id: str,
        jwt_token: Optional[str] = None,
    ):
        """
        Create a LangChain-compatible tool from RAG configuration.

        Args:
            name: Tool name
            description: Tool description
            config: Tool configuration
            input_schema: JSON schema for inputs
            tenant_id: Tenant UUID
            jwt_token: Optional JWT token

        Returns:
            LangChain StructuredTool
        """
        from langchain_core.tools import StructuredTool

        # Create RAG tool instance
        rag_tool = RAGTool(
            config=config,
            input_schema=input_schema,
            tenant_id=tenant_id,
            jwt_token=jwt_token,
        )

        # Create Pydantic model from input schema
        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])

        fields = {}
        for field_name, field_spec in properties.items():
            field_type = str  # Default to str
            field_description = field_spec.get("description", "")

            if field_spec.get("type") == "string":
                field_type = str
            elif field_spec.get("type") == "integer":
                field_type = int
            elif field_spec.get("type") == "number":
                field_type = float
            elif field_spec.get("type") == "boolean":
                field_type = bool

            # Make optional if not required
            if field_name not in required_fields:
                field_type = Optional[field_type]
                fields[field_name] = (field_type, Field(None, description=field_description))
            else:
                fields[field_name] = (field_type, Field(..., description=field_description))

        InputModel = create_model(f"{name}Input", **fields)

        # Create LangChain tool
        return StructuredTool(
            name=name,
            description=description,
            func=rag_tool.execute,
            args_schema=InputModel,
        )
