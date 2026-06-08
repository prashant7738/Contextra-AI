from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import UserLogin, TokenResponse, RefreshTokenRequest
from app.services import auth_service
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])



@router.post("/register", response_model=TokenResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    return auth_service.register_user(db, user_data)


@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login user with email and password."""
    return auth_service.login_user(db, login_data)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    return auth_service.refresh_access_token(db, request.refresh_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current authenticated user."""
    return current_user
