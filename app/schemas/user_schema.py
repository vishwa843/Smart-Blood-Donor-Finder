"""Pydantic schemas for User authentication."""

from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional


# -----------------------------
# Base User Schema
# -----------------------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "donor"  # donor, patient, hospital, admin


# -----------------------------
# User Registration
# -----------------------------
class UserCreate(UserBase):
    password: str


# -----------------------------
# User Update Profile
# -----------------------------
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


# -----------------------------
# Change Password Schema
# -----------------------------
class ChangePassword(BaseModel):
    old_password: str
    new_password: str


# -----------------------------
# User Login
# -----------------------------
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# -----------------------------
# User Response
# -----------------------------
class UserResponse(UserBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# JWT Token Response
# -----------------------------
class Token(BaseModel):
    access_token: str
    token_type: str


# -----------------------------
# Token Payload
# -----------------------------
class TokenData(BaseModel):
    email: Optional[str] = None