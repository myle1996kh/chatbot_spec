# AgentHub Testing Guide

Complete guide for seeding test data and testing the AgentHub chatbot system.

---

## Prerequisites

1. **Database Setup**: PostgreSQL, Redis, and ChromaDB must be running
2. **Environment**: Virtual environment activated
3. **Database Migrated**: Run `alembic upgrade head`

---

## Step 1: Seed Test Data

The seed script creates a complete test environment with:
- ✅ Test tenant
- ✅ LLM model configuration (OpenRouter GPT-4o-mini)
- ✅ Base tools (HTTPGetTool)
- ✅ Two debt query tools
- ✅ AgentDebt with JSON-structured prompt
- ✅ Tool assignments

### Run the Seed Script

```bash
cd backend
PYTHONPATH=. ./venv/Scripts/python.exe seed_test_data.py
```

### Expected Output

```
====================================================================
  AgentHub Test Data Seeder
====================================================================

🌱 Starting test data seeding...

📦 Creating test tenant...
✅ Created tenant: Test Corporation (ID: <tenant_id>)

🤖 Setting up LLM model...
✅ Using existing LLM model: openai/gpt-4o-mini

🔧 Creating base tools...
✅ Using existing base tool: HTTPGetTool

🛠️  Creating tool configurations...
✅ Created tool: get_customer_debt_by_mst
✅ Created tool: get_salesman_debt

🤖 Creating AgentDebt with JSON prompt...
✅ Created agent: AgentDebt with JSON prompt

🔗 Assigning tools to AgentDebt...
✅ Assigned 2 tools to AgentDebt

====================================================================
🎉 TEST DATA SEEDING COMPLETED SUCCESSFULLY!
====================================================================

📊 Summary:
  • Tenant ID: <your_tenant_id>
  • Tenant Name: Test Corporation
  • LLM Model: openai/gpt-4o-mini
  • Agent: AgentDebt (ID: <agent_id>)
  • Tools: get_customer_debt_by_mst, get_salesman_debt
```

**⚠️ IMPORTANT**: Copy the `Tenant ID` from the output - you'll need it for testing!

---

## Step 2: Test the Chat API

### Option A: Using the Python Test Script

The test script includes 5 pre-configured test cases:

```bash
cd backend
PYTHONPATH=. ./venv/Scripts/python.exe test_chat_api.py <your_tenant_id>
```

Replace `<your_tenant_id>` with the ID from Step 1.

### Test Cases Included

1. **Query customer debt by tax code**
   - Message: "What is the debt for customer with MST 0123456789012?"
   - Expected: AgentDebt uses `get_customer_debt_by_mst` tool

2. **Query salesman receivables**
   - Message: "Show me all receivables for salesman JOHN_DOE"
   - Expected: AgentDebt uses `get_salesman_debt` tool

3. **Invalid tax code format**
   - Message: "What is the debt for MST 123?"
   - Expected: Agent responds with validation error

4. **General greeting**
   - Message: "Hello, can you help me with customer debts?"
   - Expected: Agent acknowledges and offers assistance

5. **Multi-intent query**
   - Message: "What is the debt for MST 0123456789012 AND what about salesman JANE_DOE?"
   - Expected: SupervisorAgent detects multiple intents and requests clarification

---

### Option B: Using cURL

**Basic Chat Request:**

```bash
curl -X POST http://localhost:8000/api/<tenant_id>/chat \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: <tenant_id>" \
  -d '{
    "user_id": "test_user_001",
    "message": "What is the debt for customer with MST 0123456789012?",
    "metadata": {
      "jwt_token": "test_token_for_demo"
    }
  }'
```

**With Session Continuation:**

```bash
curl -X POST http://localhost:8000/api/<tenant_id>/chat \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: <tenant_id>" \
  -d '{
    "user_id": "test_user_001",
    "session_id": "<session_id_from_previous_response>",
    "message": "What about salesman JOHN_DOE?",
    "metadata": {
      "jwt_token": "test_token_for_demo"
    }
  }'
```

---

### Option C: Using Postman

1. **Import Settings:**
   - Method: `POST`
   - URL: `http://localhost:8000/api/<tenant_id>/chat`

2. **Headers:**
   ```
   Content-Type: application/json
   X-Tenant-ID: <your_tenant_id>
   ```

3. **Body (JSON):**
   ```json
   {
     "user_id": "test_user_001",
     "message": "What is the debt for customer with MST 0123456789012?",
     "metadata": {
       "jwt_token": "test_token_for_demo"
     }
   }
   ```

---

## Step 3: Verify Results

### Expected Successful Response Structure

```json
{
  "session_id": "uuid-of-session",
  "message_id": "uuid-of-message",
  "response": {
    "message": "Customer debt information...",
    "data": {...}
  },
  "agent": "AgentDebt",
  "intent": "query",
  "format": "structured_json",
  "renderer_hint": {},
  "metadata": {
    "duration_ms": 1234.56,
    "status": "success",
    "agent_id": "uuid",
    "tenant_id": "uuid"
  }
}
```

### Check Server Logs

Look for these log events:
```
supervisor_routing (tenant_id, detected_agent)
agent_debt_invoked (tenant_id)
tool_executed (tool_name, tenant_id)
chat_response_completed (duration_ms, status)
```

---

## Tools Configuration Reference

### Tool 1: get_customer_debt_by_mst

**Purpose**: Retrieve customer debt by tax code (MST)

**Configuration:**
- Base URL: `https://uat-accounting-api-efms.logtechub.com`
- Endpoint: `/api/v1/vi/AccountReceivable/GetReceivableByTaxCode/{tax_code}`
- Method: GET
- Auth: Bearer token (injected from JWT)

**Input Schema:**
```json
{
  "tax_code": "string (10-13 digits)"
}
```

**Example:**
```
Message: "What is the debt for customer with MST 0123456789012?"
```

---

### Tool 2: get_salesman_debt

**Purpose**: Retrieve aggregated debt for all customers of a salesman

**Configuration:**
- Base URL: `https://uat-accounting-api-efms.logtechub.com`
- Endpoint: `/api/v1/vi/AccountReceivable/GetReceivableBySalesman/{salesman}`
- Method: GET
- Auth: Bearer token (injected from JWT)

**Input Schema:**
```json
{
  "salesman": "string (1-50 characters)"
}
```

**Example:**
```
Message: "Show me receivables for salesman JOHN_DOE"
```

---

## AgentDebt JSON Prompt Structure

The agent uses a JSON-structured prompt for better consistency:

```json
{
  "role": "debt_specialist",
  "identity": {
    "name": "AgentDebt",
    "title": "Customer Debt & Receivables Specialist"
  },
  "capabilities": [
    "Query customer debt by tax code (MST)",
    "Retrieve salesman-specific receivables",
    "Analyze account aging",
    "Provide payment recommendations"
  ],
  "instructions": {
    "primary_objective": "...",
    "query_handling": [...],
    "response_format": [...],
    "tone": "Professional, helpful, and detail-oriented"
  },
  "examples": [...],
  "constraints": [...],
  "error_handling": {...}
}
```

---

## Troubleshooting

### Issue: "Tenant not found"
- **Cause**: Incorrect tenant_id in URL or header
- **Solution**: Verify tenant_id from seed script output

### Issue: "Tool execution failed"
- **Cause**: External API unavailable or authentication failure
- **Solution**:
  1. Check API endpoint is accessible
  2. Verify JWT token is valid
  3. Check server logs for detailed error

### Issue: "Agent not found"
- **Cause**: AgentDebt not created or inactive
- **Solution**: Re-run seed script

### Issue: Server not responding
- **Cause**: Server not running or port conflict
- **Solution**:
  1. Check server is running: `curl http://localhost:8000/health`
  2. View server logs
  3. Restart server if needed

---

## Advanced Testing

### Test Knowledge Base (RAG)

1. **Create AgentAnalysis** (if not exists)
2. **Ingest documents:**
   ```bash
   curl -X POST http://localhost:8000/api/admin/tenants/<tenant_id>/knowledge \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <admin_jwt>" \
     -d '{
       "documents": [
         "Our refund policy allows returns within 30 days...",
         "Shipping takes 3-5 business days for domestic orders..."
       ],
       "metadatas": [
         {"source": "refund_policy.pdf"},
         {"source": "shipping_policy.pdf"}
       ]
     }'
   ```

3. **Query knowledge base:**
   ```bash
   curl -X POST http://localhost:8000/api/<tenant_id>/chat \
     -H "Content-Type: application/json" \
     -H "X-Tenant-ID: <tenant_id>" \
     -d '{
       "user_id": "test_user_001",
       "message": "What is our refund policy?",
       "metadata": {"jwt_token": "test_token"}
     }'
   ```

---

## API Endpoints Reference

### Chat Endpoint
- **POST** `/api/{tenant_id}/chat`
- Create or continue a chat session

### Session Management
- **GET** `/api/{tenant_id}/sessions` - List sessions
- **GET** `/api/{tenant_id}/sessions/{session_id}` - Get session details
- **GET** `/api/{tenant_id}/sessions/{session_id}/messages` - Get messages

### Admin Endpoints (Require Admin JWT)
- **GET** `/api/admin/agents` - List agents
- **POST** `/api/admin/agents` - Create agent
- **GET** `/api/admin/tools` - List tools
- **POST** `/api/admin/tools` - Create tool
- **POST** `/api/admin/tenants/{tenant_id}/knowledge` - Ingest documents

---

## Next Steps

1. ✅ Seed test data
2. ✅ Test chat API with provided test cases
3. ✅ Verify tool execution in logs
4. ✅ Test session continuation
5. ✅ Test multi-intent detection
6. 🚀 Integrate with your frontend
7. 🚀 Add more agents and tools as needed

---

## Support

For issues or questions:
1. Check server logs: `tail -f logs/app.log`
2. Review database state: `psql -d chatbot_db`
3. Verify Docker services: `docker-compose ps`

---

**Happy Testing! 🎉**
