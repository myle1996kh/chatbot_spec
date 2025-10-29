"""
Seed test data for AgentHub with tenants, tools, and agents.

This script creates:
- Test tenant
- Base tools (HTTPGetTool for debt queries)
- Tool configurations (get_customer_debt_by_mst, get_salesman_debt)
- AgentDebt with JSON prompt
- Tool assignments to agent
"""
import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.config import get_db

# Import ALL models to ensure SQLAlchemy relationships are properly registered
from src.models.tenant import Tenant
from src.models.session import ChatSession
from src.models.message import Message
from src.models.llm_model import LLMModel
from src.models.tenant_llm_config import TenantLLMConfig
from src.models.base_tool import BaseTool
from src.models.output_format import OutputFormat
from src.models.tool import ToolConfig
from src.models.agent import AgentConfig, AgentTools
from src.models.permissions import TenantAgentPermission, TenantToolPermission

from src.utils.logging import get_logger

logger = get_logger(__name__)


def seed_test_data():
    """Seed comprehensive test data for AgentHub."""

    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        print("🌱 Starting test data seeding...")

        # ====================================================================
        # 1. CREATE TEST TENANT
        # ====================================================================
        print("\n📦 Creating test tenant...")

        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            tenant_id=tenant_id,
            name="Test Corporation",
            domain="testcorp.com",  # Unique domain for tenant
            status="active",
        )
        db.add(tenant)
        db.flush()

        print(f"✅ Created tenant: {tenant.name} (ID: {tenant_id})")

        # ====================================================================
        # 2. CREATE/GET LLM MODEL
        # ====================================================================
        print("\n🤖 Setting up LLM model...")

        # Get existing LLM model from seed data (created by Alembic migration)
        llm_model = db.query(LLMModel).filter(
            LLMModel.provider == "openrouter",
            LLMModel.model_name == "openai/gpt-4o-mini"
        ).first()

        if not llm_model:
            # If not exists, create it (NOTE: No api_key in LLMModel - that goes in TenantLLMConfig)
            llm_model = LLMModel(
                llm_model_id=str(uuid.uuid4()),
                provider="openrouter",
                model_name="openai/gpt-4o-mini",
                context_window=128000,
                cost_per_1k_input_tokens=0.00015,
                cost_per_1k_output_tokens=0.0006,
                is_active=True,
                capabilities={"vision": False, "function_calling": True},
            )
            db.add(llm_model)
            db.flush()
            print(f"✅ Created LLM model: {llm_model.model_name}")
        else:
            print(f"✅ Using existing LLM model: {llm_model.model_name}")

        # ====================================================================
        # 3. CREATE BASE TOOL (HTTPGetTool)
        # ====================================================================
        print("\n🔧 Creating base tools...")

        base_tool_http_get = db.query(BaseTool).filter(
            BaseTool.handler_class == "tools.http.HTTPGetTool"
        ).first()

        if not base_tool_http_get:
            base_tool_http_get = BaseTool(
                base_tool_id=str(uuid.uuid4()),
                name="HTTPGetTool",
                handler_class="tools.http.HTTPGetTool",
                description="HTTP GET request tool for API calls",
                default_config={
                    "timeout": 30,
                    "verify_ssl": True,
                },
            )
            db.add(base_tool_http_get)
            db.flush()
            print(f"✅ Created base tool: HTTPGetTool")
        else:
            print(f"✅ Using existing base tool: HTTPGetTool")

        # ====================================================================
        # 4. CREATE TOOL CONFIGURATIONS
        # ====================================================================
        print("\n🛠️  Creating tool configurations...")

        # Tool 1: get_customer_debt_by_mst
        tool_debt_by_mst_id = str(uuid.uuid4())
        tool_debt_by_mst = ToolConfig(
            tool_id=tool_debt_by_mst_id,
            base_tool_id=base_tool_http_get.base_tool_id,
            name="get_customer_debt_by_mst",
            description="Retrieve customer debt information by tax code (MST). Returns account receivable details including outstanding balance, payment history, and aging analysis.",
            config={
                "base_url": "https://uat-accounting-api-efms.logtechub.com",
                "endpoint": "/api/v1/vi/AccountReceivable/GetReceivableByTaxCode/{tax_code}",
                "method": "GET",
                "auth_type": "bearer",
                "timeout": 30,
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            },
            input_schema={
                "type": "object",
                "properties": {
                    "tax_code": {
                        "type": "string",
                        "description": "Customer tax code (MST), 10-13 digits",
                        "pattern": "^[0-9]{10,13}$",
                        "minLength": 10,
                        "maxLength": 13,
                    }
                },
                "required": ["tax_code"]
            },
            is_active=True,
        )
        db.add(tool_debt_by_mst)

        print(f"✅ Created tool: get_customer_debt_by_mst")

        # Tool 2: get_salesman_debt
        tool_salesman_debt_id = str(uuid.uuid4())
        tool_salesman_debt = ToolConfig(
            tool_id=tool_salesman_debt_id,
            base_tool_id=base_tool_http_get.base_tool_id,
            name="get_salesman_debt",
            description="Retrieve debt information for all customers assigned to a specific salesman. Returns aggregated receivables and customer list with outstanding balances.",
            config={
                "base_url": "https://uat-accounting-api-efms.logtechub.com",
                "endpoint": "/api/v1/vi/AccountReceivable/GetReceivableBySalesman/{salesman}",
                "method": "GET",
                "auth_type": "bearer",
                "timeout": 30,
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            },
            input_schema={
                "type": "object",
                "properties": {
                    "salesman": {
                        "type": "string",
                        "description": "Salesman code or identifier",
                        "minLength": 1,
                        "maxLength": 50,
                    }
                },
                "required": ["salesman"]
            },
            is_active=True,
        )
        db.add(tool_salesman_debt)

        print(f"✅ Created tool: get_salesman_debt")

        db.flush()

        # ====================================================================
        # 5. CREATE AGENTDEBT WITH JSON PROMPT
        # ====================================================================
        print("\n🤖 Creating AgentDebt with JSON prompt...")

        agent_debt_id = str(uuid.uuid4())

        # JSON-structured prompt for AgentDebt
        agent_prompt = {
            "role": "debt_specialist",
            "identity": {
                "name": "AgentDebt",
                "title": "Customer Debt & Receivables Specialist",
                "organization": "Accounting Department"
            },
            "capabilities": [
                "Query customer debt by tax code (MST)",
                "Retrieve salesman-specific receivables",
                "Analyze account aging",
                "Provide payment recommendations"
            ],
            "instructions": {
                "primary_objective": "Assist users with customer debt inquiries by retrieving accurate receivable information from the accounting system.",
                "query_handling": [
                    "When user asks about a specific customer's debt, use the tax code (MST) to query get_customer_debt_by_mst tool",
                    "When user asks about a salesman's customers or portfolio, use get_salesman_debt tool",
                    "If tax code format is invalid, politely request a valid 10-13 digit tax code",
                    "If salesman code is missing, ask for the salesman identifier"
                ],
                "response_format": [
                    "Present debt information in a clear, structured format",
                    "Include key metrics: total outstanding, overdue amount, aging breakdown",
                    "Highlight urgent items (e.g., over 90 days overdue)",
                    "Provide actionable insights when relevant"
                ],
                "tone": "Professional, helpful, and detail-oriented. Use clear financial terminology."
            },
            "examples": [
                {
                    "user_query": "What is the debt for customer with MST 0123456789?",
                    "action": "Use get_customer_debt_by_mst with tax_code='0123456789'",
                    "response_format": "Present total outstanding balance, aging analysis, and payment status"
                },
                {
                    "user_query": "Show me receivables for salesman JOHN_DOE",
                    "action": "Use get_salesman_debt with salesman='JOHN_DOE'",
                    "response_format": "List customers, individual balances, and total portfolio receivables"
                }
            ],
            "constraints": [
                "Only use provided tools - do not make assumptions about debt amounts",
                "Maintain customer confidentiality - only share data with authorized users",
                "If API returns error, explain issue clearly and suggest next steps",
                "Never fabricate financial data"
            ],
            "error_handling": {
                "invalid_tax_code": "Please provide a valid tax code (MST) with 10-13 digits.",
                "customer_not_found": "No debt records found for the provided tax code. Please verify the MST is correct.",
                "salesman_not_found": "No receivables found for the specified salesman. Please check the salesman code.",
                "api_error": "Unable to retrieve debt information at this time. Please try again later or contact support."
            }
        }

        # Convert JSON prompt to string for storage
        import json
        agent_prompt_str = json.dumps(agent_prompt, indent=2)

        agent_debt = AgentConfig(
            agent_id=agent_debt_id,
            llm_model_id=llm_model.llm_model_id,
            name="AgentDebt",
            description="Specialized agent for customer debt queries, payment history, account balances, and receivables management",
            prompt_template=agent_prompt_str,  # JSON prompt as string
            is_active=True,
        )
        db.add(agent_debt)
        db.flush()

        print(f"✅ Created agent: AgentDebt with JSON prompt")

        # ====================================================================
        # 6. ASSIGN TOOLS TO AGENT
        # ====================================================================
        print("\n🔗 Assigning tools to AgentDebt...")

        # Assign get_customer_debt_by_mst (priority 1)
        agent_tool_1 = AgentTools(
            agent_id=agent_debt_id,
            tool_id=tool_debt_by_mst_id,
            priority=1,
        )
        db.add(agent_tool_1)

        # Assign get_salesman_debt (priority 2)
        agent_tool_2 = AgentTools(
            agent_id=agent_debt_id,
            tool_id=tool_salesman_debt_id,
            priority=2,
        )
        db.add(agent_tool_2)

        print(f"✅ Assigned 2 tools to AgentDebt")

        # ====================================================================
        # 7. COMMIT ALL CHANGES
        # ====================================================================
        db.commit()

        print("\n" + "="*60)
        print("🎉 TEST DATA SEEDING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\n📊 Summary:")
        print(f"  • Tenant ID: {tenant_id}")
        print(f"  • Tenant Name: {tenant.name}")
        print(f"  • LLM Model: {llm_model.model_name}")
        print(f"  • Agent: AgentDebt (ID: {agent_debt_id})")
        print(f"  • Tools: get_customer_debt_by_mst, get_salesman_debt")
        print(f"\n🧪 Test with:")
        print(f"  • Tax Code Example: 0123456789012")
        print(f"  • Salesman Example: JOHN_DOE")
        print(f"\n📝 API Endpoint: POST http://localhost:8000/api/{tenant_id}/chat")
        print(f"  Headers: X-Tenant-ID: {tenant_id}")
        print(f"  Body: {{")
        print(f'    "user_id": "test_user_001",')
        print(f'    "message": "What is the debt for customer with MST 0123456789012?",')
        print(f'    "metadata": {{"jwt_token": "your_jwt_token_here"}}')
        print(f"  }}")
        print("\n" + "="*60)

        return {
            "tenant_id": tenant_id,
            "agent_id": agent_debt_id,
            "tool_ids": [tool_debt_by_mst_id, tool_salesman_debt_id],
        }

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding data: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  AgentHub Test Data Seeder")
    print("="*60)

    result = seed_test_data()

    print(f"\n✅ Seeding complete!")
    print(f"📋 Use these IDs for testing:")
    print(f"   Tenant ID: {result['tenant_id']}")
    print(f"   Agent ID: {result['agent_id']}")
    print(f"   Tool IDs: {result['tool_ids']}")
