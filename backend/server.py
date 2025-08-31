from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends, Request, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from enum import Enum
import re

# Import Stripe payment integration
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

# Import connectors
from importers.scheduler import ImportScheduler

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize Stripe checkout
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')
stripe_checkout = None

if STRIPE_API_KEY:
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")

# Initialize import scheduler
import_scheduler = None

# Thesis pricing packages
THESIS_PACKAGES = {
    "standard": {"price": 5.0, "currency": "eur", "name": "Accès Standard"},
    "premium": {"price": 10.0, "currency": "eur", "name": "Accès Premium"},
    "institutional": {"price": 25.0, "currency": "eur", "name": "Licence Institutionnelle"}
}

# Create the main app without a prefix
app = FastAPI(title="Thèses CAMES API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class AccessType(str, Enum):
    open = "open"
    paywalled = "paywalled"

class SourceRepo(str, Enum):
    HAL = "HAL"
    GREENSTONE = "Greenstone"
    OTHER = "Other"

class PersonRole(str, Enum):
    author = "author"
    supervisor = "supervisor"

class InstitutionType(str, Enum):
    university = "university"
    doctoral_school = "doctoralSchool"

class PaymentProvider(str, Enum):
    stripe = "Stripe"
    paystack = "Paystack"
    flutterwave = "Flutterwave"

class OrderStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"

# Models
class Thesis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    abstract: str
    keywords: List[str] = []
    language: str = "fr"
    discipline: str
    sub_discipline: Optional[str] = None
    country: str
    university: str
    doctoral_school: Optional[str] = None
    author_name: str
    author_orcid: Optional[str] = None
    supervisor_names: List[str] = []
    defense_date: str  # YYYY format
    pages: Optional[int] = None
    degree: Optional[str] = None
    doi: Optional[str] = None
    handle: Optional[str] = None
    hal_id: Optional[str] = None
    url_open_access: Optional[str] = None
    file_open_access: Optional[str] = None
    access_type: AccessType = AccessType.open
    purchase_url: Optional[str] = None
    license: str = "Unknown"
    source_repo: SourceRepo = SourceRepo.OTHER
    source_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    views_count: int = 0
    downloads_count: int = 0
    site_citations_count: int = 0
    external_citations_count: Optional[int] = None
    thumbnail: Optional[str] = None

class ThesisCreate(BaseModel):
    title: str
    abstract: str
    keywords: List[str] = []
    language: str = "fr"
    discipline: str
    sub_discipline: Optional[str] = None
    country: str
    university: str
    doctoral_school: Optional[str] = None
    author_name: str
    author_orcid: Optional[str] = None
    supervisor_names: List[str] = []
    defense_date: str
    pages: Optional[int] = None
    degree: Optional[str] = None
    doi: Optional[str] = None
    handle: Optional[str] = None
    hal_id: Optional[str] = None
    url_open_access: Optional[str] = None
    file_open_access: Optional[str] = None
    access_type: AccessType = AccessType.open
    purchase_url: Optional[str] = None
    license: str = "Unknown"
    source_repo: SourceRepo = SourceRepo.OTHER
    source_url: Optional[str] = None
    thumbnail: Optional[str] = None

class Person(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: PersonRole
    affiliations: List[str] = []
    orcid: Optional[str] = None
    email: Optional[str] = None

class Institution(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: InstitutionType
    country: str
    website: Optional[str] = None

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thesis_id: str
    price: float
    currency: str
    provider: PaymentProvider
    status: OrderStatus = OrderStatus.pending
    buyer_email: str
    invoice_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thesis_id: str
    amount: float
    currency: str
    provider: PaymentProvider = PaymentProvider.stripe
    status: str = "pending"  # pending, completed, failed, expired
    payment_status: str = "initiated"  # initiated, paid, failed, canceled
    session_id: Optional[str] = None
    buyer_email: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CheckoutRequest(BaseModel):
    thesis_id: str
    origin_url: str

class WebhookEvent(BaseModel):
    event_type: str
    event_id: str
    session_id: str
    payment_status: str
    metadata: Dict[str, str]

class AuthorRanking(BaseModel):
    author_name: str
    citations_count: int
    stars: int
    theses_count: int
    disciplines: List[str]

class UniversityRanking(BaseModel):
    university_name: str
    country: str
    theses_count: int
    disciplines: List[str]

class SearchFilters(BaseModel):
    country: Optional[str] = None
    discipline: Optional[str] = None
    author: Optional[str] = None
    supervisor: Optional[str] = None
    university: Optional[str] = None
    year: Optional[str] = None
    access_type: Optional[AccessType] = None

# Helper functions
def prepare_for_mongo(data):
    """Convert non-serializable types for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    """Parse data from MongoDB"""
    if isinstance(item.get('created_at'), str):
        item['created_at'] = datetime.fromisoformat(item['created_at'])
    if isinstance(item.get('updated_at'), str):
        item['updated_at'] = datetime.fromisoformat(item['updated_at'])
    return item

def calculate_stars(citations_count: int) -> int:
    """Calculate star rating based on citations count"""
    if citations_count >= 50:
        return 5
    elif citations_count >= 25:
        return 4
    elif citations_count >= 10:
        return 3
    elif citations_count >= 5:
        return 2
    elif citations_count >= 1:
        return 1
    else:
        return 0

# Routes
@api_router.get("/")
async def root():
    return {"message": "Thèses CAMES API v1.0.0"}

@api_router.get("/theses", response_model=Dict[str, Any])
async def search_theses(
    q: Optional[str] = Query(None, description="Search query"),
    country: Optional[str] = Query(None),
    discipline: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    supervisor: Optional[str] = Query(None),
    university: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    access_type: Optional[AccessType] = Query(None),
    sort: str = Query("relevance", regex="^(relevance|date|citations|downloads)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Search theses with filters and pagination"""
    try:
        # Build search filter
        filter_dict = {}
        
        if q:
            # Full text search
            filter_dict["$or"] = [
                {"title": {"$regex": re.escape(q), "$options": "i"}},
                {"abstract": {"$regex": re.escape(q), "$options": "i"}},
                {"keywords": {"$regex": re.escape(q), "$options": "i"}},
                {"author_name": {"$regex": re.escape(q), "$options": "i"}},
                {"supervisor_names": {"$regex": re.escape(q), "$options": "i"}}
            ]
        
        if country:
            filter_dict["country"] = {"$regex": re.escape(country), "$options": "i"}
        if discipline:
            filter_dict["discipline"] = {"$regex": re.escape(discipline), "$options": "i"}
        if author:
            filter_dict["author_name"] = {"$regex": re.escape(author), "$options": "i"}
        if supervisor:
            filter_dict["supervisor_names"] = {"$regex": re.escape(supervisor), "$options": "i"}
        if university:
            filter_dict["university"] = {"$regex": re.escape(university), "$options": "i"}
        if year:
            filter_dict["defense_date"] = year
        if access_type:
            filter_dict["access_type"] = access_type.value

        # Sort options
        sort_dict = {
            "relevance": {"views_count": -1, "site_citations_count": -1},
            "date": {"defense_date": -1},
            "citations": {"site_citations_count": -1},
            "downloads": {"downloads_count": -1}
        }
        
        # Count total
        total_count = await db.theses.count_documents(filter_dict)
        
        # Get theses
        skip = (page - 1) * limit
        theses_cursor = db.theses.find(filter_dict).sort(list(sort_dict[sort].items())).skip(skip).limit(limit)
        theses = await theses_cursor.to_list(length=limit)
        
        # Parse from mongo
        theses = [parse_from_mongo(thesis) for thesis in theses]
        
        return {
            "results": [Thesis(**thesis) for thesis in theses],
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }
    except Exception as e:
        logging.error(f"Error searching theses: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.get("/theses/{thesis_id}", response_model=Thesis)
async def get_thesis(thesis_id: str):
    """Get thesis by ID and increment view count"""
    try:
        thesis = await db.theses.find_one({"id": thesis_id})
        if not thesis:
            raise HTTPException(status_code=404, detail="Thesis not found")
        
        # Increment view count
        await db.theses.update_one(
            {"id": thesis_id},
            {"$inc": {"views_count": 1}}
        )
        
        thesis = parse_from_mongo(thesis)
        return Thesis(**thesis)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting thesis {thesis_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.post("/theses", response_model=Thesis)
async def create_thesis(thesis_data: ThesisCreate):
    """Create a new thesis"""
    try:
        thesis_dict = thesis_data.dict()
        thesis = Thesis(**thesis_dict)
        
        # Prepare for MongoDB
        thesis_dict = prepare_for_mongo(thesis.dict())
        
        await db.theses.insert_one(thesis_dict)
        return thesis
    except Exception as e:
        logging.error(f"Error creating thesis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.get("/rankings/authors", response_model=List[AuthorRanking])
async def get_author_rankings(
    discipline: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Get author rankings by citations"""
    try:
        pipeline = [
            {"$group": {
                "_id": "$author_name",
                "citations_count": {"$sum": "$site_citations_count"},
                "theses_count": {"$sum": 1},
                "disciplines": {"$addToSet": "$discipline"}
            }}
        ]
        
        if discipline:
            pipeline.insert(0, {"$match": {"discipline": {"$regex": re.escape(discipline), "$options": "i"}}})
        
        pipeline.extend([
            {"$sort": {"citations_count": -1}},
            {"$limit": limit}
        ])
        
        results = await db.theses.aggregate(pipeline).to_list(length=limit)
        
        rankings = []
        for result in results:
            rankings.append(AuthorRanking(
                author_name=result["_id"],
                citations_count=result["citations_count"],
                stars=calculate_stars(result["citations_count"]),
                theses_count=result["theses_count"],
                disciplines=result["disciplines"]
            ))
        
        return rankings
    except Exception as e:
        logging.error(f"Error getting author rankings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.get("/rankings/universities", response_model=List[UniversityRanking])
async def get_university_rankings(
    discipline: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Get university rankings by thesis count"""
    try:
        pipeline = []
        match_filter = {}
        
        if discipline:
            match_filter["discipline"] = {"$regex": re.escape(discipline), "$options": "i"}
        if country:
            match_filter["country"] = {"$regex": re.escape(country), "$options": "i"}
        
        if match_filter:
            pipeline.append({"$match": match_filter})
        
        pipeline.extend([
            {"$group": {
                "_id": {"university": "$university", "country": "$country"},
                "theses_count": {"$sum": 1},
                "disciplines": {"$addToSet": "$discipline"}
            }},
            {"$sort": {"theses_count": -1}},
            {"$limit": limit}
        ])
        
        results = await db.theses.aggregate(pipeline).to_list(length=limit)
        
        rankings = []
        for result in results:
            rankings.append(UniversityRanking(
                university_name=result["_id"]["university"],
                country=result["_id"]["country"],
                theses_count=result["theses_count"],
                disciplines=result["disciplines"]
            ))
        
        return rankings
    except Exception as e:
        logging.error(f"Error getting university rankings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.get("/stats")
async def get_statistics():
    """Get general statistics"""
    try:
        total_theses = await db.theses.count_documents({})
        open_access = await db.theses.count_documents({"access_type": "open"})
        paywalled = await db.theses.count_documents({"access_type": "paywalled"})
        
        # Get top disciplines
        disciplines_pipeline = [
            {"$group": {"_id": "$discipline", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        top_disciplines = await db.theses.aggregate(disciplines_pipeline).to_list(length=10)
        
        # Get top countries
        countries_pipeline = [
            {"$group": {"_id": "$country", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        top_countries = await db.theses.aggregate(countries_pipeline).to_list(length=10)
        
        return {
            "total_theses": total_theses,
            "open_access": open_access,
            "paywalled": paywalled,
            "top_disciplines": [{"name": d["_id"], "count": d["count"]} for d in top_disciplines],
            "top_countries": [{"name": c["_id"], "count": c["count"]} for c in top_countries]
        }
    except Exception as e:
        logging.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.post("/checkout/session")
async def create_checkout_session(request: CheckoutRequest):
    """Create a payment checkout session for thesis access"""
    global stripe_checkout
    try:
        if not stripe_checkout:
            raise HTTPException(status_code=500, detail="Payment system not configured")
        
        # Get thesis information
        thesis = await db.theses.find_one({"id": request.thesis_id})
        if not thesis:
            raise HTTPException(status_code=404, detail="Thesis not found")
        
        # Check if thesis is already open access
        if thesis.get("access_type") == "open":
            raise HTTPException(status_code=400, detail="This thesis is already freely accessible")
        
        # Use standard package for thesis access
        package = THESIS_PACKAGES["standard"]
        amount = package["price"]
        currency = package["currency"]
        
        # Create success and cancel URLs
        success_url = f"{request.origin_url}/purchase-success?session_id={{CHECKOUT_SESSION_ID}}&thesis_id={request.thesis_id}"
        cancel_url = f"{request.origin_url}/?canceled=true"
        
        # Update stripe checkout webhook URL
        webhook_url = f"{request.origin_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        
        # Create checkout session request
        checkout_request = CheckoutSessionRequest(
            amount=amount,
            currency=currency,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "thesis_id": request.thesis_id,
                "package": "standard",
                "source": "theses_cames"
            }
        )
        
        # Create session with Stripe
        session = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record
        transaction = PaymentTransaction(
            thesis_id=request.thesis_id,
            amount=amount,
            currency=currency,
            session_id=session.session_id,
            metadata=checkout_request.metadata,
            status="initiated",
            payment_status="pending"
        )
        
        # Save transaction to database
        transaction_dict = prepare_for_mongo(transaction.dict())
        await db.payment_transactions.insert_one(transaction_dict)
        
        return {
            "url": session.url,
            "session_id": session.session_id,
            "amount": amount,
            "currency": currency
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

@api_router.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str):
    """Check the status of a payment checkout session"""
    try:
        if not stripe_checkout:
            raise HTTPException(status_code=500, detail="Payment system not configured")
        
        # Get status from Stripe
        checkout_status = await stripe_checkout.get_checkout_status(session_id)
        
        # Find transaction in database
        transaction = await db.payment_transactions.find_one({"session_id": session_id})
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Update transaction status if payment is completed and not already processed
        if (checkout_status.payment_status == "paid" and 
            transaction.get("payment_status") != "paid"):
            
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": "completed",
                        "payment_status": "paid",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            # Grant access to thesis (you could add logic here to create access tokens, etc.)
            await db.theses.update_one(
                {"id": transaction["thesis_id"]},
                {"$inc": {"downloads_count": 1}}
            )
        
        elif checkout_status.status == "expired":
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": "expired",
                        "payment_status": "expired",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
        
        return {
            "status": checkout_status.status,
            "payment_status": checkout_status.payment_status,
            "amount_total": checkout_status.amount_total,
            "currency": checkout_status.currency,
            "metadata": checkout_status.metadata,
            "thesis_id": transaction.get("thesis_id")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error checking checkout status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check payment status")

@api_router.post("/admin/import/trigger")
async def trigger_import(background_tasks: BackgroundTasks, max_records: int = Query(50)):
    """Manually trigger import from HAL and Greenstone"""
    try:
        global import_scheduler
        if not import_scheduler:
            import_scheduler = ImportScheduler(db)
        
        # Run import in background
        background_tasks.add_task(import_scheduler.run_full_import, max_records)
        
        return {
            "message": "Import job started",
            "max_records": max_records,
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"Error triggering import: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger import")

@api_router.get("/admin/import/history")
async def get_import_history(limit: int = Query(20, le=100)):
    """Get import job history"""
    try:
        global import_scheduler
        if not import_scheduler:
            import_scheduler = ImportScheduler(db)
        
        history = await import_scheduler.get_import_history(limit)
        return {"import_jobs": history}
        
    except Exception as e:
        logger.error(f"Error getting import history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get import history")

@api_router.get("/admin/import/status")
async def get_import_status():
    """Get current import system status"""
    try:
        # Check last import job
        last_job = await db.import_jobs.find_one({}, sort=[("started_at", -1)])
        
        # Get total imported theses by source
        hal_count = await db.theses.count_documents({"source_repo": "HAL"})
        greenstone_count = await db.theses.count_documents({"source_repo": "Greenstone"})
        other_count = await db.theses.count_documents({"source_repo": "Other"})
        
        return {
            "last_import": last_job,
            "thesis_counts": {
                "hal": hal_count,
                "greenstone": greenstone_count,
                "other": other_count,
                "total": hal_count + greenstone_count + other_count
            },
            "scheduler_status": "running" if import_scheduler and import_scheduler.running else "stopped"
        }
        
    except Exception as e:
        logger.error(f"Error getting import status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get import status")

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    try:
        if not stripe_checkout:
            raise HTTPException(status_code=500, detail="Payment system not configured")
        
        # Get request body and signature
        request_body = await request.body()
        stripe_signature = request.headers.get("Stripe-Signature")
        
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")
        
        # Handle webhook
        webhook_response = await stripe_checkout.handle_webhook(request_body, stripe_signature)
        
        # Process the webhook event
        if webhook_response.event_type == "checkout.session.completed":
            session_id = webhook_response.session_id
            
            # Update transaction status
            await db.payment_transactions.update_one(
                {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                {
                    "$set": {
                        "status": "completed",
                        "payment_status": "paid",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            # Get transaction to update thesis
            transaction = await db.payment_transactions.find_one({"session_id": session_id})
            if transaction:
                await db.theses.update_one(
                    {"id": transaction["thesis_id"]},
                    {"$inc": {"downloads_count": 1}}
                )
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error handling Stripe webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize database with sample data"""
    try:
        # Check if we already have data
        count = await db.theses.count_documents({})
        if count == 0:
            # Create sample theses data
            sample_theses = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Intelligence Artificielle et Apprentissage Automatique pour l'Agriculture en Afrique de l'Ouest",
                    "abstract": "Cette thèse explore l'application de l'intelligence artificielle et des techniques d'apprentissage automatique pour améliorer la productivité agricole en Afrique de l'Ouest. Nous présentons des modèles prédictifs pour l'optimisation des rendements agricoles basés sur les données climatiques et pédologiques.",
                    "keywords": ["intelligence artificielle", "agriculture", "apprentissage automatique", "Afrique de l'Ouest", "productivité"],
                    "language": "fr",
                    "discipline": "Informatique",
                    "sub_discipline": "Intelligence Artificielle",
                    "country": "Sénégal",
                    "university": "Université Cheikh Anta Diop",
                    "doctoral_school": "École Doctorale des Sciences et Technologies",
                    "author_name": "Aminata Diallo",
                    "author_orcid": "0000-0001-2345-6789",
                    "supervisor_names": ["Prof. Moussa Diop", "Dr. Fatou Sow"],
                    "defense_date": "2023",
                    "pages": 250,
                    "degree": "Doctorat en Informatique",
                    "access_type": "open",
                    "license": "CC BY 4.0",
                    "source_repo": "HAL",
                    "source_url": "https://hal.science/hal-04000000",
                    "url_open_access": "https://hal.science/hal-04000000/document",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "views_count": 142,
                    "downloads_count": 87,
                    "site_citations_count": 15,
                    "thumbnail": "https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=300&h=200&fit=crop"
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Développement Durable et Énergies Renouvelables au Sahel : Analyse Socio-économique",
                    "abstract": "Une analyse approfondie des défis et opportunités liés au développement des énergies renouvelables dans les pays du Sahel. Cette recherche examine les aspects techniques, économiques et sociaux de la transition énergétique dans cette région.",
                    "keywords": ["énergies renouvelables", "Sahel", "développement durable", "socio-économie", "transition énergétique"],
                    "language": "fr",
                    "discipline": "Économie",
                    "sub_discipline": "Économie du Développement",
                    "country": "Burkina Faso",
                    "university": "Université Joseph Ki-Zerbo",
                    "doctoral_school": "École Doctorale Lettres, Sciences Humaines et Communication",
                    "author_name": "Ibrahim Ouédraogo",
                    "supervisor_names": ["Prof. Marie Kaboré", "Dr. Jean-Baptiste Sawadogo"],
                    "defense_date": "2023",
                    "pages": 320,
                    "degree": "Doctorat en Sciences Économiques",
                    "access_type": "paywalled",
                    "purchase_url": "https://thesescames.org/purchase/thesis-2",
                    "license": "Tous droits réservés",
                    "source_repo": "Greenstone",
                    "source_url": "https://greenstone.lecames.org/cgi-bin/library",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "views_count": 298,
                    "downloads_count": 45,
                    "site_citations_count": 8,
                    "thumbnail": "https://images.unsplash.com/photo-1466611653911-95081537e5b7?w=300&h=200&fit=crop"
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Médecine Traditionnelle et Pharmacopée Africaine : Étude Ethnobotanique au Mali",
                    "abstract": "Cette thèse présente une étude ethnobotanique complète des plantes médicinales utilisées dans la médecine traditionnelle malienne. Elle analyse les propriétés thérapeutiques et propose des protocoles de standardisation pour une meilleure intégration dans les systèmes de santé modernes.",
                    "keywords": ["médecine traditionnelle", "ethnobotanique", "pharmacopée", "Mali", "plantes médicinales"],
                    "language": "fr",
                    "discipline": "Médecine",
                    "sub_discipline": "Pharmacologie",
                    "country": "Mali",
                    "university": "Université des Sciences, des Techniques et des Technologies de Bamako",
                    "doctoral_school": "École Doctorale Sciences de la Santé",
                    "author_name": "Fatoumata Traoré",
                    "author_orcid": "0000-0002-3456-7890",
                    "supervisor_names": ["Prof. Seydou Doumbia", "Dr. Rokia Sanogo"],
                    "defense_date": "2022",
                    "pages": 280,
                    "degree": "Doctorat en Pharmacologie",
                    "doi": "10.1234/thesis.2022.567",
                    "access_type": "open",
                    "license": "CC BY-SA 4.0",
                    "source_repo": "HAL",
                    "source_url": "https://hal.science/hal-04000001",
                    "url_open_access": "https://hal.science/hal-04000001/document",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "views_count": 456,
                    "downloads_count": 203,
                    "site_citations_count": 23,
                    "thumbnail": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=300&h=200&fit=crop"
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Gestion des Ressources Hydriques et Changement Climatique en Côte d'Ivoire",
                    "abstract": "Une analyse des impacts du changement climatique sur les ressources hydriques en Côte d'Ivoire et proposition de stratégies d'adaptation pour une gestion durable de l'eau. Cette recherche combine modélisation climatique et analyse socio-économique.",
                    "keywords": ["ressources hydriques", "changement climatique", "Côte d'Ivoire", "gestion durable", "adaptation"],
                    "language": "fr",
                    "discipline": "Géographie",
                    "sub_discipline": "Géographie Physique",
                    "country": "Côte d'Ivoire",
                    "university": "Université Félix Houphouët-Boigny",
                    "doctoral_school": "École Doctorale Homme, Société et Environnement",
                    "author_name": "Kofi Asante",
                    "supervisor_names": ["Prof. Adjoua Moise", "Dr. Yao Kouassi"],
                    "defense_date": "2023",
                    "pages": 310,
                    "degree": "Doctorat en Géographie",
                    "access_type": "open",
                    "license": "CC BY-NC 4.0",
                    "source_repo": "Other",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "views_count": 187,
                    "downloads_count": 92,
                    "site_citations_count": 12,
                    "thumbnail": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=300&h=200&fit=crop"
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Linguistique Appliquée et Préservation des Langues Africaines : Le Cas du Wolof",
                    "abstract": "Cette thèse examine les défis de préservation et de revitalisation du Wolof dans le contexte de la mondialisation. Elle propose des méthodologies innovantes pour la documentation et l'enseignement des langues africaines.",
                    "keywords": ["linguistique appliquée", "langues africaines", "Wolof", "préservation linguistique", "revitalisation"],
                    "language": "fr",
                    "discipline": "Linguistique",
                    "sub_discipline": "Linguistique Appliquée",
                    "country": "Sénégal",
                    "university": "Université Cheikh Anta Diop",
                    "doctoral_school": "École Doctorale Langues, Littératures et Civilisations",
                    "author_name": "Oumar Fall",
                    "supervisor_names": ["Prof. Aissatou Mbodj", "Dr. Pathé Diagne"],
                    "defense_date": "2022",
                    "pages": 235,
                    "degree": "Doctorat en Linguistique",
                    "access_type": "paywalled",
                    "purchase_url": "https://thesescames.org/purchase/thesis-5",
                    "license": "Tous droits réservés",
                    "source_repo": "Greenstone",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "views_count": 234,
                    "downloads_count": 67,
                    "site_citations_count": 18,
                    "thumbnail": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=300&h=200&fit=crop"
                }
            ]
            
            await db.theses.insert_many(sample_theses)
            logger.info("Sample data inserted successfully")
        else:
            logger.info("Database already contains data, skipping sample data insertion")
    except Exception as e:
        logger.error(f"Error during startup: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()