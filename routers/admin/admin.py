from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from dependencies.rbac import require_admin, require_admin_write, require_user_management, require_user_management_write
from dependencies.get_current_user import get_current_user
from routers.admin.schemas import UserListItem, UserListResponse, RoleUpdateResponse, UserRoleUpdate
from routers.admin.helpers import get_paginated_users, get_user_by_id_admin, update_user_role_admin
from sqlalchemy.ext.asyncio import AsyncSession
from config import get_db
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_model=UserListResponse)
async def list_all_users(
    page: int = 1,
    limit: int = 20,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _rbac_check = Depends(require_user_management)
):
    """
    Admin only: List all users with pagination and optional role filter
    """
    return await get_paginated_users(db, page, limit, role)


@router.put("/users/{user_id}/role", response_model=RoleUpdateResponse)
async def update_user_role(
    user_id: str,
    new_role: str = Form(..., description="New role: user, admin"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _rbac_check = Depends(require_user_management_write)
):
    """
    Admin only: Update user role
    """
    return await update_user_role_admin(user_id, new_role, current_user, db)


@router.post("/users/update-role-no-auth", response_model=RoleUpdateResponse)
async def update_user_role_no_auth(
    role_update: UserRoleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update user role without authentication - Use this ONLY for initial admin setup
    TODO: Remove this route after all admins have been created
    """
    # Create a mock current_user for the helper function
    mock_current_user = {"role": "system", "user_id": "system", "email": "system@admin.com"}
    return await update_user_role_admin(role_update.user_id, role_update.role, mock_current_user, db)


@router.get("/users/{user_id}", response_model=UserListItem)
async def get_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _rbac_check = Depends(require_user_management)
):
    """
    Admin only: Get specific user by ID
    """
    return await get_user_by_id_admin(user_id, db)
