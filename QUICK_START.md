# AgentHub Backend - Quick Start Guide

## Current Status

✅ **All services are running!**

- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **ChromaDB**: localhost:8001
- **FastAPI Backend**: http://localhost:8000

## Access Points

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "environment": "development", "version": "0.1.0"}
```

## Available API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /` - API information

### Chat API
- `POST /api/{tenant_id}/chat` - Send message and get agent response

### Sessions API
- `GET /api/{tenant_id}/session` - List user sessions
- `GET /api/{tenant_id}/session/{session_id}` - Get session details with messages

## Database Connection

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres -d chatbot_db
# Password: 123456

# View tables
\dt

# View seed data
SELECT * FROM llm_models;
SELECT * FROM base_tools;
SELECT * FROM output_formats;
```

## Redis Connection

```bash
# Test Redis
redis-cli
> PING
PONG

# View keys
> KEYS agenthub:*
```

## Stop Services

### Stop Backend Server
```bash
# Find process ID
ps aux | grep "python.*main.py"

# Kill process (replace PID)
kill <PID>
```

### Stop Docker Services
```bash
cd backend
docker-compose down
```

## Restart Everything

```bash
cd backend

# Start Docker services
docker-compose up -d

# Wait for PostgreSQL to be ready
sleep 5

# Start backend server
PYTHONPATH=. ./venv/Scripts/python.exe src/main.py
```

## Configuration

All configuration is in [backend/.env](backend/.env):

- **Database**: `chatbot_db` (user: `postgres`, password: `123456`)
- **OpenRouter API Key**: Configured for LLM access
- **JWT Public Key**: Placeholder for development
- **Fernet Key**: For API key encryption

## Implemented Features

### Phase 3 (MVP) - Complete ✅

1. **LLM Integration**
   - OpenRouter with 4 models (GPT-4o-mini, GPT-4o, Gemini 1.5 Pro, Claude 3.5 Sonnet)
   - Dynamic LLM client creation
   - Tenant-specific LLM configurations

2. **Agent Framework**
   - SupervisorAgent for intent detection
   - AgentDebt for debt/payment queries
   - Dynamic tool loading
   - Output formatting

3. **API Endpoints**
   - Chat endpoint with message persistence
   - Session management endpoints
   - JWT authentication middleware
   - Structured logging

4. **Database**
   - 13 tables created and seeded
   - Multi-tenant isolation
   - Session and message tracking

## Next Phase (Phase 4 - Admin API)

The next implementation phase will add:
- Admin endpoints for agent management
- Admin endpoints for tool management
- Admin endpoints for tenant configuration
- Permission management

## Documentation

- **Complete Setup Guide**: [SETUP_COMPLETE.md](SETUP_COMPLETE.md)
- **Backend README**: [backend/README.md](backend/README.md)
- **Project Spec**: `specs/001-agenthub-chatbot-framework/`

## Testing

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### View API Documentation
Open browser to: http://localhost:8000/docs

### Check Database
```bash
psql -h localhost -U postgres -d chatbot_db -c "SELECT COUNT(*) FROM sessions;"
```

## Troubleshooting

### Server Not Starting
- Check if port 8000 is already in use: `netstat -ano | findstr :8000`
- Check Python path: `cd backend && PYTHONPATH=. ./venv/Scripts/python.exe src/main.py`

### Database Connection Error
- Ensure PostgreSQL is running: `docker ps | grep postgres`
- Check credentials in `.env` match database

### Module Not Found Errors
- Always set PYTHONPATH when running Python: `PYTHONPATH=. python script.py`
- Or use uvicorn: `uvicorn src.main:app --reload`

---

**The backend is ready for development and testing!** 🚀
