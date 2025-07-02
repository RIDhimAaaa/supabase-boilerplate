# app/users.py

from fastapi import APIRouter, Depends
from dependencies.deps import get_current_user
from app.config import supabase

users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.get("/me")
def get_profile(user=Depends(get_current_user)):
    profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute().data
    return profile
