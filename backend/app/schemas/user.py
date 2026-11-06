from datetime import datetime, timezone

import re

from pydantic import BaseModel, Field, field_validator, model_validator

MICRO = 1_000_000

# Pragmatic shape check (no extra dependency): one @, no spaces, a dot in the domain.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    return (value or "").strip().lower()


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name cannot be blank")
        return cleaned

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        email = normalize_email(value)
        if not _EMAIL_PATTERN.match(email):
            raise ValueError("Enter a valid email address")
        return email


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    budget_usd: float
    spent_usd: float

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _from_user_row(cls, data):
        """Convert a User row's micro-USD columns into USD fields for the API."""
        if not hasattr(data, "monthly_budget_micro_usd"):
            return data
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        spent = data.spent_micro_usd or 0 if data.spend_month == month else 0
        return {
            "id": data.id,
            "name": data.name,
            "email": data.email,
            "budget_usd": data.monthly_budget_micro_usd / MICRO,
            "spent_usd": spent / MICRO,
        }
