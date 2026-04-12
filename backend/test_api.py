"""
Test script for the Smart Research Paper Analyzer API
"""
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_upload(pdf_path: str):
    """Test document upload"""
    print("\n=== Testing Document Upload ===")
    
    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found at {pdf_path}")
        return None
    
    with open(pdf_path, 'rb') as f:
        files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
        response = requests.post(f"{BASE_URL}/upload", files=files)
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        return result.get('document_id')
    return None


def test_query(question: str, document_id: str = None):
    """Test query endpoint"""
    print("\n=== Testing Query Endpoint ===")
    
    payload = {
        "question": "what is the topic of the paper and is it relevent to genAI",
        "top_k": 5
    }
    
    if document_id:
        payload["document_id"] = document_id
    
    response = requests.post(f"{BASE_URL}/query", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Question: {question}")
    print(f"Answer: {result.get('answer', 'N/A')}")
    print(f"Citations: {len(result.get('citations', []))}")
    return response.status_code == 200


def test_analyze(document_id: str):
    """Test document analysis"""
    print("\n=== Testing Document Analysis ===")
    
    response = requests.get(f"{BASE_URL}/analyze/{document_id}")
    print(f"Status: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        print(f"Summary: {result.get('summary', 'N/A')[:200]}...")
        print(f"Key Findings: {len(result.get('key_findings', []))} found")
        print(f"Key Findings: {result.get('key_findings', 'N/A')[:200]}...")
        print(f"Methodology: {result.get('methodology', 'N/A')[:200]}...")
        print(f"Limitations: {len(result.get('limitations', []))} found")
        print(f"Key Findings: {result.get('limitations', 'N/A')[:200]}...")
    else:
        print(f"Error: {result.get('error')}")
    
    return response.status_code == 200


def test_stats():
    """Test statistics endpoint"""
    print("\n=== Testing Statistics Endpoint ===")
    
    response = requests.get(f"{BASE_URL}/stats")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return response.status_code == 200


def test_delete(document_id: str):
    """Test document deletion"""
    print("\n=== Testing Document Deletion ===")

    response = requests.delete(f"{BASE_URL}/documents/{document_id}")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return response.status_code == 200


# ====================== Embedding Provider Tests ======================


def test_get_embedding_config():
    """Test GET /embedding – retrieve current embedding configuration"""
    print("\n=== Testing GET /embedding ===")

    response = requests.get(f"{BASE_URL}/embedding")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    if response.status_code == 200 and result.get("success"):
        print(f"  Provider : {result.get('provider')}")
        print(f"  Model    : {result.get('model')}")
        print(f"  Dimension: {result.get('dimension')}")
        print(f"  Available: {result.get('available_providers')}")
        return True

    print("❌ Failed to get embedding config")
    return False


def test_switch_embedding(provider: str):
    """Test PUT /embedding – switch to a specific provider"""
    print(f"\n=== Testing PUT /embedding (switch to '{provider}') ===")

    response = requests.put(
        f"{BASE_URL}/embedding",
        json={"provider": provider}
    )
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    if response.status_code == 200 and result.get("success"):
        active = result.get("provider", "")
        if active == provider.lower():
            print(f"✅ Successfully switched to '{provider}'")
            return True
        else:
            print(f"❌ Provider mismatch: expected '{provider}', got '{active}'")
            return False

    print(f"❌ Failed to switch to '{provider}'")
    return False


def test_switch_embedding_invalid():
    """Test PUT /embedding with an invalid provider name"""
    print("\n=== Testing PUT /embedding (invalid provider) ===")

    response = requests.put(
        f"{BASE_URL}/embedding",
        json={"provider": "nonexistent_provider"}
    )
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    if response.status_code == 400:
        print("✅ Correctly rejected invalid provider")
        return True

    print("❌ Expected 400 for invalid provider")
    return False


def test_embedding_round_trip():
    """
    Full round-trip test:
    1. Get current config (should be the default)
    2. Switch to each provider and verify
    3. Switch back to the original provider
    """
    print("\n" + "=" * 60)
    print("Embedding Provider – Round-Trip Test")
    print("=" * 60)

    passed = 0
    failed = 0

    # 1. Get initial config
    if test_get_embedding_config():
        passed += 1
    else:
        failed += 1

    # Remember the starting provider so we can restore it
    initial = requests.get(f"{BASE_URL}/embedding").json()
    original_provider = ("openai")

    # 2. Cycle through all providers
    for provider in ["gemma", "langchain", "openai"]:
        if test_switch_embedding(provider):
            passed += 1

            # Verify GET returns the new provider
            check = requests.get(f"{BASE_URL}/embedding").json()
            if check.get("provider") == provider:
                print(f"  ✅ GET /embedding confirms '{provider}' is active")
                passed += 1
            else:
                print(f"  ❌ GET /embedding returned '{check.get('provider')}' instead of '{provider}'")
                failed += 1
        else:
            failed += 1

    # 3. Test invalid provider
    if test_switch_embedding_invalid():
        passed += 1
    else:
        failed += 1

    # 4. Restore original provider
    print(f"\n--- Restoring original provider: {original_provider} ---")
    if test_switch_embedding(original_provider):
        passed += 1
    else:
        failed += 1

    # Summary
    print("\n" + "-" * 40)
    print(f"Embedding tests: {passed} passed, {failed} failed")
    print("-" * 40)

    return failed == 0


# ====================== Research & Scoring Tests ======================


def test_get_research():
    """Test GET /research – retrieve current research context"""
    print("\n=== Testing GET /research ===")
    response = requests.get(f"{BASE_URL}/research")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return response.status_code == 200


def test_set_research(topic: str, description: str):
    """Test POST /research – set research context"""
    print(f"\n=== Testing POST /research (topic='{topic}') ===")
    response = requests.post(
        f"{BASE_URL}/research",
        json={"topic": topic, "description": description},
    )
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Topic   : {result.get('topic')}")
    print(f"Breakdown (first 200 chars): {str(result.get('breakdown', ''))[:200]}")

    if response.status_code == 200 and result.get("success"):
        print("✅ Research context saved")
        return True
    print("❌ Failed to set research")
    return False


def test_score_document(document_id: str):
    """Test POST /score/{document_id} – score document against research"""
    print(f"\n=== Testing POST /score/{document_id} ===")
    response = requests.post(f"{BASE_URL}/score/{document_id}")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Score      : {result.get('score')}/100")
    print(f"Explanation: {result.get('explanation', 'N/A')[:200]}")

    if response.status_code == 200 and result.get("success"):
        print(f"✅ Document scored: {result['score']}/100")
        return True
    print(f"❌ Scoring failed: {result.get('error', result.get('detail'))}")
    return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Smart Research Paper Analyzer - API Test Suite")
    print("=" * 60)

    # Test health
    if not test_health():
        print("\n❌ Health check failed! Make sure the server is running.")
        return

    print("\n✅ Health check passed!")

    # Test stats
    test_stats()

    # Test embedding provider switching
    test_embedding_round_trip()

    # Test research (before upload so scoring can happen after)
    test_get_research()
    topic = input("\nEnter a research topic (or Enter to skip): ").strip()
    if topic:
        desc = input("Enter research description: ").strip()
        test_set_research(topic, desc)
        test_get_research()

    # Test upload (you need to provide a PDF path)
    pdf_path = input("\nEnter path to a PDF file to test (or press Enter to skip): ").strip()

    if pdf_path:
        document_id = test_upload(pdf_path)

        if document_id:
            print(f"\n✅ Document uploaded successfully! ID: {document_id}")

            # Test scoring against research
            if topic:
                test_score_document(document_id)

            # Test query
            test_query("What are the main findings of this paper?", document_id)

            # Test analysis
            test_analyze(document_id)

            # Ask if user wants to delete
            delete = input("\nDelete the uploaded document? (y/n): ").strip().lower()
            if delete == 'y':
                test_delete(document_id)
        else:
            print("\n❌ Document upload failed!")

    print("\n" + "=" * 60)
    print("Test suite completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

