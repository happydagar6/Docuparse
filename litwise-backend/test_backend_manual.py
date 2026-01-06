"""
Manual Test Suite for Litwise Backend API
Tests core endpoints with proper authentication
"""

import requests
import json
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
SUPABASE_URL = "https://ptnyazbnncsxskkvlvnc.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB0bnlhemJubmNzeHNra3Zsdm5jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM3MDI0MjIsImV4cCI6MjA3OTI3ODQyMn0.-P42lKAgwPQKSNO9RGbtWBi9-HC05gJw9Hk8Qfk6oMM"

# Test Results Storage
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": []
}

def signup_user(email: str, password: str) -> bool:
    """Create a new user account in Supabase"""
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            headers={
                "Content-Type": "application/json",
                "apikey": ANON_KEY
            },
            json={
                "email": email,
                "password": password
            }
        )
        if response.status_code == 200:
            print(f"✅ Account created successfully")
            return True
        else:
            error_msg = response.json().get("msg", "Unknown error")
            if "already registered" in error_msg.lower():
                print(f"ℹ️  Account already exists")
                return True
            print(f"❌ Signup failed: {error_msg}")
            return False
    except Exception as e:
        print(f"❌ Signup error: {e}")
        return False

def get_auth_token(email: str, password: str) -> Optional[str]:
    """Get JWT token from Supabase"""
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "Content-Type": "application/json",
                "apikey": ANON_KEY
            },
            json={
                "email": email,
                "password": password
            }
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"❌ Auth failed: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def run_test(name: str, method: str, endpoint: str, token: str, data: dict = None):
    """Run a single API test"""
    test_results["total"] += 1
    
    try:
        url = f"{BASE_URL}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            response = requests.request(method, url, headers=headers, json=data)
        
        # Check if successful (2xx status code)
        if 200 <= response.status_code < 300:
            test_results["passed"] += 1
            test_results["tests"].append({
                "name": name,
                "status": "✅ PASSED",
                "endpoint": endpoint,
                "status_code": response.status_code
            })
            print(f"✅ {name} - {response.status_code}")
        else:
            test_results["failed"] += 1
            error_msg = response.json().get("detail", "Unknown error") if response.text else "No response body"
            test_results["tests"].append({
                "name": name,
                "status": "❌ FAILED",
                "endpoint": endpoint,
                "status_code": response.status_code,
                "error": error_msg
            })
            print(f"❌ {name} - {response.status_code}: {error_msg}")
    except Exception as e:
        test_results["failed"] += 1
        test_results["tests"].append({
            "name": name,
            "status": "❌ ERROR",
            "endpoint": endpoint,
            "error": str(e)
        })
        print(f"❌ {name} - Exception: {e}")

def main():
    print("🚀 Starting Litwise Backend API Tests\n")
    
    # Step 1: Get credentials
    print("📝 Enter credentials...")
    email = input("Enter test email: ").strip()
    password = input("Enter test password: ").strip()
    
    # Step 2: Try signup first (in case account doesn't exist)
    print("\n🔐 Creating account if needed...")
    signup_user(email, password)
    
    # Step 3: Get auth token
    print("\n🔑 Getting authentication token...")
    token = get_auth_token(email, password)
    if not token:
        print("❌ Failed to get auth token. Exiting.")
        return
    
    print("✅ Authentication successful\n")
    
    # Step 2: Run tests
    print("🧪 Running API Tests\n")
    print("=" * 60)
    
    # Health check
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ API Health Check - {response.status_code}")
        test_results["passed"] += 1
    except:
        print("❌ API Health Check - Failed to connect")
        test_results["failed"] += 1
    
    test_results["total"] = 1
    
    # Paper endpoints
    print("\n📄 Paper Endpoints:")
    import time
    time.sleep(2)  # Wait for token to be valid
    run_test("List papers", "GET", "/papers", token)
    
    # Chat endpoints
    print("\n💬 Chat Endpoints:")
    # Use a valid UUID format for testing
    import uuid
    test_paper_id = str(uuid.uuid4())
    run_test("Create chat session", "POST", f"/api/chat/sessions?paper_id={test_paper_id}", token, {"title": "Test Chat"})
    
    # Citations endpoints
    print("\n📚 Citation Endpoints:")
    run_test("Get citation formats", "GET", "/api/citations/formats", token)
    
    # Notes endpoints
    print("\n📝 Notes Endpoints:")
    run_test("Get notes", "GET", "/api/notes", token)
    
    # Literature review endpoints
    print("\n📖 Literature Review Endpoints:")
    run_test("Get literature reviews", "GET", "/api/literature-review/list", token)
    
    # Quiz endpoints
    print("\n❓ Quiz Endpoints:")
    run_test("List quizzes", "GET", "/api/quiz/list", token)
    
    # Export endpoints
    print("\n📤 Export Endpoints:")
    run_test("Get APA export example", "GET", "/api/export/apa/example", token)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {test_results['total']}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"Success Rate: {(test_results['passed']/test_results['total']*100):.1f}%")
    
    # Save results
    with open("test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print("\n✅ Results saved to test_results.json")

if __name__ == "__main__":
    main()
