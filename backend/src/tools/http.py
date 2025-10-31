"""HTTP tools for making GET and POST requests with JWT injection."""
import httpx
from typing import Any, Dict, Optional
from src.tools.base import BaseTool
from src.utils.logging import get_logger
from src.config import settings

logger = get_logger(__name__)


class HTTPGetTool(BaseTool):
    """HTTP GET request tool with JWT injection."""

    async def execute(
        self,
        jwt_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        **params
    ) -> Any:
        """
        Execute HTTP GET request.

        Args:
            jwt_token: User JWT token (injected via RunnableConfig)
            tenant_id: Tenant ID (injected via RunnableConfig)
            **params: URL path parameters and query parameters

        Returns:
            Response data (JSON)

        Raises:
            httpx.HTTPError: If request fails
        """
        base_url = self.config.get("base_url", "")
        endpoint = self.config.get("endpoint", "")
        headers = self.config.get("headers", {}).copy()
        timeout = self.config.get("timeout", 30)

        # Inject JWT token into Authorization header
        # ⚠️ TESTING MODE: Use TEST_BEARER_TOKEN from env when DISABLE_AUTH=True
        # TODO: REMOVE this logic before pushing to GitLab/production
        if settings.DISABLE_AUTH and settings.TEST_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {settings.TEST_BEARER_TOKEN}"
            logger.warning(
                "http_using_test_token",
                reason="DISABLE_AUTH=True, using TEST_BEARER_TOKEN for external API"
            )
        elif jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"

        # Replace path parameters in endpoint
        formatted_endpoint = endpoint.format(**params)

        # Combine base_url with formatted endpoint
        full_url = base_url + formatted_endpoint if base_url else formatted_endpoint

        logger.info(
            "http_get_request",
            full_url=full_url,
            tenant_id=tenant_id,
            has_jwt=bool(jwt_token)
        )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(full_url, headers=headers)
                response.raise_for_status()

                logger.info(
                    "http_get_success",
                    endpoint=formatted_endpoint,
                    status_code=response.status_code,
                    tenant_id=tenant_id
                )

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "http_get_error",
                endpoint=formatted_endpoint,
                status_code=e.response.status_code,
                error=str(e),
                tenant_id=tenant_id
            )
            raise ValueError(f"HTTP request failed: {e.response.status_code} - {e.response.text}")

        except httpx.RequestError as e:
            logger.error(
                "http_get_request_error",
                endpoint=formatted_endpoint,
                error=str(e),
                tenant_id=tenant_id
            )
            raise ValueError(f"HTTP request error: {str(e)}")


class HTTPPostTool(BaseTool):
    """HTTP POST request tool with JWT injection."""

    async def execute(
        self,
        jwt_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
        **params
    ) -> Any:
        """
        Execute HTTP POST request.

        Args:
            jwt_token: User JWT token (injected via RunnableConfig)
            tenant_id: Tenant ID (injected via RunnableConfig)
            body: Request body (JSON)
            **params: URL path parameters

        Returns:
            Response data (JSON)

        Raises:
            httpx.HTTPError: If request fails
        """
        endpoint = self.config.get("endpoint", "")
        headers = self.config.get("headers", {}).copy()
        timeout = self.config.get("timeout", 30)

        # Inject JWT token into Authorization header
        # ⚠️ TESTING MODE: Use TEST_BEARER_TOKEN from env when DISABLE_AUTH=True
        # TODO: REMOVE this logic before pushing to GitLab/production
        if settings.DISABLE_AUTH and settings.TEST_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {settings.TEST_BEARER_TOKEN}"
            logger.warning(
                "http_using_test_token",
                reason="DISABLE_AUTH=True, using TEST_BEARER_TOKEN for external API"
            )
        elif jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"

        # Set content type if not specified
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        # Replace path parameters in endpoint
        formatted_endpoint = endpoint.format(**params)

        logger.info(
            "http_post_request",
            endpoint=formatted_endpoint,
            tenant_id=tenant_id,
            has_jwt=bool(jwt_token),
            has_body=bool(body)
        )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    formatted_endpoint,
                    headers=headers,
                    json=body or {}
                )
                response.raise_for_status()

                logger.info(
                    "http_post_success",
                    endpoint=formatted_endpoint,
                    status_code=response.status_code,
                    tenant_id=tenant_id
                )

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "http_post_error",
                endpoint=formatted_endpoint,
                status_code=e.response.status_code,
                error=str(e),
                tenant_id=tenant_id
            )
            raise ValueError(f"HTTP request failed: {e.response.status_code} - {e.response.text}")

        except httpx.RequestError as e:
            logger.error(
                "http_post_request_error",
                endpoint=formatted_endpoint,
                error=str(e),
                tenant_id=tenant_id
            )
            raise ValueError(f"HTTP request error: {str(e)}")
