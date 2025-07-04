from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.auth.auth import auth_router
from routers.users import users_router

app = FastAPI(
    title="Supabase FastAPI Boilerplate",
    description="A FastAPI application with Supabase authentication",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
