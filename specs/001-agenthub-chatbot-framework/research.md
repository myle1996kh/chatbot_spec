# Research & Technology Decisions: AgentHub Multi-Agent Chatbot Framework

**Feature**: 001-agenthub-chatbot-framework
**Date**: 2025-10-28
**Status**: Complete

## Overview

This document captures all technology decisions, architecture patterns, and best practices research conducted for the AgentHub Multi-Agent Chatbot Framework implementation.

---

## 1. SupervisorAgent Routing Architecture

### Decision: LangGraph with Tool-Based Handoffs

**Rationale**:
- LangGraph is the official LangChain 0.3+ pattern for multi-agent systems
- Tool-based handoffs provide better control than deprecated AgentExecutor or legacy chains
- `Command` primitive enables clean state transfer between supervisor and worker agents
- Unified `MessagesState` maintains conversation context across agent transitions
- Production-proven pattern from LangChain official documentation

**Alternatives Considered**:
1. **Custom Chains**: Too rigid, no dynamic routing capability
2. **AgentExecutor**: Deprecated in LangChain 0.3+, legacy pattern
3. **LangGraph Supervisor Library**: Deprecated in favor of tool-based handoffs

**Implementation Pattern**:
```python
@tool
def assign_to_debt_agent(
    state: Annotated[MessagesState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Assign task to debt agent for customer debt queries."""
    tool_message = ToolMessage(
        content="Assigned to debt agent",
        name="assign_to_debt_agent",
        tool_call_id=tool_call_id,
    )
    return Command(
        goto="debt_agent",
        update={**state, "messages": state["messages"] + [tool_message]},
        graph=Command.PARENT,
    )

# SupervisorAgent with handoff tools
supervisor = create_react_agent(
    model="openai:gpt-4o-mini",
    tools=[assign_to_debt_agent, assign_to_shipment_agent, assign_to_ocr_agent, assign_to_analysis_agent],
    state_schema=MessagesState,
)
```

**References**:
- LangChain LangGraph Documentation: Multi-Agent Architectures
- Tool-Based Handoffs Pattern (2024)

---

## 2. Dynamic Tool Loading & Registry

### Decision: StructuredTool Factory with Pydantic create_model()

**Rationale**:
- `StructuredTool.from_function()` supports programmatic tool creation
- Pydantic's `create_model()` generates schemas from JSON at runtime (required for database-driven config)
- `RunnableConfig` + `InjectedToolArg` provides secure context injection (JWT, tenant_id) invisible to LLM
- Tool caching by tenant reduces database overhead
- Follows LangChain 0.3+ best practices for dynamic tool generation

**Alternatives Considered**:
1. **Static Tool Definitions**: Violates "Configuration Over Code" principle
2. **JSON Schema Only**: No type safety, poor LLM performance
3. **Manual Tool Classes**: Not scalable for config-driven architecture

**Implementation Pattern**:
```python
from pydantic import create_model, Field
from langchain_core.tools import StructuredTool, InjectedToolArg
from langchain_core.runnables import RunnableConfig

class ToolRegistry:
    def create_tool_from_db_config(self, tool_config: dict, execution_context: dict) -> StructuredTool:
        # Build dynamic Pydantic schema from JSON
        schema_fields = {}
        for field_name, field_spec in tool_config["schema"].items():
            field_type = self._map_json_type(field_spec["type"])
            schema_fields[field_name] = (
                field_type,
                Field(description=field_spec["description"])
            )

        DynamicSchema = create_model(f"{tool_config['name']}_Schema", **schema_fields)

        # Execution function with context injection
        def tool_executor(config: Annotated[RunnableConfig, InjectedToolArg], **kwargs) -> str:
            jwt_token = config["configurable"]["jwt_token"]
            tenant_id = config["configurable"]["tenant_id"]
            executor_func = EXECUTOR_REGISTRY[tool_config["executor"]]
            return executor_func(**kwargs, jwt_token=jwt_token, tenant_id=tenant_id)

        return StructuredTool.from_function(
            func=tool_executor,
            name=tool_config["name"],
            description=tool_config["description"],
            args_schema=DynamicSchema,
            metadata={"priority": tool_config["priority"]}
        )
```

**References**:
- LangChain Custom Tools Documentation
- Pydantic Dynamic Model Creation Guide

---

## 3. Tool Priority & Selection Mechanism

### Decision: Pre-filter to Top 5 Priority Tools Before LLM Selection

**Rationale**:
- LangChain LLMs select tools semantically, not by explicit ordering
- Priority controls tool visibility (what LLM sees), not selection order (which tool LLM chooses)
- Pre-filtering to top 5 prevents overwhelming LLM with too many tool choices
- Balances control (priority-based filtering) with intelligence (semantic matching)
- Reduces token usage and improves response time

**Alternatives Considered**:
1. **Strict Priority Order**: Breaks semantic tool selection, defeats LLM intelligence
2. **Priority as Metadata Only**: Makes priority field meaningless
3. **Weighted Semantic Search**: Complex, not natively supported by LangChain

**Implementation Pattern**:
```python
def load_agent_tools_with_priority(agent_id: str, tenant_id: str) -> list[StructuredTool]:
    # Query tools ordered by priority ASC (1=highest)
    tool_configs = db.query(
        "SELECT * FROM agent_tools WHERE agent_id = %s ORDER BY priority ASC LIMIT 5",
        [agent_id]
    )

    tools = []
    for config in tool_configs:
        tool = tool_registry.create_tool_from_db_config(config, {"tenant_id": tenant_id})
        tools.append(tool)

    return tools

# Bind filtered tools to LLM
llm_with_tools = llm.bind_tools(tools)
```

**References**:
- LangChain Tool Selection Best Practices
- Agent Tool Binding Patterns

---

## 4. Multi-Turn Conversation Memory

### Decision: LangGraph PostgresSaver with Sliding Window Context

**Rationale**:
- `PostgresSaver` is the official LangChain 0.3+ checkpointer (ConversationBufferMemory deprecated)
- PostgreSQL-backed persistence for production reliability
- Sliding window (last 10 messages + system prompt) prevents token limit issues
- `trim_messages()` function handles long conversations efficiently
- Thread ID pattern `tenant_{id}__user_{id}__session_{id}` ensures multi-tenant isolation

**Alternatives Considered**:
1. **ConversationBufferMemory**: Deprecated in LangChain 0.3+
2. **ConversationSummaryMemory**: Adds latency with summarization LLM calls
3. **Full History Until Limit**: Unpredictable, risks context window overflow

**Implementation Pattern**:
```python
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import trim_messages

DB_URI = "postgresql://user:pass@localhost:5432/agenthub"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()

    def call_agent(state: MessagesState):
        messages = state["messages"]

        # Sliding window for conversations >10 messages
        if len(messages) > 10:
            trimmed = trim_messages(
                messages,
                max_tokens=4000,
                strategy="last",
                token_counter=model,
                include_system=True,
                start_on="human"
            )
        else:
            trimmed = messages

        response = model.invoke(trimmed)
        return {"messages": [response]}

    graph = builder.compile(checkpointer=checkpointer)

# Thread ID for multi-tenant isolation
thread_id = f"tenant_{tenant_id}__user_{user_id}__session_{session_id}"
```

**References**:
- LangGraph Checkpointing Documentation
- LangChain Memory Migration Guide (0.2 → 0.3)

---

## 5. Output Formatting Strategy

### Decision: Hybrid Approach - Custom OutputParser + Post-Processing

**Rationale**:
- Custom `OutputParser` for structured formats (JSON, markdown tables) with format instructions
- Post-processing for complex visualizations (charts, graphs) that require transformations
- Tool return schemas for tool-specific format requirements
- Format instructions in system prompt guide LLM output structure
- Separation of concerns: parsing vs. transformation

**Alternatives Considered**:
1. **OutputParser Only**: Insufficient for complex chart data transformations
2. **Post-Processing Only**: Loses type safety and LLM guidance
3. **Tool Schemas Only**: Doesn't apply to agent synthesis responses

**Implementation Pattern**:
```python
from langchain_core.output_parsers import BaseOutputParser

class AgentHubOutputParser(BaseOutputParser[dict]):
    format_type: Literal["structured_json", "markdown_table", "chart_data", "text"]

    def parse(self, text: str) -> dict:
        if self.format_type == "structured_json":
            return self._parse_json(text)
        elif self.format_type == "markdown_table":
            return self._parse_table(text)
        elif self.format_type == "chart_data":
            return self._parse_chart(text)
        else:
            return {"content": text, "format": "text"}

    def get_format_instructions(self) -> str:
        if self.format_type == "structured_json":
            return "Format your response as valid JSON with structure: {...}"
        # ... other formats

# Add format instructions to system prompt
system_prompt = f"""You are a helpful assistant.

{parser.get_format_instructions()}
"""

agent = create_react_agent(model=model, tools=tools, state_modifier=system_prompt)
```

**References**:
- LangChain Output Parsers Documentation
- Structured Output Best Practices

---

## 6. JWT Context Injection & Security

### Decision: RunnableConfig with InjectedToolArg for Secure Context Passing

**Rationale**:
- `InjectedToolArg` passes context (JWT, tenant_id) to tools without LLM visibility
- Prevents prompt injection attacks (LLM never sees sensitive tokens)
- Aligns with "Security & Token Isolation" constitution principle
- Clean separation between user-visible parameters and system context
- Native LangChain pattern for secure context injection

**Alternatives Considered**:
1. **Global Variables**: Not thread-safe, violates multi-tenant isolation
2. **Tool Parameter Injection**: Exposes sensitive data to LLM (security risk)
3. **Custom Context Managers**: Reinvents LangChain native capability

**Implementation Pattern**:
```python
def tool_executor(
    config: Annotated[RunnableConfig, InjectedToolArg],
    customer_mst: str  # User-visible parameter
) -> str:
    # Extract injected context (invisible to LLM)
    jwt_token = config["configurable"]["jwt_token"]
    tenant_id = config["configurable"]["tenant_id"]

    # Make authenticated API call
    response = requests.get(
        f"{API_BASE}/customers/{customer_mst}/debt",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    return response.json()

# Invoke with injected context
agent.invoke(
    {"messages": [{"role": "user", "content": "Check debt for MST 0123456789"}]},
    config={
        "configurable": {
            "jwt_token": user_jwt,
            "tenant_id": tenant_id
        }
    }
)
```

**References**:
- LangChain RunnableConfig Documentation
- Secure Tool Execution Patterns

---

## 7. FastAPI Async Architecture

### Decision: Async FastAPI with Dependency Injection for Multi-Tenant Context

**Rationale**:
- Async/await for high concurrency (100+ concurrent users per tenant)
- FastAPI dependency injection for JWT validation and tenant extraction
- Pydantic models for request/response validation
- Aligns with constitution requirement: FastAPI (async)
- Built-in OpenAPI documentation generation

**Alternatives Considered**:
1. **Flask**: No native async support, slower for I/O-bound operations
2. **Django**: Overkill for API-only service, slower startup
3. **Sync FastAPI**: Lower concurrency, doesn't meet 100+ concurrent users requirement

**Implementation Pattern**:
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI()
security = HTTPBearer()

async def get_current_tenant(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
    return payload["tenant_id"]

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@app.post("/api/{tenant_id}/chat")
async def chat(
    tenant_id: str,
    request: ChatRequest,
    auth_tenant: str = Depends(get_current_tenant)
):
    if tenant_id != auth_tenant:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Process chat request asynchronously
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": request.message}]},
        config={"configurable": {"tenant_id": tenant_id}}
    )
    return result
```

**References**:
- FastAPI Async Best Practices
- Multi-Tenant API Patterns

---

## 8. Database Schema & Migrations

### Decision: SQLAlchemy ORM with Alembic Migrations

**Rationale**:
- SQLAlchemy provides ORM abstraction for PostgreSQL
- Alembic handles schema migrations with rollback support (constitution requirement)
- Type-safe models with Pydantic integration
- Connection pooling (minimum 20 connections per constitution)
- Supports tenant-based row-level security

**Alternatives Considered**:
1. **Raw SQL**: No type safety, harder to maintain
2. **Django ORM**: Requires full Django framework (overkill)
3. **Tortoise ORM**: Less mature, smaller ecosystem

**Implementation Pattern**:
```python
from sqlalchemy import create_engine, Column, String, Integer, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.pool import QueuePool

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    tenant_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, default="active")

    agents = relationship("TenantAgentPermission", back_populates="tenant")

class AgentConfig(Base):
    __tablename__ = "agent_configs"
    agent_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    prompt_template = Column(String, nullable=False)
    llm_model_id = Column(String, ForeignKey("llm_models.llm_model_id"))
    default_output_format_id = Column(String, ForeignKey("output_formats.format_id"))

# Engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10
)
```

**References**:
- SQLAlchemy Documentation
- Alembic Migration Best Practices

---

## 9. Redis Caching Strategy

### Decision: Redis 7.x with Tenant-Namespaced Keys and 1-Hour TTL

**Rationale**:
- Pattern `agenthub:{tenant_id}:cache:{key}` ensures multi-tenant isolation (constitution requirement)
- 1-hour TTL balances freshness with database load reduction
- Redis 7.x supports JSON data types for complex configurations
- Async Redis client (aioredis) for non-blocking operations
- Cache warming strategy prevents stampede on expiration

**Alternatives Considered**:
1. **In-Memory Dict**: No persistence, lost on restart
2. **Memcached**: No data structure support, less feature-rich
3. **Longer TTL (24h)**: Stale configurations, violates constitution requirement

**Implementation Pattern**:
```python
import redis.asyncio as redis
import json

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

async def get_agent_config(tenant_id: str, agent_id: str) -> dict:
    cache_key = f"agenthub:{tenant_id}:cache:agent:{agent_id}"

    # Try cache first
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Cache miss: load from database
    config = await db.get_agent_config(agent_id)

    # Cache with 1-hour TTL
    await redis_client.setex(
        cache_key,
        3600,  # 1 hour in seconds
        json.dumps(config)
    )

    return config

async def invalidate_agent_cache(tenant_id: str, agent_id: str):
    cache_key = f"agenthub:{tenant_id}:cache:agent:{agent_id}"
    await redis_client.delete(cache_key)
```

**References**:
- Redis Multi-Tenancy Patterns
- Cache Invalidation Strategies

---

## 10. ChromaDB for RAG Vector Store

### Decision: ChromaDB with OpenAI Embeddings and Tenant Collections

**Rationale**:
- Lightweight, embeddable vector database (no separate server required for dev)
- Native Python API integrates cleanly with LangChain
- Collection-per-tenant isolation for multi-tenancy
- Supports metadata filtering for granular access control
- Persistent storage with configurable path

**Alternatives Considered**:
1. **Pinecone**: Requires external service, adds cost and latency
2. **Weaviate**: More complex setup, overkill for initial MVP
3. **FAISS**: No built-in persistence, requires manual management

**Implementation Pattern**:
```python
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

def get_tenant_vectorstore(tenant_id: str) -> Chroma:
    collection_name = f"tenant_{tenant_id}_knowledge"

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=OpenAIEmbeddings(),
        persist_directory=f"./chroma_db/{tenant_id}"
    )

    return vectorstore

# RAG retrieval
vectorstore = get_tenant_vectorstore(tenant_id)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

docs = retriever.get_relevant_documents("What is the return policy?")
```

**References**:
- LangChain ChromaDB Integration
- Vector Store Multi-Tenancy Patterns

---

## 11. Fernet Encryption for API Keys

### Decision: Cryptography Fernet for Symmetric Encryption of LLM API Keys

**Rationale**:
- Fernet provides authenticated encryption (HMAC + AES-128-CBC)
- Simple key rotation support
- Constitution requirement: API keys encrypted with Fernet
- Encrypt at rest in database, decrypt only at runtime
- Key stored in environment variable, never in code

**Alternatives Considered**:
1. **AES-GCM Directly**: More complex, Fernet provides better API
2. **Asymmetric Encryption (RSA)**: Overkill for symmetric secret encryption
3. **Database-Level Encryption**: Doesn't meet constitution requirement (application-level needed)

**Implementation Pattern**:
```python
from cryptography.fernet import Fernet
import os

# Load encryption key from environment
FERNET_KEY = os.getenv("FERNET_KEY")
cipher = Fernet(FERNET_KEY.encode())

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key before storing in database."""
    return cipher.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key at runtime for LLM client."""
    return cipher.decrypt(encrypted_key.encode()).decode()

# Usage
encrypted = encrypt_api_key("sk-...")
db.save_tenant_llm_config(tenant_id, llm_model_id, encrypted)

# At runtime
encrypted_key = db.get_tenant_api_key(tenant_id)
api_key = decrypt_api_key(encrypted_key)
llm_client = OpenAI(api_key=api_key)
```

**References**:
- Cryptography Fernet Documentation
- API Key Storage Best Practices

---

## 12. Structured JSON Logging

### Decision: Python structlog for JSON Structured Logging

**Rationale**:
- JSON format for log aggregation systems (ELK, Datadog)
- Constitution requirement: structured JSON logs
- Automatic context injection (tenant_id, user_id, agent_name)
- Performance metrics logging (duration_ms, token_count)
- Sanitization of PII and sensitive data (JWT tokens, API keys)

**Alternatives Considered**:
1. **Standard Logging**: Not structured, harder to parse/analyze
2. **Custom JSON Logger**: Reinvents wheel, structlog is battle-tested
3. **Plain Text Logs**: Violates constitution requirement

**Implementation Pattern**:
```python
import structlog
import logging

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Usage with context
logger.info(
    "agent_invoked",
    tenant_id=tenant_id,
    agent_name="AgentDebt",
    duration_ms=1234,
    token_count=150,
    success=True
)

# Output: {"event": "agent_invoked", "tenant_id": "...", "duration_ms": 1234, ...}
```

**References**:
- structlog Documentation
- Structured Logging Best Practices

---

## 13. Testing Strategy

### Decision: Pytest with 80%+ Coverage (Constitution Requirement)

**Rationale**:
- Constitution requires ≥80% test coverage
- Pytest supports fixtures, async tests, parametrization
- Integration tests for end-to-end conversation flows
- Contract tests for tool execution
- Mock external services (LLM, external APIs)

**Test Categories**:
1. **Unit Tests**: Models, services, utilities (src/tests/unit/)
2. **Integration Tests**: Agent invocation, tool execution, JWT validation (src/tests/integration/)
3. **Contract Tests**: API endpoint validation (src/tests/contract/)
4. **E2E Tests**: Full conversation flows (src/tests/e2e/)

**Implementation Pattern**:
```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_llm():
    with patch("langchain_openai.ChatOpenAI") as mock:
        yield mock

def test_chat_endpoint_requires_jwt(test_client):
    response = test_client.post("/api/tenant123/chat", json={"message": "test"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_agent_debt_query(mock_llm, test_db):
    # Setup
    tenant_id = "test_tenant"
    agent = await create_debt_agent(tenant_id)

    # Execute
    result = await agent.ainvoke({"messages": [{"role": "user", "content": "debt for MST 123"}]})

    # Verify
    assert "debt" in result["messages"][-1].content.lower()
    assert mock_llm.called
```

**References**:
- Pytest Async Testing
- FastAPI Testing Guide

---

## Summary of Key Decisions

| Area | Technology | Rationale |
|------|-----------|-----------|
| **Agent Framework** | LangGraph tool-handoffs | Official LangChain 0.3+ multi-agent pattern |
| **Tool Creation** | StructuredTool + create_model() | Dynamic schema generation from database JSON |
| **Tool Priority** | Pre-filter top 5 by priority ASC | Balance control with semantic intelligence |
| **Memory** | PostgresSaver + trim_messages() | Production persistence with sliding window |
| **Output Formatting** | Custom OutputParser + post-processing | Structured formats with LLM guidance |
| **Security Context** | RunnableConfig + InjectedToolArg | Invisible JWT injection (no prompt leakage) |
| **Web Framework** | FastAPI (async) | High concurrency, dependency injection |
| **Database** | PostgreSQL + SQLAlchemy + Alembic | ORM, migrations, connection pooling |
| **Cache** | Redis 7.x (1h TTL, tenant namespace) | Multi-tenant isolation, performance |
| **Vector DB** | ChromaDB | Lightweight, embeddable, LangChain integration |
| **Encryption** | Fernet (Cryptography) | API key encryption per constitution |
| **Logging** | structlog (JSON) | Structured logs per constitution |
| **Testing** | Pytest (≥80% coverage) | Async support, meets constitution requirement |

---

## Implementation Priorities

**Phase 1 (MVP - User Story 1):**
1. FastAPI project setup with async endpoints
2. PostgreSQL database schema (Alembic migrations)
3. LangGraph SupervisorAgent with handoff pattern
4. Single domain agent (AgentDebt) with StructuredTool
5. JWT authentication middleware
6. Redis caching for agent configs
7. Basic structured JSON output formatting

**Phase 2 (User Stories 2-3):**
1. Admin API endpoints for agent/tool management
2. Dynamic tool loader with ToolRegistry
3. Tenant isolation enforcement (database, cache, tools)
4. Fernet encryption for LLM API keys
5. Multi-tenant testing and security validation

**Phase 3 (User Stories 4-7):**
1. Multi-intent detection (rejection for MVP)
2. Additional domain agents (Shipment, OCR, Analysis)
3. RAG integration with ChromaDB
4. Session management with PostgresSaver
5. Advanced output formatting (tables, charts)

---

## Constitution Compliance Checklist

- ✅ **Configuration Over Code**: Dynamic tool loading from database
- ✅ **Multi-Agent & Multi-Tenant**: LangGraph supervisor + tenant-namespaced cache
- ✅ **LangChain-First**: LangGraph, StructuredTool, PostgresSaver (no AgentExecutor)
- ✅ **Security & Token Isolation**: JWT RS256, Fernet encryption, InjectedToolArg
- ✅ **Unified Output & Observability**: Custom OutputParser, structlog JSON logging
- ✅ **Performance**: Async FastAPI, Redis cache (1h TTL), PostgreSQL pool (20+)
- ✅ **Test Coverage**: Pytest with ≥80% coverage requirement
- ✅ **Deployment**: Alembic migrations with rollback scripts

---

**Research Status**: ✅ Complete
**Ready for Phase 1**: Data Model Design, API Contracts, Quickstart Scenarios
