"""
Script to add permissions for tenant_id: 2628802d-1dff-4a98-9325-704433c5d3ab 
to access all existing LLM models, Agents & Tools in the system.
"""
import uuid
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

def add_tenant_permissions():
    """Add permissions for tenant_id 2628802d-1dff-4a98-9325-704433c5d3ab to access all existing resources."""
    
    target_tenant_id = "2628802d-1dff-4a98-9325-704433c5d3ab"
    
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        print("🔧 Starting to add permissions for tenant: 2628802d-1dff-4a98-9325-704433c5d3ab")
        
        # Check if tenant exists
        tenant = db.query(Tenant).filter(Tenant.tenant_id == uuid.UUID(target_tenant_id)).first()
        if not tenant:
            # Create the tenant if it doesn't exist
            print(f"⚠️ Tenant {target_tenant_id} does not exist. Creating it...")
            tenant = Tenant(
                tenant_id=target_tenant_id,
                name="Test Tenant for Chat API",
                domain="test-chat-api.com",
                status="active"
            )
            db.add(tenant)
            db.commit()
            print(f"✅ Created tenant: {tenant.name}")
        else:
            print(f"✅ Found existing tenant: {tenant.name}")
        
        # ====================================================================
        # 1. ADD/UPDATE LLM MODEL CONFIGURATION
        # ====================================================================
        print("\n🤖 Adding/Updating LLM model configuration...")
        
        # Get all active LLM models
        llm_models = db.query(LLMModel).filter(LLMModel.is_active == True).all()
        print(f"   Found {len(llm_models)} active LLM models")
        
        # Check if a config already exists for this tenant
        existing_config = db.query(TenantLLMConfig).filter(
            TenantLLMConfig.tenant_id == uuid.UUID(target_tenant_id)
        ).first()
        
        if not existing_config:
            # Create a TenantLLMConfig for the tenant (by default, use the first LLM model)
            if llm_models:
                primary_llm_model = llm_models[0]  # Use the first available model
                tenant_llm_config = TenantLLMConfig(
                    tenant_id=target_tenant_id,
                    llm_model_id=primary_llm_model.llm_model_id,
                    encrypted_api_key="test_encrypted_api_key_placeholder",  # Placeholder - should be real encrypted key in production
                    rate_limit_rpm=60,
                    rate_limit_tpm=10000
                )
                db.add(tenant_llm_config)
                print(f"   ✅ Added LLM config using model: {primary_llm_model.model_name}")
            else:
                print("   ❌ No LLM models found to assign")
        else:
            print(f"   ℹ️  LLM config already exists for tenant (using model: {existing_config.llm_model.model_name})")
        
        print(f"✅ LLM configuration set up")
        
        # ====================================================================
        # 2. ADD AGENT PERMISSIONS
        # ====================================================================
        print("\n🤖 Adding Agent permissions...")
        
        # Get all active Agent configs
        agents = db.query(AgentConfig).filter(AgentConfig.is_active == True).all()
        print(f"   Found {len(agents)} active agents")
        
        for agent in agents:
            # Check if permission already exists
            existing_permission = db.query(TenantAgentPermission).filter(
                TenantAgentPermission.tenant_id == uuid.UUID(target_tenant_id),
                TenantAgentPermission.agent_id == agent.agent_id
            ).first()
            
            if not existing_permission:
                # Create permission for tenant to access this agent
                agent_permission = TenantAgentPermission(
                    tenant_id=target_tenant_id,
                    agent_id=agent.agent_id,
                    enabled=True
                )
                db.add(agent_permission)
                print(f"   ✅ Added permission for agent: {agent.name}")
            else:
                print(f"   ℹ️  Agent permission already exists for {agent.name}")
        
        print(f"✅ Added/verified {len(agents)} agent permissions")
        
        # ====================================================================
        # 3. ADD TOOL PERMISSIONS
        # ====================================================================
        print("\n🔧 Adding Tool permissions...")
        
        # Get all active Tool configs
        tools = db.query(ToolConfig).filter(ToolConfig.is_active == True).all()
        print(f"   Found {len(tools)} active tools")
        
        for tool in tools:
            # Check if permission already exists
            existing_permission = db.query(TenantToolPermission).filter(
                TenantToolPermission.tenant_id == uuid.UUID(target_tenant_id),
                TenantToolPermission.tool_id == tool.tool_id
            ).first()
            
            if not existing_permission:
                # Create permission for tenant to access this tool
                tool_permission = TenantToolPermission(
                    tenant_id=target_tenant_id,
                    tool_id=tool.tool_id,
                    enabled=True
                )
                db.add(tool_permission)
                print(f"   ✅ Added permission for tool: {tool.name}")
            else:
                print(f"   ℹ️  Tool permission already exists for {tool.name}")
        
        print(f"✅ Added/verified {len(tools)} tool permissions")
        
        # ====================================================================
        # 4. COMMIT ALL CHANGES
        # ====================================================================
        db.commit()
        
        print("\n" + "="*60)
        print("🎉 TENANT PERMISSIONS ADDED SUCCESSFULLY!")
        print("="*60)
        print(f"\n📊 Summary for tenant: {target_tenant_id}")
        print(f"  • LLM Models accessible: {len(llm_models)}")
        print(f"  • Agents accessible: {len(agents)}")
        print(f"  • Tools accessible: {len(tools)}")
        print(f"\n🧪 Ready for /chat API testing!")
        print("="*60)

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error adding tenant permissions: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Add Tenant Permissions Script")
    print("  Target Tenant: 2628802d-1dff-4a98-9325-704433c5d3ab")
    print("="*60)
    
    add_tenant_permissions()
    
    print(f"\n✅ Permissions setup complete!")
    print(f"📝 You can now test the /chat API with tenant_id: 2628802d-1dff-4a98-9325-704433c5d3ab")