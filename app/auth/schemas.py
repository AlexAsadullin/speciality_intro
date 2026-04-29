from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8)

    model_config = {"json_schema_extra": {"example": {"username": "trader1", "email": "trader@example.com", "password": "securepass"}}}


class LoginRequest(BaseModel):
    username: str
    password: str

    model_config = {"json_schema_extra": {"example": {"username": "trader1", "password": "securepass"}}}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str

    model_config = {"json_schema_extra": {"example": {"refresh_token": "<jwt-refresh-token>"}}}


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
