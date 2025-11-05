"""
Pydantic schemas for authentication
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
import uuid


# ============================================================================
# Magic Link Request/Response
# ============================================================================

class MagicLinkRequest(BaseModel):
    """Request to send magic link"""
    email: EmailStr = Field(..., description="User email address")


class MagicLinkResponse(BaseModel):
    """Response after requesting magic link"""
    message: str = "Magic link sent to your email"
    email: str


# ============================================================================
# User
# ============================================================================

class UserResponse(BaseModel):
    """User information"""
    id: uuid.UUID
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# Token Verify
# ============================================================================

class TokenVerifyRequest(BaseModel):
    """Request to verify magic link token"""
    token: str = Field(..., min_length=20)


class TokenVerifyResponse(BaseModel):
    """Response after verifying token"""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse


class UserCreate(BaseModel):
    """Create new user"""
    email: EmailStr


# ============================================================================
# Auth
# ============================================================================

class LogoutRequest(BaseModel):
    """Logout request"""
    token: str


class LogoutResponse(BaseModel):
    """Logout response"""
    message: str = "Successfully logged out"
