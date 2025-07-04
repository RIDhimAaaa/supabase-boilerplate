from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import JWT_SECRET_KEY
import jwt
import os
from typing import Dict, Any

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
        role = user_metadata.get("role", "user")

        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create a user-like object with the decoded information
        user = {
            "id": user_id,
            "email": email, 
            "role": role,
            "payload": payload
        }
        
        return user
        
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
