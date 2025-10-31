"""Domain agent implementations using LangChain."""
import json
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

    def _build_entity_extraction_prompt(self, user_message: str) -> str:
        """
        Build entity extraction prompt dynamically from agent's tools.

        Analyzes each tool's input_schema to know what entities to extract.
        """
        import json

        # Build list of required entities from tools
        required_entities = {}
        entity_descriptions = {}

        for tool in self.tools:
            # tool.args is the input_schema
            if hasattr(tool, 'args') and tool.args:
                input_schema = tool.args

                # Extract properties from JSON schema
                if isinstance(input_schema, dict) and 'properties' in input_schema:
                    for prop_name, prop_schema in input_schema['properties'].items():
                        if prop_name not in required_entities:
                            required_entities[prop_name] = True
                            description = prop_schema.get('description', f'Parameter: {prop_name}')
                            entity_descriptions[prop_name] = description

        # If no entities found from tools, use defaults
        if not required_entities:
            required_entities = {
                "tax_code": True,
                "salesman": True,
                "mst": True,
                "amount": True,
                "date": True,
                "shipment_id": True
            }
            entity_descriptions = {
                "tax_code": "Customer tax code",
                "salesman": "Salesman name or ID",
                "mst": "MST number",
                "amount": "Amount in currency",
                "date": "Date/time information",
                "shipment_id": "Shipment ID (format: VSG + 10 digits + FM)"
            }

        # Build entity examples
        entities_template = {}
        for entity_name, description in entity_descriptions.items():
            entities_template[entity_name] = f"value_if_found ({description})"

        entity_list = "\n".join([f"- {name}: {desc}" for name, desc in entity_descriptions.items()])

        extraction_prompt = f"""Analyze the user's message and extract:
1. Intent: What is the user trying to do?
2. Entities: Extract the following entities if present:

{entity_list}

User message: "{user_message}"

Respond ONLY with valid JSON (no markdown, no explanation):
{{
    "intent": "detected_intent",
    "entities": {{
{chr(10).join([f'        "{name}": "value_if_found"' for name in required_entities.keys()])}
    }}
}}

If an entity is not mentioned, omit it from the entities object."""

        return extraction_prompt

    async def _extract_intent_and_entities(self, user_message: str) -> tuple[str, Dict[str, Any]]:
        """
        Extract intent and entities from user message using LLM.

        Args:
            user_message: User's message

        Returns:
            Tuple of (intent, extracted_entities)
        """
        import json

        # Build extraction prompt dynamically from tools
        extraction_prompt = self._build_entity_extraction_prompt(user_message)

        try:
            extraction_response = await self.llm.ainvoke([
                SystemMessage(content="You are an entity extraction expert. Extract structured data from text."),
                HumanMessage(content=extraction_prompt)
            ])

            # Parse JSON response
            response_text = extraction_response.content.strip()
            # Handle markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            extraction_data = json.loads(response_text)
            intent = extraction_data.get("intent", "query")
            entities = extraction_data.get("entities", {})

            logger.info(
                "intent_entities_extracted",
                intent=intent,
                entities=entities
            )

            return intent, entities

        except Exception as e:
            logger.warning(f"Failed to extract intent/entities: {str(e)}")
            return "query", {}

    async def invoke(self, user_message: str) -> Dict[str, Any]:
        """
        Invoke agent with user message.

        Args:
            user_message: User's message

        Returns:
            Agent response dictionary
        """
        try:
            # Extract intent and entities from user message
            detected_intent, initial_entities = await self._extract_intent_and_entities(user_message)

            # Invoke LLM
            tool_calls_info = []
            extracted_entities = initial_entities.copy()  # Start with LLM-extracted entities
            tool_results = {}  # Store tool execution results

            if self.tools:
                # Build system prompt with dynamic tool instructions
                system_prompt = self.agent_config.prompt_template

                # Build tool descriptions from available tools
                tool_descriptions = []
                for tool in self.tools:
                    tool_desc = f'- "{tool.name}": {tool.description}'

                    # Add required parameters from tool schema
                    if hasattr(tool, 'args') and tool.args:
                        input_schema = tool.args
                        if isinstance(input_schema, dict) and 'required' in input_schema:
                            required_params = input_schema.get('required', [])
                            if required_params:
                                tool_desc += f" (requires: {', '.join(required_params)})"

                    tool_descriptions.append(tool_desc)

                tools_list = "\n".join(tool_descriptions)

                system_prompt += f"""

IMPORTANT: You have access to these tools:
{tools_list}

TOOL USAGE RULES:
1. When you have the required parameters for a tool, CALL IT IMMEDIATELY
2. Do NOT ask the user for missing information if you already have sufficient data
3. Match extracted entities to tool requirements
4. If a tool needs parameter X and you have entity X, use it

Available entities extracted from user message:
{json.dumps(extracted_entities, ensure_ascii=False, indent=2)}

For each tool:
- Check if you have all required parameters
- If YES → Call the tool with those parameters NOW
- If NO → Ask user for missing parameters (only if necessary)"""

                # Create messages
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message)
                ]

                # Bind tools to LLM
                llm_with_tools = self.llm.bind_tools(self.tools)
                response = await llm_with_tools.ainvoke(messages)

                # Extract and execute tool calls if present
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    logger.info(
                        "tool_calls_detected",
                        agent_name=self.agent_config.name,
                        tool_count=len(response.tool_calls)
                    )

                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get("name", "unknown")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id", "")

                        tool_info = {
                            "tool_name": tool_name,
                            "tool_args": tool_args,
                            "tool_id": tool_id
                        }
                        tool_calls_info.append(tool_info)

                        # Extract entities from tool arguments
                        for key in ["tax_code", "salesman", "mst", "amount", "date"]:
                            if key in tool_args and key not in extracted_entities:
                                extracted_entities[key] = tool_args[key]

                        # Execute the tool
                        try:
                            # Find tool by name
                            tool_to_execute = None
                            for tool in self.tools:
                                if tool.name == tool_name:
                                    tool_to_execute = tool
                                    break

                            if tool_to_execute:
                                logger.info(
                                    "tool_executing",
                                    tool_name=tool_name,
                                    tool_args=tool_args,
                                    agent_name=self.agent_config.name
                                )

                                # Execute tool using ainvoke (LangChain StructuredTool API)
                                # StructuredTool.ainvoke() expects tool_input as dict argument
                                tool_result = await tool_to_execute.ainvoke(tool_args)
                                tool_results[tool_id] = tool_result

                                logger.info(
                                    "tool_executed_success",
                                    tool_name=tool_name,
                                    agent_name=self.agent_config.name,
                                    result_type=type(tool_result).__name__
                                )
                            else:
                                logger.warning(
                                    "tool_not_found",
                                    tool_name=tool_name,
                                    agent_name=self.agent_config.name
                                )
                                tool_results[tool_id] = {"error": f"Tool {tool_name} not found"}

                        except Exception as e:
                            logger.error(
                                "tool_execution_error",
                                tool_name=tool_name,
                                error=str(e),
                                agent_name=self.agent_config.name
                            )
                            tool_results[tool_id] = {"error": str(e)}
            else:
                # No tools available, just invoke LLM
                messages = [
                    SystemMessage(content=self.agent_config.prompt_template),
                    HumanMessage(content=user_message)
                ]
                response = await self.llm.ainvoke(messages)

            logger.info(
                "agent_invoked",
                agent_name=self.agent_config.name,
                tenant_id=self.tenant_id,
                intent=detected_intent,
                tool_calls_count=len(tool_calls_info),
                extracted_entities=extracted_entities
            )

            # Get LLM model info
            llm_model_info = {
                "llm_model_id": str(self.agent_config.llm_model_id),
                "model_class": self.llm.__class__.__name__,
                "model_name": getattr(self.llm, 'model_name', 'unknown')
            }

            # Format response with tool results
            response_data = {"response": response.content}
            if tool_results:
                response_data["tool_results"] = tool_results

            # Format response
            return format_agent_response(
                agent_name=self.agent_config.name,
                intent=detected_intent,  # Use detected intent instead of hardcoded
                data=response_data,
                format_type="structured_json",
                metadata={
                    "agent_id": str(self.agent_id),
                    "tenant_id": self.tenant_id,
                    "llm_model": llm_model_info,
                    "tool_calls": tool_calls_info,
                    "extracted_entities": extracted_entities
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
        jwt_token: str,
        handler_class: str = None
    ) -> DomainAgent:
        """
        Create domain agent by name with dynamic class loading.

        Args:
            db: Database session
            agent_name: Name of the agent (e.g., "AgentDebt")
            tenant_id: Tenant UUID
            jwt_token: User JWT token
            handler_class: Optional pre-loaded handler_class path (avoids re-query)

        Returns:
            Domain agent instance

        Note:
            If handler_class is provided, uses it directly (no DB query).
            Otherwise, queries database to get handler_class.
            100% database-driven with optional optimization!
        """
        # Query database to get agent_config (needed for agent_id)
        agent_config = db.query(AgentConfig).filter(
            AgentConfig.name == agent_name,
            AgentConfig.is_active == True
        ).first()

        if not agent_config:
            raise ValueError(f"Agent {agent_name} not found")

        # Use pre-loaded handler_class if provided (optimization to avoid re-query)
        if handler_class:
            handler_class_path = handler_class
            logger.debug(
                "using_preloaded_handler_class",
                agent_name=agent_name,
                handler_class=handler_class_path
            )
        else:
            handler_class_path = agent_config.handler_class or "services.domain_agents.DomainAgent"

        try:
            # Dynamically import and load the class
            module_path, class_name = handler_class_path.rsplit(".", 1)
            module = __import__(f"src.{module_path}", fromlist=[class_name])
            AgentClass = getattr(module, class_name)

            logger.info(
                "agent_class_loaded",
                agent_name=agent_name,
                handler_class=handler_class_path,
                tenant_id=tenant_id
            )

            # Create and return agent instance
            return AgentClass(db, str(agent_config.agent_id), tenant_id, jwt_token)

        except (ImportError, AttributeError) as e:
            logger.error(
                "agent_class_load_failed",
                agent_name=agent_name,
                handler_class=handler_class_path,
                error=str(e),
                tenant_id=tenant_id
            )
            # Fallback to generic DomainAgent
            logger.warning(
                "using_generic_agent_fallback",
                agent_name=agent_name,
                tenant_id=tenant_id
            )
            return DomainAgent(db, str(agent_config.agent_id), tenant_id, jwt_token)
