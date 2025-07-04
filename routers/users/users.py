from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func
from dependencies.get_current_user import get_current_user
from dependencies.rbac import require_profile_read, require_profile_write, require_admin
from config import get_db, supabase_admin
from models import Profile, Role
from routers.users.schemas import ProfileUpdate, UserProfileResponse, RoleCreate, Role as RoleSchema, UserRoleUpdate
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)
users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile using optimized JWT structure"""
    result = await db.execute(
        select(Profile).where(Profile.id == current_user["user_id"])
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create profile if it doesn't exist
        profile = Profile(
            id=current_user["user_id"],
            email=current_user["email"],
            is_active=True
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    
    # Create user data combining profile and JWT info
    user_data = {
        **profile.__dict__,
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "role": current_user["role"]
    }
    
    return UserProfileResponse.model_validate(user_data)

@users_router.put("/me", response_model=UserProfileResponse, dependencies=[Depends(require_profile_write)])
async def update_current_user_profile(
    profile_update: ProfileUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile information"""
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        
        result = await db.execute(
            select(Profile).where(Profile.id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            # Create profile if it doesn't exist
            profile = Profile(
                id=user_id,
                email=user_email,
                is_active=True
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
        
        # Update only provided fields
        update_data = profile_update.model_dump(exclude_unset=True)
        
        if update_data:
            for field, value in update_data.items():
                setattr(profile, field, value)
            
            await db.commit()
            await db.refresh(profile)
        
        # Create user data combining profile and JWT info
        user_data = {
            **profile.__dict__,
            "user_id": current_user["user_id"],
            "email": user_email,
            "role": current_user["role"]
        }
        
        return UserProfileResponse.model_validate(user_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


# Admin endpoints
@users_router.get("/", response_model=List[UserProfileResponse], dependencies=[Depends(require_admin)])
async def list_users(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all users (admin only)"""
    try:
        # Get all profiles
        result = await db.execute(
            select(Profile).offset(skip).limit(limit)
        )
        profiles = result.scalars().all()
        
        # Convert to response format
        users = []
        for profile in profiles:
            user_data = {
                **profile.__dict__,
                "user_id": str(profile.id),
                "role": "user"  # Default role since we don't have role info in profile
            }
            users.append(UserProfileResponse.model_validate(user_data))
        
        return users
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@users_router.post("/update-role")
async def update_user_role(
    role_update: UserRoleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update user role using Supabase Admin API (no authentication required)"""
    try:
        # Update user metadata using Supabase Admin API
        response = supabase_admin.auth.admin.update_user_by_id(
            uid=role_update.user_id,
            attributes={
                "user_metadata": {
                    "role": role_update.role
                }
            }
        )
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Also update the profile in our database if it exists
        stmt = select(Profile).where(Profile.id == role_update.user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if profile:
            # Update profile record for consistency
            profile.updated_at = func.now()
            await db.commit()
        
        return {
            "message": f"User role updated to {role_update.role} successfully",
            "user_id": role_update.user_id,
            "new_role": role_update.role,
            "updated_at": response.user.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user role: {str(e)}"
        )

