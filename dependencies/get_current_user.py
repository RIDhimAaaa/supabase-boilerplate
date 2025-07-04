from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import JWT_SECRET_KEY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from config import get_db
import jwt
import os
import logging
from typing import Dict, Any, List, Callable

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get current user from JWT token"""
    try:
        token = credentials.credentials
        
        # Get JWT secret from Supabase anon key
        jwt_secret = JWT_SECRET_KEY
        
        # Decode the JWT token
        payload = jwt.decode(
            token, 
            jwt_secret, 
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_exp": True, "verify_aud": False}
        )
        
        # Extract user information from payload
        user_id = payload.get("sub")
        email = payload.get("email")
        user_metadata = payload.get("user_metadata", {})
        role = user_metadata.get("role", "user")  # default to user

        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create a user-like object with the decoded information
        current_user = {
            "user_id": user_id,
            "email": email, 
            "role": role,
            "payload": payload
        }

        logger.info(f"User {user_id} authenticated via JWT role: {role}")
        
        # Set current user in request state for RBAC
        request.state.current_user = current_user
        
        return current_user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )



