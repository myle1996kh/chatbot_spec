"""JWT authentication middleware."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
from src.utils.jwt import decode_jwt, extract_tenant_id, extract_user_id
from src.utils.logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current user from JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        JWT payload with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    payload = decode_jwt(token)

    # Log authentication
    logger.info(
        "user_authenticated",
        user_id=payload.get("sub"),
        tenant_id=payload.get("tenant_id")
    )

    return payload


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Dependency to extract tenant_id from JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Tenant ID string

    Raises:
        HTTPException: If token is invalid or tenant_id not found
    """
    token = credentials.credentials
    payload = decode_jwt(token)
    tenant_id = extract_tenant_id(payload)

    return tenant_id


async def verify_tenant_access(
    tenant_id_path: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """
    Verify that JWT tenant_id matches path parameter tenant_id.

    Args:
        tenant_id_path: Tenant ID from path parameter
        credentials: HTTP Bearer credentials

    Returns:
        True if tenant_id matches

    Raises:
        HTTPException: If tenant_id mismatch (403 Forbidden)
    """
    token = credentials.credentials
    payload = decode_jwt(token)
    tenant_id_jwt = extract_tenant_id(payload)

    if tenant_id_path != tenant_id_jwt:
        logger.warning(
            "tenant_access_denied",
            tenant_id_path=tenant_id_path,
            tenant_id_jwt=tenant_id_jwt,
            user_id=payload.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: tenant_id mismatch"
        )

    return True


async def require_admin_role(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to require admin role in JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        JWT payload if user has admin role

    Raises:
        HTTPException: If user doesn't have admin role (403 Forbidden)
    """
    token = credentials.credentials
    payload = decode_jwt(token)

    roles = payload.get("roles", [])
    if "admin" not in roles:
        logger.warning(
            "admin_access_denied",
            user_id=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            roles=roles
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )

    logger.info(
        "admin_authenticated",
        user_id=payload.get("sub"),
        tenant_id=payload.get("tenant_id")
    )

    return payload
