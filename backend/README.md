# AgentHub Multi-Agent Chatbot Framework - Backend

Production-ready multi-tenant chatbot framework using LangChain 0.3+ for agent orchestration.

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7.x
- ChromaDB (optional, for RAG features)

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and configure:
# - DATABASE_URL (your PostgreSQL connection)
# - REDIS_URL
# - JWT_PUBLIC_KEY (RS256 public key)
# - FERNET_KEY (generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
```

### 3. Start Services with Docker Compose

```bash
# Start PostgreSQL, Redis, and ChromaDB
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 4. Run Database Migrations

```bash
# Initialize database schema
alembic upgrade head

# Verify tables created
psql -d chatbot_db -c "\dt"
```

### 5. Start API Server

```bash
# Development mode (with auto-reload)
python src/main.py

# Or use uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## Project Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/
│   │   ├── 20251028_001_initial_schema.py
│   │   └── 20251028_002_seed_data.py
│   └── env.py
├── src/
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Application configuration
│   │
│   ├── models/                 # SQLAlchemy ORM models (13 tables)
│   │   ├── tenant.py
│   │   ├── llm_model.py
│   │   ├── tenant_llm_config.py
│   │   ├── base_tool.py
│   │   ├── output_format.py
│   │   ├── tool.py
│   │   ├── agent.py
│   │   ├── permissions.py
│   │   ├── session.py
│   │   └── message.py
│   │
│   ├── schemas/                # Pydantic request/response schemas
│   │   └── chat.py
│   │
│   ├── services/               # Business logic (Phase 3+)
│   │
│   ├── api/                    # FastAPI route handlers (Phase 3+)
│   │   └── admin/
│   │
│   ├── middleware/             # FastAPI middleware
│   │   ├── auth.py             # JWT authentication
│   │   └── logging.py          # Structured logging
│   │
│   ├── tools/                  # Tool implementations (Phase 3+)
│   │
│   └── utils/                  # Utilities
│       ├── encryption.py       # Fernet encryption
│       ├── jwt.py              # JWT validation
│       └── logging.py          # Structlog configuration
│
├── tests/                      # Test suite (Phase 3+)
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── contract/
│
├── docker-compose.yml          # Service orchestration
├── Dockerfile                  # FastAPI container (TODO)
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Project configuration
├── alembic.ini                 # Alembic configuration
└── README.md                   # This file
```

## Database Schema

The database consists of 13 tables:

1. **tenants** - Organizations using the system
2. **llm_models** - Available LLM providers/models
3. **tenant_llm_configs** - Tenant-specific LLM configurations
4. **base_tools** - Tool type templates
5. **output_formats** - Response format definitions
6. **tool_configs** - Specific tool instances
7. **agent_configs** - Domain agent configurations
8. **agent_tools** - Many-to-many junction (agents ↔ tools)
9. **tenant_agent_permissions** - Agent access per tenant
10. **tenant_tool_permissions** - Tool access per tenant
11. **sessions** - Conversation sessions
12. **messages** - Chat messages
13. **checkpoints** - LangGraph checkpointer data

## Development

### Run Tests

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=term --cov-fail-under=80

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Code Quality

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Current Implementation Status

### ✅ Phase 1: Setup (Complete)
- [x] Project structure
- [x] Dependencies configured
- [x] Docker Compose setup
- [x] Environment configuration
- [x] Alembic setup

### ✅ Phase 2: Foundational (Complete)
- [x] All 13 SQLAlchemy models
- [x] Database schema migration
- [x] Seed data (base_tools, output_formats, llm_models)
- [x] Configuration management (Pydantic Settings)
- [x] Fernet encryption utilities
- [x] JWT validation utilities
- [x] Structured logging (structlog)
- [x] FastAPI application skeleton
- [x] JWT authentication middleware
- [x] Logging middleware
- [x] Pydantic schemas for chat

### ⏳ Phase 3+: User Stories (Pending)
- [ ] User Story 1: Core agent framework (MVP)
- [ ] User Story 2: Admin API
- [ ] User Story 3: Multi-tenant security
- [ ] Additional phases...

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | `postgresql://postgres:123456@localhost:5432/chatbot_db` |
| `REDIS_URL` | Redis connection string | Yes | `redis://localhost:6379` |
| `JWT_PUBLIC_KEY` | RS256 public key for JWT validation | Yes | - |
| `FERNET_KEY` | Encryption key for API keys | Yes | - |
| `ENVIRONMENT` | Application environment | No | `development` |
| `LOG_LEVEL` | Logging level | No | `INFO` |
| `API_HOST` | API server host | No | `0.0.0.0` |
| `API_PORT` | API server port | No | `8000` |

### Generating Keys

```bash
# Generate Fernet encryption key
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'

# JWT RS256 keys (if you need to generate test keys)
# Use openssl or your authentication provider's key management
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
psql -h localhost -U postgres -d chatbot_db

# View logs
docker-compose logs postgres
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli ping

# View logs
docker-compose logs redis
```

### Migration Issues

```bash
# Reset database (WARNING: destroys all data)
alembic downgrade base
alembic upgrade head

# Check current migration version
alembic current

# View pending migrations
alembic show
```

## Next Steps

To continue implementation:

1. Review the [tasks.md](../specs/001-agenthub-chatbot-framework/tasks.md) file
2. Begin Phase 3: User Story 1 implementation
3. Follow the task-by-task execution plan

## Support

For issues or questions:
- Check the [quickstart.md](../specs/001-agenthub-chatbot-framework/quickstart.md) for test scenarios
- Review the [plan.md](../specs/001-agenthub-chatbot-framework/plan.md) for architecture details
- Consult the [research.md](../specs/001-agenthub-chatbot-framework/research.md) for technical decisions

## License

MIT
