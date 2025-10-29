"""Chat API endpoints for conversational interface."""
import time
import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from src.config import get_db, settings
from typing import Optional
from src.models.session import ChatSession
from src.models.message import Message
from src.models.tenant import Tenant
from src.schemas.chat import ChatRequest, ChatResponse
from src.services.supervisor_agent import SupervisorAgent
from src.middleware.auth import get_current_tenant, verify_tenant_access
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/{tenant_id}/chat", response_model=ChatResponse)
async def chat_endpoint(
    tenant_id: str = Path(..., description="Tenant UUID"),
    request: ChatRequest = ...,
    db: Session = Depends(get_db),
    current_tenant: Optional[str] = Depends(get_current_tenant) if not settings.DISABLE_AUTH else None,
) -> ChatResponse:
    """
    Process user message and return agent response.

    Flow:
    1. Validate tenant access
    2. Create or retrieve session
    3. Save user message
    4. Route to SupervisorAgent
    5. Save assistant response
    6. Track performance metrics
    """
    start_time = time.time()

    try:
        # Validate tenant exists and user has access
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        logger.info(f"DISABLE_AUTH: {settings.DISABLE_AUTH}")
        logger.info(f"current_tenant: {current_tenant}")

        if not settings.DISABLE_AUTH and current_tenant != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied to this tenant")

        # Create or retrieve session
        session = await _get_or_create_session(
            db, tenant_id, request.session_id, request.user_id
        )

        # Save user message
        user_message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            role="user",
            content=request.message,
            metadata=request.metadata or {},
        )
        db.add(user_message)
        db.commit()

        logger.info(
            "user_message_received",
            tenant_id=tenant_id,
            session_id=session.session_id,
            user_id=session.user_id,
            message_length=len(request.message),
        )

        # Extract JWT token from current_tenant context (passed via middleware)
        # In production, middleware would inject full JWT token into request state
        jwt_token = request.metadata.get("jwt_token", "") if request.metadata else ""

        # Route message through SupervisorAgent
        supervisor = SupervisorAgent(
            db=db,
            tenant_id=tenant_id,
            jwt_token=jwt_token,
        )

        agent_response = await supervisor.route_message(request.message)

        # Save assistant response
        assistant_message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            role="assistant",
            content=str(agent_response.get("data", {})),
            metadata={
                "agent": agent_response.get("agent"),
                "intent": agent_response.get("intent"),
                "format": agent_response.get("format"),
                "renderer_hint": agent_response.get("renderer_hint"),
            },
        )
        db.add(assistant_message)

        # Update session metadata - track last message time
        from datetime import datetime, timezone
        session.last_message_at = datetime.now(timezone.utc)

        db.commit()

        # Calculate response time
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "chat_response_completed",
            tenant_id=tenant_id,
            session_id=session.session_id,
            agent=agent_response.get("agent"),
            intent=agent_response.get("intent"),
            duration_ms=duration_ms,
            status="success",
        )

        # Check performance requirement (<2.5s)
        if duration_ms > 2500:
            logger.warning(
                "chat_response_slow",
                tenant_id=tenant_id,
                session_id=session.session_id,
                duration_ms=duration_ms,
                threshold_ms=2500,
            )

        return ChatResponse(
            session_id=session.session_id,
            message_id=assistant_message.message_id,
            response=agent_response.get("data", {}),
            agent=agent_response.get("agent", "unknown"),
            intent=agent_response.get("intent", "unknown"),
            format=agent_response.get("format", "text"),
            renderer_hint=agent_response.get("renderer_hint", {}),
            metadata={
                "duration_ms": duration_ms,
                "status": agent_response.get("status", "success"),
                **agent_response.get("metadata", {}),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "chat_endpoint_error",
            tenant_id=tenant_id,
            error=str(e),
            duration_ms=duration_ms,
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def _get_or_create_session(
    db: Session, tenant_id: str, session_id: str | None, user_id: str
) -> ChatSession:
    """
    Get existing session or create new one.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        session_id: Optional existing session ID
        user_id: User identifier

    Returns:
        ChatSession instance
    """
    if session_id:
        # Retrieve existing session
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.session_id == session_id,
                ChatSession.tenant_id == tenant_id,
                ChatSession.user_id == user_id,
            )
            .first()
        )

        if session:
            return session

        logger.warning(
            "session_not_found",
            tenant_id=tenant_id,
            session_id=session_id,
            user_id=user_id,
            action="creating_new_session",
        )

    # Create new session
    new_session_id = str(uuid.uuid4())
    thread_id = f"tenant_{tenant_id}__user_{user_id}__session_{new_session_id}"

    session = ChatSession(
        session_id=new_session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        thread_id=thread_id,
        metadata={},
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.post("/{tenant_id}/test/chat", response_model=ChatResponse)
async def test_chat_endpoint(
    tenant_id: str = Path(..., description="Tenant UUID"),
    request: ChatRequest = ...,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Process user message and return agent response for testing.
    This endpoint bypasses authentication.
    """
    start_time = time.time()

    try:
        # Validate tenant exists
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Create or retrieve session
        session = await _get_or_create_session(
            db, tenant_id, request.session_id, request.user_id
        )

        # Save user message
        user_message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            role="user",
            content=request.message,
            metadata=request.metadata or {},
        )
        db.add(user_message)
        db.commit()

        logger.info(
            "user_message_received_test",
            tenant_id=tenant_id,
            session_id=session.session_id,
            user_id=session.user_id,
            message_length=len(request.message),
        )

        # Extract JWT token from current_tenant context (passed via middleware)
        # In production, middleware would inject full JWT token into request state
        jwt_token = request.metadata.get("jwt_token", "") if request.metadata else ""

        # Route message through SupervisorAgent
        supervisor = SupervisorAgent(
            db=db,
            tenant_id=tenant_id,
            jwt_token=jwt_token,
        )

        agent_response = await supervisor.route_message(request.message)

        # Save assistant response
        assistant_message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            role="assistant",
            content=str(agent_response.get("data", {})),
            metadata={
                "agent": agent_response.get("agent"),
                "intent": agent_response.get("intent"),
                "format": agent_response.get("format"),
                "renderer_hint": agent_response.get("renderer_hint"),
            },
        )
        db.add(assistant_message)

        # Update session metadata - track last message time
        from datetime import datetime, timezone
        session.last_message_at = datetime.now(timezone.utc)

        db.commit()

        # Calculate response time
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "test_chat_response_completed",
            tenant_id=tenant_id,
            session_id=session.session_id,
            agent=agent_response.get("agent"),
            intent=agent_response.get("intent"),
            duration_ms=duration_ms,
            status="success",
        )

        return ChatResponse(
            session_id=session.session_id,
            message_id=assistant_message.message_id,
            response=agent_response.get("data", {}),
            agent=agent_response.get("agent", "unknown"),
            intent=agent_response.get("intent", "unknown"),
            format=agent_response.get("format", "text"),
            renderer_hint=agent_response.get("renderer_hint", {}),
            metadata={
                "duration_ms": duration_ms,
                "status": agent_response.get("status", "success"),
                **agent_response.get("metadata", {}),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "test_chat_endpoint_error",
            tenant_id=tenant_id,
            error=str(e),
            duration_ms=duration_ms,
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
