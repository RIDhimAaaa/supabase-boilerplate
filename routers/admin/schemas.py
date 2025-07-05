from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import uuid


class UserRoleUpdate(BaseModel):
    user_id: str
    role: str
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ['user', 'admin']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {allowed_roles}')
        return v


class UserListItem(BaseModel):
    id: str
    user_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    role: str = "user"
    
    @field_validator('id', 'user_id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserListItem]
    page: int
    limit: int
    total: int
    total_pages: int


class RoleUpdateResponse(BaseModel):
    message: str
    user_id: str
    old_role: str
    new_role: str
    updated_by: str
    metadata_updated: bool
    note: str
