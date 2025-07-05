"""
Helper functions for admin operations
Contains business logic separated from route handlers for better maintainability
"""
import logging
import math
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from config import supabase_admin
from models import Profile
from routers.admin.schemas import UserListItem, UserListResponse, RoleUpdateResponse
from routers.users.helpers import get_all_user_profiles

logger = logging.getLogger(__name__)


async def get_paginated_users(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    role: Optional[str] = None
) -> UserListResponse:
    """
    Get paginated list of users with optional role filtering
    
    Args:
        db: Database session
        page: Page number (1-based)
        limit: Number of users per page
        role: Optional role filter
        
    Returns:
        UserListResponse: Paginated user list
        
    Raises:
        HTTPException: If listing fails
    """
    try:
        # Validate pagination parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 20
        
        offset = (page - 1) * limit
        
        # Get total count
        count_query = select(func.count(Profile.id))
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Use existing helper function to get user profiles
        all_users = await get_all_user_profiles(db, offset, limit)
        
        # Apply role filter if specified
        if role:
            filtered_users = [user for user in all_users if user.role == role]
        else:
            filtered_users = all_users
        
        # Convert to UserListItem format
        users = [UserListItem.model_validate(user.model_dump()) for user in filtered_users]
        
        # Calculate total pages
        total_pages = math.ceil(total / limit)
        
        return UserListResponse(
            users=users,
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Get paginated users failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


async def get_user_by_id_admin(
    user_id: str,
    db: AsyncSession
) -> UserListItem:
    """
    Get specific user by ID for admin purposes
    
    Args:
        user_id: User ID to retrieve
        db: Database session
        
    Returns:
        UserListItem: User information
        
    Raises:
        HTTPException: If user not found or retrieval fails
    """
    try:
        # Get user profile from database
        result = await db.execute(
            select(Profile).where(Profile.id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user role from Supabase
        try:
            supabase_user = supabase_admin.auth.admin.get_user_by_id(str(profile.id))
            user_role = "user"  # Default fallback
            
            if supabase_user.user and supabase_user.user.user_metadata:
                user_role = supabase_user.user.user_metadata.get("role", "user")
            
            user_data = {
                **profile.__dict__,
                "user_id": str(profile.id),
                "role": user_role
            }
            
            return UserListItem.model_validate(user_data)
            
        except Exception as role_error:
            logger.warning(f"Failed to get role for user {profile.id}: {str(role_error)}")
            user_data = {
                **profile.__dict__,
                "user_id": str(profile.id),
                "role": "user"
            }
            return UserListItem.model_validate(user_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user by ID failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


async def update_user_role_admin(
    user_id: str,
    new_role: str,
    current_user: Dict[str, Any],
    db: AsyncSession
) -> RoleUpdateResponse:
    """
    Update user role via admin API
    
    Args:
        user_id: User ID to update
        new_role: New role to assign
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        RoleUpdateResponse: Update result
        
    Raises:
        HTTPException: If user not found or update fails
    """
    try:
        if new_role not in ['user', 'admin']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be one of: user, admin"
            )
        
        # Get current user role from Supabase first to show in response
        try:
            supabase_user = supabase_admin.auth.admin.get_user_by_id(user_id)
            if not supabase_user.user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            old_role = "user"  # Default fallback
            if supabase_user.user.user_metadata:
                old_role = supabase_user.user.user_metadata.get("role", "user")
            
        except Exception as e:
            logger.error(f"Failed to get user from Supabase: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user metadata using Supabase Admin API
        try:
            response = supabase_admin.auth.admin.update_user_by_id(
                uid=user_id,
                attributes={
                    "user_metadata": {
                        "role": new_role
                    }
                }
            )
            
            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user role in authentication system"
                )
            
            logger.info(f"Updated Supabase user metadata for {user_id} with role: {new_role}")
            
        except Exception as supabase_error:
            logger.error(f"Failed to update Supabase metadata: {str(supabase_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user role in authentication system"
            )
        
        # Update profile timestamp for consistency (optional)
        try:
            result = await db.execute(
                select(Profile).where(Profile.id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                profile.updated_at = datetime.utcnow()
                await db.commit()
                
        except Exception as db_error:
            logger.warning(f"Failed to update profile timestamp: {str(db_error)}")
        
        return RoleUpdateResponse(
            message=f"User role updated from {old_role} to {new_role}",
            user_id=user_id,
            old_role=old_role,
            new_role=new_role,
            updated_by=current_user["role"],
            metadata_updated=True,
            note="Role will be available in JWT tokens after next login"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user role failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )
