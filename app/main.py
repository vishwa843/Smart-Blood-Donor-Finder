from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import PROJECT_NAME
from app.database.base import Base
from app.database.database import engine

# Import all models to ensure they are created in the database metadata
from app.models.user import User
from app.models.donor import Donor
from app.models.patient import Patient
from app.models.hospital import Hospital
from app.models.blood_request import BloodRequest
from app.models.donation import Donation
from app.models.notification import Notification

# Import routers
from app.routes.auth import router as auth_router
from app.routes.user import router as user_router
from app.routes.donor import router as donor_router
from app.routes.patient import router as patient_router
from app.routes.hospital import router as hospital_router
from app.routes.blood_request import router as blood_request_router
from app.routes.donation import router as donation_router
from app.routes.notification import router as notification_router
from app.routes.admin import router as admin_router
from app.routes.reports import router as reports_router

# Create FastAPI application
app = FastAPI(
    title=PROJECT_NAME
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development; adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(donor_router)
app.include_router(patient_router)
app.include_router(hospital_router)
app.include_router(blood_request_router)
app.include_router(donation_router)
app.include_router(notification_router)
app.include_router(admin_router)
app.include_router(reports_router)

# Create database tables on startup
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Smart Blood Donor Finder API is running",
        "version": "1.0.0"
    }