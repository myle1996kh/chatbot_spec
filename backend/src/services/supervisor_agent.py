"""SupervisorAgent for routing user messages to domain agents."""
from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session
from src.services.llm_manager import llm_manager
from src.services.domain_agents import AgentFactory
from src.models.tenant import Tenant
from src.utils.logging import get_logger
from src.utils.formatters import format_clarification_response

logger = get_logger(__name__)


class SupervisorAgent:
    """Supervisor agent for intent detection and routing."""

    SUPERVISOR_PROMPT = """You are a Supervisor Agent that routes user queries to specialized domain agents.

Available agents:
- AgentDebt: Handles customer debt queries, payment history, account balances, and billing
- AgentAnalysis: Handles knowledge base queries, analysis questions, and information retrieval from documents

Your task:
1. Analyze the user's message carefully
2. Detect if the message contains ONE or MULTIPLE distinct questions/intents
3. Respond with ONLY the agent name or status code

Detection Rules:
- SINGLE INTENT examples:
  * "What is my account balance?" → AgentDebt
  * "Show me my recent payments" → AgentDebt
  * "What do I owe?" → AgentDebt
  * "What does our policy say about refunds?" → AgentAnalysis
  * "Find information about product warranties" → AgentAnalysis
  * "What are the company guidelines for returns?" → AgentAnalysis
  * "Search the knowledge base for shipping policies" → AgentAnalysis

- MULTIPLE INTENTS examples (queries asking about 2+ different topics):
  * "What's my debt for account MST 123 AND where is shipment ABC?" → MULTI_INTENT
  * "Show my balance and also track my order" → MULTI_INTENT
  * "What do I owe and what does the policy say about late payments?" → MULTI_INTENT

- UNCLEAR examples:
  * Ambiguous or nonsensical queries → UNCLEAR
  * Questions not related to any available agent → UNCLEAR

Response Format:
Respond with ONLY ONE of these: "AgentDebt", "AgentAnalysis", "MULTI_INTENT", or "UNCLEAR"
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

    async def route_message(self, user_message: str) -> Dict[str, Any]:
        """
        Route user message to appropriate domain agent.

        Args:
            user_message: User's message

        Returns:
            Agent response dictionary
        """
        try:
            # Detect intent and determine agent
            agent_name = await self._detect_intent(user_message)

            logger.info(
                "supervisor_routing",
                tenant_id=self.tenant_id,
                detected_agent=agent_name
            )

            # Handle special cases
            if agent_name == "MULTI_INTENT":
                return format_clarification_response(
                    detected_intents=["debt", "other"],
                    message="I detected multiple questions. Please ask one question at a time so I can help you better."
                )

            if agent_name == "UNCLEAR":
                return format_clarification_response(
                    detected_intents=[],
                    message="I'm not sure what you're asking about. Can you please rephrase your question?"
                )

            # Route to domain agent
            agent = await AgentFactory.create_agent(
                self.db,
                agent_name,
                self.tenant_id,
                self.jwt_token
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
            return {
                "status": "error",
                "agent": "SupervisorAgent",
                "intent": "routing_error",
                "data": {"message": str(e)},
                "format": "text",
                "renderer_hint": {"type": "error"},
                "metadata": {}
            }

    async def _detect_intent(self, user_message: str) -> str:
        """
        Detect user intent and determine appropriate agent.

        Args:
            user_message: User's message

        Returns:
            Agent name or special status (MULTI_INTENT, UNCLEAR)
        """
        messages = [
            SystemMessage(content=self.SUPERVISOR_PROMPT),
            HumanMessage(content=user_message)
        ]

        response = await self.llm.ainvoke(messages)
        agent_name = response.content.strip()

        logger.debug(
            "intent_detected",
            user_message=user_message[:100],
            detected_agent=agent_name,
            tenant_id=self.tenant_id
        )

        return agent_name
