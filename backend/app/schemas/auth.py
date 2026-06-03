from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)
    role: str = Field(default="analyst")
    tenant_id: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"admin", "manager", "analyst", "viewer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class RefreshRequest(BaseModel):
    refresh_token: str
