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
        "question": question,
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
        print(f"Methodology: {result.get('methodology', 'N/A')[:200]}...")
        print(f"Limitations: {len(result.get('limitations', []))} found")
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
    
    # Test upload (you need to provide a PDF path)
    pdf_path = input("\nEnter path to a PDF file to test (or press Enter to skip): ").strip()
    
    if pdf_path:
        document_id = test_upload(pdf_path)
        
        if document_id:
            print(f"\n✅ Document uploaded successfully! ID: {document_id}")
            
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

