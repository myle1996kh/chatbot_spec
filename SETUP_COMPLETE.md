# AgentHub Backend - Setup Complete

## What Was Accomplished

Successfully completed Phase 3 (User Story 1 - MVP) implementation of the AgentHub Multi-Agent Chatbot Framework backend.

### Phase 3 Implementation Summary

**Tasks Completed (12/12):**

1. **Core Services**
   - T032: LLMManager with OpenRouter support
   - T033: CacheService with tenant namespace isolation
   - T034-T036: Tool framework (BaseTool, HTTPGetTool, HTTPPostTool)
   - T037: ToolRegistry with dynamic tool loading

2. **Agent Framework**
   - T039-T042: Domain agent implementation (DomainAgent, AgentDebt)
   - T043-T045: SupervisorAgent for intent detection and routing
   - T046-T047: Output formatting utilities

3. **API Endpoints**
   - T048-T052: Chat API endpoint (POST /api/{tenant_id}/chat)
   - T053-T054: Sessions API endpoints (GET /api/{tenant_id}/session)

### Database Schema

Successfully created and seeded 13 database tables:

1. **tenants** - Multi-tenant organization data
2. **llm_models** - LLM providers (OpenRouter with 4 models)
3. **tenant_llm_configs** - Tenant-specific LLM configurations
4. **base_tools** - Tool templates (HTTP_GET, HTTP_POST, RAG, DB_QUERY, OCR)
5. **output_formats** - Response formats (structured_json, markdown_table, chart_data, summary_text)
6. **tool_configs** - Tool instances with configurations
7. **agent_configs** - Domain agent definitions
8. **agent_tools** - Many-to-many relationship (agents ↔ tools)
9. **tenant_agent_permissions** - Agent access control
10. **tenant_tool_permissions** - Tool access control
11. **sessions** - Conversation session tracking
12. **messages** - Chat message history
13. **checkpoints** - LangGraph state management

### Technology Stack

- **FastAPI**: Async web framework
- **LangChain 0.3+**: Agent orchestration
- **PostgreSQL 15**: Primary database
- **Redis 7**: Caching layer
- **SQLAlchemy 2.0**: ORM
- **Alembic**: Database migrations
- **Pydantic**: Data validation
- **Structlog**: Structured logging
- **OpenRouter**: Unified LLM API gateway

### OpenRouter Configuration

Configured with 4 LLM models:

1. **openai/gpt-4o-mini** (128k context, $0.00015/$0.0006 per 1k tokens)
2. **openai/gpt-4o** (128k context, $0.0025/$0.01 per 1k tokens)
3. **google/gemini-1.5-pro** (1M context, $0.00125/$0.00375 per 1k tokens)
4. **anthropic/claude-3.5-sonnet** (200k context, $0.003/$0.015 per 1k tokens)

API Key: `sk-or-v1-5020d221bad86d654b5f93bd0439f0380a3adda497b63844c40f7cebb7a1716`

---

## Current Status

### Running Services

- **PostgreSQL**: localhost:5432 (database: `chatbot_db`, user: `postgres`)
- **Redis**: localhost:6379
- **ChromaDB**: localhost:8001
- **FastAPI**: localhost:8000

### API Endpoints

Base URL: http://localhost:8000

#### Core Endpoints

- **GET /health** - Health check
- **GET /** - API information
- **GET /docs** - Swagger UI (OpenAPI documentation)
- **GET /redoc** - ReDoc documentation

#### Chat Endpoints

- **POST /api/{tenant_id}/chat** - Send message and get agent response
  - Validates tenant access
  - Creates or retrieves session
  - Routes to SupervisorAgent
  - Persists messages
  - Returns formatted response

#### Session Endpoints

- **GET /api/{tenant_id}/session** - List user sessions
  - Query params: `user_id` (required), `limit` (default 50), `offset` (default 0)
  - Returns session summaries with message counts

- **GET /api/{tenant_id}/session/{session_id}** - Get session details
  - Returns full message history in chronological order

---

## API Documentation

### Accessing Swagger UI

Open your browser and navigate to:

```
http://localhost:8000/docs
```

This provides:
- Interactive API documentation
- Request/response schemas
- Try-it-out functionality
- Authentication testing

### Accessing ReDoc

Alternative documentation format:

```
http://localhost:8000/redoc
```

---

## Testing the API

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0"
}
```

### 2. Send Chat Message (Example)

Note: This requires JWT authentication. For testing without authentication, you would need to:
1. Generate a test JWT token with tenant_id claim
2. Or temporarily disable authentication middleware

```bash
curl -X POST "http://localhost:8000/api/{tenant_id}/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is my account balance?",
    "user_id": "test_user_123",
    "metadata": {}
  }'
```

---

## How to Stop/Start Services

### Stop Backend Server

The server is running in the background. To stop it:

```bash
# Find the process
ps aux | grep "python.*main.py"

# Kill the process (replace PID with actual process ID)
kill <PID>
```

Or press `Ctrl+C` if running in foreground.

### Stop Docker Services

```bash
cd backend
docker-compose down
```

### Start Everything Again

```bash
cd backend

# Start Docker services
docker-compose up -d

# Wait for PostgreSQL to be ready
sleep 5

# Start API server (from backend directory with venv activated)
PYTHONPATH=. ./venv/Scripts/python.exe src/main.py
```

Or use the startup script:

```bash
cd backend
bash setup.sh
```

---

## Directory Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/
│   │   ├── 20251028_001_initial_schema.py
│   │   └── 20251028_002_seed_data.py
│   └── env.py
├── src/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Configuration
│   ├── models/                 # SQLAlchemy models (13 tables)
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic
│   │   ├── llm_manager.py
│   │   ├── cache_service.py
│   │   ├── tool_loader.py
│   │   ├── domain_agents.py
│   │   └── supervisor_agent.py
│   ├── api/                    # API endpoints
│   │   ├── chat.py
│   │   └── sessions.py
│   ├── tools/                  # Tool implementations
│   │   ├── base.py
│   │   └── http.py
│   ├── middleware/             # FastAPI middleware
│   │   ├── auth.py
│   │   └── logging.py
│   └── utils/                  # Utilities
│       ├── encryption.py
│       ├── jwt.py
│       ├── logging.py
│       └── formatters.py
├── venv/                       # Virtual environment
├── .env                        # Environment configuration
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Service orchestration
└── README.md                   # Documentation
```

---

## Key Implementation Details

### 1. Multi-Tenancy

All operations are tenant-isolated:
- Database queries filtered by `tenant_id`
- Cache keys namespaced: `agenthub:{tenant_id}:cache:{key}`
- JWT tokens must contain `tenant_id` claim

### 2. Agent Routing

**SupervisorAgent** detects user intent and routes to appropriate domain agent:
- **AgentDebt**: Handles debt/payment/balance queries
- Returns `MULTI_INTENT` for complex multi-topic queries
- Returns `UNCLEAR` for ambiguous queries

### 3. Dynamic Tool Loading

Tools are loaded dynamically from database configuration:
- Pydantic schemas generated at runtime from JSON
- JWT tokens injected into tool execution context
- Priority-based tool filtering (top 5 tools per agent)

### 4. Output Formatting

Standardized response format:

```json
{
  "status": "success",
  "agent": "AgentDebt",
  "intent": "balance_inquiry",
  "data": { ... },
  "format": "structured_json",
  "renderer_hint": { "type": "json" },
  "metadata": { "duration_ms": 1234 }
}
```

### 5. Performance Tracking

All responses include:
- `duration_ms`: Total response time
- Warning logged if response time > 2.5s
- Structured logging for monitoring

---

## Environment Configuration

Current `.env` settings:

```bash
# Database
DATABASE_URL=postgresql://postgres:123456@localhost:5432/chatbot_db

# Redis
REDIS_URL=redis://localhost:6379

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-5020d221bad86d654b5f93bd0439f0380a3adda497b63844c40f7cebb7a1716
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# JWT (placeholder for development)
JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----...-----END PUBLIC KEY-----

# Fernet Encryption
FERNET_KEY=kN8j3xP5mR7qT9wV2yB4nL6oC1eH3fA8gD0iK5sU9jM=

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## Next Steps

### Immediate Next Steps (Phase 4 - Admin API)

1. **Admin Agent Management**
   - POST /api/admin/{tenant_id}/agent - Create agent
   - GET /api/admin/{tenant_id}/agent - List agents
   - PUT /api/admin/{tenant_id}/agent/{id} - Update agent
   - DELETE /api/admin/{tenant_id}/agent/{id} - Delete agent

2. **Admin Tool Management**
   - CRUD operations for tools
   - Tool configuration management
   - Agent-tool associations

3. **Admin Tenant Management**
   - Tenant creation and configuration
   - LLM configuration per tenant
   - Permission management

### Future Phases

- **Phase 5**: Multi-tenant security hardening
- **Phase 6**: Multi-intent detection improvements
- **Phase 7**: Advanced RAG capabilities
- **Phase 8**: Session management enhancements
- **Phase 9**: Additional domain agents
- **Phase 10**: Monitoring and observability
- **Phase 11**: Testing and documentation

---

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -U postgres -d chatbot_db

# View logs
docker logs agenthub-postgres
```

### Redis Connection Issues

```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli ping

# View logs
docker logs agenthub-redis
```

### API Not Responding

```bash
# Check if server is running
ps aux | grep "python.*main.py"

# Check server logs
tail -f backend/logs/app.log  # if logging to file

# Restart server
cd backend
PYTHONPATH=. ./venv/Scripts/python.exe src/main.py
```

### Import Errors

Always run Python commands with PYTHONPATH set:

```bash
cd backend
PYTHONPATH=. ./venv/Scripts/python.exe <script>
```

---

## Resources

- **Backend README**: [backend/README.md](backend/README.md)
- **API Documentation**: http://localhost:8000/docs
- **Project Spec**: specs/001-agenthub-chatbot-framework/
- **Tasks Tracking**: specs/001-agenthub-chatbot-framework/tasks.md

---

## Summary

✅ **Phase 1 (Setup)**: 5/5 tasks completed
✅ **Phase 2 (Foundational)**: 26/26 tasks completed
✅ **Phase 3 (User Story 1)**: 12/12 tasks completed

**Total Progress**: 43/112 tasks (38.4% of full implementation)

**Services Running**:
- PostgreSQL: ✅ Running on localhost:5432
- Redis: ✅ Running on localhost:6379
- ChromaDB: ✅ Running on localhost:8001
- FastAPI: ✅ Running on http://localhost:8000

**API Endpoints**:
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Chat endpoint: POST /api/{tenant_id}/chat
- Sessions endpoints: GET /api/{tenant_id}/session

The AgentHub backend is now fully operational and ready for testing!
