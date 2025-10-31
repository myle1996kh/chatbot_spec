"""SupervisorAgent for routing user messages to domain agents."""
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session
from src.services.llm_manager import llm_manager
from src.services.domain_agents import AgentFactory
from src.models.agent import AgentConfig
from src.models.permissions import TenantAgentPermission
from src.utils.logging import get_logger
from src.utils.formatters import format_clarification_response
import re

logger = get_logger(__name__)


class SupervisorAgent:
    """Supervisor agent for intent detection and routing."""

    SUPERVISOR_PROMPT_TEMPLATE = """You are a Supervisor Agent that routes user queries to specialized domain agents.

Available agents:
{agents_list}

Your task:
1. Analyze the user's message carefully
2. Detect if the message contains ONE or MULTIPLE distinct questions/intents
3. Respond with ONLY the agent name or status code

Detection Rules:
- SINGLE INTENT: User asks ONE clear question matching ONE agent → respond with agent name
- MULTIPLE INTENTS: User asks 2+ DIFFERENT questions → respond with "MULTI_INTENT"
- UNCLEAR: Ambiguous or not related to any agent → respond with "UNCLEAR"

Response Format:
Respond with ONLY ONE of these: {agent_names}MULTI_INTENT", or "UNCLEAR"
NO explanations, NO additional text."""

    def __init__(self, db: Session, tenant_id: str, jwt_token: str):
        """
        Initialize supervisor agent.

        Args:
            db: Database session
            tenant_id: Tenant UUID
            jwt_token: User JWT token
        """
        self.db = db
        self.tenant_id = tenant_id
        self.jwt_token = jwt_token

        # Initialize LLM for routing
        self.llm = llm_manager.get_llm_for_tenant(db, tenant_id)

        # Load available agents for this tenant from database
        self.available_agents = self._load_available_agents()
        self.supervisor_prompt = self._build_supervisor_prompt()

    async def route_message(self, user_message: str) -> Dict[str, Any]:
        """
        Route user message to appropriate domain agent.

        Args:
            user_message: User's message

        Returns:
            Agent response dictionary
        """
        try:
            # Detect user language for multi-language support
            detected_language = self._detect_language(user_message)

            # Detect intent and determine agent
            agent_name = await self._detect_intent(user_message, detected_language)

            logger.info(
                "supervisor_routing",
                tenant_id=self.tenant_id,
                detected_agent=agent_name
            )

            # Get LLM model info for metadata
            llm_model_info = {
                "llm_model_id": "supervisor",
                "model_class": self.llm.__class__.__name__,
                "model_name": getattr(self.llm, 'model_name', 'unknown')
            }

            # Handle special cases with language-aware messages
            if agent_name == "MULTI_INTENT":
                multi_intent_msg = self._get_message("multiple_intents", detected_language)
                return format_clarification_response(
                    detected_intents=["debt", "other"],
                    message=multi_intent_msg,
                    llm_model_info=llm_model_info,
                    agent_id="supervisor",
                    tenant_id=self.tenant_id
                )

            if agent_name == "UNCLEAR":
                unclear_msg = self._get_message("unclear", detected_language)
                return format_clarification_response(
                    detected_intents=[],
                    message=unclear_msg,
                    llm_model_info=llm_model_info,
                    agent_id="supervisor",
                    tenant_id=self.tenant_id
                )

            # Route to domain agent with handler_class from available agents
            # Find handler_class for this agent (already loaded, no re-query)
            agent_config = next(
                (a for a in self.available_agents if a["name"] == agent_name),
                None
            )
            handler_class = agent_config["handler_class"] if agent_config else None

            agent = await AgentFactory.create_agent(
                self.db,
                agent_name,
                self.tenant_id,
                self.jwt_token,
                handler_class=handler_class  # Pass pre-loaded handler_class
            )

            response = await agent.invoke(user_message)

            logger.info(
                "supervisor_routed",
                tenant_id=self.tenant_id,
                agent=agent_name,
                status="success"
            )

            return response

        except Exception as e:
            logger.error(
                "supervisor_routing_error",
                tenant_id=self.tenant_id,
                error=str(e)
            )

            # Get LLM model info for error response
            llm_model_info = {
                "llm_model_id": "supervisor",
                "model_class": self.llm.__class__.__name__,
                "model_name": getattr(self.llm, 'model_name', 'unknown')
            }

            return {
                "status": "error",
                "agent": "SupervisorAgent",
                "intent": "routing_error",
                "data": {"message": str(e)},
                "format": "text",
                "renderer_hint": {"type": "error"},
                "metadata": {
                    "agent_id": "supervisor",
                    "tenant_id": self.tenant_id,
                    "llm_model": llm_model_info
                }
            }

    async def _detect_intent(self, user_message: str, language: str = "en") -> str:
        """
        Detect user intent and determine appropriate agent.

        Args:
            user_message: User's message
            language: Detected user language code (en, vi)

        Returns:
            Agent name or special status (MULTI_INTENT, UNCLEAR)
        """
        # Add language hint to prompt for better routing
        language_hint = f"\nUser's language: {language}. Route appropriately and respond in user's language."

        messages = [
            SystemMessage(content=self.supervisor_prompt + language_hint),
            HumanMessage(content=user_message)
        ]

        response = await self.llm.ainvoke(messages)
        agent_name = response.content.strip()

        logger.debug(
            "intent_detected",
            user_message=user_message[:100],
            detected_agent=agent_name,
            language=language,
            available_agents=[a["name"] for a in self.available_agents],
            tenant_id=self.tenant_id
        )

        return agent_name

    def _detect_language(self, text: str) -> str:
        """
        Detect language from user message (English or Vietnamese).

        Args:
            text: User message text

        Returns:
            Language code (en or vi)
        """
        # Vietnamese character ranges
        vietnamese_chars = r'[\u0100-\u01B0\u1E00-\u1EFF]'

        if re.search(vietnamese_chars, text):
            logger.debug("language_detected", language="vi", tenant_id=self.tenant_id)
            return 'vi'
        else:
            logger.debug("language_detected", language="en", tenant_id=self.tenant_id)
            return 'en'

    def _get_message(self, message_type: str, language: str = "en") -> str:
        """
        Get language-specific messages (English or Vietnamese).

        Args:
            message_type: Type of message (multiple_intents, unclear)
            language: Language code (en or vi)

        Returns:
            Message in the specified language
        """
        messages = {
            "multiple_intents": {
                "en": "I detected multiple questions. Please ask one question at a time so I can help you better.",
                "vi": "Tôi phát hiện nhiều câu hỏi. Vui lòng đặt một câu hỏi cùng một lúc để tôi có thể giúp bạn tốt hơn."
            },
            "unclear": {
                "en": "I'm sorry, I can only help with topics related to our system — such as checking customer debt, tracking shipments, analyzing data, or searching the knowledge base. Could you please ask something related to those?",
                "vi": "Xin lỗi, tôi chỉ có thể hỗ trợ các nội dung liên quan đến hệ thống — như tra cứu công nợ khách hàng, tra cứu vận đơn, phân tích dữ liệu hoặc tìm kiếm trong kho kiến thức. Bạn có thể đặt câu hỏi liên quan đến các nội dung đó không?"
            }
        }

        # Get message for specific language, fallback to English
        message_dict = messages.get(message_type, {})
        return message_dict.get(language, message_dict.get("en", "Please try again."))

    def _load_available_agents(self) -> List[Dict[str, Any]]:
        """
        Load all available agents for this tenant from database.

        Returns:
            List of agent dicts with name and description
        """
        try:
            # Query agents enabled for this tenant
            agents = (
                self.db.query(AgentConfig)
                .join(
                    TenantAgentPermission,
                    TenantAgentPermission.agent_id == AgentConfig.agent_id
                )
                .filter(
                    TenantAgentPermission.tenant_id == self.tenant_id,
                    TenantAgentPermission.enabled == True,
                    AgentConfig.is_active == True
                )
                .all()
            )

            available = [
                {
                    "name": agent.name,
                    "handler_class": agent.handler_class or "services.domain_agents.DomainAgent",
                    "description": agent.description or f"Handles {agent.name} queries"
                }
                for agent in agents
            ]

            logger.info(
                "agents_loaded",
                tenant_id=self.tenant_id,
                agent_count=len(available),
                agent_names=[a["name"] for a in available]
            )

            return available

        except Exception as e:
            logger.error(
                "agents_load_failed",
                tenant_id=self.tenant_id,
                error=str(e)
            )
            return []

    def _build_supervisor_prompt(self) -> str:
        """
        Build supervisor prompt dynamically from available agents.

        Returns:
            Formatted supervisor prompt
        """
        if not self.available_agents:
            # Fallback if no agents found
            agents_list = "- No agents available"
            agent_names = '"UNCLEAR"'
            logger.warning(
                "no_agents_available",
                tenant_id=self.tenant_id
            )
        else:
            # Build agent list with descriptions
            agents_list = "\n".join([
                f"- {agent['name']}: {agent['description']}"
                for agent in self.available_agents
            ])

            # Build valid response options
            agent_names_str = ", ".join([
                f'"{agent["name"]}"'
                for agent in self.available_agents
            ])
            agent_names = agent_names_str + ', '

        prompt = self.SUPERVISOR_PROMPT_TEMPLATE.format(
            agents_list=agents_list,
            agent_names=agent_names
        )

        logger.debug(
            "supervisor_prompt_built",
            tenant_id=self.tenant_id,
            agent_count=len(self.available_agents)
        )

        return prompt
