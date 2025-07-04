from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import JWT_SECRET_KEY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.config import get_db
import jwt
import os
from typing import Dict, Any, List

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        
        # Get JWT secret from Supabase anon key
        jwt_secret = JWT_SECRET_KEY
        
        # Decode the JWT token
        payload = jwt.decode(
            token, 
            jwt_secret, 
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_exp": True, "verify_aud": False}
        )
        
        # Extract user information from payload
        user_id = payload.get("sub")
        email = payload.get("email")
        user_metadata = payload.get("user_metadata", {})
        role = user_metadata.get("role", "user")

        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create a user-like object with the decoded information
        user = {
            "id": user_id,
            "email": email, 
            "role": role,
            "payload": payload
        }
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# RBAC Functions - New additions
async def get_user_with_roles(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user with their roles loaded"""
    from app.models import Profile
    
    stmt = select(Profile).options(selectinload(Profile.roles)).where(Profile.id == current_user["id"])
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create profile with default 'user' role if it doesn't exist
        from app.models import Role
        
        profile = Profile(
            id=current_user["id"],
            email=current_user["email"],
            is_active=True
        )
        db.add(profile)
        
        # Assign default 'user' role
        user_role_stmt = select(Role).where(Role.name == "user")
        user_role_result = await db.execute(user_role_stmt)
        user_role = user_role_result.scalar_one_or_none()
        
        if user_role:
            profile.roles.append(user_role)
        
        await db.commit()
        await db.refresh(profile)
    
    return profile

def require_roles(allowed_roles: List[str]):
    """Dependency factory to require specific roles"""
    async def dependency(profile = Depends(get_user_with_roles)):
        user_role_names = [role.name for role in profile.roles]
        
        if not any(role in user_role_names for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of these roles: {', '.join(allowed_roles)}"
            )
        
        return profile
    
    return dependency

def require_role(role_name: str):
    """Dependency to require a specific role"""
    async def dependency(profile = Depends(get_user_with_roles)):
        user_role_names = [role.name for role in profile.roles]
        
        if role_name not in user_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_name}' required"
            )
        
        return profile
    
    return dependency

async def require_admin(profile = Depends(get_user_with_roles)):
    """Dependency to require admin role"""
    user_role_names = [role.name for role in profile.roles]
    
    if 'admin' not in user_role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return profile
