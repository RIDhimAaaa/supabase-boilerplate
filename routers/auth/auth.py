from fastapi import APIRouter, HTTPException, Query
from pydantic import EmailStr, BaseModel
from routers.auth.schemas import UserSignup, UserLogin, RefreshTokenRequest, AuthResponse
from routers.auth.helpers import create_auth_response, create_refresh_response, handle_auth_error, validate_token_refresh
from config import supabase
import logging

logger = logging.getLogger(__name__)

class PasswordReset(BaseModel):
    password: str

auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/signup")
def signup(user: UserSignup):
    result = supabase.auth.sign_up(
        {"email": user.email, "password": user.password}
    )

    if result.user is None:
        raise HTTPException(status_code=400, detail="Signup failed")

    supabase.table("profiles").insert({
        "id": result.user.id,
        "username": user.username,
        "email": user.email
    }).execute()

    return {"message": "Check your email to confirm sign-up."}

@auth_router.post("/login", response_model=AuthResponse)
def login(user: UserLogin):
    try:
        result = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })

        if result.session is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        logger.info(f"User {user.email} logged in successfully")
        return create_auth_response(result.session, result.user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_auth_error(e, "Login")


@auth_router.post("/refresh", response_model=AuthResponse)
def refresh_token(refresh_request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    """
    try:
        # Validate refresh token format
        if not validate_token_refresh(refresh_request.refresh_token):
            raise HTTPException(status_code=400, detail="Invalid refresh token format")
        
        result = supabase.auth.refresh_session(refresh_request.refresh_token)
        
        if result.session is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        logger.info("Token refreshed successfully")
        return create_refresh_response(result.session)
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_auth_error(e, "Token refresh")


@auth_router.post("/logout")
def logout():
    """
    Logout user (client should discard tokens)
    """
    try:
        # Supabase doesn't require server-side logout for JWTs
        # Client should discard both access and refresh tokens
        logger.info("User logged out")
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Logout failed: {str(e)}")

@auth_router.post("/forgot-password")
def forgot_password(email: EmailStr):
    try:
        supabase.auth.reset_password_email(email)
        return {"message": "Check your email for reset instructions."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to send reset email: {str(e)}")


@auth_router.post("/reset-password")
def reset_password(reset_data: PasswordReset, access_token: str = Query(...)):
    try:
        import jwt
        from config import supabase_admin
        
        # Decode the JWT to get user ID
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        user_id = decoded_token.get('sub')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token")
        
        # Update user password using admin client
        update_result = supabase_admin.auth.admin.update_user_by_id(
            user_id, 
            {"password": reset_data.password}
        )
        
        if update_result.user:
            return {"message": "Password reset successfully!"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update password")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Password reset failed: {str(e)}")



@auth_router.get("/confirm")
def confirm_email(token_hash: str = Query(...), type: str = Query(...)):
    try:
        result = supabase.auth.verify_otp({
            'token_hash': token_hash,
            'type': type
        })
        
        if result.user:
            return {"message": "Email confirmed successfully!", "user": result.user}
        else:
            raise HTTPException(status_code=400, detail="Invalid confirmation token")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Confirmation failed: {str(e)}")

@auth_router.post("/resend-confirmation")
def resend_confirmation(email: EmailStr):
    try:
        result = supabase.auth.resend(type="signup", email=email)
        return {"message": "Confirmation email sent. Check your inbox."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to resend confirmation: {str(e)}")
