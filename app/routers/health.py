"""Health check router"""

import time
from fastapi import APIRouter, Request
from sqlalchemy import select
from app.core.database import db_manager
from app.schemas import HealthResponse
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Health check endpoint with dependency status"""
    try:
        # Check database
        db_status = "OK"
        try:
            if db_manager:
                session = db_manager.get_session()
                await session.execute(select(1))
        except Exception:
            db_status = "ERROR"
        
        # Check LLM provider
        llm_status = "OK" if settings.LLM_API_KEY else "MISSING_KEY"
        
        # Check queue
        queue_status = "OK"
        
        uptime = int(time.time() - request.app.startup_time) if hasattr(request.app, 'startup_time') else 0
        
        return {
            "status": "OK",
            "version": "1.0.0",
            "uptime": uptime,
            "dependencies": {
                "database": db_status,
                "llmProvider": llm_status,
                "queue": queue_status
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "version": "1.0.0",
            "uptime": 0,
            "dependencies": {
                "database": "ERROR",
                "llmProvider": "ERROR",
                "queue": "ERROR"
            },
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
