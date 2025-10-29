"""Test script to verify server can start and endpoints work."""
import sys
import time
import requests
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all imports work."""
    print("Testing imports...")
    try:
        from src.main import app
        from src.api import chat, sessions
        from src.config import settings
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_creation():
    """Test that FastAPI app is created properly."""
    print("\nTesting FastAPI app creation...")
    try:
        from src.main import app
        routes = [route.path for route in app.routes]
        print(f"✓ FastAPI app created with {len(routes)} routes:")
        for route in routes:
            print(f"  - {route}")
        return True
    except Exception as e:
        print(f"✗ App creation error: {e}")
        return False


def test_health_endpoint_local():
    """Test health endpoint by importing the function."""
    print("\nTesting health endpoint function...")
    try:
        from src.main import health_check
        import asyncio
        result = asyncio.run(health_check())
        print(f"✓ Health endpoint returns: {result}")
        return True
    except Exception as e:
        print(f"✗ Health endpoint error: {e}")
        return False


def test_server_running():
    """Test if server is running and responding."""
    print("\nTesting if server is running on http://localhost:8000...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ Server is running! Response: {response.json()}")
            return True
        else:
            print(f"✗ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Server is not running (connection refused)")
        print("\nTo start the server, run:")
        print("  cd backend")
        print("  PYTHONPATH=. ./venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"✗ Error checking server: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("AgentHub Backend Server Test")
    print("="*60)

    results = []

    # Test imports
    results.append(("Imports", test_imports()))

    # Test app creation
    results.append(("App Creation", test_app_creation()))

    # Test health endpoint function
    results.append(("Health Endpoint Function", test_health_endpoint_local()))

    # Test if server is running
    results.append(("Server Running", test_server_running()))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {test_name}: {status}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 All tests passed! Server is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
