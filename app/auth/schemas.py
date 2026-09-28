import uuid
from zoneinfo import available_timezones

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=100)
    timezone: str = "America/Buenos_Aires"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, v: str) -> str:
        if v not in available_timezones():
            raise ValueError("Zona horaria inválida")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    name: str
    timezone: str
