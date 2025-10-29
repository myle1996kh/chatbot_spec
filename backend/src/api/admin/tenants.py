"""Admin API endpoints for tenant permission management."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from src.config import get_db, get_redis
from src.models.tenant import Tenant
from src.models.agent import AgentConfig
from src.models.tool import ToolConfig
from src.models.permissions import TenantAgentPermission, TenantToolPermission
from src.schemas.admin import (
    TenantPermissionsResponse,
    PermissionUpdateRequest,
    MessageResponse,
)
from src.middleware.auth import require_admin_role
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin-tenants"])


@router.get("/tenants/{tenant_id}/permissions", response_model=TenantPermissionsResponse)
async def get_tenant_permissions(
    tenant_id: str = Path(..., description="Tenant UUID"),
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
) -> TenantPermissionsResponse:
    """
    Get all permissions (enabled agents and tools) for a tenant.

    Requires admin role in JWT.
    """
    try:
        # Validate tenant exists
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Get enabled agent permissions
        agent_perms = (
            db.query(TenantAgentPermission, AgentConfig)
            .join(AgentConfig, TenantAgentPermission.agent_id == AgentConfig.agent_id)
            .filter(
                TenantAgentPermission.tenant_id == tenant_id,
                TenantAgentPermission.enabled == True
            )
            .all()
        )

        enabled_agents = [
            {
                "agent_id": str(perm.agent_id),
                "agent_name": agent.name,
                "enabled": perm.enabled,
            }
            for perm, agent in agent_perms
        ]

        # Get enabled tool permissions
        tool_perms = (
            db.query(TenantToolPermission, ToolConfig)
            .join(ToolConfig, TenantToolPermission.tool_id == ToolConfig.tool_id)
            .filter(
                TenantToolPermission.tenant_id == tenant_id,
                TenantToolPermission.enabled == True
            )
            .all()
        )

        enabled_tools = [
            {
                "tool_id": str(perm.tool_id),
                "tool_name": tool.name,
                "enabled": perm.enabled,
            }
            for perm, tool in tool_perms
        ]

        logger.info(
            "tenant_permissions_retrieved",
            admin_user=admin_payload.get("user_id"),
            tenant_id=tenant_id,
            enabled_agents_count=len(enabled_agents),
            enabled_tools_count=len(enabled_tools),
        )

        return TenantPermissionsResponse(
            tenant_id=tenant_id,
            enabled_agents=enabled_agents,
            enabled_tools=enabled_tools,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_tenant_permissions_error",
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tenant permissions: {str(e)}"
        )


@router.patch("/tenants/{tenant_id}/permissions", response_model=MessageResponse)
async def update_tenant_permissions(
    tenant_id: str = Path(..., description="Tenant UUID"),
    request: PermissionUpdateRequest = ...,
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    admin_payload: dict = Depends(require_admin_role),
) -> MessageResponse:
    """
    Update tenant permissions (enable/disable agents and tools for a tenant).

    This will create permission records if they don't exist, or update if they do.
    Requires admin role in JWT.
    """
    try:
        # Validate tenant exists
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        updated_agents = 0
        updated_tools = 0

        # Update agent permissions
        if request.agent_permissions:
            for perm_update in request.agent_permissions:
                agent_id = perm_update.get("agent_id")
                enabled = perm_update.get("enabled", True)

                if not agent_id:
                    continue

                # Validate agent exists
                agent = db.query(AgentConfig).filter(
                    AgentConfig.agent_id == agent_id
                ).first()
                if not agent:
                    logger.warning(
                        "agent_not_found_skipping",
                        agent_id=agent_id,
                        tenant_id=tenant_id
                    )
                    continue

                # Check if permission exists
                existing_perm = db.query(TenantAgentPermission).filter(
                    TenantAgentPermission.tenant_id == tenant_id,
                    TenantAgentPermission.agent_id == agent_id
                ).first()

                if existing_perm:
                    # Update existing permission
                    existing_perm.enabled = enabled
                else:
                    # Create new permission
                    new_perm = TenantAgentPermission(
                        tenant_id=uuid.UUID(tenant_id),
                        agent_id=uuid.UUID(agent_id),
                        enabled=enabled,
                    )
                    db.add(new_perm)

                updated_agents += 1

        # Update tool permissions
        if request.tool_permissions:
            for perm_update in request.tool_permissions:
                tool_id = perm_update.get("tool_id")
                enabled = perm_update.get("enabled", True)

                if not tool_id:
                    continue

                # Validate tool exists
                tool = db.query(ToolConfig).filter(
                    ToolConfig.tool_id == tool_id
                ).first()
                if not tool:
                    logger.warning(
                        "tool_not_found_skipping",
                        tool_id=tool_id,
                        tenant_id=tenant_id
                    )
                    continue

                # Check if permission exists
                existing_perm = db.query(TenantToolPermission).filter(
                    TenantToolPermission.tenant_id == tenant_id,
                    TenantToolPermission.tool_id == tool_id
                ).first()

                if existing_perm:
                    # Update existing permission
                    existing_perm.enabled = enabled
                else:
                    # Create new permission
                    new_perm = TenantToolPermission(
                        tenant_id=uuid.UUID(tenant_id),
                        tool_id=uuid.UUID(tool_id),
                        enabled=enabled,
                    )
                    db.add(new_perm)

                updated_tools += 1

        db.commit()

        # Invalidate cache for this tenant
        async for redis_client in redis:
            pattern = f"agenthub:{tenant_id}:cache:*"
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted_count += await redis_client.delete(*keys)
                if cursor == 0:
                    break

            logger.info(
                "tenant_permissions_updated",
                admin_user=admin_payload.get("user_id"),
                tenant_id=tenant_id,
                updated_agents=updated_agents,
                updated_tools=updated_tools,
                cache_keys_deleted=deleted_count,
            )

        return MessageResponse(
            message="Successfully updated tenant permissions",
            details={
                "tenant_id": tenant_id,
                "updated_agents": updated_agents,
                "updated_tools": updated_tools,
                "cache_invalidated": True,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            "update_tenant_permissions_error",
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update tenant permissions: {str(e)}"
        )
