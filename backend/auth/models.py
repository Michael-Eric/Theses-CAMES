"""
Authentication models for Thèses CAMES
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import uuid

class UserRole(str, Enum):
    visitor = "visitor"
    author = "author"
    university = "university"
    admin = "admin"

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: UserRole = UserRole.visitor
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    orcid: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    profile_picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    claimed_theses: List[str] = []  # List of thesis IDs claimed by this user
    settings: Dict[str, Any] = {}

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: UserRole = UserRole.visitor
    orcid: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    orcid: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    profile_picture: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    orcid: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    profile_picture: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    claimed_theses: List[str] = []

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None

class ThesisClaim(BaseModel):
    thesis_id: str
    user_id: str
    claim_type: str = "ownership"  # ownership, correction, etc.
    message: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

class ThesisClaimCreate(BaseModel):
    thesis_id: str
    claim_type: str = "ownership"
    message: Optional[str] = None

class ThesisReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thesis_id: str
    user_id: Optional[str] = None
    report_type: str  # copyright, metadata_error, inappropriate_content
    description: str
    status: str = "pending"  # pending, reviewing, resolved, rejected
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    resolution: Optional[str] = None

class ThesisReportCreate(BaseModel):
    thesis_id: str
    report_type: str
    description: str