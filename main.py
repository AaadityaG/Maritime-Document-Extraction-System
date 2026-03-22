"""
Smart Maritime Document Extractor (SMDE) - Main Application

A vision-based LLM system for automated maritime document analysis
and compliance validation.
"""

import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.database import init_database, close_database
from app.routers import health, extraction


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI application
app = FastAPI(
    title="Smart Maritime Document Extractor",
    description="Automated maritime document analysis using vision-capable LLMs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_database()
    app.startup_time = time.time()
    
    print("=" * 60)
    print("Smart Maritime Document Extractor (SMDE)")
    print("=" * 60)
    print(f"Starting server on http://{settings.HOST}:{settings.PORT}")
    print(f"API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"Health Check: http://{settings.HOST}:{settings.PORT}/api/health")
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    await close_database()


# Include routers
app.include_router(health.router)
app.include_router(extraction.router)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
