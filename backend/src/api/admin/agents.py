"""Admin API endpoints for agent management."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.config import get_db, get_redis
from src.models.agent import AgentConfig, AgentTools
from src.models.llm_model import LLMModel
from src.models.tool import ToolConfig
from src.schemas.admin import (
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentResponse,
    AgentListResponse,
    MessageResponse,
)
from src.middleware.auth import require_admin_role
from src.utils.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin-agents"])


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    is_active: bool = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> AgentListResponse:
    """
    List all agents with optional filtering.

    Requires admin role in JWT.
    """
    try:
        # Build query
        query = db.query(AgentConfig)

        if is_active is not None:
            query = query.filter(AgentConfig.is_active == is_active)

        # Get total count
        total = query.count()

        # Get agents with pagination
        agents = (
            query.order_by(desc(AgentConfig.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        # Build response with tools
        agent_responses = []
        for agent in agents:
            # Get associated tools
            agent_tools = (
                db.query(ToolConfig)
                .join(AgentTools, ToolConfig.tool_id == AgentTools.tool_id)
                .filter(AgentTools.agent_id == agent.agent_id)
                .order_by(desc(AgentTools.priority))
                .all()
            )

            tools_data = [
                {
                    "tool_id": str(tool.tool_id),
                    "name": tool.name,
                    "description": tool.description,
                }
                for tool in agent_tools
            ]

            agent_responses.append(
                AgentResponse(
                    agent_id=str(agent.agent_id),
                    name=agent.name,
                    description=agent.description,
                    prompt_template=agent.prompt_template,
                    llm_model_id=str(agent.llm_model_id),
                    is_active=agent.is_active,
                    created_at=agent.created_at,
                    updated_at=agent.updated_at,
                    tools=tools_data,
                    metadata={},  # AgentConfig doesn't have metadata column
                )
            )

        logger.info(
            "agents_listed",
            admin_user=admin_payload.get("user_id"),
            count=len(agent_responses),
            total=total,
        )

        return AgentListResponse(agents=agent_responses, total=total)

    except Exception as e:
        logger.error("list_agents_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.post("/agents", response_model=AgentResponse, status_code=201)
async def create_agent(
    request: AgentCreateRequest,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> AgentResponse:
    """
    Create a new agent configuration.

    Requires admin role in JWT.
    """
    try:
        # Validate LLM model exists
        llm_model = db.query(LLMModel).filter(
            LLMModel.llm_model_id == request.llm_model_id
        ).first()

        if not llm_model:
            raise HTTPException(status_code=404, detail="LLM model not found")

        # Validate tools exist
        if request.tool_ids:
            tools = db.query(ToolConfig).filter(
                ToolConfig.tool_id.in_(request.tool_ids)
            ).all()

            if len(tools) != len(request.tool_ids):
                raise HTTPException(status_code=404, detail="One or more tools not found")

        # Create agent
        agent_id = uuid.uuid4()
        agent = AgentConfig(
            agent_id=agent_id,
            name=request.name,
            description=request.description,
            prompt_template=request.prompt_template,
            llm_model_id=uuid.UUID(request.llm_model_id),
            is_active=request.is_active,
            # Note: AgentConfig doesn't have metadata column
        )

        db.add(agent)
        db.flush()  # Get agent_id before adding tools

        # Add tool associations
        if request.tool_ids:
            for idx, tool_id in enumerate(request.tool_ids):
                agent_tool = AgentTools(
                    agent_id=agent_id,
                    tool_id=uuid.UUID(tool_id),
                    priority=len(request.tool_ids) - idx,  # Higher priority for earlier tools
                )
                db.add(agent_tool)

        db.commit()
        db.refresh(agent)

        # Build response
        tools_data = []
        if request.tool_ids:
            tools = db.query(ToolConfig).filter(
                ToolConfig.tool_id.in_([uuid.UUID(tid) for tid in request.tool_ids])
            ).all()
            tools_data = [
                {
                    "tool_id": str(tool.tool_id),
                    "name": tool.name,
                    "description": tool.description,
                }
                for tool in tools
            ]

        logger.info(
            "agent_created",
            admin_user=admin_payload.get("user_id"),
            agent_id=str(agent_id),
            agent_name=request.name,
        )

        return AgentResponse(
            agent_id=str(agent.agent_id),
            name=agent.name,
            description=agent.description,
            prompt_template=agent.prompt_template,
            llm_model_id=str(agent.llm_model_id),
            is_active=agent.is_active,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            tools=tools_data,
            metadata={},  # AgentConfig doesn't have metadata column
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("create_agent_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> AgentResponse:
    """
    Get details of a specific agent.

    Requires admin role in JWT.
    """
    try:
        agent = db.query(AgentConfig).filter(
            AgentConfig.agent_id == agent_id
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Get associated tools
        agent_tools = (
            db.query(ToolConfig)
            .join(AgentTools, ToolConfig.tool_id == AgentTools.tool_id)
            .filter(AgentTools.agent_id == agent_id)
            .order_by(desc(AgentTools.priority))
            .all()
        )

        tools_data = [
            {
                "tool_id": str(tool.tool_id),
                "name": tool.name,
                "description": tool.description,
            }
            for tool in agent_tools
        ]

        return AgentResponse(
            agent_id=str(agent.agent_id),
            name=agent.name,
            description=agent.description,
            prompt_template=agent.prompt_template,
            llm_model_id=str(agent.llm_model_id),
            is_active=agent.is_active,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            tools=tools_data,
            metadata={},  # AgentConfig doesn't have metadata column
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_agent_error", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> AgentResponse:
    """
    Update an existing agent configuration.

    Requires admin role in JWT.
    """
    try:
        agent = db.query(AgentConfig).filter(
            AgentConfig.agent_id == agent_id
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Update fields if provided
        if request.name is not None:
            agent.name = request.name
        if request.description is not None:
            agent.description = request.description
        if request.prompt_template is not None:
            agent.prompt_template = request.prompt_template
        if request.llm_model_id is not None:
            # Validate LLM model exists
            llm_model = db.query(LLMModel).filter(
                LLMModel.llm_model_id == request.llm_model_id
            ).first()
            if not llm_model:
                raise HTTPException(status_code=404, detail="LLM model not found")
            agent.llm_model_id = uuid.UUID(request.llm_model_id)
        if request.is_active is not None:
            agent.is_active = request.is_active
        # Note: AgentConfig doesn't have metadata column, ignoring metadata updates

        # Update tool associations if provided
        if request.tool_ids is not None:
            # Validate tools exist
            if request.tool_ids:
                tools = db.query(ToolConfig).filter(
                    ToolConfig.tool_id.in_([uuid.UUID(tid) for tid in request.tool_ids])
                ).all()
                if len(tools) != len(request.tool_ids):
                    raise HTTPException(status_code=404, detail="One or more tools not found")

            # Remove existing tool associations
            db.query(AgentTools).filter(AgentTools.agent_id == agent_id).delete()

            # Add new tool associations
            for idx, tool_id in enumerate(request.tool_ids):
                agent_tool = AgentTools(
                    agent_id=uuid.UUID(agent_id),
                    tool_id=uuid.UUID(tool_id),
                    priority=len(request.tool_ids) - idx,
                )
                db.add(agent_tool)

        agent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(agent)

        # Get updated tools
        agent_tools = (
            db.query(ToolConfig)
            .join(AgentTools, ToolConfig.tool_id == AgentTools.tool_id)
            .filter(AgentTools.agent_id == agent_id)
            .order_by(desc(AgentTools.priority))
            .all()
        )

        tools_data = [
            {
                "tool_id": str(tool.tool_id),
                "name": tool.name,
                "description": tool.description,
            }
            for tool in agent_tools
        ]

        logger.info(
            "agent_updated",
            admin_user=admin_payload.get("user_id"),
            agent_id=agent_id,
        )

        return AgentResponse(
            agent_id=str(agent.agent_id),
            name=agent.name,
            description=agent.description,
            prompt_template=agent.prompt_template,
            llm_model_id=str(agent.llm_model_id),
            is_active=agent.is_active,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            tools=tools_data,
            metadata={},  # AgentConfig doesn't have metadata column
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("update_agent_error", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


@router.post("/agents/reload", response_model=MessageResponse)
async def reload_agents_cache(
    tenant_id: str = Query(None, description="Optional tenant ID to reload cache for specific tenant"),
    redis = Depends(get_redis),
    admin_payload: dict = Depends(require_admin_role),
) -> MessageResponse:
    """
    Invalidate Redis cache for agents (optionally for a specific tenant).

    This forces agents to be reloaded from database on next request.
    Requires admin role in JWT.
    """
    try:
        if tenant_id:
            # Clear cache for specific tenant
            pattern = f"agenthub:{tenant_id}:cache:*"
        else:
            # Clear all agent caches
            pattern = "agenthub:*:cache:*"

        # Get Redis client
        async for redis_client in redis:
            # Find and delete matching keys
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted_count += await redis_client.delete(*keys)
                if cursor == 0:
                    break

            logger.info(
                "agents_cache_cleared",
                admin_user=admin_payload.get("user_id"),
                tenant_id=tenant_id,
                keys_deleted=deleted_count,
            )

            return MessageResponse(
                message=f"Successfully cleared agent cache",
                details={
                    "tenant_id": tenant_id,
                    "keys_deleted": deleted_count,
                }
            )

    except Exception as e:
        logger.error("reload_cache_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to reload cache: {str(e)}")
