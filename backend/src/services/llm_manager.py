"""LLM Manager for loading and managing language model clients."""
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.orm import Session
from src.models.llm_model import LLMModel
from src.models.tenant_llm_config import TenantLLMConfig
from src.utils.encryption import decrypt_api_key
from src.utils.logging import get_logger
from src.config import settings

logger = get_logger(__name__)


class LLMManager:
    """Manager for instantiating and caching LLM clients."""

    def __init__(self):
        """Initialize LLM manager."""
        self._cache: Dict[str, Any] = {}

    def get_llm_for_tenant(
        self,
        db: Session,
        tenant_id: str,
        llm_model_id: Optional[str] = None
    ) -> Any:
        """
        Get LLM client for a specific tenant.

        Args:
            db: Database session
            tenant_id: Tenant UUID
            llm_model_id: Optional specific model ID, otherwise uses tenant's default

        Returns:
            LangChain LLM client instance

        Raises:
            ValueError: If tenant LLM config not found or model not supported
        """
        cache_key = f"llm:{tenant_id}:{llm_model_id or 'default'}"

        # Check cache
        if cache_key in self._cache:
            logger.debug("llm_cache_hit", tenant_id=tenant_id)
            return self._cache[cache_key]

        # Load tenant LLM config
        tenant_config = db.query(TenantLLMConfig).filter(
            TenantLLMConfig.tenant_id == tenant_id
        ).first()

        if not tenant_config:
            raise ValueError(f"No LLM configuration found for tenant {tenant_id}")

        # Use specified model or tenant's default
        model_id = llm_model_id or tenant_config.llm_model_id

        # Load LLM model details
        llm_model = db.query(LLMModel).filter(
            LLMModel.llm_model_id == model_id
        ).first()

        if not llm_model:
            raise ValueError(f"LLM model {model_id} not found")

        if not llm_model.is_active:
            raise ValueError(f"LLM model {llm_model.model_name} is not active")

        # Decrypt API key
        api_key = decrypt_api_key(tenant_config.encrypted_api_key)

        # Instantiate LLM client based on provider
        llm_client = self._create_llm_client(llm_model, api_key)

        # Cache the client
        self._cache[cache_key] = llm_client

        logger.info(
            "llm_client_created",
            tenant_id=tenant_id,
            provider=llm_model.provider,
            model_name=llm_model.model_name
        )

        return llm_client

    def _create_llm_client(self, llm_model: LLMModel, api_key: str) -> Any:
        """
        Create LLM client instance based on provider.

        Args:
            llm_model: LLM model configuration
            api_key: Decrypted API key

        Returns:
            LangChain LLM client

        Raises:
            ValueError: If provider not supported
        """
        provider = llm_model.provider.lower()
        model_name = llm_model.model_name

        # OpenRouter (unified API for multiple providers)
        if provider == "openrouter":
            return ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                openai_api_base=settings.OPENROUTER_BASE_URL,
                temperature=0.7,
                max_tokens=4096,
                model_kwargs={
                    "extra_headers": {
                        "HTTP-Referer": "https://agenthub.local",
                        "X-Title": "AgentHub"
                    }
                }
            )

        # Direct OpenAI
        elif provider == "openai":
            return ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                temperature=0.0,
                max_tokens=4096
            )

        # Google Gemini
        elif provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.0,
                max_output_tokens=4096
            )

        # Anthropic Claude
        elif provider == "anthropic":
            return ChatAnthropic(
                model=model_name,
                anthropic_api_key=api_key,
                temperature=0.0,
                max_tokens=4096
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def clear_cache(self, tenant_id: Optional[str] = None):
        """
        Clear LLM client cache.

        Args:
            tenant_id: Optional tenant ID to clear specific tenant cache
        """
        if tenant_id:
            # Clear specific tenant's cache
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"llm:{tenant_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info("llm_cache_cleared", tenant_id=tenant_id)
        else:
            # Clear all cache
            self._cache.clear()
            logger.info("llm_cache_cleared_all")


# Global LLM manager instance
llm_manager = LLMManager()
