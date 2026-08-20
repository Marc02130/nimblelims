"""
Pydantic schemas for authentication
"""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Request schema for user login"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Response schema for successful login"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    email: str
    role: str
    permissions: List[str]
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    """Request schema for changing password (Q7)"""
    current_password: str
    new_password: str = Field(..., min_length=1)


class ChangePasswordResponse(BaseModel):
    """Response after successful password change"""
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False
    message: str = "Password updated"


class VerifyEmailRequest(BaseModel):
    """Request schema for email verification"""
    email: EmailStr
    token: str


class VerifyEmailResponse(BaseModel):
    """Response schema for email verification"""
    message: str
    verified: bool


class TokenData(BaseModel):
    """Schema for JWT token payload"""
    user_id: str
    username: str
    role: str
    permissions: List[str]
    must_change_password: bool = False
