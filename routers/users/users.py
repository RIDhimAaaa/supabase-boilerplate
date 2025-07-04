from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func
from dependencies.get_current_user import get_current_user
from dependencies.rbac import require_profile_read, require_profile_write, require_admin
from config import get_db, supabase_admin, supabase
from models import Profile, Role
from routers.users.schemas import ProfileUpdate, UserProfileResponse, RoleCreate, Role as RoleSchema, UserRoleUpdate, ProfileImageUpload
from typing import Optional, Dict, Any, List
import logging
import uuid
import os
from datetime import datetime

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

@users_router.put("/me", response_model=UserProfileResponse)
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


@users_router.post("/me/profile-image", response_model=ProfileImageUpload)
async def upload_profile_image(
    file: UploadFile = File(..., description="Profile image file (JPEG, PNG, GIF, or WebP, max 5MB)"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a new profile image to Supabase storage
    
    Accepts image files in the following formats:
    - JPEG (.jpg, .jpeg)
    - PNG (.png) 
    - GIF (.gif)
    - WebP (.webp)
    
    Maximum file size: 5MB
    """
    try:
        user_id = current_user["user_id"]
        
        # Get user profile
        result = await db.execute(
            select(Profile).where(Profile.id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file uploaded"
            )
        
        # Check file size (5MB limit)
        file_content = await file.read()
        if len(file_content) > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size too large. Maximum size is 5MB"
            )
        
        # Reset file pointer
        await file.seek(0)
        
        # Check file type
        allowed_types = {
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
            'image/gif': ['.gif'],
            'image/webp': ['.webp']
        }
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed"
            )
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{user_id}_{uuid.uuid4()}{file_extension}"
        
        # Upload to Supabase storage
        try:
            # Delete old profile image if exists
            if profile.avatar_url:
                # Extract filename from URL
                if "profile-images/" in profile.avatar_url:
                    old_filename = profile.avatar_url.split("profile-images/")[-1]
                else:
                    old_filename = profile.avatar_url.split('/')[-1]
                try:
                    # Use admin client for deletion
                    supabase_admin.storage.from_("profile-images").remove([old_filename])
                    logger.info(f"Deleted old profile image: {old_filename}")
                except Exception as e:
                    logger.warning(f"Failed to delete old profile image: {str(e)}")
            
            # Upload new image
            logger.info(f"Attempting to upload file: {unique_filename}")
            response = supabase.storage.from_("profile-images").upload(
                path=unique_filename,
                file=file_content,
                file_options={"content-type": file.content_type}
            )
            
            logger.info(f"Upload response: {response}")
            
            # Check if upload was successful
            if hasattr(response, 'status_code') and response.status_code != 200:
                logger.error(f"Upload failed with status: {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload image to storage: {response.status_code}"
                )
            
            # Check for error in response
            if hasattr(response, 'error') and response.error:
                logger.error(f"Upload error: {response.error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Storage upload error: {response.error}"
                )
            
            # Get public URL
            public_url = supabase.storage.from_("profile-images").get_public_url(unique_filename)
            logger.info(f"Generated public URL: {public_url}")
            
            # Update profile with new avatar URL
            profile.avatar_url = public_url
            profile.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(profile)
            
            return {
                "avatar_url": public_url,
                "message": "Profile image uploaded successfully"
            }
            
        except Exception as storage_error:
            logger.error(f"Storage error: {str(storage_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image to storage"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading profile image: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile image"
        )


@users_router.delete("/me/profile-image")
async def delete_profile_image(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete current user's profile image"""
    try:
        user_id = current_user["user_id"]
        
        # Get user profile
        result = await db.execute(
            select(Profile).where(Profile.id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        if not profile.avatar_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No profile image found"
            )
        
        # Delete from storage
        try:
            # Extract filename from URL more carefully
            if "profile-images/" in profile.avatar_url:
                # Handle full URL format
                filename = profile.avatar_url.split("profile-images/")[-1]
            else:
                # Handle simple filename
                filename = profile.avatar_url.split('/')[-1]
            
            logger.info(f"Attempting to delete file: {filename}")
            
            # Use admin client for deletion to ensure permissions
            response = supabase_admin.storage.from_("profile-images").remove([filename])
            logger.info(f"Delete response: {response}")
            
            # Check if deletion was successful
            if hasattr(response, 'error') and response.error:
                logger.error(f"Storage deletion error: {response.error}")
                raise Exception(f"Storage deletion failed: {response.error}")
            
            # Update profile
            profile.avatar_url = None
            profile.updated_at = datetime.utcnow()
            
            await db.commit()
            
            return {
                "message": "Profile image deleted successfully",
                "deleted_file": filename
            }
            
        except Exception as storage_error:
            logger.error(f"Storage deletion error: {str(storage_error)}")
            # Even if storage deletion fails, clear the URL from profile
            profile.avatar_url = None
            profile.updated_at = datetime.utcnow()
            await db.commit()
            
            return {
                "message": "Profile image reference removed (storage deletion may have failed)"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile image: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete profile image"
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

