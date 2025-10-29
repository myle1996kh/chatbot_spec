# AgentHub Chatbot Constitution

## Core Principles

### I. Configuration Over Code
Mọi hành vi, công cụ, và agent phải được cấu hình qua cơ sở dữ liệu, không hard-code.  
Cấu hình bao gồm: prompts, tools, model LLM, output format, và tenant permissions.  
Hệ thống chỉ load các cấu hình này tại runtime thông qua factory + registry.

### II. Multi-Agent & Multi-Tenant Architecture
Hệ thống được thiết kế để mỗi tenant có tập hợp agent riêng biệt (ví dụ: Debt, Shipment, Analysis).  
Mỗi Agent là một domain nghiệp vụ độc lập, có công cụ, prompt và LLM riêng.  
Không chia sẻ state giữa tenants; tất cả dữ liệu, cache và memory đều được namespace theo `tenant_id`.

### III. LangChain-First Orchestration
Toàn bộ agent, tool, và supervisor phải được triển khai dựa trên LangChain framework.  
Cấu trúc reasoning sử dụng `AgentExecutor`, tool dùng `StructuredTool`, và routing dùng `SupervisorAgent`.  
Không được gọi HTTP/API trực tiếp trong business logic – chỉ thông qua tool abstractions.

### IV. Security & Token Isolation (NON-NEGOTIABLE)
Mọi request đều yêu cầu JWT hợp lệ (RS256).  
Khi Agent gọi Tool, phải truyền context `user_token` vào headers (`Authorization: Bearer <token>`).  
Các khóa API LLM (OpenAI, Gemini, v.v.) được mã hóa bằng Fernet, lưu trong DB, và chỉ giải mã tại runtime.

### V. Unified Output Format & Observability
Tất cả Agents/Tools phải trả kết quả theo định dạng chuẩn hóa trong bảng `output_formats`.  
Logging sử dụng JSON structured logs.  
Mọi tool call và agent invocation phải được theo dõi bằng metrics: `latency`, `usage_count`, `token_cost`.

---

## System Constraints

### A. Performance & Scalability
- Response time < 2.5s cho các truy vấn chuẩn (không bao gồm RAG).  
- Redis cache TTL 1 giờ cho cấu hình Agent.  
- 100+ tenants hoạt động song song mà không ảnh hưởng đến độ trễ.  
- PostgreSQL connection pool tối thiểu 20.

### B. Security Standards
- JWT xác thực chữ ký RS256, TTL 24h.  
- Redis namespace theo tenant (`agenthub:{tenant_id}:cache`).  
- API key mã hóa bằng Fernet và không bao giờ log ra ngoài.  
- Logs chứa PII phải được ẩn hoặc hash trước khi lưu.

### C. Technology Stack
| Thành phần | Công nghệ |
|-------------|------------|
| **Backend** | FastAPI (async) |
| **AI Framework** | LangChain 0.3+ |
| **Cache** | Redis 7.x |
| **Database** | PostgreSQL 15 |
| **Vector DB** | ChromaDB |
| **Auth** | JWT RS256 + Fernet |
| **Deployment** | Docker Compose + Alembic |

---

## Development Workflow & Quality Gates

### A. Test-Driven Implementation
- Mọi module phải có test coverage ≥ 80%.  
- Tests phải mô phỏng conversation flow end-to-end.  
- Integration tests bao gồm: tool execution, agent invocation, JWT validation.

### B. Code Review & Documentation
- Mỗi PR yêu cầu ít nhất 1 reviewer.  
- Phải có mô tả đầy đủ trong docstring và cập nhật README nếu thêm module mới.  
- Prompt và config thay đổi phải được ghi nhận trong changelog.

### C. Deployment Rules
- Không deploy trực tiếp cấu hình trong code.  
- Chỉ sử dụng dữ liệu từ DB hoặc environment variables.  
- Mọi migration phải có rollback script và test sandbox trước khi merge.

---

## Governance
- **Constitution này có hiệu lực cao nhất**: mọi thay đổi code hoặc quy trình đều phải tuân thủ các nguyên tắc trên.  
- Thay đổi cấu trúc kiến trúc hoặc nguyên tắc core phải được phê duyệt bởi nhóm kiến trúc (Architecture Council).  
- Mọi PR/review phải xác nhận compliance với 5 Core Principles.  
- Amendments phải có bản ghi “Version Diff” và được cập nhật tại `CONSTITUTION_CHANGELOG.md`.

**Version**: 1.0.0 | **Ratified**: 2025-10-28 | **Last Amended**: 2025-10-28

