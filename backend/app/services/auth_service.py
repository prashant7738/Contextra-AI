from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories import user_repository
from app.core.auth import verify_password, create_access_token, create_refresh_token, verify_token
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import TokenResponse, UserLogin


def register_user(db: Session, user_data: UserCreate) -> TokenResponse:
    """Register a new user and return access and refresh tokens."""
    # Check if user already exists
    existing_user = user_repository.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = user_repository.create_user(
        db,
        name=user_data.name,
        email=user_data.email,
        password=user_data.password
    )
    
    # Generate tokens
    return _generate_tokens(user)


def login_user(db: Session, login_data: UserLogin) -> TokenResponse:
    """Authenticate user and return access and refresh tokens."""
    user = user_repository.get_user_by_email(db, login_data.email)
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return _generate_tokens(user)


def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    """Generate a new access token from a refresh token."""
    payload = verify_token(refresh_token, token_type="refresh")
    
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = int(payload["sub"])
    user = user_repository.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return _generate_tokens(user)


def get_current_user(db: Session, token: str) -> UserResponse:
    """Get current user from access token."""
    payload = verify_token(token, token_type="access")
    
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = int(payload["sub"])
    user = user_repository.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return UserResponse.model_validate(user)


def _generate_tokens(user) -> TokenResponse:
    """Generate access and refresh tokens for a user."""
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )
