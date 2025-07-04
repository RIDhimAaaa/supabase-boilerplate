from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from dependencies.deps import get_current_user, get_user_with_roles, require_admin, require_roles
from app.config import get_db
from app.models import Profile, Role
from app.schemas import ProfileUpdate, UserProfileResponse, RoleCreate, Role as RoleSchema
from typing import Optional, Dict, Any, List

users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    profile: Profile = Depends(get_user_with_roles),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile with roles"""
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
        
        # Get updated profile with roles
        stmt = select(Profile).where(Profile.id == current_user["id"])
        result = await db.execute(stmt)
        profile = result.scalar_one()
    
    return profile

# Admin-only endpoints
@users_router.get("/", response_model=List[UserProfileResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    stmt = select(Profile).offset(skip).limit(limit)
    result = await db.execute(stmt)
    profiles = result.scalars().all()
    return profiles

@users_router.post("/roles", response_model=RoleSchema)
async def create_role(
    role_data: RoleCreate,
    admin_user: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new role (admin only)"""
    role = Role(
        name=role_data.name,
        description=role_data.description
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role

@users_router.post("/{user_id}/roles/{role_name}")
async def assign_role_to_user(
    user_id: str,
    role_name: str,
    admin_user: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Assign role to user (admin only)"""
    # Get user
    user_stmt = select(Profile).where(Profile.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get role
    role_stmt = select(Role).where(Role.name == role_name)
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Add role if not already assigned
    if role not in user.roles:
        user.roles.append(role)
        await db.commit()
    
    return {"message": f"Role '{role_name}' assigned to user"}

@users_router.delete("/{user_id}/roles/{role_name}")
async def remove_role_from_user(
    user_id: str,
    role_name: str,
    admin_user: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Remove role from user (admin only)"""
    # Get user with roles
    user_stmt = select(Profile).where(Profile.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Find and remove role
    role_to_remove = None
    for role in user.roles:
        if role.name == role_name:
            role_to_remove = role
            break
    
    if role_to_remove:
        user.roles.remove(role_to_remove)
        await db.commit()
        return {"message": f"Role '{role_name}' removed from user"}
    else:
        raise HTTPException(status_code=404, detail="User does not have this role")
