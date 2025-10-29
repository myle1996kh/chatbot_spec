# Feature Specification: AgentHub Multi-Agent Chatbot Framework

**Feature Branch**: `001-agenthub-chatbot-framework`
**Created**: 2025-10-28
**Status**: Draft
**Input**: Build AgentHub Multi-Agent Chatbot Framework with LangChain, SupervisorAgent routing, dynamic tool loading, JWT security, multi-tenant support, and config-driven architecture for ERP/CRM data interaction

## Clarifications

### Session 2025-10-28

- Q: For MVP (P1), should the SupervisorAgent support sequential multi-agent execution for multi-intent queries, or reject them? → A: Single-intent only for MVP - reject multi-intent queries with "Please ask one question at a time" message. Sequential multi-agent execution deferred to P2.

- Q: For conversations exceeding 10 messages, which context management strategy should agents use? → A: Sliding window - keep last 10 messages + system prompt, discard older messages using LangChain's trim_messages() function.

- Q: How should the "priority" field in agent_tools table control which tools the agent considers? → A: Pre-filter to top 5 priority tools (sorted by priority ASC), then LLM chooses semantically from filtered set. Priority controls tool visibility, not selection order.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Business User Queries Customer Debt via Natural Language (Priority: P1)

A business user (sales representative, account manager) needs to quickly check customer debt information by simply asking the chatbot "What is the debt status for customer MST 0123456789?" without needing to navigate through multiple ERP screens or understand complex query interfaces.

**Why this priority**: This is the core value proposition - enabling non-technical users to access critical business data through natural conversation. It demonstrates the end-to-end flow: user input → intent detection → agent selection → tool execution → formatted response.

**Independent Test**: Can be fully tested by sending a natural language debt query via the chat widget and verifying that the system returns accurate, formatted debt information from the backend ERP system. Delivers immediate value by reducing time to access debt data from minutes to seconds.

**Acceptance Scenarios**:

1. **Given** a logged-in user with valid JWT token, **When** user asks "Show me debt for customer MST 0123456789", **Then** system returns structured debt data including total amount, overdue status, and payment history
2. **Given** a user asks about customer debt, **When** the MST number is invalid or not found, **Then** system responds with a clear error message explaining the issue
3. **Given** a user asks a debt-related question, **When** SupervisorAgent analyzes the intent, **Then** it correctly routes to AgentDebt (not other agents)
4. **Given** AgentDebt receives the query, **When** it extracts the MST parameter, **Then** it calls the correct tool (get_customer_debt_by_mst) with proper JWT authentication headers

---

### User Story 2 - Tenant Administrator Configures New Agent Without Code Changes (Priority: P1)

A tenant administrator or system integrator needs to add a new business domain agent (e.g., "AgentInventory" for warehouse queries) by simply configuring it through the admin interface - specifying the agent's purpose, available tools, LLM model, and output format - without requiring any code deployment or system restart.

**Why this priority**: This validates the "Configuration Over Code" principle and demonstrates system extensibility. It's critical for onboarding new tenants and proving the multi-tenant architecture works as designed.

**Independent Test**: Can be fully tested by using admin API endpoints to create a new agent configuration, assign tools to it, enable it for a specific tenant, and then verify that users can interact with this new agent immediately. Delivers value by enabling rapid business expansion without engineering involvement.

**Acceptance Scenarios**:

1. **Given** an admin user with proper permissions, **When** they POST to `/api/admin/agents` with agent configuration (name, prompt, tools, model), **Then** system creates the agent and returns agent_id
2. **Given** a newly created agent, **When** admin assigns it to a tenant via `/api/admin/tenants/{id}/permissions`, **Then** users of that tenant can immediately interact with the new agent
3. **Given** an active agent, **When** admin updates its prompt or tool list via PATCH `/api/admin/agents/{id}`, **Then** subsequent conversations use the updated configuration
4. **Given** a tenant with multiple agents enabled, **When** user sends a message, **Then** SupervisorAgent can route to any of the tenant's available agents based on intent

---

### User Story 3 - Multi-Tenant Isolation and Security (Priority: P1)

Two different companies (TenantA and TenantB) use the same AgentHub system but must never access each other's data, agent configurations, or conversation history. Each tenant has their own API keys, agent permissions, and data isolation enforced at every layer (cache, database, API calls).

**Why this priority**: Security and data isolation are non-negotiable for enterprise SaaS. This validates the JWT-based tenant isolation, namespaced caching, and permission system - all critical for production deployment.

**Independent Test**: Can be fully tested by creating two tenant accounts, configuring agents for each, sending queries from both tenants simultaneously, and verifying that: (1) TenantA cannot see TenantB's conversations, (2) TenantA's agents use TenantA's API keys when calling external systems, (3) Cache keys are properly namespaced. Delivers value by proving the system is production-ready for multi-tenant deployment.

**Acceptance Scenarios**:

1. **Given** TenantA user with JWT token, **When** they query the chatbot, **Then** system only accesses data and agents configured for TenantA
2. **Given** TenantB has different LLM model configured, **When** their users query the chatbot, **Then** system uses TenantB's LLM model and API key, not TenantA's
3. **Given** an agent tool makes an HTTP call to external API, **When** it executes, **Then** it includes the user's JWT token in Authorization header (not system token)
4. **Given** two tenants sharing Redis cache, **When** configurations are cached, **Then** keys use pattern `agenthub:{tenant_id}:cache:{key}` preventing cross-tenant access

---

### User Story 4 - SupervisorAgent Handles Multi-Intent Queries (Priority: P2)

A user asks a complex question like "What's the debt status for customer MST 0123456789 and where is their latest shipment?" For MVP (P1), the SupervisorAgent detects multiple intents and politely asks the user to ask one question at a time. Sequential multi-agent execution is planned for P2 post-MVP.

**Why this priority**: MVP focuses on single-intent routing (P1). Multi-intent handling is valuable but adds complexity (state management, result aggregation, error handling across agents). Better to prove single-intent works first, then layer on multi-agent orchestration.

**Independent Test**: Can be fully tested by sending multi-domain queries and verifying that SupervisorAgent responds with "I detected multiple questions. Please ask about debt or shipment separately so I can help you better." Delivers value by setting clear user expectations about system capabilities.

**Acceptance Scenarios**:

1. **Given** a user asks a multi-intent question (debt + shipment), **When** SupervisorAgent analyzes it, **Then** it detects both intents and responds "Please ask one question at a time"
2. **Given** a user asks a single-intent question after multi-intent rejection, **When** SupervisorAgent processes it, **Then** it correctly routes to the appropriate domain agent
3. **Given** P2 enhancement adds sequential execution, **When** multi-intent detected, **Then** SupervisorAgent routes to first agent, gets result, then routes to second agent and synthesizes combined response

---

### User Story 5 - Dynamic Tool Loading from Database Configuration (Priority: P2)

A developer or integrator adds a new external API endpoint (e.g., "get_warehouse_inventory") by inserting a record into `tool_configs` table with the endpoint URL, HTTP method, headers, input schema, and output format. The system automatically makes this tool available to any agent configured to use it, without code changes or redeployment.

**Why this priority**: This validates the "Dynamic Tool Loading" architecture and ToolLoader factory pattern. It's P2 because basic tool execution (P1 agents using existing tools) must work first.

**Independent Test**: Can be fully tested by: (1) inserting a new tool configuration into database, (2) assigning it to an existing agent, (3) asking the agent a question that should trigger this tool, (4) verifying the tool executes correctly with proper authentication and returns formatted data. Delivers value by enabling rapid integration with new business systems.

**Acceptance Scenarios**:

1. **Given** a new tool config inserted into `tool_configs` table, **When** an agent with this tool_id is invoked, **Then** ToolLoader successfully instantiates the tool at runtime
2. **Given** a tool requires specific HTTP headers, **When** tool config includes custom headers, **Then** ToolLoader passes these headers along with JWT token when making requests
3. **Given** a tool has an output_format_id specified, **When** tool returns data, **Then** OutputFormatter applies the specified format (e.g., structured_json, markdown_table, chart_data)
4. **Given** a tool is updated in database (e.g., endpoint URL changed), **When** cache TTL expires or manual reload triggered, **Then** subsequent tool calls use the new configuration

---

### User Story 6 - RAG-Powered Knowledge Base Queries (Priority: P3)

A user asks "What is our company's return policy?" and the system uses a RAGTool to search the knowledge base (stored in ChromaDB as vector embeddings), retrieves relevant documentation chunks, and uses an LLM to synthesize a natural language answer.

**Why this priority**: RAG is valuable for unstructured knowledge retrieval but is P3 because transactional data queries (P1) are more critical for initial MVP. RAG can be added once core agent/tool architecture is proven.

**Independent Test**: Can be fully tested by: (1) loading sample company documents into ChromaDB, (2) configuring an AgentAnalysis with RAGTool, (3) asking knowledge-based questions, (4) verifying relevant chunks are retrieved and coherent answers generated. Delivers value by enabling self-service access to company documentation.

**Acceptance Scenarios**:

1. **Given** knowledge documents loaded in ChromaDB, **When** user asks a policy question, **Then** RAGTool retrieves top 3 relevant chunks based on semantic similarity
2. **Given** retrieved chunks, **When** AgentAnalysis generates answer, **Then** response cites the source documents or sections
3. **Given** no relevant knowledge found, **When** RAG similarity score is below threshold, **Then** agent responds "I don't have information about that in my knowledge base"

---

### User Story 7 - Widget Integration and Session Management (Priority: P2)

A business application (ERP web interface) embeds the AgentHub chat widget, which maintains conversation context across multiple messages in a session. Users can see their conversation history, and the system remembers context from previous messages in the same session.

**Why this priority**: Session management is important for conversational UX but is P2 because single-query interactions (P1) must work first. Multi-turn conversations add complexity that can be layered on.

**Independent Test**: Can be fully tested by: (1) embedding the widget in a test HTML page, (2) sending multiple messages in sequence, (3) verifying each message is stored with correct session_id, (4) confirming agents can access conversation history for context. Delivers value by enabling natural multi-turn conversations.

**Acceptance Scenarios**:

1. **Given** a user starts a conversation, **When** first message sent, **Then** system creates a new session_id and returns it to the widget
2. **Given** an existing session, **When** user sends follow-up message, **Then** system appends message to same session and agent can reference previous context
3. **Given** a session with history, **When** user asks "What about shipment ABC123?", **Then** agent understands this is follow-up to previous debt query about same customer
4. **Given** user wants to see past conversations, **When** they call GET `/api/{tenant}/session`, **Then** system returns list of their sessions with timestamps

---

### Edge Cases

- **What happens when a JWT token expires mid-conversation?** System should return 401 Unauthorized with clear message "Session expired, please refresh your token", and widget should handle re-authentication
- **How does system handle when an external API tool returns 500 or timeout?** Tool should catch the error, return a structured error response, and agent should inform user "I couldn't retrieve that data right now, please try again later"
- **What if SupervisorAgent cannot determine intent?** System should respond asking for clarification: "I'm not sure what you're asking about. Can you try rephrasing your question or specify if you're asking about debt, shipments, or something else?"
- **What happens when tenant's LLM API quota is exceeded?** System should catch quota error, log it for admin, and respond to user: "Service temporarily unavailable due to usage limits, please contact your administrator"
- **How does system handle when database connection pool is exhausted?** FastAPI should queue requests up to a timeout threshold, then return 503 Service Unavailable with retry-after header
- **What if a malicious user tries to inject SQL or prompt injection?** All user inputs must be sanitized/escaped before passing to LLM or tools. LLM prompts should include instructions to ignore commands in user input. Tool input schemas should validate/sanitize parameters.
- **What happens when multiple tenants update the same agent configuration simultaneously?** Use database row-level locking or optimistic concurrency control (version field) to prevent race conditions. Last write wins with conflict detection.
- **How does system handle when ChromaDB is unavailable?** RAGTool should catch connection errors and gracefully fail with message "Knowledge base temporarily unavailable", allowing other non-RAG agents to continue working

## Requirements *(mandatory)*

### Functional Requirements

#### Core Chat Interaction
- **FR-001**: System MUST accept user messages via POST `/api/{tenant_id}/chat` endpoint with JWT authentication
- **FR-002**: System MUST validate JWT token signature (RS256) and extract tenant_id, user_id, and access_token from payload
- **FR-003**: System MUST return responses in under 2.5 seconds for standard queries (excluding RAG operations)
- **FR-004**: System MUST maintain conversation sessions and associate messages with session_id
- **FR-005**: System MUST return structured JSON responses with fields: status, agent, intent, data, format, renderer_hint, metadata

#### SupervisorAgent Routing
- **FR-006**: System MUST implement a SupervisorAgent that analyzes user messages to determine intent and target domain
- **FR-007**: SupervisorAgent MUST have access to list of available agents for the tenant (from tenant_agent_permissions)
- **FR-008**: SupervisorAgent MUST route messages to the most appropriate domain agent (AgentDebt, AgentShipment, AgentOCR, AgentAnalysis)
- **FR-009**: SupervisorAgent MUST use a lightweight LLM model (e.g., GPT-4o-mini) for fast intent classification
- **FR-010**: SupervisorAgent MUST handle cases where intent is unclear by asking clarifying questions
- **FR-010a**: For MVP, SupervisorAgent MUST reject multi-intent queries with message "Please ask one question at a time" (sequential multi-agent execution deferred to P2)

#### Domain Agents
- **FR-011**: System MUST support multiple domain-specific agents, each with its own prompt, tools, and LLM model
- **FR-012**: Each domain agent MUST be implemented using LangChain create_react_agent pattern with LangGraph for reasoning and tool calling
- **FR-013**: Agents MUST load their configuration from database (`agent_configs` table) at runtime
- **FR-014**: Agents MUST only use tools explicitly assigned to them in `agent_tools` table, pre-filtered to top 5 priority tools (sorted by priority ASC) before LLM selection
- **FR-015**: Agents MUST pass user context (JWT token) to tools when making external API calls
- **FR-015a**: For multi-turn conversations exceeding 10 messages, agents MUST use sliding window context management (keep last 10 messages + system prompt) using LangChain's trim_messages() function

#### Dynamic Tool Loading
- **FR-016**: System MUST implement a ToolLoader component that creates tool instances from database configuration
- **FR-017**: System MUST support multiple tool types: HTTPGetTool, HTTPPostTool, RAGTool, DBQueryTool, OCRTool
- **FR-018**: Each tool configuration MUST specify: name, base_tool_id, endpoint/connection info, input schema, output format
- **FR-019**: HTTPTools MUST automatically inject Authorization header with user JWT token when calling external APIs
- **FR-020**: Tools MUST validate input parameters against their defined JSON schema before execution

#### Multi-Tenant Architecture
- **FR-021**: System MUST isolate data, configurations, and cache between tenants using tenant_id namespace
- **FR-022**: System MUST enforce tenant permissions: agents and tools must be explicitly enabled for each tenant
- **FR-023**: Redis cache keys MUST use pattern `agenthub:{tenant_id}:cache:{key}` for namespace isolation
- **FR-024**: Each tenant MUST have their own LLM model configuration with encrypted API keys
- **FR-025**: System MUST prevent cross-tenant data access at database query level (filter by tenant_id)

#### LLM Management
- **FR-026**: System MUST support multiple LLM providers (OpenAI GPT, Google Gemini, Anthropic Claude, OpenRouter)
- **FR-027**: System MUST load LLM model configuration from `llm_models` and `tenant_llm_configs` tables
- **FR-028**: System MUST encrypt LLM API keys using Fernet encryption before storing in database
- **FR-029**: System MUST decrypt API keys only at runtime when instantiating LLM clients
- **FR-030**: System MUST track token usage and costs per tenant for billing/monitoring purposes

#### Output Formatting
- **FR-031**: System MUST support multiple output formats: structured_json, markdown_table, chart_data, summary_text
- **FR-032**: Each tool MUST specify a default output_format_id from `output_formats` table
- **FR-033**: System MUST apply OutputFormatter to standardize responses before returning to user
- **FR-034**: Formatted responses MUST include renderer_hint to guide UI on how to display data (table, chart, text)
- **FR-035**: Tenants MUST be able to override output format for specific agents via `tenant_agent_permissions.output_override_id`

#### Security & Authentication
- **FR-036**: System MUST require valid JWT token (RS256 algorithm) for all API endpoints
- **FR-037**: JWT tokens MUST have 24-hour TTL and be validated on every request
- **FR-038**: System MUST return 401 Unauthorized for expired or invalid tokens
- **FR-039**: System MUST return 403 Forbidden when tenant lacks permission for requested agent/tool
- **FR-040**: System MUST sanitize all user inputs to prevent SQL injection and prompt injection attacks
- **FR-041**: System MUST NOT log or expose API keys, tokens, or sensitive PII in logs or responses

#### Agent & Tool Management (Admin API)
- **FR-042**: System MUST provide admin endpoints to create, read, update agents (`/api/admin/agents`)
- **FR-043**: System MUST provide admin endpoints to create, read, update tools (`/api/admin/tools`)
- **FR-044**: System MUST provide admin endpoints to manage tenant permissions (`/api/admin/tenants/{id}/permissions`)
- **FR-045**: System MUST support cache reload via `/api/admin/agents/reload` without requiring system restart
- **FR-046**: Admin endpoints MUST be protected with elevated permission checks (admin role required)

#### Session & Message History
- **FR-047**: System MUST persist all messages to `messages` table with session_id, role (user/assistant), content, timestamp
- **FR-048**: System MUST persist session metadata to `sessions` table including tenant_id, agent_id, created_at
- **FR-049**: Users MUST be able to retrieve their session list via GET `/api/{tenant_id}/session`
- **FR-050**: Users MUST be able to retrieve full message history for a session via GET `/api/{tenant_id}/session/{id}`
- **FR-050a**: System MUST use LangGraph PostgresSaver for conversation checkpointing with thread_id pattern: `tenant_{tenant_id}__user_{user_id}__session_{session_id}` for multi-tenant isolation

#### RAG (Vector Knowledge Base)
- **FR-051**: System MUST support RAGTool for semantic search over knowledge documents stored in ChromaDB
- **FR-052**: RAGTool MUST convert user query to embeddings and retrieve top-k similar document chunks
- **FR-053**: RAGTool MUST return source document references along with retrieved content
- **FR-054**: System MUST handle cases where no relevant knowledge is found (similarity below threshold)

#### Monitoring & Observability
- **FR-055**: System MUST log all agent invocations with: tenant_id, agent_name, duration_ms, timestamp
- **FR-056**: System MUST log all tool calls with: tenant_id, tool_name, duration_ms, success/failure status
- **FR-057**: System MUST track metrics: agent_calls_total, tool_calls_total, tool_avg_latency, llm_cost_total
- **FR-058**: System MUST provide admin endpoint GET `/api/admin/metrics` to retrieve aggregated usage statistics
- **FR-059**: System MUST use structured JSON logging for all application logs

### Key Entities

- **Tenant**: Represents a company/organization using the system. Attributes: tenant_id (UUID), name, domain, status (active/suspended), created_at. Relationships: has many agents (via permissions), has many tools (via permissions), has LLM config.

- **Agent Configuration**: Defines a domain-specific agent. Attributes: agent_id, name (e.g., "AgentDebt"), prompt_template, llm_model_id, default_output_format_id, description. Relationships: belongs to base agent config, has many tools (via agent_tools), enabled for many tenants (via tenant_agent_permissions).

- **Tool Configuration**: Defines a specific tool instance. Attributes: tool_id, name, base_tool_id (type), config (JSON: endpoint, method, headers), input_schema (JSON), output_format_id. Relationships: belongs to base_tool, assigned to many agents (via agent_tools), enabled for many tenants (via tenant_tool_permissions).

- **Base Tool**: Template for tool types. Attributes: base_tool_id, type (HTTP_GET, HTTP_POST, RAG, DB_QUERY, OCR), handler_class, description. Relationships: has many tool configs.

- **LLM Model**: Available language models. Attributes: llm_model_id, provider (openai, gemini, anthropic), model_name (gpt-4o, gemini-pro), context_window, cost_per_token. Relationships: has many tenant configs.

- **Tenant LLM Config**: Tenant-specific LLM settings. Attributes: tenant_id, llm_model_id, encrypted_api_key, rate_limit, created_at. Relationships: belongs to tenant and llm_model.

- **Session**: Conversation session. Attributes: session_id (UUID), tenant_id, user_id, agent_id (optional), created_at, last_message_at. Relationships: belongs to tenant, has many messages.

- **Message**: Individual chat message. Attributes: message_id, session_id, role (user/assistant), content, timestamp, metadata (JSON: intent, tool_calls). Relationships: belongs to session.

- **Output Format**: Response format definition. Attributes: format_id, name (structured_json, markdown_table), schema (JSON), renderer_hint (JSON: type, fields). Relationships: used by many tools and agents.

- **Agent-Tool Assignment**: Many-to-many relationship. Attributes: agent_id, tool_id, priority (1=highest). Defines which tools each agent can use. Priority controls tool visibility: system pre-filters to top 5 priority tools (ASC order) before LLM semantic selection.

- **Tenant Agent Permission**: Enables agents for tenants. Attributes: tenant_id, agent_id, enabled (boolean), output_override_id (optional). Controls which agents are available to each tenant.

- **Tenant Tool Permission**: Enables tools for tenants. Attributes: tenant_id, tool_id, enabled (boolean). Controls which tools are accessible by tenant's agents.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Business users can retrieve customer debt information by asking natural language questions, receiving results in under 2.5 seconds for 95% of queries
- **SC-002**: System administrators can configure and deploy a new domain agent (with prompt, tools, LLM model) for a tenant in under 5 minutes without code changes or system restart
- **SC-003**: System supports 100+ tenants simultaneously with isolated data and configurations, maintaining under 2.5 second response time under normal load
- **SC-004**: When a new external API tool is added via database configuration, it becomes available to assigned agents immediately (within cache TTL window of 1 hour, or instantly with manual cache reload)
- **SC-005**: Multi-turn conversations maintain context across 10+ messages in a session, with agents correctly referencing previous conversation history
- **SC-006**: SupervisorAgent achieves 95%+ accuracy in routing user queries to the correct domain agent (measured against labeled test dataset)
- **SC-007**: Zero cross-tenant data leakage incidents - tenants can only access their own conversations, configurations, and data (validated through security testing)
- **SC-008**: System maintains 90%+ cache hit rate for agent and tool configurations, reducing database load
- **SC-009**: RAG-based knowledge queries return relevant answers in under 4 seconds, with source document citations
- **SC-010**: Admin monitoring dashboard shows real-time metrics (agent calls, tool usage, latency, costs) with under 10 second delay
- **SC-011**: System achieves 99.9% uptime for chat endpoint, with graceful degradation when external APIs or services fail
- **SC-012**: 80%+ of user queries result in successful tool execution and data retrieval (not errors or clarification requests)

## Scope Boundaries

### In Scope
- Multi-tenant chatbot framework with JWT-based authentication
- SupervisorAgent for intent routing to domain agents
- Four initial domain agents: AgentDebt, AgentShipment, AgentOCR, AgentAnalysis
- Dynamic tool loading from database (HTTP, RAG, DB query, OCR tools)
- LangChain-based agent orchestration and tool calling
- Multiple LLM provider support (OpenAI, Gemini, Claude, OpenRouter)
- Output formatting and rendering hints for UI
- Admin APIs for agent/tool/tenant management
- Session and message persistence
- Redis caching for configurations
- PostgreSQL for relational data, ChromaDB for vector embeddings
- Structured logging and metrics tracking

### Out of Scope (Future Enhancements)
- Voice input/output (speech-to-text, text-to-speech)
- Multilingual support beyond English and Vietnamese
- Real-time streaming responses (currently batch response only)
- Parallel multi-agent execution (currently sequential routing)
- Fine-tuning custom LLM models (only using pre-trained models)
- OAuth2/SSO integration (currently JWT only, external auth provider assumed)
- Automated agent orchestration workflows (e.g., trigger agent on schedule)
- Mobile native apps (currently web widget only)
- Advanced RAG features (re-ranking, hybrid search, query expansion)
- Billing and payment processing (metrics tracked but no billing system)

## Assumptions

1. **Authentication Provider Exists**: System assumes JWT tokens are issued by an external authentication service (SSO, OAuth2 provider). AgentHub validates tokens but does not handle user login/registration.

2. **External APIs Are Available**: Business data (debt, shipment, inventory) comes from existing ERP/CRM APIs that are accessible via HTTP and return JSON responses.

3. **Database Schema Pre-Created**: Database tables (`base_tools`, `tool_configs`, `agent_configs`, `llm_models`, etc.) are created via migration scripts before first deployment.

4. **LLM API Keys Provided**: Tenants or system admins provide valid API keys for their chosen LLM providers during onboarding.

5. **Network Connectivity**: System has reliable network access to LLM provider APIs (OpenAI, Google, Anthropic) and external business APIs.

6. **UTF-8 Encoding**: All text (messages, prompts, API responses) uses UTF-8 encoding, supporting English and Vietnamese languages.

7. **Redis Persistence**: Redis is configured with appropriate persistence (RDB/AOF) to prevent cache data loss on restart.

8. **Single Region Deployment**: Initial deployment is single-region; multi-region replication and geo-distribution are not required.

9. **Reasonable Data Volumes**: Each tenant has under 10,000 conversations per day, and response payloads are under 100KB (no large file transfers via chat).

10. **Browser Compatibility**: Chat widget targets modern browsers (Chrome, Firefox, Safari, Edge) with ES6+ support; no IE11 support required.

## Implementation Architecture Notes

### LangChain 0.3+ Patterns

Based on clarification session 2025-10-28 and LangChain 0.3+ best practices research:

1. **SupervisorAgent Pattern**: Use LangGraph with tool-based handoffs (not deprecated AgentExecutor or legacy chains). Create handoff tools for each domain agent using `@tool` decorator with `InjectedState` and `Command` primitive for routing.

2. **Dynamic Tool Creation**: Use `StructuredTool.from_function()` with Pydantic's `create_model()` to build tool schemas dynamically from database JSON. Inject JWT/tenant context via `RunnableConfig` + `InjectedToolArg` (not visible to LLM).

3. **Tool Registry & Caching**: Implement ToolRegistry class with cache keyed by `{tool_id}_{tenant_id}`. Load tools on-demand, cache instances to avoid recreation overhead.

4. **Conversation Memory**: Use LangGraph `PostgresSaver` checkpointer (ConversationBufferMemory is deprecated). Thread IDs follow pattern: `tenant_{id}__user_{id}__session_{id}` for multi-tenant isolation. Use `trim_messages()` for conversations >10 messages.

5. **Priority-Based Tool Filtering**: Query `agent_tools` ordered by `priority ASC`, take top 5, pass to `llm.bind_tools()`. LLM chooses semantically from pre-filtered set. Priority controls visibility, not selection order.

6. **Output Formatting**: Use custom `OutputParser` for structured formats (JSON, tables) with format instructions in system prompt. Post-process for complex visualizations (charts).

## Dependencies

### External Systems
- **LLM Provider APIs**: OpenAI API, Google Gemini API, Anthropic Claude API, or OpenRouter
- **Business Backend APIs**: ERP system (debt data), logistics system (shipment tracking), OCR service
- **Authentication Provider**: External system issuing JWT tokens (RS256) for users

### Infrastructure
- **PostgreSQL 15+**: Primary database for configurations, sessions, messages
- **Redis 7.x**: Cache layer for agent configs, session state
- **ChromaDB**: Vector database for RAG embeddings
- **Docker & Docker Compose**: Containerization and orchestration
- **Alembic**: Database migration tool

### Software Libraries
- **FastAPI**: Async web framework for backend API
- **LangChain 0.3+**: Agent orchestration, tool calling, LLM abstraction
- **Pydantic**: Data validation and schema management
- **SQLAlchemy**: ORM for PostgreSQL
- **Cryptography (Fernet)**: API key encryption
- **PyJWT**: JWT token validation
- **Pytest**: Testing framework

### Development Tools
- **Git**: Version control
- **Python 3.11+**: Runtime environment
- **Poetry or pip**: Dependency management

## Constraints

### Technical Constraints
- Response time must be under 2.5 seconds for 95% of standard queries (excluding RAG)
- Redis cache TTL set to 1 hour for agent/tool configs (configurable)
- JWT tokens expire after 24 hours (configurable by auth provider)
- PostgreSQL connection pool minimum 20 connections to handle concurrent requests
- LLM context window limited by chosen model (e.g., 128k for GPT-4o, 32k for Gemini)
- Tool input/output JSON payloads limited to 100KB to prevent memory issues

### Security Constraints
- ALL API endpoints require valid JWT authentication (no public endpoints except health check)
- LLM API keys MUST be encrypted with Fernet before storing in database
- User JWT tokens MUST be passed to external API tools in Authorization header
- Redis and database credentials MUST be stored in environment variables, not code
- Logs MUST NOT contain PII, API keys, or JWT tokens (sanitize before logging)

### Operational Constraints
- System must support 100+ tenants on single deployment instance
- Agent configuration changes can take up to 1 hour to propagate (cache TTL) unless manual reload triggered
- Database migrations require downtime window or blue-green deployment strategy
- No code deployment required for adding new agents or tools (config-only changes)

### Business Constraints
- Initial MVP supports 4 domain agents (Debt, Shipment, OCR, Analysis); additional agents added post-launch
- English and Vietnamese language support only (prompts and UI text)
- System tracks LLM usage costs but does not enforce budget limits or automatic cutoff (manual monitoring required)
- Admin APIs require elevated permissions but RBAC details are assumed handled by external auth provider

## Non-Functional Requirements

### Performance
- **Response Time**: 95% of queries return results in under 2.5 seconds (excluding RAG which may take up to 4 seconds)
- **Throughput**: System handles 100 concurrent users per tenant without degradation
- **Scalability**: Horizontal scaling via multiple FastAPI worker processes behind load balancer

### Reliability
- **Uptime**: 99.9% availability target for chat endpoint
- **Fault Tolerance**: Graceful degradation when external APIs fail (return user-friendly error, log for admin)
- **Data Durability**: Redis persistence enabled (RDB snapshots every 5 minutes), PostgreSQL with daily backups

### Security
- **Authentication**: JWT RS256 signature validation on every request
- **Authorization**: Tenant-level permissions enforced at database and cache layer
- **Encryption**: API keys encrypted at rest (Fernet), TLS 1.3 for all network traffic
- **Audit Logging**: All agent/tool invocations logged with tenant_id, user_id, timestamp

### Maintainability
- **Code Coverage**: Minimum 80% test coverage for backend modules
- **Documentation**: Inline docstrings for all public functions, README with setup instructions
- **Configuration Management**: All runtime config in database or environment variables (no hard-coded values)
- **Observability**: Structured JSON logs, Prometheus-compatible metrics endpoint

### Usability
- **User Experience**: Natural language queries, no need to learn query syntax
- **Error Messages**: Clear, actionable error messages (e.g., "Customer MST not found" not "API returned 404")
- **Response Format**: Consistent JSON structure with renderer hints for UI display

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM API rate limit exceeded | Users see "service unavailable" errors | Medium | Implement tenant-level rate limiting, queue requests, cache common queries, notify admins when approaching limit |
| External business API changes schema | Tool calls fail, data not parsed correctly | Medium | Version tool configs, implement schema validation on responses, alert on parsing errors, maintain fallback schemas |
| SupervisorAgent misroutes queries | User gets wrong data or "cannot help" message | Low-Medium | Build labeled test dataset, monitor routing accuracy metric, allow manual agent selection override in UI, continuously improve routing prompt |
| Cross-tenant data leakage | Critical security incident, data breach | Low | Mandatory code review for all tenant isolation logic, automated tests for tenant boundary, security audit before launch, database row-level security policies |
| JWT token secret compromised | Unauthorized access to all tenant data | Low | Use RS256 (public/private key), rotate keys periodically, monitor for suspicious token usage, implement token revocation list |
| Database connection pool exhaustion | API becomes unresponsive, requests timeout | Medium | Monitor pool usage, auto-scale workers, implement request timeout and circuit breaker, increase pool size if needed |
| Cache stampede on popular queries | Database overload when cache expires | Low-Medium | Implement cache warming, stagger TTL expirations, use distributed locks for cache refresh, implement request coalescing |
| LLM cost explosion | High operational costs, budget overrun | Medium | Track costs per tenant, implement daily spending alerts, provide cost dashboard for admins, allow budget caps per tenant |
| Prompt injection attacks | Users manipulate LLM to leak data or behave incorrectly | Medium | Sanitize user input, include anti-injection instructions in system prompts, validate tool parameters, log suspicious activity, limit LLM permissions |

## Open Questions

*No critical open questions remaining - all necessary clarifications have been incorporated into requirements based on business documentation provided.*
