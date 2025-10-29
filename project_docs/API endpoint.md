# 📘 API ENDPOINT SPECIFICATION — AGENTHUB CHATBOT

## 1. Tổng quan
Hệ thống API cung cấp các endpoint để:
- Gửi và nhận tin nhắn giữa người dùng và agents.
- Quản lý cấu hình agents, tools, tenants.
- Theo dõi logs, hội thoại và metrics.

Framework: **FastAPI (async)**  
Auth: **JWT Bearer Token (RS256)**  
Format: **JSON (UTF-8)**  
Response: **Unified JSON Structure**

---

## 2. Authentication & Context
| Phương thức | Mô tả |
|--------------|------|
| **JWT Validation** | Mọi endpoint cần header `Authorization: Bearer <token>` |
| **Tenant Context** | `tenant_id` được xác định từ JWT hoặc URL path `/api/{tenant_id}/...` |
| **User Context** | Thông tin người dùng lấy từ payload JWT: `{sub, email, roles}` |

---

## 3. API Endpoint Danh Mục

### 3.1 Chat Interaction
| Endpoint | Method | Mô tả | Input | Output |
|-----------|---------|-------|--------|---------|
| `/api/{tenant_id}/chat` | `POST` | Gửi tin nhắn từ user → SupervisorAgent | `{ message: str, session_id?: str }` | JSON output từ agent |
| `/api/{tenant_id}/session` | `GET` | Lấy danh sách session hiện tại | Query params: user_id | `[session_id, agent_id, created_at]` |
| `/api/{tenant_id}/session/{id}` | `GET` | Lấy chi tiết 1 session | session_id | `{ messages: [...] }` |

---

### 3.2 Agent Management
| Endpoint | Method | Mô tả | Input | Output |
|-----------|---------|-------|--------|---------|
| `/api/admin/agents` | `GET` | Danh sách agents đang hoạt động | — | `[AgentConfig]` |
| `/api/admin/agents/{id}` | `GET` | Lấy chi tiết 1 agent | agent_id | `{ name, prompt, tools, model }` |
| `/api/admin/agents` | `POST` | Tạo mới agent | `{ name, prompt, llm_model_id, tools: [] }` | `{ agent_id }` |
| `/api/admin/agents/{id}` | `PATCH` | Cập nhật agent | `{ prompt?, tools?, model? }` | `{ success: true }` |
| `/api/admin/agents/reload` | `POST` | Reload lại cache agent runtime | `{ tenant_id? }` | `{ reloaded_agents: [...] }` |

---

### 3.3 Tool Management
| Endpoint | Method | Mô tả | Input | Output |
|-----------|---------|-------|--------|---------|
| `/api/admin/tools` | `GET` | Danh sách tools có sẵn | — | `[ToolConfig]` |
| `/api/admin/tools/{id}` | `GET` | Lấy chi tiết 1 tool | tool_id | `{ name, config, schema }` |
| `/api/admin/tools` | `POST` | Tạo tool mới | `{ name, base_tool_id, config, input_schema }` | `{ tool_id }` |
| `/api/admin/tools/{id}` | `PATCH` | Cập nhật tool | `{ config?, schema?, format? }` | `{ success: true }` |

---

### 3.4 Tenant Management
| Endpoint | Method | Mô tả | Input | Output |
|-----------|---------|-------|--------|---------|
| `/api/admin/tenants` | `GET` | Danh sách tenants | — | `[Tenant]` |
| `/api/admin/tenants/{id}` | `GET` | Chi tiết tenant | tenant_id | `{ name, domain, status }` |
| `/api/admin/tenants/{id}/agents` | `GET` | Agents khả dụng cho tenant | — | `[available_agents]` |
| `/api/admin/tenants/{id}/permissions` | `PATCH` | Cập nhật quyền agent/tool cho tenant | `{ agents: [], tools: [] }` | `{ success: true }` |

---

### 3.5 LLM Configuration
| Endpoint | Method | Mô tả | Input | Output |
|-----------|---------|-------|--------|---------|
| `/api/admin/llm/models` | `GET` | Danh sách models khả dụng | — | `[LLMModel]` |
| `/api/admin/llm/providers` | `GET` | Danh sách provider | — | `[Provider]` |
| `/api/admin/tenants/{id}/llm` | `GET` | Lấy model tenant đang dùng | tenant_id | `{ model, provider, key_status }` |
| `/api/admin/tenants/{id}/llm` | `PATCH` | Gán model cho tenant | `{ llm_model_id, api_key? }` | `{ success: true }` |

---

### 3.6 Monitoring & Logs
| Endpoint | Method | Mô tả | Input | Output |
|-----------|---------|-------|--------|---------|
| `/api/admin/logs/conversations` | `GET` | Lấy log hội thoại | Filter: tenant, agent | `[session_id, message_count, timestamp]` |
| `/api/admin/logs/tools` | `GET` | Theo dõi tool usage | Filter: tenant, tool | `[tool_name, call_count, latency]` |
| `/api/admin/metrics` | `GET` | Tổng hợp số liệu (API usage, LLM cost, latency) | — | `{ cost, count, avg_latency }` |

---

## 4. Response Structure Chuẩn
```json
{
  "status": "success",
  "agent": "AgentDebt",
  "intent": "get_customer_debt",
  "data": { ... },
  "format": "structured_json",
  "renderer_hint": { "type": "table", "fields": ["mst", "total_debt"] },
  "metadata": {
    "session_id": "uuid",
    "duration_ms": 1234
  }
}
```

---

## 5. Error Handling
| Mã lỗi | Nguyên nhân | Phản hồi |
|---------|-------------|----------|
| 400 | Input không hợp lệ | `{ status: "error", message: "Invalid input" }` |
| 401 | JWT hết hạn hoặc sai | `{ status: "error", message: "Unauthorized" }` |
| 403 | Tenant không có quyền dùng agent/tool | `{ status: "error", message: "Forbidden" }` |
| 404 | Không tìm thấy agent/tool | `{ status: "error", message: "Not found" }` |
| 500 | Lỗi hệ thống | `{ status: "error", message: "Internal server error" }` |

---

## 6. Quy ước naming & versioning
| Quy tắc | Ví dụ |
|----------|--------|
| Endpoint dùng prefix `/api/{tenant_id}/` | `/api/tenant-uuid/chat` |
| Admin endpoint dùng `/api/admin/` | `/api/admin/agents` |
| Version hóa theo `/v1/` nếu cần backward compat | `/api/v1/chat` |
| Response thống nhất field `status` | `success` / `error` |

---

## 7. Security & Audit
- Mọi request cần JWT hợp lệ (RS256, 24h TTL)
- API key LLM được mã hóa (Fernet)
- Log mọi call tool / agent (tenant_id, agent_name, duration_ms)
- Rate limit theo tenant và user (Redis token bucket)

---

## 8. Metrics & Monitoring
| Metric | Mô tả |
|---------|--------|
| `agent_calls_total` | Tổng số lần gọi agent |
| `tool_calls_total` | Tổng số tool được gọi |
| `tool_avg_latency` | Độ trễ trung bình mỗi tool |
| `llm_cost_total` | Tổng chi phí token LLM |
| `tenant_usage` | Thống kê usage per-tenant |

---

## 9. Future Extension
| Mục tiêu | Hướng phát triển |
|-----------|------------------|
| **Async multi-agent pipeline** | Parallel tool execution và agent delegation |
| **OAuth2 integration** | Cho phép login qua hệ thống SSO doanh nghiệp |
| **OpenAPI auto-docs** | Tự động sinh spec bằng FastAPI schema |
| **Fine-grained permissions** | Role-based access trên từng API endpoint |

---

**Tài liệu này mô tả chi tiết endpoint chuẩn cho backend AgentHub Chatbot** — đảm bảo đồng bộ giữa nhóm Backend, AI, và Frontend trong toàn hệ thống.

