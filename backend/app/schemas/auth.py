from pydantic import BaseModel, Field, field_validator

from app.schemas.user import normalize_email


class UserLogin(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return normalize_email(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
