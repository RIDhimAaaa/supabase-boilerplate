from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from dependencies.deps import get_current_user
from app.config import get_db
from app.models import Profile
from app.schemas import ProfileUpdate, UserProfileResponse
from typing import Optional, Dict, Any

users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile"""
    # Get profile from database using user_id from JWT
    stmt = select(Profile).where(Profile.id == current_user["id"])
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create profile if it doesn't exist
        profile = Profile(
            id=current_user["id"],
            email=current_user["email"],
            is_active=True
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    
    return profile

@users_router.put("/me", response_model=UserProfileResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile"""
    # Get existing profile
    stmt = select(Profile).where(Profile.id == current_user["id"])
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create profile if it doesn't exist
        profile = Profile(
            id=current_user["id"],
            email=current_user["email"],
            is_active=True
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    
    # Update only provided fields
    update_data = profile_update.model_dump(exclude_unset=True)
    
    if update_data:
        stmt = update(Profile).where(Profile.id == current_user["id"]).values(**update_data)
        await db.execute(stmt)
        await db.commit()
        
        # Get updated profile
        stmt = select(Profile).where(Profile.id == current_user["id"])
        result = await db.execute(stmt)
        profile = result.scalar_one()
    
    return profile
