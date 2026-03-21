"""Main API router for document extraction and validation"""

import uuid
import time
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aiofiles

from app.core.database import get_db
from app.models import Session, Extraction, Validation
from app.schemas import JobResponse, JobStatus, SessionSummary, ValidationResult, ComplianceReport, OverallHealth
from app.services.extraction import ExtractionService
from app.services.job_queue import job_queue
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["Documents"])


@router.post("/extract")
async def extract_document(
    document: UploadFile = File(...),
    sessionId: Optional[str] = Form(None),
    mode: str = Query("async", description="sync or async mode")
):
    """Extract structured data from uploaded document"""
    # Validate file type
    if document.content_type not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={"error": "UNSUPPORTED_FORMAT", "message": f"File type {document.content_type} not accepted"}
        )
    
    # Read file content
    file_content = await document.read()
    
    # Check file size
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"error": "FILE_TOO_LARGE", "message": f"File exceeds {settings.MAX_FILE_SIZE // (1024*1024)}MB limit"}
        )
    
    # Determine if async is forced
    force_async = len(file_content) > settings.ASYNC_THRESHOLD or mode == "async"
    
    # Create or use session
    session_id = sessionId or str(uuid.uuid4())
    
    async for db in get_db():
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
            file_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4()}_{document.filename}")
            async with aiofiles.open(file_path, 'wb') as out_file:
                await out_file.write(file_content)
            
            if force_async:
                # Async mode
                job_id = str(uuid.uuid4())
                job = await job_queue.enqueue(job_id, session_id)
                
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
                    return JSONResponse(content=response, headers={"X-Deduplicated": "true"})
                return response
                
        except ValueError as e:
            error_msg = str(e)
            if "INSUFFICIENT_DOCUMENTS" in error_msg:
                raise HTTPException(status_code=400, detail={"error": "INSUFFICIENT_DOCUMENTS", "message": error_msg})
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": str(e)})


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get status of an async extraction job"""
    job = await job_queue.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"})
    
    return job


@router.get("/sessions/{session_id}", response_model=SessionSummary)
async def get_session_summary(session_id: str):
    """Get summary of all documents in a session"""
    async for db in get_db():
        # Get session
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail={"error": "SESSION_NOT_FOUND", "message": f"Session {session_id} not found"})
        
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
                "flagCount": 0,
                "criticalFlagCount": 0,
                "createdAt": ext.created_at.isoformat()
            }
            documents.append(doc_summary)
            
            if ext.applicable_role:
                detected_roles.add(ext.applicable_role)
            
            if ext.is_expired:
                overall_health = OverallHealth.CRITICAL
        
        pending_jobs = []
        
        return {
            "sessionId": session_id,
            "documentCount": len(documents),
            "detectedRole": list(detected_roles)[0] if len(detected_roles) == 1 else None,
            "overallHealth": overall_health.value,
            "documents": documents,
            "pendingJobs": pending_jobs
        }


@router.post("/sessions/{session_id}/validate", response_model=ValidationResult)
async def validate_session(session_id: str):
    """Validate cross-document compliance for a session"""
    async for db in get_db():
        # Check session exists
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail={"error": "SESSION_NOT_FOUND", "message": f"Session {session_id} not found"})
        
        # Get all complete extractions
        stmt = select(Extraction).where(
            Extraction.session_id == session_id,
            Extraction.status == "COMPLETE"
        )
        result = await db.execute(stmt)
        extractions = result.scalars().all()
        
        if len(extractions) < 2:
            raise HTTPException(
                status_code=400,
                detail={"error": "INSUFFICIENT_DOCUMENTS", "message": "Need at least 2 documents for validation"}
            )
        
        # TODO: Implement LLM validation call
        # For now, return placeholder
        return {
            "sessionId": session_id,
            "holderProfile": {},
            "consistencyChecks": [],
            "missingDocuments": [],
            "expiringDocuments": [],
            "medicalFlags": [],
            "overallStatus": "CONDITIONAL",
            "overallScore": 75,
            "summary": "Validation not yet implemented",
            "recommendations": []
        }


@router.get("/sessions/{session_id}/report", response_model=ComplianceReport)
async def get_compliance_report(session_id: str):
    """Generate human-readable compliance report"""
    async for db in get_db():
        # Get session
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail={"error": "SESSION_NOT_FOUND", "message": f"Session {session_id} not found"})
        
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
            import json
            validation_data = json.loads(latest_validation.result_json)
        
        holder_profile = validation_data.get("holderProfile", {})
        
        document_overview = []
        for ext in extractions:
            doc_info = {
                "type": ext.document_type,
                "fileName": ext.file_name,
                "status": "EXPIRED" if ext.is_expired else "VALID",
                "confidence": ext.confidence
            }
            document_overview.append(doc_info)
        
        overall_status = validation_data.get("overallStatus", "CONDITIONAL")
        if overall_status == "APPROVED":
            hiring_rec = "RECOMMENDED FOR HIRE - All documents valid and compliant"
        elif overall_status == "REJECTED":
            hiring_rec = "NOT RECOMMENDED - Critical compliance issues identified"
        else:
            hiring_rec = "CONDITIONAL - Minor issues require attention before hire"
        
        return {
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
                "criticalIssues": 0,
                "medicalConcerns": validation_data.get("medicalFlags", []),
                "consistencyIssues": []
            },
            "hiringRecommendation": hiring_rec,
            "actionItems": validation_data.get("recommendations", []),
            "detailedFindings": []
        }
