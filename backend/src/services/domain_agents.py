"""Domain agent implementations using LangChain."""
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session
from src.services.llm_manager import llm_manager
from src.services.tool_loader import tool_registry
from src.models.agent import AgentConfig
from src.utils.logging import get_logger
from src.utils.formatters import format_agent_response, format_error_response

logger = get_logger(__name__)


class DomainAgent:
    """Base class for domain-specific agents."""

    def __init__(
        self,
        db: Session,
        agent_id: str,
        tenant_id: str,
        jwt_token: str
    ):
        """
        Initialize domain agent.

        Args:
            db: Database session
            agent_id: Agent UUID
            tenant_id: Tenant UUID
            jwt_token: User JWT token
        """
        self.db = db
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.jwt_token = jwt_token

        # Load agent configuration
        self.agent_config = db.query(AgentConfig).filter(
            AgentConfig.agent_id == agent_id,
            AgentConfig.is_active == True
        ).first()

        if not self.agent_config:
            raise ValueError(f"Agent {agent_id} not found or inactive")

        # Initialize LLM
        self.llm = llm_manager.get_llm_for_tenant(
            db,
            tenant_id,
            str(self.agent_config.llm_model_id)
        )

        # Load tools
        self.tools = tool_registry.load_agent_tools(
            db,
            agent_id,
            tenant_id,
            jwt_token,
            top_n=5
        )

    async def invoke(self, user_message: str) -> Dict[str, Any]:
        """
        Invoke agent with user message.

        Args:
            user_message: User's message

        Returns:
            Agent response dictionary
        """
        try:
            # Create messages
            messages = [
                SystemMessage(content=self.agent_config.prompt_template),
                HumanMessage(content=user_message)
            ]

            # Invoke LLM
            if self.tools:
                # Bind tools to LLM
                llm_with_tools = self.llm.bind_tools(self.tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await self.llm.ainvoke(messages)

            logger.info(
                "agent_invoked",
                agent_name=self.agent_config.name,
                tenant_id=self.tenant_id
            )

            # Format response
            return format_agent_response(
                agent_name=self.agent_config.name,
                intent="query",  # Could be extracted from message analysis
                data={"response": response.content},
                format_type="structured_json",
                metadata={
                    "agent_id": str(self.agent_id),
                    "tenant_id": self.tenant_id
                }
            )

        except Exception as e:
            logger.error(
                "agent_invocation_error",
                agent_name=self.agent_config.name,
                error=str(e),
                tenant_id=self.tenant_id
            )
            return format_error_response(
                agent_name=self.agent_config.name,
                intent="query",
                error_message=str(e)
            )


class AgentDebt(DomainAgent):
    """Specialized agent for customer debt queries."""

    async def invoke(self, user_message: str) -> Dict[str, Any]:
        """Invoke debt agent with customer debt query."""
        logger.info("agent_debt_invoked", tenant_id=self.tenant_id)
        return await super().invoke(user_message)


class AgentAnalysis(DomainAgent):
    """Specialized agent for knowledge base and analysis queries using RAG."""

    async def invoke(self, user_message: str) -> Dict[str, Any]:
        """
        Invoke analysis agent with knowledge query.

        This agent uses RAG (Retrieval-Augmented Generation) to answer
        questions based on the tenant's knowledge base stored in ChromaDB.
        """
        logger.info("agent_analysis_invoked", tenant_id=self.tenant_id)

        try:
            # Create messages with RAG-specific instructions
            system_prompt = f"""{self.agent_config.prompt_template}

IMPORTANT: You have access to a knowledge base retrieval tool (RAGTool).
When answering questions:
1. Use the RAG tool to search for relevant information
2. Cite sources from the retrieved documents in your response
3. If no relevant information is found, acknowledge this
4. Combine retrieved information with your reasoning

Format citations as: [Source: <metadata_info>]
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]

            # Invoke LLM with tools
            if self.tools:
                llm_with_tools = self.llm.bind_tools(self.tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await self.llm.ainvoke(messages)

            logger.info(
                "agent_analysis_response_generated",
                agent_name=self.agent_config.name,
                tenant_id=self.tenant_id,
                has_tool_calls=hasattr(response, "tool_calls") and len(response.tool_calls) > 0
            )

            # Format response with citation support
            return format_agent_response(
                agent_name=self.agent_config.name,
                intent="knowledge_query",
                data={"response": response.content},
                format_type="structured_json",
                metadata={
                    "agent_id": str(self.agent_id),
                    "tenant_id": self.tenant_id,
                    "supports_citations": True
                }
            )

        except Exception as e:
            logger.error(
                "agent_analysis_error",
                agent_name=self.agent_config.name,
                error=str(e),
                tenant_id=self.tenant_id
            )
            return format_error_response(
                agent_name=self.agent_config.name,
                intent="knowledge_query",
                error_message=str(e)
            )


class AgentFactory:
    """Factory for creating domain agents."""

    @staticmethod
    async def create_agent(
        db: Session,
        agent_name: str,
        tenant_id: str,
        jwt_token: str
    ) -> DomainAgent:
        """
        Create domain agent by name.

        Args:
            db: Database session
            agent_name: Name of the agent (e.g., "AgentDebt")
            tenant_id: Tenant UUID
            jwt_token: User JWT token

        Returns:
            Domain agent instance
        """
        # Find agent by name
        agent_config = db.query(AgentConfig).filter(
            AgentConfig.name == agent_name,
            AgentConfig.is_active == True
        ).first()

        if not agent_config:
            raise ValueError(f"Agent {agent_name} not found")

        # Create agent instance
        if agent_name == "AgentDebt":
            return AgentDebt(db, str(agent_config.agent_id), tenant_id, jwt_token)
        elif agent_name == "AgentAnalysis":
            return AgentAnalysis(db, str(agent_config.agent_id), tenant_id, jwt_token)
        else:
            # Generic domain agent
            return DomainAgent(db, str(agent_config.agent_id), tenant_id, jwt_token)
