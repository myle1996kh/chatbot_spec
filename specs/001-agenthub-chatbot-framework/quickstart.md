# Quickstart & Test Scenarios: AgentHub Multi-Agent Chatbot Framework

**Feature**: 001-agenthub-chatbot-framework
**Date**: 2025-10-28
**Purpose**: End-to-end test scenarios for validating user stories independently

---

## Prerequisites

1. **Database Setup**:
   ```bash
   # Run Alembic migrations
   alembic upgrade head

   # Verify seed data loaded
   psql -d agenthub -c "SELECT COUNT(*) FROM base_tools;"  # Should return 5
   psql -d agenthub -c "SELECT COUNT(*) FROM output_formats;"  # Should return 4
   ```

2. **Environment Variables**:
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost:5432/agenthub"
   export REDIS_URL="redis://localhost:6379"
   export FERNET_KEY="[generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())']"
   export JWT_PUBLIC_KEY="[RS256 public key from auth provider]"
   ```

3. **Start Services**:
   ```bash
   # Start Redis
   redis-server

   # Start PostgreSQL (Docker example)
   docker run --name postgres-agenthub -e POSTGRES_PASSWORD=secret -p 5432:5432 -d postgres:15

   # Start FastAPI
   uvicorn main:app --reload --port 8000
   ```

---

## User Story 1: Business User Queries Customer Debt

### Goal
Verify end-to-end flow: user message → SupervisorAgent → AgentDebt → tool execution → formatted response

### Setup

1. **Create Test Tenant**:
   ```bash
   curl -X POST http://localhost:8000/api/admin/tenants \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test Corporation",
       "domain": "testcorp.local"
     }'
   # Save tenant_id from response
   ```

2. **Configure LLM Model for Tenant**:
   ```bash
   curl -X PATCH http://localhost:8000/api/admin/tenants/$TENANT_ID/llm \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "llm_model_id": "[gpt-4o-mini model ID from seed data]",
       "api_key": "sk-..."
     }'
   ```

3. **Create Debt Query Tool**:
   ```bash
   curl -X POST http://localhost:8000/api/admin/tools \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "get_customer_debt_by_mst",
       "base_tool_id": "[HTTP_GET base_tool_id from seed]",
       "config": {
         "endpoint": "https://erp.testcorp.local/api/customers/{customer_mst}/debt",
         "method": "GET",
         "timeout": 30
       },
       "input_schema": {
         "type": "object",
         "properties": {
           "customer_mst": {
             "type": "string",
             "description": "Customer tax code (MST) - 10 digits",
             "pattern": "^[0-9]{10}$"
           }
         },
         "required": ["customer_mst"]
       },
       "output_format_id": "[structured_json format_id from seed]"
     }'
   # Save tool_id
   ```

4. **Create AgentDebt**:
   ```bash
   curl -X POST http://localhost:8000/api/admin/agents \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "AgentDebt",
       "prompt_template": "You are AgentDebt, specialized in customer debt inquiries. Extract MST from user query, validate format, and use get_customer_debt_by_mst tool.",
       "llm_model_id": "[gpt-4o-mini model ID]",
       "tools": [
         {"tool_id": "[debt tool_id from step 3]", "priority": 1}
       ]
     }'
   # Save agent_id
   ```

5. **Enable Agent for Tenant**:
   ```bash
   curl -X PATCH http://localhost:8000/api/admin/tenants/$TENANT_ID/permissions \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "agents": [
         {"agent_id": "[AgentDebt agent_id]", "enabled": true}
       ],
       "tools": [
         {"tool_id": "[debt tool_id]", "enabled": true}
       ]
     }'
   ```

### Test Execution

**Test Case 1.1: Valid Debt Query**
```bash
curl -X POST http://localhost:8000/api/$TENANT_ID/chat \
  -H "Authorization: Bearer $USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the debt status for customer MST 0123456789?"
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "agent": "AgentDebt",
  "intent": "get_customer_debt",
  "data": {
    "customer_mst": "0123456789",
    "customer_name": "Acme Corporation",
    "total_debt": 125000000,
    "overdue_amount": 45000000,
    "currency": "VND"
  },
  "format": "structured_json",
  "renderer_hint": {
    "type": "table",
    "fields": ["customer_name", "total_debt", "overdue_amount"]
  },
  "metadata": {
    "session_id": "uuid",
    "duration_ms": "<2500"
  }
}
```

**Validation**:
- ✅ Response time < 2.5 seconds (FR-003, SC-001)
- ✅ SupervisorAgent correctly routed to AgentDebt (FR-008)
- ✅ Tool executed with JWT in Authorization header (FR-019, FR-015)
- ✅ Structured JSON format applied (FR-033)
- ✅ Session ID created (FR-004)

---

**Test Case 1.2: Invalid MST Format**
```bash
curl -X POST http://localhost:8000/api/$TENANT_ID/chat \
  -H "Authorization: Bearer $USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show debt for MST 123"
  }'
```

**Expected Response**:
```json
{
  "status": "error",
  "agent": "AgentDebt",
  "intent": "get_customer_debt",
  "data": {
    "message": "Invalid MST format. MST must be exactly 10 digits."
  },
  "format": "text"
}
```

---

**Test Case 1.3: Customer Not Found**
```bash
curl -X POST http://localhost:8000/api/$TENANT_ID/chat \
  -H "Authorization: Bearer $USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Debt for MST 9999999999"
  }'
```

**Expected Response**:
```json
{
  "status": "error",
  "agent": "AgentDebt",
  "data": {
    "message": "Customer MST 9999999999 not found in system."
  }
}
```

---

## User Story 2: Admin Configures New Agent

### Goal
Verify config-driven architecture: create agent → assign tools → enable for tenant → user can interact

### Test Execution

**Test Case 2.1: Create New Agent (AgentInventory)**
```bash
curl -X POST http://localhost:8000/api/admin/agents \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AgentInventory",
    "prompt_template": "You are AgentInventory, specialized in warehouse inventory queries.",
    "llm_model_id": "[gpt-4o-mini]",
    "tools": []
  }'
```

**Validation**:
- ✅ Agent created without code deployment (FR-042, SC-002)
- ✅ Returns agent_id (FR-042)

---

**Test Case 2.2: Update Agent Prompt**
```bash
curl -X PATCH http://localhost:8000/api/admin/agents/$AGENT_INVENTORY_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_template": "You are AgentInventory. Query warehouse stock levels and locations."
  }'
```

**Test Case 2.3: Assign Tools to Agent**
```bash
curl -X PATCH http://localhost:8000/api/admin/agents/$AGENT_INVENTORY_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tools": [
      {"tool_id": "[inventory_check_tool_id]", "priority": 1}
    ]
  }'
```

---

**Test Case 2.4: Enable for Tenant and Test**
```bash
# Enable agent
curl -X PATCH http://localhost:8000/api/admin/tenants/$TENANT_ID/permissions \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"agents": [{"agent_id": "$AGENT_INVENTORY_ID", "enabled": true}]}'

# Test user interaction
curl -X POST http://localhost:8000/api/$TENANT_ID/chat \
  -H "Authorization: Bearer $USER_JWT" \
  -d '{"message": "Check inventory for SKU ABC123"}'
```

**Validation**:
- ✅ Agent immediately available after permission grant (FR-044)
- ✅ No cache wait (manual reload if needed via /api/admin/agents/reload)
- ✅ SupervisorAgent can route to new agent (FR-008)
- ✅ Configuration time < 5 minutes (SC-002)

---

## User Story 3: Multi-Tenant Isolation

### Goal
Verify TenantA cannot access TenantB's data, configs, or conversations

### Setup

1. Create TenantA and TenantB
2. Configure different LLM models for each
3. Create agents enabled only for specific tenants

### Test Execution

**Test Case 3.1: Tenant A Cannot Access Tenant B's Sessions**
```bash
# TenantA user tries to access TenantB session
curl -X GET http://localhost:8000/api/$TENANT_B_ID/session/$TENANT_B_SESSION_ID \
  -H "Authorization: Bearer $TENANT_A_USER_JWT"
```

**Expected**: 403 Forbidden

---

**Test Case 3.2: Different LLM Models**
```bash
# TenantA uses GPT-4o-mini
curl -X POST http://localhost:8000/api/$TENANT_A_ID/chat \
  -H "Authorization: Bearer $TENANT_A_JWT" \
  -d '{"message": "test"}'
# Check logs: should show model=gpt-4o-mini

# TenantB uses Gemini
curl -X POST http://localhost:8000/api/$TENANT_B_ID/chat \
  -H "Authorization: Bearer $TENANT_B_JWT" \
  -d '{"message": "test"}'
# Check logs: should show model=gemini-1.5-pro
```

**Validation**:
- ✅ Each tenant uses their configured LLM model (FR-027, FR-029)
- ✅ API keys are tenant-specific (FR-024)

---

**Test Case 3.3: Redis Cache Namespace Isolation**
```bash
# Check Redis keys after both tenants make requests
redis-cli KEYS "agenthub:*"
```

**Expected**:
```
agenthub:tenant-a-uuid:cache:agent:agent-debt-id
agenthub:tenant-b-uuid:cache:agent:agent-debt-id
```

**Validation**:
- ✅ Cache keys namespaced by tenant_id (FR-023, SC-007)

---

**Test Case 3.4: Tool Execution with User JWT**
```bash
# Mock external API to capture Authorization header
# Send chat request
curl -X POST http://localhost:8000/api/$TENANT_ID/chat \
  -H "Authorization: Bearer $USER_JWT" \
  -d '{"message": "Check debt MST 0123456789"}'

# Verify external API received:
# Authorization: Bearer $USER_JWT (not system token)
```

**Validation**:
- ✅ User JWT passed to tools (FR-019, FR-015)
- ✅ No system-level JWT leakage (FR-041)

---

## User Story 4: Multi-Intent Detection (MVP Rejection)

### Test Execution

**Test Case 4.1: Multi-Intent Rejection**
```bash
curl -X POST http://localhost:8000/api/$TENANT_ID/chat \
  -H "Authorization: Bearer $USER_JWT" \
  -d '{
    "message": "What is the debt for MST 0123456789 and where is their latest shipment?"
  }'
```

**Expected Response**:
```json
{
  "status": "clarification_needed",
  "agent": "SupervisorAgent",
  "intent": "multi_intent_detected",
  "data": {
    "message": "I detected multiple questions. Please ask about debt or shipment separately so I can help you better.",
    "detected_intents": ["customer_debt", "shipment_tracking"]
  }
}
```

**Validation**:
- ✅ MVP rejects multi-intent (FR-010a, clarification decision)

---

## User Story 7: Session Management

### Test Execution

**Test Case 7.1: Multi-Turn Conversation**
```bash
# Message 1 (creates session)
RESPONSE=$(curl -X POST http://localhost:8000/api/$TENANT_ID/chat \
  -H "Authorization: Bearer $USER_JWT" \
  -d '{"message": "What is the debt for MST 0123456789?"}')
SESSION_ID=$(echo $RESPONSE | jq -r '.metadata.session_id')

# Message 2 (follow-up in same session)
curl -X POST http://localhost:8000/api/$TENANT_ID/chat \
  -H "Authorization: Bearer $USER_JWT" \
  -d "{\"message\": \"What about their payment history?\", \"session_id\": \"$SESSION_ID\"}"
```

**Expected**: Agent references previous query context (customer MST 0123456789)

**Validation**:
- ✅ Session created on first message (FR-048)
- ✅ Follow-up uses same session (FR-004)
- ✅ Context maintained across messages (FR-015a)

---

**Test Case 7.2: List User Sessions**
```bash
curl -X GET "http://localhost:8000/api/$TENANT_ID/session?limit=20" \
  -H "Authorization: Bearer $USER_JWT"
```

**Expected**: List of sessions for current user

---

**Test Case 7.3: Get Session Details**
```bash
curl -X GET http://localhost:8000/api/$TENANT_ID/session/$SESSION_ID \
  -H "Authorization: Bearer $USER_JWT"
```

**Expected**: Full message history for session

**Validation**:
- ✅ All messages retrieved chronologically (FR-050)
- ✅ Metadata includes agent_used, tool_calls (FR-047)

---

## Performance & Load Testing

### Response Time (SC-001)
```bash
# Run 100 concurrent requests
for i in {1..100}; do
  (curl -X POST http://localhost:8000/api/$TENANT_ID/chat \
    -H "Authorization: Bearer $USER_JWT" \
    -d '{"message": "Debt MST 0123456789"}' \
    -w "Time: %{time_total}s\n" -o /dev/null) &
done
wait

# Check: 95% of requests < 2.5s
```

### Cache Hit Rate (SC-008)
```bash
# Monitor Redis metrics
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses
# Calculate hit rate: hits / (hits + misses)
# Target: >90%
```

### Multi-Tenant Concurrency (SC-003)
```bash
# Simulate 10 tenants, 10 users each, simultaneous requests
# Total: 100 concurrent users
# Monitor response times remain <2.5s
```

---

## Troubleshooting

### Issue: 401 Unauthorized
- Check JWT expiration: `jwt decode $TOKEN`
- Verify RS256 signature with public key
- Confirm tenant_id claim matches path parameter

### Issue: Agent Not Routing Correctly
- Check agent permissions: `GET /api/admin/tenants/$TENANT_ID/permissions`
- Verify cache: `redis-cli GET agenthub:$TENANT_ID:cache:permissions:agents`
- Force reload: `POST /api/admin/agents/reload`

### Issue: Tool Execution Fails
- Check tool config in database: `SELECT * FROM tool_configs WHERE tool_id='...'`
- Verify external API accessibility
- Check logs for JWT token presence in tool execution

---

**Quickstart Status**: ✅ Complete
**Ready for**: Implementation & Testing
