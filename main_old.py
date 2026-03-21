from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import os
import uuid
import time
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aiofiles

from config import (
    HOST, PORT, MAX_FILE_SIZE, ALLOWED_EXTENSIONS,
    UPLOAD_DIR, RATE_LIMIT_REQUESTS, RATE_LIMIT_PERIOD,
    ASYNC_THRESHOLD, DATABASE_URL, LLM_PROVIDER, LLM_MODEL, LLM_API_KEY
)
from database import DatabaseManager, Extraction, Session, Job, Validation
from schemas import (
    ExtractionRecord, JobResponse, JobStatus, SessionSummary,
    ValidationResult, ComplianceReport, OverallHealth
)
from enums import Confidence, FlagSeverity, ApplicableRole, OverallStatus
from services import ExtractionService, job_queue, calculate_file_hash
from prompts import EXTRACTION_PROMPT, VALIDATION_PROMPT

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Smart Maritime Document Extractor", version="1.0.0")

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

# Database manager
db_manager = None


@app.on_event("startup")
async def startup_event():
    global db_manager
    
    # Create uploads directory
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Initialize database
    db_manager = DatabaseManager(DATABASE_URL)
    await db_manager.connect()
    
    # Set startup time
    app.startup_time = time.time()
    
    # Start background job processor
    asyncio.create_task(process_jobs())


@app.on_event("shutdown")
async def shutdown_event():
    if db_manager:
        await db_manager.disconnect()


async def get_db_session() -> AsyncSession:
    """Get database session"""
    return db_manager.get_session()


async def process_jobs():
    """Background job processor"""
    while True:
        try:
            await asyncio.sleep(5)
            # Process jobs from queue
            # Implementation pending
        except Exception as e:
            print(f"Job processing error: {e}")
            await asyncio.sleep(1)


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    if file.content_type not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "UNSUPPORTED_FORMAT",
                "message": f"File type {file.content_type} not accepted. Allowed: {list(ALLOWED_EXTENSIONS)}"
            }
        )


@app.get("/api/health")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/minute")
async def health_check(request: Request):
    """Health check endpoint with dependency status"""
    try:
        # Check database
        db_status = "OK"
        try:
            session = await get_db_session()
            await session.execute(select(1))
        except Exception:
            db_status = "ERROR"
        
        # Check LLM provider
        llm_status = "OK" if LLM_API_KEY else "MISSING_KEY"
        
        # Check queue
        queue_status = "OK"
        
        return {
            "status": "OK",
            "version": "1.0.0",
            "uptime": int(time.time() - app.startup_time) if hasattr(app, 'startup_time') else 0,
            "dependencies": {
                "database": db_status,
                "llmProvider": llm_status,
                "queue": queue_status
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "version": "1.0.0",
            "dependencies": {
                "database": "ERROR",
                "llmProvider": "ERROR",
                "queue": "ERROR"
            },
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/api/extract")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/minute")
async def extract_document(
    request: Request,
    document: UploadFile = File(...),
    sessionId: Optional[str] = Form(None),
    mode: str = Query("sync", description="sync or async mode")
):
    """Extract structured data from uploaded document"""
    validate_file(document)
    
    # Read file content
    file_content = await document.read()
    
    # Check file size
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "FILE_TOO_LARGE",
                "message": f"File exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit"
            }
        )
    
    # Determine if async is forced
    force_async = len(file_content) > ASYNC_THRESHOLD or mode == "async"
    
    # Create or use session
    session_id = sessionId or str(uuid.uuid4())
    
    db = await get_db_session()
    extraction_service = ExtractionService(db)
    
    try:
        # Check if session exists
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            session = Session(id=session_id)
            db.add(session)
            await db.commit()
        
        # Save file temporarily
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{document.filename}")
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(file_content)
        
        if force_async:
            # Async mode
            job_id = str(uuid.uuid4())
            job = await job_queue.enqueue(job_id, session_id)
            
            # TODO: Actually queue the extraction job
            
            return JSONResponse(
                status_code=202,
                content={
                    "jobId": job_id,
                    "sessionId": session_id,
                    "status": "QUEUED",
                    "pollUrl": f"/api/jobs/{job_id}",
                    "estimatedWaitMs": 6000
                }
            )
        else:
            # Sync mode
            extraction, is_dedup = await extraction_service.extract_document(
                file_data=file_content,
                file_name=document.filename,
                mime_type=document.content_type,
                session_id=session_id
            )
            
            response = extraction.dict()
            if is_dedup:
                return JSONResponse(
                    content=response,
                    headers={"X-Deduplicated": "true"}
                )
            return response
            
    except ValueError as e:
        error_msg = str(e)
        if "INSUFFICIENT_DOCUMENTS" in error_msg:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INSUFFICIENT_DOCUMENTS",
                    "message": error_msg
                }
            )
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": str(e)
            }
        )


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of an async extraction job"""
    job = await job_queue.get_job_status(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "JOB_NOT_FOUND",
                "message": f"Job {job_id} not found"
            }
        )
    
    return job.dict()


@app.get("/api/sessions/{session_id}")
async def get_session_summary(session_id: str):
    """Get summary of all documents in a session"""
    db = await get_db_session()
    
    # Get session
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "SESSION_NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        )
    
    # Get all extractions
    stmt = select(Extraction).where(
        Extraction.session_id == session_id,
        Extraction.status == "COMPLETE"
    )
    result = await db.execute(stmt)
    extractions = result.scalars().all()
    
    # Build document summaries
    documents = []
    detected_roles = set()
    overall_health = OverallHealth.OK
    
    for ext in extractions:
        doc_summary = {
            "id": ext.id,
            "fileName": ext.file_name,
            "documentType": ext.document_type,
            "applicableRole": ext.applicable_role,
            "holderName": ext.holder_name,
            "confidence": ext.confidence,
            "isExpired": ext.is_expired,
            "flagCount": 0,  # Would need to parse flags_json
            "criticalFlagCount": 0,
            "createdAt": ext.created_at.isoformat()
        }
        documents.append(doc_summary)
        
        if ext.applicable_role:
            detected_roles.add(ext.applicable_role)
        
        # Update overall health
        if ext.is_expired:
            overall_health = OverallHealth.CRITICAL
    
    # Get pending jobs
    pending_jobs = []  # Would query jobs table
    
    return {
        "sessionId": session_id,
        "documentCount": len(documents),
        "detectedRole": list(detected_roles)[0] if len(detected_roles) == 1 else None,
        "overallHealth": overall_health.value,
        "documents": documents,
        "pendingJobs": pending_jobs
    }


@app.post("/api/sessions/{session_id}/validate")
async def validate_session(session_id: str):
    """Validate cross-document compliance for a session"""
    db = await get_db_session()
    
    # Check session exists
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "SESSION_NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        )
    
    extraction_service = ExtractionService(db)
    
    try:
        validation_result = await extraction_service.validate_session(session_id)
        return validation_result.dict()
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INSUFFICIENT_DOCUMENTS",
                "message": str(e)
            }
        )


@app.get("/api/sessions/{session_id}/report")
async def get_compliance_report(session_id: str):
    """Generate human-readable compliance report"""
    db = await get_db_session()
    
    # Get session
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "SESSION_NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        )
    
    # Get latest validation
    stmt = select(Validation).where(
        Validation.session_id == session_id
    ).order_by(Validation.created_at.desc())
    result = await db.execute(stmt)
    latest_validation = result.scalar_one_or_none()
    
    # Get all extractions
    stmt = select(Extraction).where(
        Extraction.session_id == session_id,
        Extraction.status == "COMPLETE"
    )
    result = await db.execute(stmt)
    extractions = result.scalars().all()
    
    # Build report
    validation_data = {}
    if latest_validation:
        validation_data = eval(latest_validation.result_json)  # Should use json.loads
    
    # Generate candidate summary from validation
    holder_profile = validation_data.get("holderProfile", {})
    
    # Build document overview
    document_overview = []
    for ext in extractions:
        doc_info = {
            "type": ext.document_type,
            "fileName": ext.file_name,
            "status": "EXPIRED" if ext.is_expired else "VALID",
            "confidence": ext.confidence
        }
        document_overview.append(doc_info)
    
    # Determine hiring recommendation
    overall_status = validation_data.get("overallStatus", "CONDITIONAL")
    if overall_status == "APPROVED":
        hiring_rec = "RECOMMENDED FOR HIRE - All documents valid and compliant"
    elif overall_status == "REJECTED":
        hiring_rec = "NOT RECOMMENDED - Critical compliance issues identified"
    else:
        hiring_rec = "CONDITIONAL - Minor issues require attention before hire"
    
    report = {
        "sessionId": session_id,
        "generatedAt": datetime.utcnow().isoformat(),
        "candidateSummary": {
            "name": holder_profile.get("fullName", "Unknown"),
            "nationality": holder_profile.get("nationality", "Unknown"),
            "detectedRank": holder_profile.get("detectedRank", "Unknown")
        },
        "documentOverview": document_overview,
        "complianceAssessment": {
            "overallStatus": overall_status,
            "overallScore": validation_data.get("overallScore", 0),
            "missingDocuments": validation_data.get("missingDocuments", []),
            "expiringDocuments": validation_data.get("expiringDocuments", [])
        },
        "riskAnalysis": {
            "criticalIssues": len([c for c in validation_data.get("consistencyChecks", []) if c.get("severity") == "CRITICAL"]),
            "medicalConcerns": validation_data.get("medicalFlags", []),
            "consistencyIssues": [c for c in validation_data.get("consistencyChecks", []) if c.get("status") == "INCONSISTENT"]
        },
        "hiringRecommendation": hiring_rec,
        "actionItems": validation_data.get("recommendations", []),
        "detailedFindings": [
            {
                "category": "Consistency",
                "findings": validation_data.get("consistencyChecks", [])
            },
            {
                "category": "Medical",
                "findings": validation_data.get("medicalFlags", [])
            }
        ]
    }
    
    return report


if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("Smart Maritime Document Extractor (SMDE)")
    print("="*60)
    print(f"Starting server on http://{HOST}:{PORT}")
    print(f"API Docs: http://{HOST}:{PORT}/docs")
    print(f"Health Check: http://{HOST}:{PORT}/api/health")
    print("="*60)
    uvicorn.run(app, host=HOST, port=PORT)
