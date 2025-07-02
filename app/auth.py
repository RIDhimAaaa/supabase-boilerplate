from fastapi import APIRouter, HTTPException, Query
from pydantic import EmailStr, BaseModel
from app.schemas import UserSignup, UserLogin
from app.config import supabase

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

@auth_router.post("/login")
def login(user: UserLogin):
    result = supabase.auth.sign_in_with_password({
        "email": user.email,
        "password": user.password
    })

    if result.session is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "access_token": result.session.access_token,
        "user": result.user
    }

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
        # Set the access token in the Supabase client
        supabase.auth.set_session(access_token, '')
        
        # Update the password using the access token
        update_result = supabase.auth.update_user({
            'password': reset_data.password
        })
        
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
