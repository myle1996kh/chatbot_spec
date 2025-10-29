# Data Model: AgentHub Multi-Agent Chatbot Framework

**Feature**: 001-agenthub-chatbot-framework
**Date**: 2025-10-28
**Database**: PostgreSQL 15+
**ORM**: SQLAlchemy 2.0+
**Migrations**: Alembic

---

## Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌───────────────┐
│   Tenant     │◄──────┤ TenantLLMConfig  ├──────►│   LLMModel    │
└──────┬───────┘       └──────────────────┘       └───────────────┘
       │
       │ 1:N
       │
       ├──────────────────┐
       │                  │
       ▼                  ▼
┌─────────────────┐  ┌──────────────────────┐
│    Session      │  │ TenantAgentPermission│
└────────┬────────┘  └──────┬──────────────┘
         │                  │
         │ 1:N              │ N:M
         ▼                  ▼
┌─────────────────┐  ┌───────────────┐       ┌──────────────┐
│    Message      │  │  AgentConfig  │       │   BaseTool   │
└─────────────────┘  └───────┬───────┘       └──────┬───────┘
                             │                      │
                             │ N:M                  │ 1:N
                             ▼                      ▼
                     ┌─────────────────┐   ┌───────────────┐
                     │  AgentTools     ├──►│  ToolConfig   │
                     └─────────────────┘   └───────┬───────┘
                                                   │
                                                   │ N:1
                                                   ▼
                                           ┌───────────────┐
                                           │ OutputFormat  │
                                           └───────────────┘
```

---

## Core Entities

### 1. Tenant

Represents a company/organization using the AgentHub system.

**Table**: `tenants`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tenant_id` | UUID | PK | Unique tenant identifier |
| `name` | VARCHAR(255) | NOT NULL | Company/organization name |
| `domain` | VARCHAR(255) | UNIQUE | Domain for tenant (e.g., "acme.com") |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'active' | active/suspended/deleted |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- PRIMARY KEY: `tenant_id`
- UNIQUE INDEX: `domain`
- INDEX: `status`

**Relationships**:
- `sessions` (1:N) → Session
- `agent_permissions` (1:N) → TenantAgentPermission
- `tool_permissions` (1:N) → TenantToolPermission
- `llm_config` (1:1) → TenantLLMConfig

**Validation Rules**:
- `status` ENUM: ('active', 'suspended', 'deleted')
- `domain` must be valid DNS format

---

### 2. LLMModel

Available language models from various providers.

**Table**: `llm_models`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `llm_model_id` | UUID | PK | Unique model identifier |
| `provider` | VARCHAR(50) | NOT NULL | openai/gemini/anthropic/openrouter |
| `model_name` | VARCHAR(100) | NOT NULL | e.g., "gpt-4o", "gemini-pro" |
| `context_window` | INTEGER | NOT NULL | Max context window in tokens |
| `cost_per_1k_input_tokens` | DECIMAL(10,6) | NOT NULL | Input token cost (USD) |
| `cost_per_1k_output_tokens` | DECIMAL(10,6) | NOT NULL | Output token cost (USD) |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Model availability |
| `capabilities` | JSONB | | Model capabilities (e.g., {"vision": true}) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |

**Indexes**:
- PRIMARY KEY: `llm_model_id`
- INDEX: `provider`, `model_name`
- INDEX: `is_active`

**Relationships**:
- `tenant_configs` (1:N) → TenantLLMConfig
- `agent_configs` (1:N) → AgentConfig

---

### 3. TenantLLMConfig

Tenant-specific LLM settings and encrypted API keys.

**Table**: `tenant_llm_configs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `config_id` | UUID | PK | Unique config identifier |
| `tenant_id` | UUID | FK → tenants, NOT NULL | Tenant reference |
| `llm_model_id` | UUID | FK → llm_models, NOT NULL | Model reference |
| `encrypted_api_key` | TEXT | NOT NULL | Fernet-encrypted API key |
| `rate_limit_rpm` | INTEGER | DEFAULT 60 | Requests per minute limit |
| `rate_limit_tpm` | INTEGER | DEFAULT 10000 | Tokens per minute limit |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- PRIMARY KEY: `config_id`
- UNIQUE INDEX: `tenant_id` (one config per tenant)
- FK INDEX: `llm_model_id`

**Relationships**:
- `tenant` (N:1) → Tenant
- `llm_model` (N:1) → LLMModel

**Security**:
- `encrypted_api_key` MUST be encrypted with Fernet before insert/update
- Never logged or exposed in API responses

---

### 4. BaseTool

Template for tool types (HTTP, RAG, DB, OCR).

**Table**: `base_tools`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `base_tool_id` | UUID | PK | Unique base tool identifier |
| `type` | VARCHAR(50) | NOT NULL | HTTP_GET/HTTP_POST/RAG/DB_QUERY/OCR |
| `handler_class` | VARCHAR(255) | NOT NULL | Python class path (e.g., "tools.http.HTTPGetTool") |
| `description` | TEXT | | Tool type description |
| `default_config_schema` | JSONB | | JSON schema for config validation |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |

**Indexes**:
- PRIMARY KEY: `base_tool_id`
- UNIQUE INDEX: `type`

**Relationships**:
- `tool_configs` (1:N) → ToolConfig

**Validation Rules**:
- `type` ENUM: ('HTTP_GET', 'HTTP_POST', 'RAG', 'DB_QUERY', 'OCR')

---

### 5. OutputFormat

Response format definitions for structured output.

**Table**: `output_formats`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `format_id` | UUID | PK | Unique format identifier |
| `name` | VARCHAR(100) | NOT NULL, UNIQUE | structured_json/markdown_table/chart_data/summary_text |
| `schema` | JSONB | | JSON schema for output structure |
| `renderer_hint` | JSONB | | UI rendering hints (type, fields) |
| `description` | TEXT | | Format description |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |

**Indexes**:
- PRIMARY KEY: `format_id`
- UNIQUE INDEX: `name`

**Relationships**:
- `tool_configs` (1:N) → ToolConfig
- `agent_configs` (1:N) → AgentConfig

**Example `renderer_hint`**:
```json
{
  "type": "table",
  "fields": ["customer_name", "total_debt", "overdue_amount"],
  "sortable": true,
  "filterable": true
}
```

---

### 6. ToolConfig

Specific tool instances configured from base tools.

**Table**: `tool_configs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tool_id` | UUID | PK | Unique tool instance identifier |
| `name` | VARCHAR(100) | NOT NULL | Tool name (e.g., "get_customer_debt") |
| `base_tool_id` | UUID | FK → base_tools, NOT NULL | Base tool type reference |
| `config` | JSONB | NOT NULL | Tool-specific config (endpoint, method, headers) |
| `input_schema` | JSONB | NOT NULL | JSON schema for tool parameters |
| `output_format_id` | UUID | FK → output_formats, NULL | Default output format |
| `description` | TEXT | | Tool description for LLM |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Tool availability |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- PRIMARY KEY: `tool_id`
- FK INDEX: `base_tool_id`
- FK INDEX: `output_format_id`
- INDEX: `is_active`

**Relationships**:
- `base_tool` (N:1) → BaseTool
- `output_format` (N:1) → OutputFormat
- `agent_tools` (1:N) → AgentTools
- `tenant_tool_permissions` (1:N) → TenantToolPermission

**Example `config` (HTTP_GET)**:
```json
{
  "endpoint": "https://erp.example.com/api/customers/{customer_mst}/debt",
  "method": "GET",
  "headers": {
    "X-API-Version": "v1"
  },
  "timeout": 30
}
```

**Example `input_schema`**:
```json
{
  "type": "object",
  "properties": {
    "customer_mst": {
      "type": "string",
      "description": "Customer tax code (MST)",
      "pattern": "^[0-9]{10}$"
    }
  },
  "required": ["customer_mst"]
}
```

---

### 7. AgentConfig

Domain-specific agent configurations.

**Table**: `agent_configs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `agent_id` | UUID | PK | Unique agent identifier |
| `name` | VARCHAR(100) | NOT NULL | Agent name (e.g., "AgentDebt") |
| `prompt_template` | TEXT | NOT NULL | Agent system prompt template |
| `llm_model_id` | UUID | FK → llm_models, NOT NULL | LLM model reference |
| `default_output_format_id` | UUID | FK → output_formats, NULL | Default output format |
| `description` | TEXT | | Agent description |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Agent availability |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- PRIMARY KEY: `agent_id`
- UNIQUE INDEX: `name`
- FK INDEX: `llm_model_id`
- FK INDEX: `default_output_format_id`
- INDEX: `is_active`

**Relationships**:
- `llm_model` (N:1) → LLMModel
- `output_format` (N:1) → OutputFormat
- `agent_tools` (1:N) → AgentTools
- `tenant_agent_permissions` (1:N) → TenantAgentPermission

**Example `prompt_template`**:
```
You are AgentDebt, a specialized assistant for customer debt inquiries.

Your capabilities:
- Query customer debt by MST (tax code)
- Check payment history
- Identify overdue amounts

Always:
- Extract MST from user query
- Validate MST format (10 digits)
- Use get_customer_debt tool with JWT authorization
- Return structured debt information

Never:
- Process multi-domain queries (route to SupervisorAgent)
- Access data outside your tenant scope
```

---

### 8. AgentTools

Many-to-many relationship: which tools each agent can use.

**Table**: `agent_tools`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `agent_id` | UUID | FK → agent_configs, NOT NULL | Agent reference |
| `tool_id` | UUID | FK → tool_configs, NOT NULL | Tool reference |
| `priority` | INTEGER | NOT NULL | Tool priority (1=highest) for pre-filtering |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Assignment timestamp |

**Indexes**:
- PRIMARY KEY: `(agent_id, tool_id)`
- FK INDEX: `agent_id`
- FK INDEX: `tool_id`
- INDEX: `(agent_id, priority ASC)` (for priority-based filtering)

**Relationships**:
- `agent` (N:1) → AgentConfig
- `tool` (N:1) → ToolConfig

**Priority Semantics**:
- System pre-filters to top 5 priority tools (ORDER BY priority ASC LIMIT 5)
- LLM then selects semantically from filtered set
- Lower number = higher priority (1 is highest)

---

### 9. TenantAgentPermission

Enables agents for specific tenants with optional overrides.

**Table**: `tenant_agent_permissions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tenant_id` | UUID | FK → tenants, NOT NULL | Tenant reference |
| `agent_id` | UUID | FK → agent_configs, NOT NULL | Agent reference |
| `enabled` | BOOLEAN | NOT NULL, DEFAULT TRUE | Permission status |
| `output_override_id` | UUID | FK → output_formats, NULL | Tenant-specific output format override |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Permission grant timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- PRIMARY KEY: `(tenant_id, agent_id)`
- FK INDEX: `tenant_id`
- FK INDEX: `agent_id`
- FK INDEX: `output_override_id`
- INDEX: `enabled`

**Relationships**:
- `tenant` (N:1) → Tenant
- `agent` (N:1) → AgentConfig
- `output_format` (N:1) → OutputFormat

---

### 10. TenantToolPermission

Enables tools for specific tenants.

**Table**: `tenant_tool_permissions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tenant_id` | UUID | FK → tenants, NOT NULL | Tenant reference |
| `tool_id` | UUID | FK → tool_configs, NOT NULL | Tool reference |
| `enabled` | BOOLEAN | NOT NULL, DEFAULT TRUE | Permission status |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Permission grant timestamp |

**Indexes**:
- PRIMARY KEY: `(tenant_id, tool_id)`
- FK INDEX: `tenant_id`
- FK INDEX: `tool_id`
- INDEX: `enabled`

**Relationships**:
- `tenant` (N:1) → Tenant
- `tool` (N:1) → ToolConfig

---

### 11. Session

Conversation sessions for tracking multi-turn interactions.

**Table**: `sessions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `session_id` | UUID | PK | Unique session identifier |
| `tenant_id` | UUID | FK → tenants, NOT NULL | Tenant reference |
| `user_id` | VARCHAR(255) | NOT NULL | User identifier from JWT |
| `agent_id` | UUID | FK → agent_configs, NULL | Last agent used in session |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Session start timestamp |
| `last_message_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last message timestamp |
| `metadata` | JSONB | | Additional session metadata |

**Indexes**:
- PRIMARY KEY: `session_id`
- FK INDEX: `tenant_id`
- FK INDEX: `agent_id`
- INDEX: `(tenant_id, user_id, created_at DESC)` (for user session list)
- INDEX: `last_message_at` (for session cleanup)

**Relationships**:
- `tenant` (N:1) → Tenant
- `agent` (N:1) → AgentConfig
- `messages` (1:N) → Message

**Thread ID Pattern** (for LangGraph PostgresSaver):
```
tenant_{tenant_id}__user_{user_id}__session_{session_id}
```

---

### 12. Message

Individual chat messages within sessions.

**Table**: `messages`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `message_id` | UUID | PK | Unique message identifier |
| `session_id` | UUID | FK → sessions, NOT NULL | Session reference |
| `role` | VARCHAR(50) | NOT NULL | user/assistant/system |
| `content` | TEXT | NOT NULL | Message content |
| `timestamp` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Message timestamp |
| `metadata` | JSONB | | Additional metadata (intent, tool_calls, tokens) |

**Indexes**:
- PRIMARY KEY: `message_id`
- FK INDEX: `session_id`
- INDEX: `(session_id, timestamp ASC)` (for chronological retrieval)

**Relationships**:
- `session` (N:1) → Session

**Example `metadata`**:
```json
{
  "intent": "customer_debt_query",
  "agent_used": "AgentDebt",
  "tool_calls": ["get_customer_debt"],
  "token_count": 150,
  "duration_ms": 1234
}
```

**Validation Rules**:
- `role` ENUM: ('user', 'assistant', 'system')

---

## Supporting Tables

### 13. ConversationCheckpoints

LangGraph PostgresSaver checkpointing table (auto-managed).

**Table**: `checkpoints`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `thread_id` | TEXT | PK | Thread identifier |
| `checkpoint_id` | TEXT | PK | Checkpoint identifier |
| `parent_id` | TEXT | NULL | Parent checkpoint reference |
| `checkpoint` | BYTEA | NOT NULL | Serialized checkpoint data |
| `metadata` | JSONB | | Checkpoint metadata |

**Note**: This table is managed by LangGraph's `PostgresSaver.setup()` - do not manually modify schema.

---

## Indexes Summary

**Performance-Critical Indexes**:
1. `(tenant_id, agent_id)` on tenant_agent_permissions (fast permission checks)
2. `(agent_id, priority ASC)` on agent_tools (priority-based tool filtering)
3. `(tenant_id, user_id, created_at DESC)` on sessions (user session list)
4. `(session_id, timestamp ASC)` on messages (chronological message retrieval)
5. `tenant_id` on all tenant-scoped tables (multi-tenant isolation)

**Cache Keys Pattern** (Redis):
```
agenthub:{tenant_id}:cache:agent:{agent_id}
agenthub:{tenant_id}:cache:tool:{tool_id}
agenthub:{tenant_id}:cache:permissions:agents
agenthub:{tenant_id}:cache:permissions:tools
```

---

## Data Volume Estimates

| Entity | Expected Volume | Growth Rate | Retention |
|--------|----------------|-------------|-----------|
| Tenants | 100-500 | 10/month | Indefinite |
| AgentConfigs | 20-50 | 2/month | Indefinite |
| ToolConfigs | 50-200 | 5/month | Indefinite |
| Sessions | 10k-100k | 1k/day | 90 days |
| Messages | 100k-1M | 10k/day | 90 days |
| LLMModels | 10-20 | 2/quarter | Indefinite |

**Assumptions**:
- Each tenant has ~100 conversations/day
- Each conversation has ~5 messages average
- 90-day retention for conversation history (configurable)

---

## Alembic Migration Strategy

**Initial Migration** (`001_initial_schema.py`):
1. Create all base tables (tenants, llm_models, base_tools, output_formats)
2. Create config tables (agent_configs, tool_configs)
3. Create junction tables (agent_tools, tenant_agent_permissions, tenant_tool_permissions)
4. Create conversation tables (sessions, messages)
5. Create all indexes
6. Insert seed data (base_tools, output_formats, default LLM models)

**Rollback Strategy**:
- Each migration has `downgrade()` function
- Test rollback in sandbox before production
- Backup database before running migrations

**Sample Alembic Command**:
```bash
# Generate migration
alembic revision --autogenerate -m "initial schema"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Seed Data

### Base Tools
```sql
INSERT INTO base_tools (base_tool_id, type, handler_class, description) VALUES
('uuid-1', 'HTTP_GET', 'tools.http.HTTPGetTool', 'HTTP GET request tool'),
('uuid-2', 'HTTP_POST', 'tools.http.HTTPPostTool', 'HTTP POST request tool'),
('uuid-3', 'RAG', 'tools.rag.RAGTool', 'RAG vector search tool'),
('uuid-4', 'DB_QUERY', 'tools.db.DBQueryTool', 'Database query tool'),
('uuid-5', 'OCR', 'tools.ocr.OCRTool', 'OCR document processing tool');
```

### Output Formats
```sql
INSERT INTO output_formats (format_id, name, schema, renderer_hint) VALUES
('uuid-1', 'structured_json', '{"type": "object"}', '{"type": "json"}'),
('uuid-2', 'markdown_table', '{"type": "string"}', '{"type": "table"}'),
('uuid-3', 'chart_data', '{"type": "object"}', '{"type": "chart", "chartType": "bar"}'),
('uuid-4', 'summary_text', '{"type": "string"}', '{"type": "text"}');
```

### Default LLM Models
```sql
INSERT INTO llm_models (llm_model_id, provider, model_name, context_window, cost_per_1k_input_tokens, cost_per_1k_output_tokens) VALUES
('uuid-1', 'openai', 'gpt-4o-mini', 128000, 0.00015, 0.0006),
('uuid-2', 'openai', 'gpt-4o', 128000, 0.0025, 0.01),
('uuid-3', 'gemini', 'gemini-1.5-pro', 1048576, 0.00125, 0.00375),
('uuid-4', 'anthropic', 'claude-3-5-sonnet-20241022', 200000, 0.003, 0.015);
```

---

## SQLAlchemy Model Example

```python
from sqlalchemy import Column, String, Integer, Text, Boolean, TIMESTAMP, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sessions = relationship("Session", back_populates="tenant")
    agent_permissions = relationship("TenantAgentPermission", back_populates="tenant")
    tool_permissions = relationship("TenantToolPermission", back_populates="tenant")
    llm_config = relationship("TenantLLMConfig", back_populates="tenant", uselist=False)

class AgentConfig(Base):
    __tablename__ = "agent_configs"

    agent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    prompt_template = Column(Text, nullable=False)
    llm_model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.llm_model_id"), nullable=False)
    default_output_format_id = Column(UUID(as_uuid=True), ForeignKey("output_formats.format_id"))
    description = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    llm_model = relationship("LLMModel")
    output_format = relationship("OutputFormat")
    agent_tools = relationship("AgentTools", back_populates="agent")
    tenant_permissions = relationship("TenantAgentPermission", back_populates="agent")
```

---

**Data Model Status**: ✅ Complete
**Ready for**: API Contract Definition, Implementation Planning
