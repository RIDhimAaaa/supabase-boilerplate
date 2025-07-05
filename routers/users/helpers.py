"""
Helper functions for user management operations
Contains business logic separated from route handlers for better maintainability
"""
import logging
import uuid
import os
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func

from config import supabase, supabase_admin
from models import Profile
from routers.users.schemas import ProfileUpdate, UserProfileResponse

logger = logging.getLogger(__name__)


async def get_or_create_user_profile(
    current_user: Dict[str, Any], 
    db: AsyncSession
) -> Profile:
    """
    Get user profile from database or create if it doesn't exist
    
    Args:
        current_user: Current authenticated user info from JWT
        db: Database session
        
    Returns:
        Profile: User profile object
    """
    user_id = current_user["user_id"]
    
    # Get user profile
    result = await db.execute(
        select(Profile).where(Profile.id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create profile if it doesn't exist
        profile = Profile(
            id=user_id,
            email=current_user["email"],
            is_active=True
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        logger.info(f"Created new profile for user: {user_id}")
    
    return profile


def create_user_response_data(
    profile: Profile, 
    current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create user response data combining profile and JWT info
    
    Args:
        profile: User profile from database
        current_user: Current authenticated user info from JWT
        
    Returns:
        Dict: Combined user data for API response
    """
    return {
        **profile.__dict__,
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "role": current_user["role"]
    }


async def update_user_profile(
    profile_update: ProfileUpdate,
    current_user: Dict[str, Any],
    db: AsyncSession
) -> UserProfileResponse:
    """
    Update user profile with provided data
    
    Args:
        profile_update: Profile update data
        current_user: Current authenticated user info
        db: Database session
        
    Returns:
        UserProfileResponse: Updated user profile
        
    Raises:
        HTTPException: If update fails
    """
    try:
        # Get or create profile
        profile = await get_or_create_user_profile(current_user, db)
        
        # Update only provided fields
        update_data = profile_update.model_dump(exclude_unset=True)
        
        if update_data:
            for field, value in update_data.items():
                setattr(profile, field, value)
            
            await db.commit()
            await db.refresh(profile)
            logger.info(f"Updated profile for user: {current_user['user_id']}")
        
        # Create response data
        user_data = create_user_response_data(profile, current_user)
        return UserProfileResponse.model_validate(user_data)
        
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


def validate_uploaded_file(file: UploadFile, file_content: bytes) -> None:
    """
    Validate uploaded file for size and type
    
    Args:
        file: Uploaded file object
        file_content: File content as bytes
        
    Raises:
        HTTPException: If validation fails
    """
    # Check if file was provided
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded"
        )
    
    # Check file size (5MB limit)
    if len(file_content) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size too large. Maximum size is 5MB"
        )
    
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


def generate_unique_filename(user_id: str, original_filename: str) -> str:
    """
    Generate unique filename for storage
    
    Args:
        user_id: User ID
        original_filename: Original file name
        
    Returns:
        str: Unique filename
    """
    file_extension = os.path.splitext(original_filename)[1].lower()
    return f"{user_id}_{uuid.uuid4()}{file_extension}"


async def delete_old_profile_image(avatar_url: str) -> None:
    """
    Delete old profile image from storage
    
    Args:
        avatar_url: URL of the image to delete
    """
    try:
        # Extract filename from URL
        if "profile-images/" in avatar_url:
            old_filename = avatar_url.split("profile-images/")[-1]
        else:
            old_filename = avatar_url.split('/')[-1]
        
        # Use admin client for deletion
        supabase_admin.storage.from_("profile-images").remove([old_filename])
        logger.info(f"Deleted old profile image: {old_filename}")
        
    except Exception as e:
        logger.warning(f"Failed to delete old profile image: {str(e)}")


async def upload_image_to_storage(
    file_content: bytes,
    filename: str,
    content_type: str
) -> str:
    """
    Upload image to Supabase storage
    
    Args:
        file_content: Image file content
        filename: Unique filename
        content_type: MIME type of the file
        
    Returns:
        str: Public URL of uploaded image
        
    Raises:
        HTTPException: If upload fails
    """
    try:
        logger.info(f"Attempting to upload file: {filename}")
        
        # Upload to Supabase storage
        response = supabase.storage.from_("profile-images").upload(
            path=filename,
            file=file_content,
            file_options={"content-type": content_type}
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
        public_url = supabase.storage.from_("profile-images").get_public_url(filename)
        logger.info(f"Generated public URL: {public_url}")
        
        return public_url
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Storage upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image to storage"
        )


async def handle_profile_image_upload(
    file: UploadFile,
    current_user: Dict[str, Any],
    db: AsyncSession
) -> Dict[str, str]:
    """
    Handle complete profile image upload process
    
    Args:
        file: Uploaded image file
        current_user: Current authenticated user info
        db: Database session
        
    Returns:
        Dict: Response with avatar URL and message
        
    Raises:
        HTTPException: If any step fails
    """
    try:
        # Get user profile
        profile = await get_or_create_user_profile(current_user, db)
        
        # Read and validate file
        file_content = await file.read()
        validate_uploaded_file(file, file_content)
        
        # Generate unique filename
        unique_filename = generate_unique_filename(current_user["user_id"], file.filename)
        
        # Delete old image if exists
        if profile.avatar_url:
            await delete_old_profile_image(profile.avatar_url)
        
        # Upload new image
        public_url = await upload_image_to_storage(
            file_content, 
            unique_filename, 
            file.content_type
        )
        
        # Update profile with new avatar URL
        profile.avatar_url = public_url
        profile.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(profile)
        
        return {
            "avatar_url": public_url,
            "message": "Profile image uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in profile image upload: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile image"
        )


def extract_filename_from_url(avatar_url: str) -> str:
    """
    Extract filename from avatar URL
    
    Args:
        avatar_url: Full URL of the avatar image
        
    Returns:
        str: Extracted filename
    """
    if "profile-images/" in avatar_url:
        return avatar_url.split("profile-images/")[-1]
    else:
        return avatar_url.split('/')[-1]


async def delete_image_from_storage(filename: str) -> None:
    """
    Delete image from Supabase storage
    
    Args:
        filename: Name of file to delete
        
    Raises:
        Exception: If deletion fails
    """
    logger.info(f"Attempting to delete file: {filename}")
    
    # Use admin client for deletion to ensure permissions
    response = supabase_admin.storage.from_("profile-images").remove([filename])
    logger.info(f"Delete response: {response}")
    
    # Check if deletion was successful
    if hasattr(response, 'error') and response.error:
        logger.error(f"Storage deletion error: {response.error}")
        raise Exception(f"Storage deletion failed: {response.error}")


async def handle_profile_image_deletion(
    current_user: Dict[str, Any],
    db: AsyncSession
) -> Dict[str, str]:
    """
    Handle complete profile image deletion process
    
    Args:
        current_user: Current authenticated user info
        db: Database session
        
    Returns:
        Dict: Response with deletion status
        
    Raises:
        HTTPException: If user not found or deletion fails
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
        
        if not profile.avatar_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No profile image found"
            )
        
        # Extract filename and delete from storage
        filename = extract_filename_from_url(profile.avatar_url)
        
        try:
            await delete_image_from_storage(filename)
            
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


async def get_all_user_profiles(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> list[UserProfileResponse]:
    """
    Get all user profiles for admin listing
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[UserProfileResponse]: List of user profiles
        
    Raises:
        HTTPException: If listing fails
    """
    try:
        # Get all profiles
        result = await db.execute(
            select(Profile).offset(skip).limit(limit)
        )
        profiles = result.scalars().all()
        
        # Get user roles from Supabase for each profile
        users = []
        for profile in profiles:
            try:
                # Get user from Supabase to fetch role
                supabase_user = supabase_admin.auth.admin.get_user_by_id(str(profile.id))
                user_role = "user"  # Default fallback
                
                if supabase_user.user and supabase_user.user.user_metadata:
                    user_role = supabase_user.user.user_metadata.get("role", "user")
                
                user_data = {
                    **profile.__dict__,
                    "user_id": str(profile.id),
                    "role": user_role
                }
                users.append(UserProfileResponse.model_validate(user_data))
                
            except Exception as role_error:
                logger.warning(f"Failed to get role for user {profile.id}: {str(role_error)}")
                # Fallback to default role if can't fetch from Supabase
                user_data = {
                    **profile.__dict__,
                    "user_id": str(profile.id),
                    "role": "user"
                }
                users.append(UserProfileResponse.model_validate(user_data))
        
        return users
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


async def update_user_role_via_admin_api(
    user_id: str,
    role: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Update user role using Supabase Admin API
    
    Args:
        user_id: User ID to update
        role: New role to assign
        db: Database session (kept for consistency but not used for role storage)
        
    Returns:
        Dict: Response with update status
        
    Raises:
        HTTPException: If user not found or update fails
    """
    try:
        # Update user metadata using Supabase Admin API
        response = supabase_admin.auth.admin.update_user_by_id(
            uid=user_id,
            attributes={
                "user_metadata": {
                    "role": role
                }
            }
        )
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Note: We don't store roles in the database, only in Supabase user_metadata
        # This ensures consistency with JWT-based authentication
        
        logger.info(f"Updated role for user {user_id} to {role}")
        
        return {
            "message": f"User role updated to {role} successfully",
            "user_id": user_id,
            "new_role": role,
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
