# Implementation Plan: AgentHub Multi-Agent Chatbot Framework

**Branch**: `001-agenthub-chatbot-framework` | **Date**: 2025-10-28 | **Spec**: [spec.md](spec.md)

## Summary

Build a production-ready multi-tenant chatbot framework using LangChain 0.3+ for agent orchestration, enabling natural language queries against internal business systems (ERP, CRM, logistics). System features config-driven architecture where agents, tools, and prompts are loaded from database at runtime - no code deployment required for new agents or integrations.

**Core Innovation**: SupervisorAgent uses LangGraph tool-handoffs to route user intents to specialized domain agents (Debt, Shipment, OCR, Analysis), with all tools dynamically created from database configurations using Pydantic schemas and JWT context injection.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- FastAPI 0.100+ (async web framework)
- LangChain 0.3+ (agent orchestration)
- LangGraph (multi-agent routing with tool handoffs)
- SQLAlchemy 2.0+ (ORM)
- Alembic (database migrations)

**Storage**:
- PostgreSQL 15+ (configurations, sessions, messages)
- Redis 7.x (cache, 1h TTL)
- ChromaDB (RAG vector embeddings)

**Testing**:
- pytest (async support)
- pytest-cov (≥80% coverage requirement per constitution)
- httpx (FastAPI test client)

**Target Platform**: Linux server (Docker Compose deployment)

**Project Type**: Web application (backend API + optional widget frontend)

**Performance Goals**:
- Response time < 2.5s for 95% of standard queries
- Support 100+ concurrent tenants
- Handle 100 concurrent users per tenant
- Cache hit rate >90% for agent/tool configs
- 99.9% uptime target

**Constraints**:
- All configuration via database (no hard-coded agents/tools)
- JWT RS256 authentication required (24h TTL)
- Redis cache TTL exactly 1 hour (per constitution)
- PostgreSQL connection pool minimum 20
- LLM API keys encrypted with Fernet before storage
- Structured JSON logging only (no plain text logs)
- Test coverage ≥80% (per constitution)

**Scale/Scope**:
- Initial: 100 tenants, 10k conversations/day
- Growth: 500 tenants, 100k conversations/day
- 90-day conversation history retention
- 4 domain agents (Debt, Shipment, OCR, Analysis)
- 50-200 tool configurations

---

## Constitution Check

*GATE: Must pass before implementation. Re-checked after Phase 1 design.*

### I. Configuration Over Code ✅
- **Compliance**: All agents, tools, prompts loaded from PostgreSQL at runtime
- **Evidence**: `agent_configs`, `tool_configs`, `AgentTools` junction tables (data-model.md)
- **Validation**: User Story 2 tests creating agent without code deployment

### II. Multi-Agent & Multi-Tenant Architecture ✅
- **Compliance**:
  - LangGraph SupervisorAgent routes to domain agents
  - Redis cache keys namespaced: `agenthub:{tenant_id}:cache:{key}`
  - PostgreSQL queries filtered by `tenant_id`
  - Session thread IDs: `tenant_{id}__user_{id}__session_{id}`
- **Evidence**: research.md (LangGraph handoffs), data-model.md (tenant isolation)
- **Validation**: User Story 3 tests cross-tenant access prevention

### III. LangChain-First Orchestration ✅
- **Compliance**:
  - SupervisorAgent uses Lang Graph tool-based handoffs (NOT AgentExecutor)
  - Domain agents use `create_react_agent` pattern
  - Tools use `StructuredTool.from_function()`
  - No direct HTTP/API calls in business logic
- **Evidence**: research.md decisions 1, 2
- **Validation**: All tool execution goes through LangChain abstractions

### IV. Security & Token Isolation ✅
- **Compliance**:
  - JWT RS256 validation on all endpoints (FastAPI dependency injection)
  - User JWT passed to tools via `RunnableConfig` + `InjectedToolArg`
  - LLM API keys encrypted with Fernet before PostgreSQL storage
  - Keys decrypted only at runtime in memory
- **Evidence**: research.md decisions 6, 11; data-model.md (`encrypted_api_key` column)
- **Validation**: User Story 3 tests JWT in tool Authorization headers

### V. Unified Output Format & Observability ✅
- **Compliance**:
  - All responses use `output_formats` table definitions
  - Custom `OutputParser` applies format with renderer hints
  - Structured JSON logging via `structlog`
  - Metrics tracked: `agent_calls_total`, `tool_calls_total`, `tool_avg_latency`, `llm_cost_total`
- **Evidence**: research.md decisions 5, 12; data-model.md (`output_formats` table)
- **Validation**: All chat responses include `format` and `renderer_hint` fields

### Performance & Scalability ✅
- **Compliance**:
  - FastAPI async for high concurrency
  - Redis cache 1h TTL for agent configs (constitution requirement)
  - PostgreSQL connection pool ≥20 (constitution requirement)
  - Response time target <2.5s (constitution requirement)
- **Evidence**: research.md decision 7 (FastAPI async), constitution constraints

### Test Coverage ✅
- **Compliance**: pytest with ≥80% coverage (constitution requirement)
- **Evidence**: research.md decision 13
- **Validation**: CI/CD runs `pytest --cov=src --cov-report=term --cov-fail-under=80`

### Deployment ✅
- **Compliance**:
  - Alembic migrations with rollback scripts (constitution requirement)
  - Environment variables for secrets (no hard-coded configs)
  - Docker Compose for service orchestration
- **Evidence**: research.md decision 8 (Alembic)

**Gate Status**: ✅ PASSED - All 5 core principles satisfied

---

## Project Structure

### Documentation (this feature)

```
specs/001-agenthub-chatbot-framework/
├── plan.md              # This file
├── spec.md              # Feature specification with user stories
├── research.md          # Technology decisions & LangChain patterns
├── data-model.md        # PostgreSQL schema (13 tables)
├── quickstart.md        # End-to-end test scenarios
├── contracts/
│   ├── chat-api.yaml    # Chat & session endpoints (User Stories 1, 7)
│   └── admin-api.yaml   # Admin management endpoints (User Stories 2, 3, 5)
└── tasks.md             # [Generated by /speckit.tasks - NOT created yet]
```

### Source Code (repository root)

```
backend/
├── alembic/                       # Database migrations
│   ├── versions/
│   │   └── 001_initial_schema.py
│   └── env.py
│
├── src/
│   ├── main.py                    # FastAPI app initialization
│   ├── config.py                  # Environment variables, settings
│   │
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── tenant.py
│   │   ├── agent.py
│   │   ├── tool.py
│   │   ├── session.py
│   │   └── llm_model.py
│   │
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── chat.py
│   │   ├── admin.py
│   │   └── session.py
│   │
│   ├── services/                  # Business logic
│   │   ├── supervisor_agent.py   # LangGraph SupervisorAgent routing
│   │   ├── domain_agents.py      # AgentDebt, AgentShipment, etc.
│   │   ├── tool_loader.py        # ToolRegistry (dynamic tool creation)
│   │   ├── llm_manager.py        # LLM client instantiation (decrypt keys)
│   │   └── cache_service.py      # Redis caching layer
│   │
│   ├── api/                       # FastAPI route handlers
│   │   ├── chat.py                # POST /api/{tenant}/chat
│   │   ├── sessions.py            # GET /api/{tenant}/session
│   │   └── admin/
│   │       ├── agents.py          # Agent CRUD
│   │       ├── tools.py           # Tool CRUD
│   │       └── tenants.py         # Tenant permissions
│   │
│   ├── middleware/                # FastAPI middleware
│   │   ├── auth.py                # JWT validation dependency
│   │   └── logging.py             # Structured logging
│   │
│   ├── tools/                     # Tool implementations
│   │   ├── base.py                # BaseTool interface
│   │   ├── http.py                # HTTPGetTool, HTTPPostTool
│   │   ├── rag.py                 # RAGTool (ChromaDB)
│   │   ├── db.py                  # DBQueryTool
│   │   └── ocr.py                 # OCRTool
│   │
│   └── utils/                     # Utilities
│       ├── encryption.py          # Fernet key encryption/decryption
│       ├── jwt.py                 # JWT decode/validate
│       └── formatters.py          # OutputParser implementations
│
├── tests/
│   ├── unit/                      # Unit tests (models, services)
│   │   ├── test_tool_loader.py
│   │   ├── test_llm_manager.py
│   │   └── test_encryption.py
│   │
│   ├── integration/               # Integration tests (agent invocation)
│   │   ├── test_supervisor_routing.py
│   │   ├── test_agent_debt.py
│   │   └── test_tool_execution.py
│   │
│   └── e2e/                       # End-to-end API tests
│       ├── test_us1_debt_query.py
│       ├── test_us2_admin_config.py
│       ├── test_us3_multi_tenant.py
│       └── test_us7_sessions.py
│
├── docker-compose.yml             # PostgreSQL, Redis, ChromaDB, FastAPI
├── Dockerfile                     # FastAPI container
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project metadata (Poetry optional)
├── alembic.ini                    # Alembic configuration
└── README.md                      # Setup & deployment instructions
```

**Structure Decision**: Selected **web application** structure because system has:
- Backend API (FastAPI) serving chat and admin endpoints
- Optional frontend widget (not in MVP scope, can be added later)
- Clear separation between API layer, business logic (services), and data layer (models)

---

## Complexity Tracking

No constitution violations. All complexity justified by requirements:

| Component | Complexity | Justification |
|-----------|------------|---------------|
| Multi-Agent Architecture | High | Required for domain-specific agents per spec (Debt, Shipment, OCR, Analysis) |
| Dynamic Tool Loading | Medium | Constitution principle "Configuration Over Code" - tools must be database-driven |
| Multi-Tenant Isolation | Medium | Enterprise SaaS requirement - tenant data isolation non-negotiable |
| LangGraph Routing | Medium | Official LangChain 0.3+ pattern for supervisor agents (replaces deprecated AgentExecutor) |

---

## Design Artifacts

### Phase 0: Research & Technology Decisions ✅

**Document**: [research.md](research.md)

**Key Decisions**:
1. **SupervisorAgent**: LangGraph tool-based handoffs (official pattern)
2. **Dynamic Tools**: `StructuredTool` + Pydantic `create_model()` from JSON schemas
3. **Tool Priority**: Pre-filter top 5 by priority ASC, LLM selects semantically
4. **Memory**: PostgresSaver checkpointer + `trim_messages()` (sliding window)
5. **Output Formatting**: Custom `OutputParser` + post-processing hybrid
6. **JWT Injection**: `RunnableConfig` + `InjectedToolArg` (secure, invisible to LLM)
7. **Web Framework**: FastAPI async (100+ concurrent users requirement)
8. **Database**: PostgreSQL + SQLAlchemy + Alembic migrations
9. **Cache**: Redis 7.x (1h TTL, tenant namespace)
10. **Vector DB**: ChromaDB (RAG for User Story 6 - P3)
11. **Encryption**: Fernet (LLM API keys)
12. **Logging**: structlog (JSON structured logs)
13. **Testing**: pytest (≥80% coverage)

**Status**: Complete - all NEEDS CLARIFICATION resolved

---

### Phase 1: Data Model ✅

**Document**: [data-model.md](data-model.md)

**Core Tables** (13 total):
1. `tenants` - Organizations using system
2. `llm_models` - Available LLM providers/models
3. `tenant_llm_configs` - Tenant-specific LLM + encrypted API keys
4. `base_tools` - Tool type templates (HTTP_GET, RAG, etc.)
5. `output_formats` - Response format definitions
6. `tool_configs` - Specific tool instances
7. `agent_configs` - Domain agent configurations
8. `agent_tools` - Many-to-many (agents ↔ tools with priority)
9. `tenant_agent_permissions` - Agent access per tenant
10. `tenant_tool_permissions` - Tool access per tenant
11. `sessions` - Conversation sessions
12. `messages` - Chat messages
13. `checkpoints` - LangGraph PostgresSaver checkpoints

**Key Relationships**:
- Tenant → 1:1 → TenantLLMConfig → N:1 → LLMModel
- AgentConfig → 1:N → AgentTools (priority) → N:1 → ToolConfig
- Tenant → N:M → AgentConfig (via TenantAgentPermission)
- Session → 1:N → Message

**Indexes**: 14 performance-critical indexes for multi-tenant queries

**Status**: Complete - ready for Alembic migration generation

---

### Phase 1: API Contracts ✅

**Documents**:
- [contracts/chat-api.yaml](contracts/chat-api.yaml) (Chat & Session endpoints)
- [contracts/admin-api.yaml](contracts/admin-api.yaml) (Admin endpoints)

**Chat API** (User Stories 1, 7):
- `POST /api/{tenant_id}/chat` - Send message to SupervisorAgent
- `GET /api/{tenant_id}/session` - List user sessions
- `GET /api/{tenant_id}/session/{id}` - Get session details

**Admin API** (User Stories 2, 3, 5):
- Agents: `POST /api/admin/agents`, `PATCH /api/admin/agents/{id}`, `POST /api/admin/agents/reload`
- Tools: `POST /api/admin/tools`, `PATCH /api/admin/tools/{id}`
- Permissions: `PATCH /api/admin/tenants/{id}/permissions`
- Monitoring: `GET /api/admin/metrics`

**Status**: Complete - OpenAPI 3.1.0 specs ready for code generation

---

### Phase 1: Test Scenarios ✅

**Document**: [quickstart.md](quickstart.md)

**Coverage**:
- User Story 1: Debt query (valid MST, invalid format, not found)
- User Story 2: Admin creates agent, updates prompt, assigns tools, enables for tenant
- User Story 3: Multi-tenant isolation (sessions, LLM models, cache namespaces, JWT in tools)
- User Story 4: Multi-intent rejection (MVP behavior)
- User Story 7: Session management (multi-turn, list sessions, get details)
- Performance: Response time, cache hit rate, concurrent load

**Status**: Complete - ready for automated test execution

---

## Implementation Strategy

### MVP Scope (User Story 1 - P1)

**Goal**: Prove end-to-end flow with single domain agent

**Delivers**:
- SupervisorAgent routing (single-intent only)
- AgentDebt with one tool (`get_customer_debt_by_mst`)
- JWT authentication
- PostgreSQL + Redis + FastAPI
- Basic structured JSON output

**Excludes** (defer to post-MVP):
- Multi-intent handling (User Story 4 - P2)
- Dynamic tool creation UI (User Story 5 - P2)
- RAG integration (User Story 6 - P3)
- Session history UI (User Story 7 - P2)

**Validation**: User can ask "Debt for MST 0123456789" and receive structured response <2.5s

---

### Incremental Delivery Plan

**Phase 1: Foundation** (User Stories 1-3 - P1)
1. Database schema + Alembic migrations
2. FastAPI project setup + JWT middleware
3. SupervisorAgent + AgentDebt (single tool)
4. Admin API for agent/tool management
5. Multi-tenant isolation testing

**Deliverable**: Working chatbot for debt queries, config-driven, multi-tenant secure

---

**Phase 2: Expansion** (User Stories 4-5 - P2)
1. Multi-intent detection (rejection for MVP, enhancement later)
2. Additional domain agents (AgentShipment, AgentOCR)
3. Dynamic tool loader UI improvements
4. Session management endpoints
5. Advanced output formatting (tables, charts)

**Deliverable**: Multiple domain agents, full admin interface, session history

---

**Phase 3: Advanced Features** (User Stories 6-7 - P3)
1. RAG integration with ChromaDB
2. AgentAnalysis with knowledge base search
3. Complex output rendering (charts, visualizations)
4. Performance optimization (caching strategies)
5. Monitoring dashboards

**Deliverable**: Full-featured multi-agent system with RAG capabilities

---

## Dependencies & Integration Points

### External Dependencies
1. **LLM Providers**: OpenAI API, Google Gemini API, Anthropic Claude API, or OpenRouter
2. **Business APIs**: ERP system (debt data), logistics system (shipment tracking), OCR service
3. **Auth Provider**: External JWT issuer (RS256 public key required)

### Infrastructure Dependencies
1. **PostgreSQL 15+**: Must be running before FastAPI starts
2. **Redis 7.x**: Cache layer, must be accessible
3. **ChromaDB**: For RAG (User Story 6), can be added later

### Library Dependencies (requirements.txt)
```
fastapi>=0.100.0
uvicorn[standard]>=0.22.0
langchain>=0.3.0
langgraph>=0.2.0
langchain-openai>=0.2.0
langchain-google-genai>=2.0.0
langchain-anthropic>=0.2.0
langchain-community>=0.3.0
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.0
redis>=5.0.0
cryptography>=41.0.0
pyjwt>=2.8.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
structlog>=23.1.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.24.0
```

---

## Risks & Mitigations

| Risk | Mitigation | Owner |
|------|------------|-------|
| LangChain 0.3 API changes | Pin exact versions, monitor changelog, test upgrades in sandbox | Backend Team |
| LLM API rate limits | Tenant-level rate limiting, request queuing, usage monitoring | DevOps |
| Tool schema validation failures | JSON schema validation before tool creation, rollback mechanism | Backend Team |
| Cache stampede on expiry | Stagger TTLs, distributed locks, cache warming on reload | Backend Team |
| Multi-tenant data leakage | Mandatory code review, automated tenant boundary tests, security audit | Security Team |
| PostgreSQL connection exhaustion | Monitor pool usage, auto-scale workers, implement circuit breaker | DevOps |

---

## Next Steps

1. **Run `/speckit.tasks`** to generate implementation task breakdown
2. Review tasks.md for task-by-task execution plan
3. Set up development environment (PostgreSQL, Redis, Python 3.11)
4. Run Alembic migrations to create database schema
5. Begin Phase 1 implementation (MVP - User Story 1)

---

**Plan Status**: ✅ Complete
**Phase 0 (Research)**: ✅ Complete
**Phase 1 (Design)**: ✅ Complete
**Phase 2 (Tasks)**: ⏳ Pending - run `/speckit.tasks`
**Constitution Check**: ✅ PASSED

---

**Last Updated**: 2025-10-28
**Approved By**: Architecture Team (Constitution Compliance Verified)
