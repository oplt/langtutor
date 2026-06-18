from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignUpIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)
    gender: Optional[str] = Field(default=None, max_length=32)
    age: Optional[int] = Field(default=None, ge=10, le=100)
    native_language: Optional[str] = Field(default="en", max_length=16)
    target_language: Optional[str] = Field(default="nl", max_length=16)
    cefr_goal: Optional[str] = Field(default=None, max_length=8)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    native_language: Optional[str] = None
    target_language: Optional[str] = None
    cefr_goal: Optional[str] = None


class AuthOut(BaseModel):
    access_token: str
    user: UserOut


class UserProfileUpdateIn(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    gender: Optional[str] = Field(default=None, max_length=32)
    age: Optional[int] = Field(default=None, ge=10, le=100)
    native_language: Optional[str] = Field(default=None, max_length=16)
    target_language: Optional[str] = Field(default=None, max_length=16)
    cefr_goal: Optional[str] = Field(default=None, max_length=8)
