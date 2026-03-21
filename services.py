import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aiofiles
import os

from database import Extraction, Session, Job, Validation
from schemas import (
    ExtractionRecord, FieldExtraction, ValidityInfo, ComplianceInfo,
    MedicalData, Flag, HolderInfo, DetectionInfo, JobResponse, JobStatus,
    ValidationResult, Holderprofile, ConsistencyCheck
)
from enums import (
    Confidence, FlagSeverity, FitnessResult, DrugTestResult,
    OverallStatus, OverallHealth, ApplicableRole
)
from prompts import EXTRACTION_PROMPT, VALIDATION_PROMPT
from llm_providers import get_provider, LLM_MODEL
from config import LLM_PROVIDER, LLM_API_KEY, JOB_TIMEOUT


def calculate_file_hash(file_data: bytes) -> str:
    """Calculate SHA-256 hash of file data"""
    return hashlib.sha256(file_data).hexdigest()


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string in DD/MM/YYYY format"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return None


def calculate_days_until_expiry(expiry_date: Optional[str]) -> Optional[int]:
    """Calculate days until expiry"""
    if not expiry_date or expiry_date in ["No Expiry", "Lifetime"]:
        return None
    
    expiry = parse_date(expiry_date)
    if not expiry:
        return None
    
    delta = expiry - datetime.utcnow()
    return delta.days


class ExtractionService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.llm_provider = get_provider(LLM_PROVIDER, LLM_API_KEY)
    
    async def extract_document(
        self,
        file_data: bytes,
        file_name: str,
        mime_type: str,
        session_id: str,
        force_async: bool = False
    ) -> tuple[ExtractionRecord, bool]:
        """
        Extract data from a document.
        Returns (extraction_record, is_deduplicated)
        """
        start_time = time.time()
        file_hash = calculate_file_hash(file_data)
        
        # Check for deduplication
        existing = await self._find_by_hash(session_id, file_hash)
        if existing:
            return existing, True
        
        # Create extraction record placeholder
        extraction = Extraction(
            session_id=session_id,
            file_name=file_name,
            file_hash=file_hash,
            status="PROCESSING",
            raw_llm_response=None
        )
        self.db.add(extraction)
        await self.db.commit()
        await self.db.refresh(extraction)
        
        try:
            # Call LLM for extraction
            llm_response = await self.llm_provider.extract_document(
                file_data=file_data,
                mime_type=mime_type,
                prompt=EXTRACTION_PROMPT
            )
            
            # Store raw response
            extraction.raw_llm_response = json.dumps(llm_response)
            
            # Parse and structure the response
            structured_data = await self._structure_extraction(llm_response)
            
            # Update extraction record
            await self._update_extraction(extraction, structured_data, start_time)
            
            return structured_data, False
            
        except Exception as e:
            # Mark as failed but keep the record
            extraction.status = "FAILED"
            extraction.raw_llm_response = f"Error: {str(e)}"
            await self.db.commit()
            
            raise e
    
    async def _find_by_hash(
        self,
        session_id: str,
        file_hash: str
    ) -> Optional[ExtractionRecord]:
        """Find existing extraction by file hash"""
        stmt = select(Extraction).where(
            Extraction.session_id == session_id,
            Extraction.file_hash == file_hash,
            Extraction.status == "COMPLETE"
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            return await self._db_to_schema(existing)
        return None
    
    async def _structure_extraction(self, llm_data: Dict[str, Any]) -> ExtractionRecord:
        """Structure LLM response into ExtractionRecord"""
        detection = llm_data.get("detection", {})
        holder = llm_data.get("holder", {})
        validity = llm_data.get("validity", {})
        compliance = llm_data.get("compliance", {})
        medical = llm_data.get("medicalData", {})
        flags = llm_data.get("flags", [])
        fields = llm_data.get("fields", [])
        
        # Calculate expiry info
        days_until_expiry = calculate_days_until_expiry(validity.get("dateOfExpiry"))
        is_expired = days_until_expiry is not None and days_until_expiry < 0
        
        return ExtractionRecord(
            id=str(int(time.time())),  # Temporary ID
            sessionId="",  # Will be set later
            fileName="",
            documentType=detection.get("documentType"),
            documentName=detection.get("documentName"),
            category=detection.get("category"),
            applicableRole=detection.get("applicableRole"),
            confidence=detection.get("confidence"),
            holderName=holder.get("fullName"),
            dateOfBirth=holder.get("dateOfBirth"),
            sirbNumber=holder.get("sirbNumber"),
            passportNumber=holder.get("passportNumber"),
            fields=[FieldExtraction(**f) for f in fields] if fields else [],
            validity=ValidityInfo(
                dateOfIssue=validity.get("dateOfIssue"),
                dateOfExpiry=validity.get("dateOfExpiry"),
                isExpired=is_expired,
                daysUntilExpiry=days_until_expiry,
                revalidationRequired=validity.get("revalidationRequired")
            ) if validity else None,
            compliance=ComplianceInfo(**compliance) if compliance else None,
            medicalData=MedicalData(**medical) if medical else None,
            flags=[Flag(**f) for f in flags] if flags else [],
            isExpired=is_expired,
            summary=llm_data.get("summary"),
            status="COMPLETE"
        )
    
    async def _update_extraction(
        self,
        extraction: Extraction,
        structured_data: ExtractionRecord,
        start_time: float
    ):
        """Update database extraction record with structured data"""
        processing_time = int((time.time() - start_time) * 1000)
        
        extraction.document_type = structured_data.documentType.value if structured_data.documentType else None
        extraction.applicable_role = structured_data.applicableRole.value if structured_data.applicableRole else None
        extraction.confidence = structured_data.confidence.value if structured_data.confidence else None
        extraction.holder_name = structured_data.holderName
        extraction.date_of_birth = structured_data.dateOfBirth
        extraction.sirb_number = structured_data.sirbNumber
        extraction.passport_number = structured_data.passportNumber
        extraction.fields_json = json.dumps([f.dict() for f in structured_data.fields])
        extraction.validity_json = json.dumps(structured_data.validity.dict()) if structured_data.validity else None
        extraction.medical_data_json = json.dumps(structured_data.medicalData.dict()) if structured_data.medicalData else None
        extraction.flags_json = json.dumps([f.dict() for f in structured_data.flags])
        extraction.is_expired = structured_data.isExpired
        extraction.summary = structured_data.summary
        extraction.processing_time_ms = processing_time
        extraction.status = "COMPLETE"
        
        self.db.add(extraction)
        await self.db.commit()
        await self.db.refresh(extraction)
    
    async def _db_to_schema(self, db_extraction: Extraction) -> ExtractionRecord:
        """Convert database extraction to schema"""
        return ExtractionRecord(
            id=db_extraction.id,
            sessionId=db_extraction.session_id,
            fileName=db_extraction.file_name,
            documentType=db_extraction.document_type,
            documentName=None,  # Would need to map from type
            applicableRole=db_extraction.applicable_role,
            category=None,
            confidence=db_extraction.confidence,
            holderName=db_extraction.holder_name,
            dateOfBirth=db_extraction.date_of_birth,
            sirbNumber=db_extraction.sirb_number,
            passportNumber=db_extraction.passport_number,
            fields=json.loads(db_extraction.fields_json) if db_extraction.fields_json else [],
            validity=json.loads(db_extraction.validity_json) if db_extraction.validity_json else None,
            compliance=json.loads(db_extraction.compliance_json) if hasattr(db_extraction, 'compliance_json') else None,
            medicalData=json.loads(db_extraction.medical_data_json) if db_extraction.medical_data_json else None,
            flags=json.loads(db_extraction.flags_json) if db_extraction.flags_json else [],
            isExpired=db_extraction.is_expired,
            processingTimeMs=db_extraction.processing_time_ms,
            summary=db_extraction.summary,
            createdAt=db_extraction.created_at,
            fileHash=db_extraction.file_hash,
            rawLlmResponse=db_extraction.raw_llm_response,
            status=db_extraction.status
        )
    
    async def validate_session(self, session_id: str) -> ValidationResult:
        """Validate all documents in a session"""
        # Get all extractions for this session
        stmt = select(Extraction).where(
            Extraction.session_id == session_id,
            Extraction.status == "COMPLETE"
        )
        result = await self.db.execute(stmt)
        extractions = result.scalars().all()
        
        if len(extractions) < 2:
            raise ValueError("INSUFFICIENT_DOCUMENTS: Need at least 2 documents for validation")
        
        # Convert to dict format for LLM
        extraction_dicts = []
        for ext in extractions:
            ext_dict = {
                "documentType": ext.document_type,
                "holderName": ext.holder_name,
                "dateOfBirth": ext.date_of_birth,
                "validity": json.loads(ext.validity_json) if ext.validity_json else None,
                "medicalData": json.loads(ext.medical_data_json) if ext.medical_data_json else None,
                "flags": json.loads(ext.flags_json) if ext.flags_json else [],
                "isExpired": ext.is_expired
            }
            extraction_dicts.append(ext_dict)
        
        # Call LLM for validation
        llm_result = await self.llm_provider.validate_documents(
            extractions=extraction_dicts,
            prompt=VALIDATION_PROMPT
        )
        
        # Structure result
        validation_result = ValidationResult(
            sessionId=session_id,
            holderProfile=Holderprofile(**llm_result.get("holderProfile", {})),
            consistencyChecks=[
                ConsistencyCheck(**check) 
                for check in llm_result.get("consistencyChecks", [])
            ],
            missingDocuments=llm_result.get("missingDocuments", []),
            expiringDocuments=llm_result.get("expiringDocuments", []),
            medicalFlags=llm_result.get("medicalFlags", []),
            overallStatus=llm_result.get("overallStatus"),
            overallScore=llm_result.get("overallScore", 0),
            summary=llm_result.get("summary"),
            recommendations=llm_result.get("recommendations", [])
        )
        
        # Save to database
        validation = Validation(
            session_id=session_id,
            result_json=json.dumps(validation_result.dict())
        )
        self.db.add(validation)
        await self.db.commit()
        
        return validation_result


class JobQueue:
    """Simple in-memory job queue"""
    
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.processing_jobs: Dict[str, JobResponse] = {}
    
    async def enqueue(self, job_id: str, session_id: str) -> JobResponse:
        """Add job to queue"""
        job = JobResponse(
            jobId=job_id,
            status=JobStatus.QUEUED,
            queuedAt=datetime.utcnow()
        )
        await self.queue.put((job_id, session_id))
        self.processing_jobs[job_id] = job
        return job
    
    async def get_job_status(self, job_id: str) -> Optional[JobResponse]:
        """Get current job status"""
        return self.processing_jobs.get(job_id)
    
    async def process_jobs(self, extraction_service: ExtractionService):
        """Background job processor"""
        while True:
            try:
                job_id, session_id = await self.queue.get()
                
                # Update status to PROCESSING
                job = self.processing_jobs[job_id]
                job.status = JobStatus.PROCESSING
                job.startedAt = datetime.utcnow()
                
                # TODO: Process the actual job here
                
                self.queue.task_done()
                
            except Exception as e:
                print(f"Job processing error: {e}")
                await asyncio.sleep(1)


# Global job queue instance
job_queue = JobQueue()
