"""
Security utilities for authentication and authorization
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import User, TokenData, UserRole

# Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        token_data = TokenData(user_id=user_id)
        return token_data
    except JWTError:
        return None

async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> Optional[User]:
    """Get user by ID from database"""
    try:
        user_doc = await db.users.find_one({"id": user_id})
        if user_doc:
            # Remove MongoDB _id for Pydantic
            user_doc.pop("_id", None)
            return User(**user_doc)
        return None
    except Exception:
        return None

async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[User]:
    """Get user by email from database"""
    try:
        user_doc = await db.users.find_one({"email": email})
        if user_doc:
            # Remove MongoDB _id for Pydantic
            user_doc.pop("_id", None)
            return User(**user_doc)
        return None
    except Exception:
        return None

async def authenticate_user(db: AsyncIOMotorDatabase, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password"""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

class AuthenticationManager:
    """Manages authentication and authorization"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
        """Get current authenticated user"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        token_data = verify_token(credentials.credentials)
        if token_data is None:
            raise credentials_exception
        
        user = await get_user_by_id(self.db, token_data.user_id)
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return user
    
    async def get_current_active_user(self, current_user: User = None) -> User:
        """Get current active user (dependency injection helper)"""
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        
        return current_user
    
    def require_role(self, required_roles: list):
        """Decorator to require specific user roles"""
        def role_checker(current_user: User = None):
            if current_user is None:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if current_user.role not in required_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Required roles: {required_roles}"
                )
            
            return current_user
        
        return role_checker
    
    async def get_optional_current_user(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
        """Get current user if authenticated, None otherwise (for optional auth)"""
        if not credentials:
            return None
        
        try:
            token_data = verify_token(credentials.credentials)
            if token_data is None:
                return None
            
            user = await get_user_by_id(self.db, token_data.user_id)
            if user is None or not user.is_active:
                return None
            
            return user
        
        except Exception:
            return None