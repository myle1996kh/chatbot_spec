"""Admin API endpoints for tool management."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.config import get_db
from src.models.tool import ToolConfig
from src.models.base_tool import BaseTool
from src.schemas.admin import (
    ToolCreateRequest,
    ToolUpdateRequest,
    ToolResponse,
    ToolListResponse,
    MessageResponse,
)
from src.middleware.auth import require_admin_role
from src.utils.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin-tools"])


@router.get("/tools", response_model=ToolListResponse)
async def list_tools(
    is_active: bool = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> ToolListResponse:
    """
    List all tools with optional filtering.

    Requires admin role in JWT.
    """
    try:
        # Build query
        query = db.query(ToolConfig)

        if is_active is not None:
            query = query.filter(ToolConfig.is_active == is_active)

        # Get total count
        total = query.count()

        # Get tools with pagination
        tools = (
            query.order_by(desc(ToolConfig.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        # Build response with base tool info
        tool_responses = []
        for tool in tools:
            # Get base tool info
            base_tool = db.query(BaseTool).filter(
                BaseTool.base_tool_id == tool.base_tool_id
            ).first()

            base_tool_data = None
            if base_tool:
                base_tool_data = {
                    "base_tool_id": str(base_tool.base_tool_id),
                    "tool_type": base_tool.tool_type,
                    "description": base_tool.description,
                }

            tool_responses.append(
                ToolResponse(
                    tool_id=str(tool.tool_id),
                    base_tool_id=str(tool.base_tool_id),
                    name=tool.name,
                    description=tool.description,
                    config=tool.config or {},
                    input_schema=tool.input_schema or {},
                    is_active=tool.is_active,
                    created_at=tool.created_at,
                    base_tool=base_tool_data,
                )
            )

        logger.info(
            "tools_listed",
            admin_user=admin_payload.get("user_id"),
            count=len(tool_responses),
            total=total,
        )

        return ToolListResponse(tools=tool_responses, total=total)

    except Exception as e:
        logger.error("list_tools_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.post("/tools", response_model=ToolResponse, status_code=201)
async def create_tool(
    request: ToolCreateRequest,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> ToolResponse:
    """
    Create a new tool configuration from a base tool template.

    Requires admin role in JWT.
    """
    try:
        # Validate base tool exists
        base_tool = db.query(BaseTool).filter(
            BaseTool.base_tool_id == request.base_tool_id
        ).first()

        if not base_tool:
            raise HTTPException(status_code=404, detail="Base tool template not found")

        # Create tool
        tool_id = uuid.uuid4()
        tool = ToolConfig(
            tool_id=tool_id,
            base_tool_id=uuid.UUID(request.base_tool_id),
            name=request.name,
            description=request.description,
            config=request.config,
            input_schema=request.input_schema,
            is_active=request.is_active,
        )

        db.add(tool)
        db.commit()
        db.refresh(tool)

        # Build response
        base_tool_data = {
            "base_tool_id": str(base_tool.base_tool_id),
            "tool_type": base_tool.tool_type,
            "description": base_tool.description,
        }

        logger.info(
            "tool_created",
            admin_user=admin_payload.get("user_id"),
            tool_id=str(tool_id),
            tool_name=request.name,
            base_tool_type=base_tool.tool_type,
        )

        return ToolResponse(
            tool_id=str(tool.tool_id),
            base_tool_id=str(tool.base_tool_id),
            name=tool.name,
            description=tool.description,
            config=tool.config or {},
            input_schema=tool.input_schema or {},
            is_active=tool.is_active,
            created_at=tool.created_at,
            base_tool=base_tool_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("create_tool_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create tool: {str(e)}")


@router.get("/tools/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> ToolResponse:
    """
    Get details of a specific tool.

    Requires admin role in JWT.
    """
    try:
        tool = db.query(ToolConfig).filter(
            ToolConfig.tool_id == tool_id
        ).first()

        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")

        # Get base tool info
        base_tool = db.query(BaseTool).filter(
            BaseTool.base_tool_id == tool.base_tool_id
        ).first()

        base_tool_data = None
        if base_tool:
            base_tool_data = {
                "base_tool_id": str(base_tool.base_tool_id),
                "tool_type": base_tool.tool_type,
                "description": base_tool.description,
            }

        return ToolResponse(
            tool_id=str(tool.tool_id),
            base_tool_id=str(tool.base_tool_id),
            name=tool.name,
            description=tool.description,
            config=tool.config or {},
            input_schema=tool.input_schema or {},
            is_active=tool.is_active,
            created_at=tool.created_at,
            base_tool=base_tool_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_tool_error", tool_id=tool_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get tool: {str(e)}")


@router.patch("/tools/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    request: ToolUpdateRequest,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> ToolResponse:
    """
    Update an existing tool configuration.

    Requires admin role in JWT.
    """
    try:
        tool = db.query(ToolConfig).filter(
            ToolConfig.tool_id == tool_id
        ).first()

        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")

        # Update fields if provided
        if request.name is not None:
            tool.name = request.name
        if request.description is not None:
            tool.description = request.description
        if request.config is not None:
            tool.config = request.config
        if request.input_schema is not None:
            tool.input_schema = request.input_schema
        if request.is_active is not None:
            tool.is_active = request.is_active

        db.commit()
        db.refresh(tool)

        # Get base tool info
        base_tool = db.query(BaseTool).filter(
            BaseTool.base_tool_id == tool.base_tool_id
        ).first()

        base_tool_data = None
        if base_tool:
            base_tool_data = {
                "base_tool_id": str(base_tool.base_tool_id),
                "tool_type": base_tool.tool_type,
                "description": base_tool.description,
            }

        logger.info(
            "tool_updated",
            admin_user=admin_payload.get("user_id"),
            tool_id=tool_id,
        )

        return ToolResponse(
            tool_id=str(tool.tool_id),
            base_tool_id=str(tool.base_tool_id),
            name=tool.name,
            description=tool.description,
            config=tool.config or {},
            input_schema=tool.input_schema or {},
            is_active=tool.is_active,
            created_at=tool.created_at,
            base_tool=base_tool_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("update_tool_error", tool_id=tool_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update tool: {str(e)}")
