"""
Authentication routes for Thèses CAMES
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import (
    User, UserCreate, UserUpdate, UserLogin, UserResponse, 
    Token, ThesisClaim, ThesisClaimCreate, ThesisReport, ThesisReportCreate,
    UserRole
)
from .security import (
    get_password_hash, authenticate_user, create_access_token,
    AuthenticationManager, security
)

def create_auth_router(db: AsyncIOMotorDatabase) -> APIRouter:
    """Create authentication router with database dependency"""
    
    router = APIRouter(prefix="/auth", tags=["authentication"])
    auth_manager = AuthenticationManager(db)
    
    @router.post("/register", response_model=UserResponse)
    async def register(user_data: UserCreate):
        """Register a new user"""
        try:
            # Check if user already exists
            existing_user = await db.users.find_one({"email": user_data.email})
            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered"
                )
            
            # Create new user
            hashed_password = get_password_hash(user_data.password)
            
            user = User(
                email=user_data.email,
                name=user_data.name,
                hashed_password=hashed_password,
                role=user_data.role,
                orcid=user_data.orcid,
                institution=user_data.institution,
                country=user_data.country
            )
            
            # Save to database
            user_dict = user.dict()
            user_dict["created_at"] = user_dict["created_at"].isoformat()
            user_dict["updated_at"] = user_dict["updated_at"].isoformat()
            
            await db.users.insert_one(user_dict)
            
            # Return user response (without password)
            return UserResponse(**user.dict())
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    
    @router.post("/login", response_model=Token)
    async def login(user_credentials: UserLogin):
        """Login user and return access token"""
        try:
            user = await authenticate_user(db, user_credentials.email, user_credentials.password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Update last login
            await db.users.update_one(
                {"id": user.id},
                {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
            )
            
            # Create access token
            access_token_expires = timedelta(minutes=30 * 24 * 60)  # 30 days
            access_token = create_access_token(
                data={"sub": user.id}, expires_delta=access_token_expires
            )
            
            return {"access_token": access_token, "token_type": "bearer"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
    
    @router.get("/me", response_model=UserResponse)
    async def get_current_user_info(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        """Get current user information"""
        try:
            current_user = await auth_manager.get_current_user(credentials)
            return UserResponse(**current_user.dict())
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    @router.put("/me", response_model=UserResponse)
    async def update_current_user(
        user_update: UserUpdate,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        """Update current user profile"""
        try:
            current_user = await auth_manager.get_current_user(credentials)
            
            # Prepare update data
            update_data = {k: v for k, v in user_update.dict().items() if v is not None}
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update user in database
            await db.users.update_one(
                {"id": current_user.id},
                {"$set": update_data}
            )
            
            # Get updated user
            updated_user_doc = await db.users.find_one({"id": current_user.id})
            updated_user_doc.pop("_id", None)
            updated_user = User(**updated_user_doc)
            
            return UserResponse(**updated_user.dict())
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")
    
    @router.post("/claim-thesis", response_model=dict)
    async def claim_thesis(
        claim_data: ThesisClaimCreate,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        """Claim ownership of a thesis"""
        try:
            current_user = await auth_manager.get_current_user(credentials)
            
            # Check if thesis exists
            thesis = await db.theses.find_one({"id": claim_data.thesis_id})
            if not thesis:
                raise HTTPException(status_code=404, detail="Thesis not found")
            
            # Check if already claimed by this user
            existing_claim = await db.thesis_claims.find_one({
                "thesis_id": claim_data.thesis_id,
                "user_id": current_user.id
            })
            if existing_claim:
                raise HTTPException(status_code=400, detail="You have already claimed this thesis")
            
            # Create claim
            claim = ThesisClaim(
                thesis_id=claim_data.thesis_id,
                user_id=current_user.id,
                claim_type=claim_data.claim_type,
                message=claim_data.message
            )
            
            claim_dict = claim.dict()
            claim_dict["created_at"] = claim_dict["created_at"].isoformat()
            
            await db.thesis_claims.insert_one(claim_dict)
            
            return {"message": "Thesis claim submitted successfully", "status": "pending"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Claim submission failed: {str(e)}")
    
    @router.post("/report-thesis", response_model=dict)
    async def report_thesis(report_data: ThesisReportCreate):
        """Report a thesis for copyright or content issues"""
        try:
            # Check if thesis exists
            thesis = await db.theses.find_one({"id": report_data.thesis_id})
            if not thesis:
                raise HTTPException(status_code=404, detail="Thesis not found")
            
            # Create report
            report = ThesisReport(
                thesis_id=report_data.thesis_id,
                report_type=report_data.report_type,
                description=report_data.description
            )
            
            report_dict = report.dict()
            report_dict["created_at"] = report_dict["created_at"].isoformat()
            
            await db.thesis_reports.insert_one(report_dict)
            
            return {"message": "Report submitted successfully", "status": "pending"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Report submission failed: {str(e)}")
    
    @router.get("/my-claims", response_model=List[dict])
    async def get_my_claims(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        """Get current user's thesis claims"""
        try:
            current_user = await auth_manager.get_current_user(credentials)
            
            claims = await db.thesis_claims.find({"user_id": current_user.id}).to_list(length=100)
            
            # Clean up MongoDB ObjectIds
            for claim in claims:
                claim.pop("_id", None)
            
            return claims
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get claims: {str(e)}")
    
    # Admin routes
    @router.get("/admin/users", response_model=List[UserResponse])
    async def get_all_users(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        skip: int = 0,
        limit: int = 50
    ):
        """Get all users (admin only)"""
        try:
            current_user = await auth_manager.get_current_user(credentials)
            
            if current_user.role != UserRole.admin:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            users = await db.users.find({}).skip(skip).limit(limit).to_list(length=limit)
            
            user_responses = []
            for user_doc in users:
                user_doc.pop("_id", None)
                user_doc.pop("hashed_password", None)  # Don't return password hashes
                user_responses.append(UserResponse(**user_doc))
            
            return user_responses
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")
    
    @router.get("/admin/claims", response_model=List[dict])
    async def get_all_claims(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        status_filter: Optional[str] = None
    ):
        """Get all thesis claims (admin only)"""
        try:
            current_user = await auth_manager.get_current_user(credentials)
            
            if current_user.role != UserRole.admin:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            filter_dict = {}
            if status_filter:
                filter_dict["status"] = status_filter
            
            claims = await db.thesis_claims.find(filter_dict).to_list(length=200)
            
            # Clean up MongoDB ObjectIds
            for claim in claims:
                claim.pop("_id", None)
            
            return claims
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get claims: {str(e)}")
    
    @router.put("/admin/claims/{claim_id}/review")
    async def review_claim(
        claim_id: str,
        action: str,  # "approve" or "reject"
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        """Review a thesis claim (admin only)"""
        try:
            current_user = await auth_manager.get_current_user(credentials)
            
            if current_user.role != UserRole.admin:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            if action not in ["approve", "reject"]:
                raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
            
            # Update claim status
            update_data = {
                "status": "approved" if action == "approve" else "rejected",
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = await db.thesis_claims.update_one(
                {"id": claim_id},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Claim not found")
            
            # If approved, add thesis to user's claimed theses
            if action == "approve":
                claim = await db.thesis_claims.find_one({"id": claim_id})
                if claim:
                    await db.users.update_one(
                        {"id": claim["user_id"]},
                        {"$addToSet": {"claimed_theses": claim["thesis_id"]}}
                    )
            
            return {"message": f"Claim {action}d successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to review claim: {str(e)}")
    
    return router