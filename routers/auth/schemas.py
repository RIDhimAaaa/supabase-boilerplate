from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
import uuid

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str