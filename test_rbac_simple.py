"""
Simple RBAC Testing Script (No External Dependencies)

This script tests RBAC endpoints using Python's built-in urllib.
Run this after starting your FastAPI server and setting up tokens.
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import sys
from typing import Dict, Any, Optional

class SimpleRBACTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.tokens = {}
        
    def set_token(self, user_type: str, token: str):
        """Set JWT token for a user type"""
        self.tokens[user_type] = token
        
    def make_request(self, method: str, endpoint: str, token: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request with authentication"""
        url = f"{self.base_url}{endpoint}"
        
        # Prepare headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Prepare request
        if data:
            json_data = json.dumps(data).encode('utf-8')
        else:
            json_data = None
            
        req = urllib.request.Request(url, data=json_data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                response_data = response.read().decode('utf-8')
                status_code = response.getcode()
                
                try:
                    result = json.loads(response_data)
                except json.JSONDecodeError:
                    result = {"text": response_data}
                    
                return {"status_code": status_code, "data": result}
                
        except urllib.error.HTTPError as e:
            error_data = e.read().decode('utf-8')
            try:
                error_result = json.loads(error_data)
            except json.JSONDecodeError:
                error_result = {"text": error_data}
                
            return {"status_code": e.code, "data": error_result}
            
        except Exception as e:
            return {"status_code": 0, "data": {"error": str(e)}}
    
    def test_endpoint(self, method: str, endpoint: str, user_type: str, 
                     data: Optional[Dict] = None, expected_status: int = 200):
        """Test an endpoint and report results"""
        if user_type not in self.tokens:
            print(f"❌ No token set for user type: {user_type}")
            return
            
        print(f"\n🔍 Testing {method} {endpoint} as {user_type}")
        print(f"   Expected status: {expected_status}")
        
        result = self.make_request(method, endpoint, self.tokens[user_type], data)
        status_code = result["status_code"]
        
        if status_code == expected_status:
            print(f"   ✅ Test PASSED (Status: {status_code})")
        else:
            print(f"   ❌ Test FAILED (Expected: {expected_status}, Got: {status_code})")
            
        print(f"   📄 Response: {json.dumps(result['data'], indent=2)}")
        
    def run_tests(self):
        """Run comprehensive RBAC tests"""
        print("🚀 Starting RBAC Tests")
        print("=" * 60)
        
        # Test 1: Create roles (admin only)
        print("\n📝 Test 1: Create Roles (Admin Only)")
        roles_to_create = [
            {"name": "admin", "description": "System administrator"},
            {"name": "user", "description": "Regular user"},
            {"name": "moderator", "description": "Content moderator"}
        ]
        
        for role in roles_to_create:
            self.test_endpoint("POST", "/users/roles", "admin", role, 201)
            
        # Test creating role as user (should fail)
        self.test_endpoint("POST", "/users/roles", "user", 
                          {"name": "test", "description": "Test role"}, 403)
        
        # Test 2: List roles
        print("\n📝 Test 2: List Roles (Admin/Moderator Only)")
        self.test_endpoint("GET", "/users/roles", "admin", expected_status=200)
        self.test_endpoint("GET", "/users/roles", "user", expected_status=403)
        
        # Test 3: Get user profile
        print("\n📝 Test 3: Get User Profile (All Authenticated)")
        self.test_endpoint("GET", "/users/me", "admin", expected_status=200)
        self.test_endpoint("GET", "/users/me", "user", expected_status=200)
        
        # Test 4: List all users (admin only)
        print("\n📝 Test 4: List All Users (Admin Only)")
        self.test_endpoint("GET", "/users/", "admin", expected_status=200)
        self.test_endpoint("GET", "/users/", "user", expected_status=403)
        
        print("\n🎉 RBAC Tests Completed!")
        print("\nNote: Role assignment tests require actual user IDs")
        print("      Get user IDs from /users/me endpoint first")


def main():
    """Main function to run tests"""
    print("🔧 RBAC Testing Setup")
    print("=" * 60)
    
    tester = SimpleRBACTester()
    
    # Get tokens from user input
    print("\n🔑 Please provide JWT tokens for testing:")
    print("   (Get these by signing in to your Supabase auth)")
    print("   (Leave empty to skip that user type)")
    
    admin_token = input("\n📝 Admin JWT Token: ").strip()
    user_token = input("📝 User JWT Token: ").strip()
    
    if not admin_token and not user_token:
        print("❌ No tokens provided. Exiting.")
        sys.exit(1)
    
    if admin_token:
        tester.set_token("admin", admin_token)
        print("✅ Admin token set")
        
    if user_token:
        tester.set_token("user", user_token)
        print("✅ User token set")
    
    # Run tests
    input("\n🚀 Press Enter to start testing...")
    tester.run_tests()


if __name__ == "__main__":
    print("⚠️  PREREQUISITES:")
    print("   1. FastAPI server running (uvicorn app.main:app --reload)")
    print("   2. Database setup with RBAC tables")
    print("   3. Default roles created (run setup_rbac.py)")
    print("   4. Test users created in Supabase Auth")
    print("   5. JWT tokens obtained for test users")
    print()
    
    choice = input("Ready to proceed? (y/n): ").strip().lower()
    if choice == 'y':
        main()
    else:
        print("👋 Setup your prerequisites first, then run this script again.")
