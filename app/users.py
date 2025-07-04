from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from dependencies.get_current_user import get_current_user, get_user_with_roles, require_admin, require_roles
from config import get_db
from models import Profile, Role
from routers.users.schemas import ProfileUpdate, UserProfileResponse, RoleCreate, Role as RoleSchema
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

# RBAC Management Endpoints
@users_router.post("/roles", response_model=Role)
async def create_role(
    role_data: RoleCreate,
    current_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new role (admin only)"""
    from models import Role
    
    # Check if role already exists
    stmt = select(Role).where(Role.name == role_data.name)
    result = await db.execute(stmt)
    existing_role = result.scalar_one_or_none()
    
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists"
        )
    
    role = Role(
        name=role_data.name,
        description=role_data.description
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    return role

@users_router.get("/roles", response_model=List[Role])
async def list_roles(
    current_user = Depends(require_roles(["admin", "moderator"])),
    db: AsyncSession = Depends(get_db)
):
    """List all roles (admin/moderator only)"""
    from models import Role
    
    stmt = select(Role)
    result = await db.execute(stmt)
    roles = result.scalars().all()
    
    return roles

@users_router.post("/{user_id}/roles/{role_name}")
async def assign_role(
    user_id: str,
    role_name: str,
    current_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Assign role to user (admin only)"""
    from models import Role
    
    # Get user profile
    user_stmt = select(Profile).options(selectinload(Profile.roles)).where(Profile.id == user_id)
    user_result = await db.execute(user_stmt)
    user_profile = user_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get role
    role_stmt = select(Role).where(Role.name == role_name)
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check if user already has this role
    if role in user_profile.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has this role"
        )
    
    # Assign role
    user_profile.roles.append(role)
    await db.commit()
    
    return {"message": f"Role '{role_name}' assigned to user"}

@users_router.delete("/{user_id}/roles/{role_name}")
async def remove_role(
    user_id: str,
    role_name: str,
    current_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Remove role from user (admin only)"""
    from models import Role
    
    # Get user profile
    user_stmt = select(Profile).options(selectinload(Profile.roles)).where(Profile.id == user_id)
    user_result = await db.execute(user_stmt)
    user_profile = user_result.scalar_one_or_none()
    
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Find and remove role
    role_to_remove = None
    for role in user_profile.roles:
        if role.name == role_name:
            role_to_remove = role
            break
    
    if not role_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User doesn't have this role"
        )
    
    user_profile.roles.remove(role_to_remove)
    await db.commit()
    
    return {"message": f"Role '{role_name}' removed from user"}

@users_router.get("/", response_model=List[UserProfileResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    stmt = select(Profile).options(selectinload(Profile.roles)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    profiles = result.scalars().all()
    
    return profiles
