from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
import uuid


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None


class UserProfileResponse(BaseModel):
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


# Role schemas
class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None


class Role(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


# Permission schemas
class PermissionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    resource: str
    action: str


class Permission(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    resource: str
    action: str
    created_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


# User role assignment schema
class UserRoleAssignment(BaseModel):
    user_id: str
    role_id: str

    @field_validator('user_id', 'role_id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


# User role update schema for admin operations
class UserRoleUpdate(BaseModel):
    user_id: str
    role: str  # 'user' or 'admin'
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ['user', 'admin']:
            raise ValueError('Role must be either "user" or "admin"')
        return v

    @field_validator('user_id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
