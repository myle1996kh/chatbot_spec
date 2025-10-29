"""
Test script for AgentHub Chat API.

This script tests the chat endpoint with various queries.
"""
import requests
import json
import sys


def test_chat_api(tenant_id: str, test_cases: list):
    """
    Test chat API with various queries.

    Args:
        tenant_id: Tenant UUID
        test_cases: List of test case dictionaries
    """
    base_url = "http://127.0.0.1:8000"
    chat_endpoint = f"{base_url}/api/{tenant_id}/chat"

    print("\n" + "="*80)
    print(f"Testing AgentHub Chat API")
    print("="*80)
    print(f"Endpoint: {chat_endpoint}")
    print(f"Tenant ID: {tenant_id}\n")

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"{'='*80}")

        # Prepare request
        payload = {
            "user_id": test_case.get("user_id", "test_user_001"),
            "message": test_case["message"],
            "session_id": test_case.get("session_id"),
            "metadata": test_case.get("metadata", {
                "jwt_token": "test_token_for_demo"
            })
        }

        print(f"\n📤 Request:")
        print(json.dumps(payload, indent=2))

        try:
            # Send request
            response = requests.post(
                chat_endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Tenant-ID": tenant_id,
                },
                timeout=30
            )

            print(f"\n📥 Response Status: {response.status_code}")

            if response.status_code == 200:
                response_data = response.json()
                print(f"\n✅ Success!")
                print(f"\nSession ID: {response_data.get('session_id')}")
                print(f"Agent: {response_data.get('agent')}")
                print(f"Intent: {response_data.get('intent')}")
                print(f"\n💬 Response Data:")
                print(json.dumps(response_data.get('response'), indent=2))

                if response_data.get('metadata'):
                    print(f"\n📊 Metadata:")
                    print(json.dumps(response_data['metadata'], indent=2))
            else:
                print(f"\n❌ Error: {response.status_code}")
                print(response.text)

        except requests.exceptions.Timeout:
            print("\n⏱️ Request timed out")
        except requests.exceptions.ConnectionError:
            print("\n🔌 Connection error - is the server running?")
        except Exception as e:
            print(f"\n💥 Exception: {str(e)}")

        print("\n" + "-"*80)


if __name__ == "__main__":
    # Check if tenant_id is provided as command line argument
    if len(sys.argv) > 1:
        tenant_id = sys.argv[1]
    else:
        # Use default tenant_id (you'll get this from seed_test_data.py output)
        print("⚠️  No tenant_id provided. Usage: python test_chat_api.py <tenant_id>")
        print("Using placeholder tenant_id - replace with actual value from seed script")
        tenant_id = "2628802d-1dff-4a98-9325-704433c5d3ab"

    # Define test cases
    test_cases = [
        {
            "name": "Query customer debt by tax code",
            "message": "What is the debt for customer with MST 0123456789012?",
            "user_id": "test_user_001",
        },
        {
            "name": "Query salesman receivables",
            "message": "Show me all receivables for salesman JOHN_DOE",
            "user_id": "test_user_001",
        },
        {
            "name": "Invalid tax code format",
            "message": "What is the debt for MST 123?",  # Too short
            "user_id": "test_user_001",
        },
        {
            "name": "General greeting",
            "message": "Hello, can you help me with customer debts?",
            "user_id": "test_user_001",
        },
        {
            "name": "Multi-intent query (should be rejected)",
            "message": "What is the debt for MST 0123456789012 AND what about salesman JANE_DOE?",
            "user_id": "test_user_001",
        },
    ]

    # Run tests
    test_chat_api(tenant_id, test_cases)

    print("\n" + "="*80)
    print("✅ All tests completed!")
    print("="*80 + "\n")
