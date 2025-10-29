"""Session management API endpoints."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from src.config import get_db
from src.models.session import ChatSession
from src.models.message import Message
from src.models.tenant import Tenant
from src.schemas.chat import SessionSummary, SessionDetail
from src.middleware.auth import get_current_tenant
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/{tenant_id}/session", response_model=List[SessionSummary])
async def list_sessions(
    tenant_id: str = Path(..., description="Tenant UUID"),
    user_id: str = Query(..., description="User ID to filter sessions"),
    start_date: Optional[datetime] = Query(None, description="Filter sessions created after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter sessions created before this date"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    db: Session = Depends(get_db),
    current_tenant: str = Depends(get_current_tenant),
) -> List[SessionSummary]:
    """
    List user's chat sessions with pagination and optional date filtering.

    Returns sessions ordered by most recent first.
    """
    try:
        # Validate tenant exists and user has access
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if current_tenant != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied to this tenant")

        # Build query with filters
        query_filters = [
            ChatSession.tenant_id == tenant_id,
            ChatSession.user_id == user_id,
        ]

        # Add date range filters if provided
        if start_date:
            query_filters.append(ChatSession.created_at >= start_date)
        if end_date:
            query_filters.append(ChatSession.created_at <= end_date)

        # Query sessions for user
        sessions = (
            db.query(ChatSession)
            .filter(and_(*query_filters))
            .order_by(desc(ChatSession.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        # Build session summaries with message count
        summaries = []
        for session in sessions:
            message_count = (
                db.query(Message)
                .filter(Message.session_id == session.session_id)
                .count()
            )

            # Get last message preview
            last_message = (
                db.query(Message)
                .filter(Message.session_id == session.session_id)
                .order_by(desc(Message.created_at))
                .first()
            )

            last_message_preview = ""
            if last_message:
                last_message_preview = (
                    last_message.content[:100] + "..."
                    if len(last_message.content) > 100
                    else last_message.content
                )

            summaries.append(
                SessionSummary(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    message_count=message_count,
                    last_message_preview=last_message_preview,
                    metadata=session.metadata,
                )
            )

        logger.info(
            "sessions_listed",
            tenant_id=tenant_id,
            user_id=user_id,
            count=len(summaries),
            limit=limit,
            offset=offset,
        )

        return summaries

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "list_sessions_error",
            tenant_id=tenant_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{tenant_id}/session/{session_id}", response_model=SessionDetail)
async def get_session(
    tenant_id: str = Path(..., description="Tenant UUID"),
    session_id: str = Path(..., description="Session UUID"),
    db: Session = Depends(get_db),
    current_tenant: str = Depends(get_current_tenant),
) -> SessionDetail:
    """
    Get session details with full message history.

    Returns all messages in chronological order.
    """
    try:
        # Validate tenant exists and user has access
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if current_tenant != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied to this tenant")

        # Query session
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.session_id == session_id,
                ChatSession.tenant_id == tenant_id,
            )
            .first()
        )

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Query all messages in chronological order
        messages = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at)
            .all()
        )

        # Build message list
        message_list = [
            {
                "message_id": msg.message_id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "metadata": msg.metadata,
            }
            for msg in messages
        ]

        logger.info(
            "session_retrieved",
            tenant_id=tenant_id,
            session_id=session_id,
            message_count=len(message_list),
        )

        return SessionDetail(
            session_id=session.session_id,
            user_id=session.user_id,
            thread_id=session.thread_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=message_list,
            metadata=session.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_session_error",
            tenant_id=tenant_id,
            session_id=session_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
