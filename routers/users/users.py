from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies.get_current_user import get_current_user
from config import get_db
from routers.users.schemas import ProfileUpdate, UserProfileResponse, ProfileImageUpload
from routers.users.helpers import (
    get_or_create_user_profile,
    create_user_response_data,
    update_user_profile,
    handle_profile_image_upload,
    handle_profile_image_deletion
)
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)
users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile using optimized JWT structure"""
    profile = await get_or_create_user_profile(current_user, db)
    user_data = create_user_response_data(profile, current_user)
    return UserProfileResponse.model_validate(user_data)


@users_router.put("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    profile_update: ProfileUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile information"""
    return await update_user_profile(profile_update, current_user, db)


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
    return await handle_profile_image_upload(file, current_user, db)


@users_router.delete("/me/profile-image")
async def delete_profile_image(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete current user's profile image"""
    return await handle_profile_image_deletion(current_user, db)

