"""Checkpoint service using PostgreSQL for LangGraph state persistence."""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from langgraph.checkpoint.postgres import PostgresSaver
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CheckpointService:
    """Service for managing LangGraph checkpoints with PostgreSQL."""

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize checkpoint service.

        Args:
            db_url: PostgreSQL connection URL. Defaults to settings.DATABASE_URL
        """
        self.db_url = db_url or settings.DATABASE_URL

        # Initialize PostgresSaver
        try:
            self.checkpointer = PostgresSaver.from_conn_string(self.db_url)
            self.checkpointer.setup()  # Create checkpoint tables if they don't exist

            logger.info(
                "checkpoint_service_initialized",
                db_url=self._mask_db_url(self.db_url),
            )
        except Exception as e:
            logger.error(
                "checkpoint_service_init_failed",
                error=str(e),
            )
            raise

    def get_checkpointer(self) -> PostgresSaver:
        """
        Get PostgresSaver instance.

        Returns:
            PostgresSaver instance for use with LangGraph
        """
        return self.checkpointer

    def _mask_db_url(self, url: str) -> str:
        """
        Mask sensitive information in database URL.

        Args:
            url: Database URL

        Returns:
            Masked URL for logging
        """
        if "@" in url:
            # postgresql://user:pass@host:port/db -> postgresql://***@host:port/db
            parts = url.split("@")
            if len(parts) == 2:
                return f"{parts[0].split('//')[0]}//***.***@{parts[1]}"
        return url


# Singleton instance
_checkpoint_service: Optional[CheckpointService] = None


def get_checkpoint_service() -> CheckpointService:
    """
    Get or create checkpoint service singleton.

    Returns:
        CheckpointService instance
    """
    global _checkpoint_service
    if _checkpoint_service is None:
        _checkpoint_service = CheckpointService()
    return _checkpoint_service


def get_checkpointer_for_session(
    session_id: str,
    tenant_id: str,
) -> PostgresSaver:
    """
    Get PostgresSaver configured for a specific session.

    Args:
        session_id: Session UUID
        tenant_id: Tenant UUID

    Returns:
        PostgresSaver instance configured with session context
    """
    service = get_checkpoint_service()
    checkpointer = service.get_checkpointer()

    logger.info(
        "checkpointer_created_for_session",
        session_id=session_id,
        tenant_id=tenant_id,
    )

    return checkpointer
