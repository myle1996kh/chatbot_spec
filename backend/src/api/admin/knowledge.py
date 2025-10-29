"""Admin API endpoints for knowledge base management."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from src.config import get_db
from src.models.tenant import Tenant
from src.schemas.admin import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    KnowledgeBaseStatsResponse,
    MessageResponse,
)
from src.services.rag_service import get_rag_service
from src.middleware.auth import require_admin_role
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin-knowledge"])


@router.post("/tenants/{tenant_id}/knowledge", response_model=DocumentIngestResponse)
async def ingest_documents(
    tenant_id: str = Path(..., description="Tenant UUID"),
    request: DocumentIngestRequest = ...,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> DocumentIngestResponse:
    """
    Ingest documents into tenant's knowledge base.

    This creates a tenant-specific ChromaDB collection and adds documents
    for later retrieval by AgentAnalysis via RAG.

    Requires admin role in JWT.
    """
    try:
        # Validate tenant exists
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Get RAG service
        rag_service = get_rag_service()

        # Create collection if it doesn't exist
        collection_result = rag_service.create_tenant_collection(
            tenant_id=tenant_id,
            metadata={"created_by_admin": admin_payload.get("user_id")}
        )

        if not collection_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=collection_result.get("error", "Failed to create collection")
            )

        # Ingest documents
        ingest_result = rag_service.ingest_documents(
            tenant_id=tenant_id,
            documents=request.documents,
            metadatas=request.metadatas,
        )

        if not ingest_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=ingest_result.get("error", "Failed to ingest documents")
            )

        logger.info(
            "documents_ingested_by_admin",
            admin_user=admin_payload.get("user_id"),
            tenant_id=tenant_id,
            document_count=ingest_result.get("document_count"),
        )

        return DocumentIngestResponse(
            success=True,
            tenant_id=tenant_id,
            collection_name=ingest_result.get("collection_name"),
            document_count=ingest_result.get("document_count"),
            document_ids=ingest_result.get("document_ids"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "ingest_documents_error",
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest documents: {str(e)}"
        )


@router.get("/tenants/{tenant_id}/knowledge/stats", response_model=KnowledgeBaseStatsResponse)
async def get_knowledge_base_stats(
    tenant_id: str = Path(..., description="Tenant UUID"),
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> KnowledgeBaseStatsResponse:
    """
    Get statistics for tenant's knowledge base.

    Returns document count and collection information.

    Requires admin role in JWT.
    """
    try:
        # Validate tenant exists
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Get RAG service
        rag_service = get_rag_service()

        # Get collection stats
        stats_result = rag_service.get_collection_stats(tenant_id=tenant_id)

        if not stats_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=stats_result.get("error", "Failed to get collection stats")
            )

        logger.info(
            "knowledge_base_stats_retrieved",
            admin_user=admin_payload.get("user_id"),
            tenant_id=tenant_id,
            document_count=stats_result.get("document_count"),
        )

        return KnowledgeBaseStatsResponse(
            success=True,
            tenant_id=tenant_id,
            collection_name=stats_result.get("collection_name"),
            document_count=stats_result.get("document_count"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_knowledge_base_stats_error",
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get knowledge base stats: {str(e)}"
        )


@router.delete("/tenants/{tenant_id}/knowledge", response_model=MessageResponse)
async def delete_documents(
    tenant_id: str = Path(..., description="Tenant UUID"),
    document_ids: List[str] = ...,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> MessageResponse:
    """
    Delete documents from tenant's knowledge base.

    Requires admin role in JWT.
    """
    try:
        # Validate tenant exists
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Get RAG service
        rag_service = get_rag_service()

        # Delete documents
        delete_result = rag_service.delete_documents(
            tenant_id=tenant_id,
            document_ids=document_ids,
        )

        if not delete_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=delete_result.get("error", "Failed to delete documents")
            )

        logger.info(
            "documents_deleted_by_admin",
            admin_user=admin_payload.get("user_id"),
            tenant_id=tenant_id,
            deleted_count=delete_result.get("deleted_count"),
        )

        return MessageResponse(
            message="Successfully deleted documents",
            details={
                "tenant_id": tenant_id,
                "deleted_count": delete_result.get("deleted_count"),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "delete_documents_error",
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete documents: {str(e)}"
        )
