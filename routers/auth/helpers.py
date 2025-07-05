"""
Helper functions for authentication operations
Contains business logic for token management and user authentication
"""
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from config import supabase
from routers.auth.schemas import AuthResponse

logger = logging.getLogger(__name__)


def create_auth_response(session, user) -> AuthResponse:
    """
    Create standardized auth response with tokens
    
    Args:
        session: Supabase session object
        user: Supabase user object
        
    Returns:
        AuthResponse: Standardized auth response
    """
    try:
        user_data = user.model_dump() if hasattr(user, 'model_dump') else user.__dict__
        
        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user=user_data
        )
    except Exception as e:
        logger.error(f"Failed to create auth response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create authentication response"
        )


def create_refresh_response(session) -> AuthResponse:
    """
    Create standardized refresh token response
    
    Args:
        session: Supabase session object
        
    Returns:
        AuthResponse: Standardized refresh response (without user data)
    """
    try:
        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user=None  # No user data needed for refresh response
        )
    except Exception as e:
        logger.error(f"Failed to create refresh response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create refresh token response"
        )


def handle_auth_error(error: Exception, operation: str) -> HTTPException:
    """
    Handle authentication errors consistently
    
    Args:
        error: The exception that occurred
        operation: The operation that failed (login, refresh, etc.)
        
    Returns:
        HTTPException: Appropriate HTTP exception
    """
    error_msg = str(error).lower()
    
    if "invalid login credentials" in error_msg or "invalid email or password" in error_msg:
        return HTTPException(status_code=401, detail="Invalid email or password")
    elif "email not confirmed" in error_msg:
        return HTTPException(status_code=401, detail="Please confirm your email before logging in")
    elif "invalid refresh token" in error_msg or "refresh_token" in error_msg:
        return HTTPException(status_code=401, detail="Invalid or expired refresh token")
    elif "token" in error_msg and "expired" in error_msg:
        return HTTPException(status_code=401, detail="Token has expired")
    else:
        logger.error(f"{operation} failed: {str(error)}")
        return HTTPException(status_code=400, detail=f"{operation} failed")


def validate_token_refresh(refresh_token: str) -> bool:
    """
    Validate refresh token format (basic validation)
    
    Args:
        refresh_token: The refresh token to validate
        
    Returns:
        bool: True if token format is valid
    """
    if not refresh_token or not isinstance(refresh_token, str):
        return False
    
    # Basic validation - refresh tokens should be substantial strings
    if len(refresh_token) < 10:
        return False
        
    return True
