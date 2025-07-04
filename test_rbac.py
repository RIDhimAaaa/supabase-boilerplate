"""
RBAC Testing Script for FastAPI + Supabase

This script demonstrates how to test Role-Based Access Control (RBAC) in your application.
Run this after starting your FastAPI server.
"""

import requests
import json
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust to your server URL
HEADERS = {"Content-Type": "application/json"}

class RBACTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.tokens = {}  # Store tokens for different users
        
    def set_auth_token(self, user_name: str, token: str):
        """Set authentication token for a user"""
        self.tokens[user_name] = token
        
    def get_auth_headers(self, user_name: str) -> Dict[str, str]:
        """Get headers with authentication token"""
        if user_name not in self.tokens:
            raise ValueError(f"No token found for user: {user_name}")
        
        return {
            "Authorization": f"Bearer {self.tokens[user_name]}",
            "Content-Type": "application/json"
        }
    
    def test_endpoint(self, method: str, endpoint: str, user_name: str, 
                     data: Optional[Dict] = None, expected_status: int = 200) -> Dict:
        """Test an endpoint with specific user credentials"""
        url = f"{self.base_url}{endpoint}"
        headers = self.get_auth_headers(user_name)
        
        print(f"\n🔍 Testing {method.upper()} {endpoint} as {user_name}")
        print(f"   Expected status: {expected_status}")
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            print(f"   ✅ Status: {response.status_code}")
            
            if response.status_code == expected_status:
                print(f"   ✅ Test PASSED")
            else:
                print(f"   ❌ Test FAILED - Expected {expected_status}, got {response.status_code}")
            
            # Try to parse JSON response
            try:
                result = response.json()
                print(f"   📄 Response: {json.dumps(result, indent=2)}")
                return result
            except:
                print(f"   📄 Response: {response.text}")
                return {"status_code": response.status_code, "text": response.text}
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return {"error": str(e)}
    
    def run_rbac_tests(self):
        """Run comprehensive RBAC tests"""
        print("🚀 Starting RBAC Tests")
        print("=" * 50)
        
        # Test 1: Create roles (admin required)
        print("\n📝 Test 1: Create Roles")
        admin_roles = [
            {"name": "admin", "description": "System administrator"},
            {"name": "user", "description": "Regular user"},
            {"name": "moderator", "description": "Content moderator"}
        ]
        
        for role in admin_roles:
            self.test_endpoint("POST", "/users/roles", "admin", role, 201)
        
        # Test 2: List roles (admin/moderator required)
        print("\n📝 Test 2: List Roles")
        self.test_endpoint("GET", "/users/roles", "admin", expected_status=200)
        self.test_endpoint("GET", "/users/roles", "moderator", expected_status=200)
        self.test_endpoint("GET", "/users/roles", "user", expected_status=403)  # Should fail
        
        # Test 3: Get user profile (authenticated users)
        print("\n📝 Test 3: Get User Profiles")
        self.test_endpoint("GET", "/users/me", "admin", expected_status=200)
        self.test_endpoint("GET", "/users/me", "user", expected_status=200)
        
        # Test 4: List all users (admin only)
        print("\n📝 Test 4: List All Users")
        self.test_endpoint("GET", "/users/", "admin", expected_status=200)
        self.test_endpoint("GET", "/users/", "user", expected_status=403)  # Should fail
        
        # Test 5: Assign roles (admin only)
        print("\n📝 Test 5: Assign Roles")
        # Note: You'll need actual user IDs for this test
        user_id = "replace-with-actual-user-id"
        self.test_endpoint("POST", f"/users/{user_id}/roles/moderator", "admin", expected_status=200)
        self.test_endpoint("POST", f"/users/{user_id}/roles/user", "user", expected_status=403)  # Should fail
        
        print("\n🎉 RBAC Tests Completed")


def main():
    """
    Main function to run RBAC tests
    
    SETUP REQUIRED:
    1. Start your FastAPI server
    2. Create test users in Supabase Auth
    3. Get JWT tokens for each user
    4. Replace the token placeholders below
    """
    
    tester = RBACTester()
    
    # TODO: Replace these with actual JWT tokens from your Supabase users
    # You can get these by:
    # 1. Creating users in Supabase Auth Dashboard
    # 2. Using Supabase client to sign in and get tokens
    # 3. Or using your frontend to authenticate and copy tokens
    
    # Example tokens (replace with real ones):
    tester.set_auth_token("admin", "your-admin-jwt-token-here")
    tester.set_auth_token("user", "your-user-jwt-token-here")
    tester.set_auth_token("moderator", "your-moderator-jwt-token-here")
    
    # Run the tests
    tester.run_rbac_tests()


if __name__ == "__main__":
    print("⚠️  SETUP REQUIRED:")
    print("   1. Start your FastAPI server")
    print("   2. Create test users in Supabase")
    print("   3. Replace JWT tokens in this script")
    print("   4. Run: python test_rbac.py")
    print()
    
    # Uncomment the line below after setup:
    # main()
