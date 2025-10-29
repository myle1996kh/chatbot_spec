"""RAG Service for managing tenant-specific knowledge bases."""
from typing import List, Dict, Any, Optional
import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RAGService:
    """Service for managing ChromaDB collections and document ingestion."""

    def __init__(
        self,
        chromadb_host: str = "localhost",
        chromadb_port: int = 8001,
    ):
        """
        Initialize RAG Service.

        Args:
            chromadb_host: ChromaDB server host
            chromadb_port: ChromaDB server port
        """
        self.chromadb_host = chromadb_host
        self.chromadb_port = chromadb_port

        try:
            self.client = chromadb.HttpClient(
                host=chromadb_host,
                port=chromadb_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                ),
            )

            # Use default sentence-transformers embedding
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

            logger.info(
                "rag_service_initialized",
                chromadb_host=chromadb_host,
                chromadb_port=chromadb_port,
            )
        except Exception as e:
            logger.error(
                "rag_service_init_failed",
                chromadb_host=chromadb_host,
                chromadb_port=chromadb_port,
                error=str(e)
            )
            raise

    def get_collection_name(self, tenant_id: str) -> str:
        """
        Get standardized collection name for tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Collection name in format: tenant_{uuid}_knowledge
        """
        # Remove hyphens from UUID for ChromaDB compatibility
        clean_tenant_id = str(tenant_id).replace("-", "")
        return f"tenant_{clean_tenant_id}_knowledge"

    def create_tenant_collection(
        self,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create or get a tenant-specific collection.

        Args:
            tenant_id: Tenant UUID
            metadata: Optional collection metadata

        Returns:
            Dictionary with collection info
        """
        collection_name = self.get_collection_name(tenant_id)

        try:
            # Prepare metadata
            collection_metadata = metadata or {}
            collection_metadata["tenant_id"] = str(tenant_id)

            # Get or create collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata=collection_metadata,
            )

            logger.info(
                "tenant_collection_created",
                tenant_id=tenant_id,
                collection_name=collection_name,
            )

            return {
                "success": True,
                "collection_name": collection_name,
                "tenant_id": tenant_id,
            }

        except Exception as e:
            logger.error(
                "create_tenant_collection_failed",
                tenant_id=tenant_id,
                collection_name=collection_name,
                error=str(e)
            )
            return {
                "success": False,
                "error": f"Failed to create collection: {str(e)}",
            }

    def ingest_documents(
        self,
        tenant_id: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Ingest documents into tenant's knowledge base.

        Args:
            tenant_id: Tenant UUID
            documents: List of document texts
            metadatas: Optional list of metadata dicts (one per document)
            ids: Optional list of document IDs (generated if not provided)

        Returns:
            Dictionary with ingestion results
        """
        collection_name = self.get_collection_name(tenant_id)

        try:
            # Get collection
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
            )

            # Generate IDs if not provided
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in documents]

            # Ensure metadatas list exists
            if metadatas is None:
                metadatas = [{} for _ in documents]

            # Add tenant_id to all metadata
            for metadata in metadatas:
                metadata["tenant_id"] = str(tenant_id)

            # Add documents to collection
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(
                "documents_ingested",
                tenant_id=tenant_id,
                collection_name=collection_name,
                document_count=len(documents),
            )

            return {
                "success": True,
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "document_count": len(documents),
                "document_ids": ids,
            }

        except Exception as e:
            logger.error(
                "ingest_documents_failed",
                tenant_id=tenant_id,
                collection_name=collection_name,
                document_count=len(documents),
                error=str(e)
            )
            return {
                "success": False,
                "error": f"Failed to ingest documents: {str(e)}",
            }

    def query_knowledge_base(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Query tenant's knowledge base.

        Args:
            tenant_id: Tenant UUID
            query: Search query
            top_k: Number of results to return

        Returns:
            Dictionary with query results
        """
        collection_name = self.get_collection_name(tenant_id)

        try:
            # Get collection
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
            )

            # Query collection
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
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
                "knowledge_base_queried",
                tenant_id=tenant_id,
                collection_name=collection_name,
                query_length=len(query),
                results_count=len(documents),
            )

            return {
                "success": True,
                "tenant_id": tenant_id,
                "query": query,
                "documents": documents,
                "total_results": len(documents),
            }

        except Exception as e:
            logger.error(
                "query_knowledge_base_failed",
                tenant_id=tenant_id,
                collection_name=collection_name,
                error=str(e)
            )
            return {
                "success": False,
                "error": f"Failed to query knowledge base: {str(e)}",
                "documents": [],
            }

    def delete_documents(
        self,
        tenant_id: str,
        document_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Delete documents from tenant's knowledge base.

        Args:
            tenant_id: Tenant UUID
            document_ids: List of document IDs to delete

        Returns:
            Dictionary with deletion results
        """
        collection_name = self.get_collection_name(tenant_id)

        try:
            # Get collection
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
            )

            # Delete documents
            collection.delete(ids=document_ids)

            logger.info(
                "documents_deleted",
                tenant_id=tenant_id,
                collection_name=collection_name,
                deleted_count=len(document_ids),
            )

            return {
                "success": True,
                "tenant_id": tenant_id,
                "deleted_count": len(document_ids),
            }

        except Exception as e:
            logger.error(
                "delete_documents_failed",
                tenant_id=tenant_id,
                collection_name=collection_name,
                error=str(e)
            )
            return {
                "success": False,
                "error": f"Failed to delete documents: {str(e)}",
            }

    def get_collection_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get statistics for tenant's collection.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dictionary with collection statistics
        """
        collection_name = self.get_collection_name(tenant_id)

        try:
            # Get collection
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
            )

            # Get count
            count = collection.count()

            logger.info(
                "collection_stats_retrieved",
                tenant_id=tenant_id,
                collection_name=collection_name,
                document_count=count,
            )

            return {
                "success": True,
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "document_count": count,
            }

        except Exception as e:
            logger.error(
                "get_collection_stats_failed",
                tenant_id=tenant_id,
                collection_name=collection_name,
                error=str(e)
            )
            return {
                "success": False,
                "error": f"Failed to get collection stats: {str(e)}",
            }


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Get or create RAG service singleton.

    Returns:
        RAGService instance
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(
            chromadb_host=getattr(settings, "CHROMADB_HOST", "localhost"),
            chromadb_port=getattr(settings, "CHROMADB_PORT", 8001),
        )
    return _rag_service
