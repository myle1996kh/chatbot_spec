# Tasks: AgentHub Multi-Agent Chatbot Framework

**Feature Branch**: `001-agenthub-chatbot-framework`
**Generated**: 2025-10-28
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Tests**: Tests are OPTIONAL and not included in this task list unless explicitly requested.

## Format: `- [ ] [ID] [P?] [Story] Description`

- **Checkbox**: `- [ ]` for markdown task tracking
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3...)
- Include exact file paths in descriptions

## Path Convention

Based on plan.md project structure:
```
backend/
├── alembic/
├── src/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── api/
│   ├── middleware/
│   ├── tools/
│   └── utils/
└── tests/
```

---

## Phase 1: Setup (Shared Infrastructure) ✅ COMPLETE

**Purpose**: Project initialization and basic structure

- [x] T001 Create backend/ project structure with src/, tests/, alembic/ directories
- [x] T002 Initialize Python project with pyproject.toml and requirements.txt (Python 3.11+, FastAPI, LangChain 0.3+)
- [x] T003 [P] Create docker-compose.yml for PostgreSQL 15, Redis 7.x, ChromaDB services
- [x] T004 [P] Create .env.example with environment variables (DATABASE_URL, REDIS_URL, JWT_PUBLIC_KEY, FERNET_KEY)
- [x] T005 [P] Setup Alembic configuration in alembic.ini and alembic/env.py

---

## Phase 2: Foundational (Blocking Prerequisites) ✅ COMPLETE

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Schema & Migrations

- [x] T006 Create Alembic migration 001_initial_schema.py with all 13 tables from data-model.md
- [x] T007 Add seed data for base_tools table (HTTP_GET, HTTP_POST, RAG, DB_QUERY, OCR)
- [x] T008 [P] Add seed data for output_formats table (structured_json, markdown_table, chart_data, summary_text)
- [x] T009 [P] Add seed data for llm_models table (gpt-4o-mini, gpt-4o, gemini-1.5-pro, claude-3-5-sonnet)

### SQLAlchemy Models

- [x] T010 [P] Create Tenant model in backend/src/models/tenant.py with relationships
- [x] T011 [P] Create LLMModel model in backend/src/models/llm_model.py
- [x] T012 [P] Create TenantLLMConfig model in backend/src/models/tenant_llm_config.py
- [x] T013 [P] Create BaseTool model in backend/src/models/base_tool.py
- [x] T014 [P] Create OutputFormat model in backend/src/models/output_format.py
- [x] T015 [P] Create ToolConfig model in backend/src/models/tool.py with relationships
- [x] T016 [P] Create AgentConfig model in backend/src/models/agent.py with relationships
- [x] T017 [P] Create AgentTools junction model in backend/src/models/agent.py
- [x] T018 [P] Create TenantAgentPermission model in backend/src/models/permissions.py
- [x] T019 [P] Create TenantToolPermission model in backend/src/models/permissions.py
- [x] T020 [P] Create Session model in backend/src/models/session.py with relationships
- [x] T021 [P] Create Message model in backend/src/models/message.py

### Core Utilities & Configuration

- [x] T022 [P] Create config.py in backend/src/config.py with Pydantic Settings (DATABASE_URL, REDIS_URL, JWT_PUBLIC_KEY, FERNET_KEY)
- [x] T023 [P] Implement Fernet encryption utilities in backend/src/utils/encryption.py (encrypt_api_key, decrypt_api_key)
- [x] T024 [P] Implement JWT validation utilities in backend/src/utils/jwt.py (decode_jwt, validate_rs256)
- [x] T025 [P] Configure structlog JSON logging in backend/src/utils/logging.py
- [x] T026 Create database connection factory in backend/src/config.py (SQLAlchemy engine with pool_size=20)
- [x] T027 Create Redis connection factory in backend/src/config.py (async Redis client)

### FastAPI Application Setup

- [x] T028 Create FastAPI app initialization in backend/src/main.py with CORS, middleware, logging
- [x] T029 Implement JWT authentication middleware in backend/src/middleware/auth.py (Depends: get_current_tenant)
- [x] T030 [P] Implement structured logging middleware in backend/src/middleware/logging.py
- [x] T031 Create Pydantic schemas for chat requests/responses in backend/src/schemas/chat.py

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Business User Queries Customer Debt (Priority: P1) 🎯 MVP

**Goal**: Prove end-to-end flow with single domain agent - user sends debt query → SupervisorAgent routes → AgentDebt executes tool → returns formatted data

**Independent Test**: Send natural language debt query via POST /api/{tenant_id}/chat, verify structured response with customer debt data in <2.5 seconds

### Core Agent Framework

- [ ] T032 [US1] Implement LLMManager in backend/src/services/llm_manager.py (load tenant LLM config, decrypt API key, instantiate ChatOpenAI/ChatGoogleGenerativeAI/ChatAnthropic)
- [ ] T033 [US1] Implement CacheService in backend/src/services/cache_service.py (Redis caching with tenant namespace pattern agenthub:{tenant_id}:cache:{key}, 1h TTL)

### Tool Framework

- [ ] T034 [P] [US1] Create BaseTool interface in backend/src/tools/base.py with execute() method signature
- [ ] T035 [P] [US1] Implement HTTPGetTool in backend/src/tools/http.py with JWT injection via RunnableConfig
- [ ] T036 [P] [US1] Implement HTTPPostTool in backend/src/tools/http.py with JWT injection
- [ ] T037 [US1] Implement ToolRegistry in backend/src/services/tool_loader.py (create_tool_from_db_config using StructuredTool.from_function + Pydantic create_model)
- [ ] T038 [US1] Add priority-based tool filtering in ToolRegistry (query top 5 tools by priority ASC)

### Domain Agent - AgentDebt

- [ ] T039 [US1] Implement AgentDebt using create_react_agent pattern in backend/src/services/domain_agents.py
- [ ] T040 [US1] Load AgentDebt tools from database with priority filtering in domain_agents.py
- [ ] T041 [US1] Configure LangGraph PostgresSaver checkpointing in domain_agents.py (thread_id: tenant_{id}__user_{id}__session_{id})
- [ ] T042 [US1] Implement sliding window context management using trim_messages() for conversations >10 messages

### SupervisorAgent Routing

- [ ] T043 [US1] Create handoff tools for AgentDebt in backend/src/services/supervisor_agent.py (assign_to_debt_agent using @tool decorator with InjectedState and Command)
- [ ] T044 [US1] Implement SupervisorAgent using create_react_agent with tool-based handoffs in supervisor_agent.py
- [ ] T045 [US1] Add multi-intent detection logic in SupervisorAgent (reject with "Please ask one question at a time" for MVP)

### Output Formatting

- [ ] T046 [P] [US1] Implement OutputParser in backend/src/utils/formatters.py (parse structured_json, markdown_table, chart_data, text formats)
- [ ] T047 [US1] Add format_instructions generation in formatters.py for LLM system prompts

### Chat API Endpoint

- [ ] T048 [US1] Implement POST /api/{tenant_id}/chat endpoint in backend/src/api/chat.py
- [ ] T049 [US1] Add session creation logic in chat.py (create Session on first message, return session_id)
- [ ] T050 [US1] Add message persistence in chat.py (save user/assistant messages to messages table)
- [ ] T051 [US1] Integrate SupervisorAgent invocation with RunnableConfig context injection (jwt_token, tenant_id)
- [ ] T052 [US1] Add response time tracking (<2.5s requirement) and structured logging

### Session Endpoints (for US7 support)

- [ ] T053 [P] [US1] Implement GET /api/{tenant_id}/session endpoint in backend/src/api/sessions.py (list user sessions)
- [ ] T054 [P] [US1] Implement GET /api/{tenant_id}/session/{id} endpoint in sessions.py (get session details with messages)

**Checkpoint**: User Story 1 complete - test end-to-end debt query flow independently

---

## Phase 4: User Story 2 - Admin Configures New Agent (Priority: P1)

**Goal**: Validate config-driven architecture - create agent via API, assign tools, enable for tenant, user can immediately interact

**Independent Test**: Use admin API to create new agent (AgentInventory), assign tools, enable for tenant, then query via chat endpoint

### Pydantic Schemas for Admin API

- [ ] T055 [P] [US2] Create admin request/response schemas in backend/src/schemas/admin.py (CreateAgentRequest, UpdateAgentRequest, AgentConfig, CreateToolRequest, ToolConfig, TenantPermissions)

### Admin API - Agents

- [ ] T056 [P] [US2] Implement GET /api/admin/agents endpoint in backend/src/api/admin/agents.py (list all agents)
- [ ] T057 [P] [US2] Implement POST /api/admin/agents endpoint in agents.py (create agent with tools)
- [ ] T058 [P] [US2] Implement GET /api/admin/agents/{agent_id} endpoint in agents.py
- [ ] T059 [P] [US2] Implement PATCH /api/admin/agents/{agent_id} endpoint in agents.py (update prompt, tools, model)
- [ ] T060 [US2] Implement POST /api/admin/agents/reload endpoint in agents.py (invalidate Redis cache for tenant agents)

### Admin API - Tools

- [ ] T061 [P] [US2] Implement GET /api/admin/tools endpoint in backend/src/api/admin/tools.py (list all tools)
- [ ] T062 [P] [US2] Implement POST /api/admin/tools endpoint in tools.py (create tool from base_tool_id with config, input_schema)

### Admin API - Tenant Permissions

- [ ] T063 [P] [US2] Implement GET /api/admin/tenants/{tenant_id}/permissions endpoint in backend/src/api/admin/tenants.py
- [ ] T064 [US2] Implement PATCH /api/admin/tenants/{tenant_id}/permissions endpoint in tenants.py (enable/disable agents and tools for tenant)
- [ ] T065 [US2] Add cache invalidation in tenants.py when permissions change

### Admin Role Protection

- [ ] T066 [US2] Add admin role validation in backend/src/middleware/auth.py (require "admin" in JWT roles claim)
- [ ] T067 [US2] Apply admin middleware to all /api/admin/* routes in main.py

**Checkpoint**: User Story 2 complete - test creating agent, assigning tools, enabling for tenant, and user interaction

---

## Phase 5: User Story 3 - Multi-Tenant Isolation (Priority: P1)

**Goal**: Enforce security boundaries - TenantA cannot access TenantB data, configs, or sessions; each tenant uses own LLM keys

**Independent Test**: Create two tenants with different configs, send queries from both, verify: (1) sessions isolated, (2) different LLM models used, (3) cache keys namespaced, (4) user JWT passed to tools

### Tenant Isolation Enforcement

- [ ] T068 [US3] Add tenant_id validation in JWT middleware in backend/src/middleware/auth.py (verify JWT tenant_id matches path parameter)
- [ ] T069 [US3] Add tenant filtering to session queries in backend/src/api/sessions.py (WHERE tenant_id = current_tenant)
- [ ] T070 [US3] Add tenant filtering to agent permission checks in backend/src/services/supervisor_agent.py
- [ ] T071 [US3] Add tenant filtering to tool permission checks in backend/src/services/tool_loader.py

### LLM Per-Tenant Configuration

- [ ] T072 [US3] Implement tenant-specific LLM loading in backend/src/services/llm_manager.py (query tenant_llm_configs, decrypt API key, instantiate model)
- [ ] T073 [US3] Add LLM model selection in SupervisorAgent based on tenant config

### Redis Cache Namespacing

- [ ] T074 [US3] Enforce tenant namespace in CacheService.get() and .set() in backend/src/services/cache_service.py (all keys: agenthub:{tenant_id}:cache:{key})
- [ ] T075 [US3] Add cache namespace validation tests in CacheService

### JWT Context Injection to Tools

- [ ] T076 [US3] Verify JWT token injection in HTTPGetTool and HTTPPostTool in backend/src/tools/http.py (use RunnableConfig + InjectedToolArg)
- [ ] T077 [US3] Add Authorization header with user JWT to all HTTP tool requests

**Checkpoint**: User Story 3 complete - test multi-tenant isolation with two tenants

---

## Phase 6: User Story 4 - Multi-Intent Detection (Priority: P2)

**Goal**: SupervisorAgent detects multi-domain queries and rejects for MVP (sequential execution deferred to P2)

**Independent Test**: Send query "What's the debt for MST 123 and where is shipment ABC?" → verify rejection message

### Multi-Intent Detection

- [ ] T078 [US4] Enhance SupervisorAgent prompt in backend/src/services/supervisor_agent.py to detect multiple intents
- [ ] T079 [US4] Add rejection logic for multi-intent queries in supervisor_agent.py (return status: clarification_needed with detected_intents array)

**Checkpoint**: User Story 4 complete - test multi-intent rejection

---

## Phase 7: User Story 5 - Dynamic Tool Loading (Priority: P2)

**Goal**: Add new external API tool via database config, immediately available to assigned agents

**Independent Test**: Insert tool_configs record with new endpoint, assign to existing agent, verify tool invoked correctly

### Enhanced Tool Types

- [ ] T080 [P] [US5] Implement RAGTool in backend/src/tools/rag.py (ChromaDB retrieval, top-k similar docs)
- [ ] T081 [P] [US5] Implement DBQueryTool in backend/src/tools/db.py (safe SQL query execution)
- [ ] T082 [P] [US5] Implement OCRTool in backend/src/tools/ocr.py (document OCR processing)

### Dynamic Tool Validation

- [ ] T083 [US5] Add JSON schema validation in ToolRegistry.create_tool_from_db_config in backend/src/services/tool_loader.py
- [ ] T084 [US5] Add input parameter validation against tool input_schema before execution

### Tool Configuration UI Support

- [ ] T085 [US5] Implement PATCH /api/admin/tools/{tool_id} endpoint in backend/src/api/admin/tools.py (update tool config, input_schema, output_format)
- [ ] T086 [US5] Add cache invalidation for updated tools

**Checkpoint**: User Story 5 complete - test adding new tool via database and immediate availability

---

## Phase 8: User Story 6 - RAG Knowledge Base (Priority: P3)

**Goal**: AgentAnalysis searches ChromaDB for company documentation, returns synthesized answers with sources

**Independent Test**: Load sample docs into ChromaDB, query "What is return policy?", verify relevant chunks retrieved and answer generated

### ChromaDB Setup

- [ ] T087 [US6] Implement tenant-specific vectorstore creation in backend/src/services/rag_service.py (collection per tenant: tenant_{id}_knowledge)
- [ ] T088 [US6] Add document ingestion endpoint POST /api/admin/knowledge in backend/src/api/admin/knowledge.py (chunk, embed, store in ChromaDB)

### AgentAnalysis Implementation

- [ ] T089 [US6] Create AgentAnalysis using create_react_agent in backend/src/services/domain_agents.py
- [ ] T090 [US6] Integrate RAGTool with AgentAnalysis (query ChromaDB, retrieve top 3 chunks)
- [ ] T091 [US6] Add source citation to RAG responses in formatters.py

### SupervisorAgent Enhancement

- [ ] T092 [US6] Add handoff tool for AgentAnalysis in backend/src/services/supervisor_agent.py (assign_to_analysis_agent)
- [ ] T093 [US6] Update SupervisorAgent prompt to route knowledge queries to AgentAnalysis

**Checkpoint**: User Story 6 complete - test RAG-based knowledge retrieval

---

## Phase 9: User Story 7 - Session Management (Priority: P2)

**Goal**: Multi-turn conversations maintain context, users can list/retrieve session history

**Independent Test**: Send 3 messages in same session, verify agent references previous context; call GET /api/{tenant_id}/session and verify session list

### Session Context Enhancement

- [ ] T094 [US7] Verify PostgresSaver checkpointing persists conversation state in domain_agents.py
- [ ] T095 [US7] Add session metadata tracking in backend/src/api/chat.py (last_message_at, message_count)

### Session History Endpoints

- [ ] T096 [P] [US7] Add pagination support to GET /api/{tenant_id}/session in backend/src/api/sessions.py
- [ ] T097 [US7] Add session filtering by date range in sessions.py

**Checkpoint**: User Story 7 complete - test multi-turn conversations and session retrieval

---

## Phase 10: Additional Domain Agents (Post-MVP)

**Purpose**: Expand beyond AgentDebt to full multi-domain system

- [ ] T098 [P] Implement AgentShipment in backend/src/services/domain_agents.py (shipment tracking tools)
- [ ] T099 [P] Implement AgentOCR in backend/src/services/domain_agents.py (document OCR tools)
- [ ] T100 Add handoff tools for AgentShipment and AgentOCR in backend/src/services/supervisor_agent.py

---

## Phase 11: Monitoring & Observability

**Purpose**: Metrics tracking and admin monitoring dashboard

- [ ] T101 [P] Implement metrics tracking in backend/src/services/metrics_service.py (agent_calls_total, tool_calls_total, tool_avg_latency, llm_cost_total)
- [ ] T102 [P] Add token usage tracking in LLMManager in backend/src/services/llm_manager.py
- [ ] T103 Implement GET /api/admin/metrics endpoint in backend/src/api/admin/monitoring.py (aggregate usage statistics)

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple components

- [ ] T104 [P] Create README.md in backend/ with setup instructions, environment variables, Docker Compose usage
- [ ] T105 [P] Add health check endpoint GET /health in backend/src/main.py
- [ ] T106 [P] Implement error handling for LLM API rate limits in backend/src/services/llm_manager.py
- [ ] T107 [P] Implement error handling for external API timeouts in backend/src/tools/http.py
- [ ] T108 [P] Add request timeout and circuit breaker in backend/src/middleware/timeout.py
- [ ] T109 Code cleanup and type hint validation across all modules
- [ ] T110 Run quickstart.md validation scenarios (User Stories 1, 2, 3, 4, 7)
- [ ] T111 Performance optimization: cache warming strategy in backend/src/services/cache_service.py
- [ ] T112 Security hardening: input sanitization, prompt injection prevention

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - MVP delivery
- **User Story 2 (Phase 4)**: Depends on Foundational - can run parallel to US1
- **User Story 3 (Phase 5)**: Depends on Foundational + US1/US2 implementation - security validation
- **User Story 4 (Phase 6)**: Depends on US1 (SupervisorAgent) - P2 enhancement
- **User Story 5 (Phase 7)**: Depends on US2 (tool CRUD) - P2 enhancement
- **User Story 6 (Phase 8)**: Depends on Foundational - P3, independent agent
- **User Story 7 (Phase 9)**: Depends on US1 (session creation) - P2 enhancement
- **Additional Agents (Phase 10)**: Depends on US1 (agent framework) - post-MVP
- **Monitoring (Phase 11)**: Can start after Foundational - parallel to user stories
- **Polish (Phase 12)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundation only → **Independently testable** ✅
- **US2 (P1)**: Foundation only → **Independently testable** ✅
- **US3 (P1)**: Requires US1/US2 implemented for isolation testing → **Independently testable** ✅
- **US4 (P2)**: Requires US1 SupervisorAgent → Enhancement to existing flow
- **US5 (P2)**: Requires US2 tool CRUD → Enhancement to tool system
- **US6 (P3)**: Foundation only (new agent) → **Independently testable** ✅
- **US7 (P2)**: Requires US1 session creation → Enhancement to existing sessions

### Within Each User Story

**User Story 1 (MVP Critical Path)**:
1. T032-T033: Core services (LLM, Cache) → Foundation
2. T034-T038: Tool framework → Required for agent tools
3. T039-T042: AgentDebt → First domain agent
4. T043-T045: SupervisorAgent → Routing layer
5. T046-T047: Output formatting → Response standardization
6. T048-T052: Chat API → User-facing endpoint
7. T053-T054: Session API → Session retrieval

**User Story 2**:
- T055: Schemas → T056-T060: Agent CRUD → T061-T062: Tool CRUD → T063-T065: Permissions → T066-T067: Admin protection

**User Story 3**:
- T068-T071: Tenant filtering → T072-T073: LLM per tenant → T074-T075: Cache namespace → T076-T077: JWT injection

### Parallel Opportunities

**Phase 2 (Foundational) - High Parallelism**:
- All SQLAlchemy models (T010-T021): 12 tasks in parallel
- Utility modules (T022-T025): 4 tasks in parallel
- Seed data (T007-T009): 3 tasks in parallel

**Phase 3 (User Story 1) - Moderate Parallelism**:
- Tool implementations (T034-T036): 3 tasks in parallel
- Output formatting + Session endpoints (T046, T053, T054): 3 tasks in parallel

**Phase 4 (User Story 2) - High Parallelism**:
- All admin endpoints (T056-T064): 9 tasks in parallel (different route files)

**Phase 5 (User Story 3) - Moderate Parallelism**:
- Isolation enforcement (T068-T071): 4 tasks in parallel

**Phase 7 (User Story 5) - Parallel Tool Types**:
- Tool implementations (T080-T082): 3 tasks in parallel

**Phase 12 (Polish) - High Parallelism**:
- Documentation, health check, error handling (T104-T108): 5 tasks in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all SQLAlchemy models together:
Task: "Create Tenant model in backend/src/models/tenant.py"
Task: "Create LLMModel model in backend/src/models/llm_model.py"
Task: "Create TenantLLMConfig model in backend/src/models/tenant_llm_config.py"
Task: "Create BaseTool model in backend/src/models/base_tool.py"
Task: "Create OutputFormat model in backend/src/models/output_format.py"
Task: "Create ToolConfig model in backend/src/models/tool.py"
Task: "Create AgentConfig model in backend/src/models/agent.py"
Task: "Create AgentTools model in backend/src/models/agent.py"
Task: "Create TenantAgentPermission model in backend/src/models/permissions.py"
Task: "Create TenantToolPermission model in backend/src/models/permissions.py"
Task: "Create Session model in backend/src/models/session.py"
Task: "Create Message model in backend/src/models/message.py"
```

---

## Parallel Example: User Story 2 (Admin API)

```bash
# Launch all admin CRUD endpoints together (different files):
Task: "GET /api/admin/agents in backend/src/api/admin/agents.py"
Task: "POST /api/admin/agents in backend/src/api/admin/agents.py"
Task: "GET /api/admin/agents/{id} in backend/src/api/admin/agents.py"
Task: "PATCH /api/admin/agents/{id} in backend/src/api/admin/agents.py"
Task: "GET /api/admin/tools in backend/src/api/admin/tools.py"
Task: "POST /api/admin/tools in backend/src/api/admin/tools.py"
Task: "GET /api/admin/tenants/{id}/permissions in backend/src/api/admin/tenants.py"
Task: "PATCH /api/admin/tenants/{id}/permissions in backend/src/api/admin/tenants.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

**Goal**: Prove core architecture with single agent, full security isolation

1. **Phase 1**: Setup (T001-T005) → Project initialized
2. **Phase 2**: Foundational (T006-T031) → **CRITICAL** - blocks all stories
3. **Phase 3**: User Story 1 (T032-T054) → End-to-end debt query
4. **Phase 4**: User Story 2 (T055-T067) → Config-driven agent creation
5. **Phase 5**: User Story 3 (T068-T077) → Multi-tenant security
6. **STOP and VALIDATE**: Test MVP independently
7. Deploy MVP to staging/production

**MVP Delivers**:
- ✅ Working chatbot for debt queries (<2.5s response time)
- ✅ Admin API for agent/tool management (no code deployment)
- ✅ Multi-tenant isolation (JWT, cache namespace, data filtering)
- ✅ LangGraph SupervisorAgent routing
- ✅ Dynamic tool loading from database
- ✅ Structured JSON output formatting

**MVP Scope**: ~77 tasks (Phases 1-5)

### Incremental Delivery (Post-MVP)

**Iteration 1** (MVP): US1 + US2 + US3 → **Deploy**
**Iteration 2** (P2 Enhancements): US4 + US5 + US7 → **Deploy**
**Iteration 3** (P3 Advanced): US6 + Additional Agents → **Deploy**
**Iteration 4** (Production Ready): Monitoring + Polish → **Deploy**

Each iteration adds value without breaking previous stories.

### Parallel Team Strategy

With 3 developers after Foundational phase complete:

- **Developer A**: User Story 1 (T032-T054) - Core agent framework
- **Developer B**: User Story 2 (T055-T067) - Admin API
- **Developer C**: User Story 6 (T087-T093) - RAG (independent agent)

Then converge on User Story 3 (security validation) together.

---

## Task Summary

### Total Tasks: 112

**By Phase**:
- Phase 1 (Setup): 5 tasks
- Phase 2 (Foundational): 26 tasks (BLOCKING)
- Phase 3 (US1 - MVP Core): 23 tasks
- Phase 4 (US2 - Admin): 13 tasks
- Phase 5 (US3 - Security): 10 tasks
- Phase 6 (US4): 2 tasks
- Phase 7 (US5): 7 tasks
- Phase 8 (US6): 7 tasks
- Phase 9 (US7): 4 tasks
- Phase 10 (Additional Agents): 3 tasks
- Phase 11 (Monitoring): 3 tasks
- Phase 12 (Polish): 9 tasks

**By Priority**:
- P1 (MVP): 77 tasks (Phases 1-5)
- P2: 26 tasks (Phases 6-7, 9)
- P3: 9 tasks (Phase 8, 10-12)

**Parallelizable Tasks**: 48 tasks marked [P] (42.8%)

**MVP Delivery Time Estimate**:
- Foundational Phase: 2-3 weeks (critical path)
- User Stories 1-3 in parallel: 2-3 weeks
- **Total MVP**: 4-6 weeks with 2-3 developers

---

## Validation Checklist (Per User Story)

### User Story 1 ✅
- [ ] Send debt query → receive structured response <2.5s
- [ ] Invalid MST → clear error message
- [ ] Customer not found → appropriate error
- [ ] SupervisorAgent routes to AgentDebt correctly
- [ ] Tool executes with JWT Authorization header
- [ ] Session created and session_id returned

### User Story 2 ✅
- [ ] Create agent via POST /api/admin/agents
- [ ] Update agent prompt via PATCH
- [ ] Assign tools with priority
- [ ] Enable agent for tenant
- [ ] User can interact with new agent immediately
- [ ] Configuration time <5 minutes

### User Story 3 ✅
- [ ] TenantA cannot access TenantB sessions (403 Forbidden)
- [ ] Each tenant uses their configured LLM model
- [ ] Redis keys namespaced correctly (agenthub:{tenant_id}:...)
- [ ] User JWT passed to tools (not system token)
- [ ] Database queries filtered by tenant_id

### User Story 4 ✅
- [ ] Multi-intent query → rejection message
- [ ] Single-intent follow-up → correct routing

### User Story 5 ✅
- [ ] Insert new tool_configs record
- [ ] Assign to agent
- [ ] Tool invoked correctly with schema validation
- [ ] Cache reload works (<1h or manual)

### User Story 6 ✅
- [ ] Load documents into ChromaDB
- [ ] Query knowledge base
- [ ] Relevant chunks retrieved (top 3)
- [ ] Answer synthesized with sources

### User Story 7 ✅
- [ ] Multi-turn conversation maintains context
- [ ] GET /api/{tenant_id}/session returns session list
- [ ] GET /api/{tenant_id}/session/{id} returns full history
- [ ] Sliding window works for >10 messages

---

## Constitution Compliance

- ✅ **Configuration Over Code**: US2 validates - agents/tools created via database
- ✅ **Multi-Agent & Multi-Tenant**: US1/US3 validate - SupervisorAgent routing + isolation
- ✅ **LangChain-First**: Research decisions implemented - LangGraph handoffs, StructuredTool, PostgresSaver
- ✅ **Security & Token Isolation**: US3 validates - JWT RS256, Fernet encryption, InjectedToolArg
- ✅ **Unified Output & Observability**: OutputParser + structlog JSON logging
- ✅ **Performance**: FastAPI async, Redis cache (1h TTL), PostgreSQL pool (≥20)
- ✅ **Test Coverage**: Quickstart.md provides E2E validation scenarios (≥80% coverage target)

---

## Notes

- **[P] marker**: Tasks in different files with no dependencies - safe to parallelize
- **[Story] label**: Maps task to user story for traceability
- **File paths**: All paths are exact locations per plan.md structure
- **MVP focus**: Phases 1-5 deliver production-ready single-agent system
- **Incremental value**: Each phase adds functionality without breaking previous phases
- **Stop points**: Each user story checkpoint allows independent validation and demo
- **Test strategy**: Quickstart.md scenarios validate each story without writing test code (tests are OPTIONAL)

---

**Generated by**: `/speckit.tasks` workflow
**Last Updated**: 2025-10-28
**Ready for**: `/speckit.implement` or manual task execution
