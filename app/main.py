from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import PROJECT_NAME, DATABASE_URL
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

# Debug database connection endpoint
@app.get("/debug/db")
def debug_db():
    import traceback
    from sqlalchemy.sql import text
    from app.database.database import db_url
    try:
        # Mask the password in db_url
        masked_url = db_url
        if db_url and "@" in db_url:
            parts = db_url.split("@")
            prefix = parts[0]
            if ":" in prefix:
                sub_parts = prefix.split(":")
                if len(sub_parts) > 2:
                    masked_url = f"{sub_parts[0]}:{sub_parts[1]}:****@{parts[1]}"
                else:
                    masked_url = f"{sub_parts[0]}:****@{parts[1]}"
        
        # Try to connect
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            val = result.scalar()
            return {
                "status": "connected",
                "database_url": masked_url,
                "test_query": val
            }
    except Exception as e:
        return {
            "status": "error",
            "database_url": masked_url,
            "error": str(e),
            "traceback": traceback.format_exc()
        }