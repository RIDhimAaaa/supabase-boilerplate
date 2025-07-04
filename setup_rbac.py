"""
RBAC Setup Script

This script sets up the initial roles and permissions in your database.
Run this after applying your Alembic migrations.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config import async_engine, get_db
from models import Role, Permission
import sys

async def create_default_roles():
    """Create default roles in the database"""
    
    # Create an async session
    async with AsyncSession(async_engine) as session:
        try:
            # Default roles to create
            default_roles = [
                {"name": "admin", "description": "System administrator with full access"},
                {"name": "user", "description": "Regular user with basic access"},
                {"name": "moderator", "description": "Content moderator with elevated access"}
            ]
            
            print("🚀 Setting up default roles...")
            
            for role_data in default_roles:
                # Check if role already exists
                stmt = select(Role).where(Role.name == role_data["name"])
                result = await session.execute(stmt)
                existing_role = result.scalar_one_or_none()
                
                if existing_role:
                    print(f"   ⚠️  Role '{role_data['name']}' already exists, skipping...")
                    continue
                
                # Create new role
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"]
                )
                session.add(role)
                print(f"   ✅ Created role: {role_data['name']}")
            
            await session.commit()
            print("✅ Default roles setup completed!")
            
        except Exception as e:
            print(f"❌ Error setting up roles: {str(e)}")
            await session.rollback()
            sys.exit(1)


async def create_default_permissions():
    """Create default permissions in the database"""
    
    async with AsyncSession(async_engine) as session:
        try:
            # Default permissions to create
            default_permissions = [
                # User management permissions
                {"name": "user:create", "description": "Create new users", "resource": "users", "action": "create"},
                {"name": "user:read", "description": "View user profiles", "resource": "users", "action": "read"},
                {"name": "user:update", "description": "Update user profiles", "resource": "users", "action": "update"},
                {"name": "user:delete", "description": "Delete users", "resource": "users", "action": "delete"},
                {"name": "user:list", "description": "List all users", "resource": "users", "action": "list"},
                
                # Role management permissions
                {"name": "role:create", "description": "Create new roles", "resource": "roles", "action": "create"},
                {"name": "role:read", "description": "View roles", "resource": "roles", "action": "read"},
                {"name": "role:update", "description": "Update roles", "resource": "roles", "action": "update"},
                {"name": "role:delete", "description": "Delete roles", "resource": "roles", "action": "delete"},
                {"name": "role:assign", "description": "Assign roles to users", "resource": "roles", "action": "assign"},
                
                # Content management permissions (example)
                {"name": "content:create", "description": "Create content", "resource": "content", "action": "create"},
                {"name": "content:moderate", "description": "Moderate content", "resource": "content", "action": "moderate"},
                {"name": "content:delete", "description": "Delete content", "resource": "content", "action": "delete"},
            ]
            
            print("🚀 Setting up default permissions...")
            
            for perm_data in default_permissions:
                # Check if permission already exists
                stmt = select(Permission).where(Permission.name == perm_data["name"])
                result = await session.execute(stmt)
                existing_perm = result.scalar_one_or_none()
                
                if existing_perm:
                    print(f"   ⚠️  Permission '{perm_data['name']}' already exists, skipping...")
                    continue
                
                # Create new permission
                permission = Permission(
                    name=perm_data["name"],
                    description=perm_data["description"],
                    resource=perm_data["resource"],
                    action=perm_data["action"]
                )
                session.add(permission)
                print(f"   ✅ Created permission: {perm_data['name']}")
            
            await session.commit()
            print("✅ Default permissions setup completed!")
            
        except Exception as e:
            print(f"❌ Error setting up permissions: {str(e)}")
            await session.rollback()
            sys.exit(1)


async def verify_setup():
    """Verify that roles and permissions were created successfully"""
    
    async with AsyncSession(async_engine) as session:
        try:
            # Count roles
            role_stmt = select(Role)
            role_result = await session.execute(role_stmt)
            roles = role_result.scalars().all()
            
            # Count permissions
            perm_stmt = select(Permission)
            perm_result = await session.execute(perm_stmt)
            permissions = perm_result.scalars().all()
            
            print(f"\n📊 Setup Summary:")
            print(f"   Roles: {len(roles)}")
            for role in roles:
                print(f"     - {role.name}: {role.description}")
            
            print(f"   Permissions: {len(permissions)}")
            for perm in permissions:
                print(f"     - {perm.name}: {perm.description}")
                
        except Exception as e:
            print(f"❌ Error verifying setup: {str(e)}")


async def main():
    """Main setup function"""
    print("🔧 RBAC Setup Starting...")
    print("=" * 50)
    
    try:
        # Create default roles
        await create_default_roles()
        
        # Create default permissions
        await create_default_permissions()
        
        # Verify setup
        await verify_setup()
        
        print("\n🎉 RBAC Setup Complete!")
        print("\nNext steps:")
        print("1. Start your FastAPI server: uvicorn app.main:app --reload")
        print("2. Create test users in Supabase Auth")
        print("3. Use the API to assign roles to users")
        print("4. Test the RBAC endpoints")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
