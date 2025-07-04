# RBAC Testing Guide for FastAPI + Supabase

This guide explains how to test Role-Based Access Control (RBAC) in your application.

## What is RBAC?

RBAC (Role-Based Access Control) controls who can access what in your application based on roles:
- **Users** have **Profiles** 
- **Profiles** can have multiple **Roles** (admin, user, moderator)
- **API endpoints** are protected by role requirements

## Your RBAC Implementation

### Models:
- `Profile`: User profiles with roles
- `Role`: Roles like "admin", "user", "moderator"  
- `Permission`: Permissions (future use)
- `user_roles`: Many-to-many relationship between users and roles

### Dependencies:
- `require_admin`: Requires "admin" role
- `require_roles(["admin", "moderator"])`: Requires one of the specified roles
- `require_role("admin")`: Requires a specific role

### Protected Endpoints:
```
POST /users/roles                     # Create role (admin only)
GET /users/roles                      # List roles (admin/moderator only)
GET /users/                           # List all users (admin only)
POST /users/{user_id}/roles/{role}    # Assign role (admin only)
DELETE /users/{user_id}/roles/{role}  # Remove role (admin only)
```

## Step-by-Step Testing Process

### 1. Setup Database with Default Roles

First, create a script to setup default roles:

```python
# Run this to create default roles in your database
python setup_rbac.py
```

### 2. Start Your FastAPI Server

```bash
# Start the server
uvicorn app.main:app --reload
```

### 3. Create Test Users in Supabase

1. Go to your Supabase Dashboard
2. Navigate to Authentication > Users
3. Create test users:
   - `admin@test.com` (will be admin)
   - `user@test.com` (will be regular user)
   - `moderator@test.com` (will be moderator)

### 4. Get JWT Tokens

You'll need JWT tokens for each user. You can get these by:

**Option A: Using Supabase Client**
```javascript
// In browser console or Node.js
const { createClient } = require('@supabase/supabase-js')
const supabase = createClient('your-url', 'your-anon-key')

// Sign in and get token
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'admin@test.com',
  password: 'your-password'
})
console.log('JWT Token:', data.session.access_token)
```

**Option B: Using curl**
```bash
# Sign in to get token
curl -X POST 'https://your-project.supabase.co/auth/v1/token?grant_type=password' \
  -H 'apikey: your-anon-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "admin@test.com",
    "password": "your-password"
  }'
```

### 5. Test RBAC Endpoints

Use the tokens to test endpoints:

#### Test 1: Create Roles (Admin Only)
```bash
# This should work (admin token)
curl -X POST "http://localhost:8000/users/roles" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "admin", "description": "System administrator"}'

# This should fail (user token)
curl -X POST "http://localhost:8000/users/roles" \
  -H "Authorization: Bearer YOUR_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "description": "Test role"}'
```

#### Test 2: List Roles (Admin/Moderator Only)
```bash
# Should work (admin token)
curl -X GET "http://localhost:8000/users/roles" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Should fail (user token)
curl -X GET "http://localhost:8000/users/roles" \
  -H "Authorization: Bearer YOUR_USER_TOKEN"
```

#### Test 3: List All Users (Admin Only)
```bash
# Should work (admin token)
curl -X GET "http://localhost:8000/users/" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Should fail (user token)
curl -X GET "http://localhost:8000/users/" \
  -H "Authorization: Bearer YOUR_USER_TOKEN"
```

#### Test 4: Assign Roles (Admin Only)
```bash
# Get user ID first from /users/me endpoint
USER_ID="get-this-from-users-me-endpoint"

# Should work (admin token)
curl -X POST "http://localhost:8000/users/${USER_ID}/roles/moderator" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Should fail (user token)
curl -X POST "http://localhost:8000/users/${USER_ID}/roles/moderator" \
  -H "Authorization: Bearer YOUR_USER_TOKEN"
```

## Expected Results

### ✅ Successful Responses:
- **200/201**: Operation successful
- **Profile data**: User profile with roles array
- **Role data**: Role information

### ❌ Expected Failures:
- **403 Forbidden**: "Admin access required" or "Requires one of these roles: admin, moderator"
- **401 Unauthorized**: Invalid or missing token
- **404 Not Found**: User or role not found

## Testing Checklist

- [ ] Default roles created in database
- [ ] Test users created in Supabase Auth
- [ ] JWT tokens obtained for each user
- [ ] Admin can create roles
- [ ] Regular users cannot create roles
- [ ] Admin/moderator can list roles
- [ ] Regular users cannot list roles
- [ ] Admin can assign/remove roles
- [ ] Regular users cannot assign roles
- [ ] Admin can list all users
- [ ] Regular users cannot list all users
- [ ] Users can view their own profile
- [ ] Role assignments persist in database

## Troubleshooting

### Common Issues:

1. **"Invalid token"**: Check JWT token format and expiration
2. **"User not found"**: Ensure user exists in profiles table
3. **"Role not found"**: Ensure roles exist in roles table
4. **403 Forbidden**: User doesn't have required role

### Debug Steps:

1. Check server logs for detailed error messages
2. Verify JWT token is valid and not expired
3. Check if user profile exists in database
4. Verify role assignments in `user_roles` table

## Next Steps

After testing, you can:
1. Add more specific permissions
2. Create role hierarchy
3. Add middleware for automatic role checking
4. Implement resource-level permissions
5. Add audit logging for role changes
