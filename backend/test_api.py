"""Quick test script to verify API setup."""
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")

    try:
        from src.main import app
        print("✓ FastAPI app imported successfully")

        from src.api import chat, sessions
        print("✓ Chat and sessions routers imported successfully")

        from src.services.supervisor_agent import SupervisorAgent
        print("✓ SupervisorAgent imported successfully")

        from src.services.domain_agents import AgentFactory
        print("✓ AgentFactory imported successfully")

        from src.services.llm_manager import llm_manager
        print("✓ LLMManager imported successfully")

        from src.services.tool_loader import ToolRegistry
        print("✓ ToolRegistry imported successfully")

        from src.config import settings
        print(f"✓ Configuration loaded: {settings.ENVIRONMENT} environment")
        print(f"  Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'N/A'}")
        print(f"  Redis: {settings.REDIS_URL}")

        # Check routes
        routes = [route.path for route in app.routes]
        print(f"\n✓ API routes registered: {len(routes)} routes")

        # Check for our new endpoints
        chat_routes = [r for r in routes if '/chat' in r]
        session_routes = [r for r in routes if '/session' in r]

        print(f"  Chat endpoints: {len(chat_routes)}")
        for route in chat_routes:
            print(f"    - {route}")

        print(f"  Session endpoints: {len(session_routes)}")
        for route in session_routes:
            print(f"    - {route}")

        print("\n✅ All imports successful! API is ready to start.")
        print("\nNext steps:")
        print("1. Ensure Docker services are running: docker-compose up -d")
        print("2. Run migrations: alembic upgrade head")
        print("3. Start API server: python src/main.py")
        print("4. Access API docs: http://localhost:8000/docs")

        return True

    except Exception as e:
        print(f"\n❌ Error during import test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_imports())
    sys.exit(0 if success else 1)
