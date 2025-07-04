"""
JWT Token Helper Script

This script helps you get JWT tokens for testing RBAC.
You can use this with curl or modify it for your needs.
"""

import json

def generate_curl_commands():
    """Generate curl commands to get JWT tokens"""
    
    print("🔑 JWT Token Helper")
    print("=" * 50)
    
    # Get Supabase configuration
    print("\n📋 You'll need your Supabase configuration:")
    project_url = input("🌐 Supabase Project URL: ").strip()
    anon_key = input("🔑 Supabase Anon Key: ").strip()
    
    if not project_url or not anon_key:
        print("❌ Both URL and anon key are required!")
        return
    
    # Make sure URL format is correct
    if not project_url.startswith('https://'):
        project_url = f"https://{project_url}"
    if not project_url.endswith('.supabase.co'):
        project_url = f"{project_url}.supabase.co"
    
    print(f"\n🔧 Using URL: {project_url}")
    
    # Test users
    test_users = [
        {"email": "admin@test.com", "password": "admin123", "role": "admin"},
        {"email": "user@test.com", "password": "user123", "role": "user"},
        {"email": "moderator@test.com", "password": "moderator123", "role": "moderator"}
    ]
    
    print("\n📝 Suggested test users to create in Supabase:")
    for user in test_users:
        print(f"   - {user['email']} (password: {user['password']})")
    
    print("\n🔨 Curl commands to get JWT tokens:")
    print("   (Run these after creating the users)")
    
    for user in test_users:
        print(f"\n# Get {user['role']} token:")
        print(f"curl -X POST '{project_url}/auth/v1/token?grant_type=password' \\")
        print(f"  -H 'apikey: {anon_key}' \\")
        print(f"  -H 'Content-Type: application/json' \\")
        print(f"  -d '{{")
        print(f"    \"email\": \"{user['email']}\",")
        print(f"    \"password\": \"{user['password']}\"")
        print(f"  }}' | jq -r '.access_token'")
    
    print("\n💡 Tips:")
    print("   - Install jq to extract tokens: winget install jqlang.jq")
    print("   - Or copy the full response and extract 'access_token' manually")
    print("   - Tokens expire, so get fresh ones if tests fail")
    print("   - Store tokens securely and don't commit them to git")


def generate_powershell_commands():
    """Generate PowerShell commands to get JWT tokens"""
    
    print("\n🔷 PowerShell Commands (Alternative):")
    print("=" * 50)
    
    project_url = input("🌐 Supabase Project URL: ").strip()
    anon_key = input("🔑 Supabase Anon Key: ").strip()
    
    if not project_url or not anon_key:
        print("❌ Both URL and anon key are required!")
        return
    
    # Make sure URL format is correct
    if not project_url.startswith('https://'):
        project_url = f"https://{project_url}"
    if not project_url.endswith('.supabase.co'):
        project_url = f"{project_url}.supabase.co"
    
    test_users = [
        {"email": "admin@test.com", "password": "admin123", "role": "admin"},
        {"email": "user@test.com", "password": "user123", "role": "user"},
    ]
    
    for user in test_users:
        print(f"\n# Get {user['role']} token:")
        print(f"$body = @{{")
        print(f"  email = \"{user['email']}\"")
        print(f"  password = \"{user['password']}\"")
        print(f"}} | ConvertTo-Json")
        print(f"")
        print(f"$response = Invoke-RestMethod -Uri '{project_url}/auth/v1/token?grant_type=password' `")
        print(f"  -Method POST `")
        print(f"  -Headers @{{")
        print(f"    'apikey' = '{anon_key}'")
        print(f"    'Content-Type' = 'application/json'")
        print(f"  }} `")
        print(f"  -Body $body")
        print(f"")
        print(f"Write-Host \"{user['role'].upper()} TOKEN: $($response.access_token)\"")


def main():
    """Main function"""
    print("🔧 JWT Token Helper for RBAC Testing")
    print("=" * 50)
    
    choice = input("\nChoose method:\n1. Curl commands\n2. PowerShell commands\n3. Both\n\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        generate_curl_commands()
    elif choice == "2":
        generate_powershell_commands()
    elif choice == "3":
        generate_curl_commands()
        generate_powershell_commands()
    else:
        print("❌ Invalid choice")
        return
    
    print("\n🎯 Next Steps:")
    print("1. Create the test users in Supabase Auth Dashboard")
    print("2. Run the generated commands to get JWT tokens")
    print("3. Use the tokens in test_rbac_simple.py")
    print("4. Test your RBAC implementation!")


if __name__ == "__main__":
    main()
