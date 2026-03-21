"""Document extraction service"""

import hashlib
import json
import time
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Extraction, Session
from app.schemas import ExtractionRecord, FieldExtraction, ValidityInfo, ComplianceInfo, MedicalData, Flag, Confidence
from app.services.llm_provider import get_llm_provider
from app.utils.prompts import EXTRACTION_PROMPT
from app.core.config import settings


def calculate_file_hash(file_data: bytes) -> str:
    """Calculate SHA-256 hash of file data"""
    return hashlib.sha256(file_data).hexdigest()


class ExtractionService:
    """Service for document extraction"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.llm_provider = get_llm_provider()
    
    async def extract_document(
        self,
        file_data: bytes,
        file_name: str,
        mime_type: str,
        session_id: str
    ) -> Tuple[ExtractionRecord, bool]:
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
            structured_data = self._structure_extraction(llm_response, session_id, file_name)
            
            # Update extraction record
            await self._update_extraction(extraction, structured_data, start_time)
            
            return structured_data, False
            
        except Exception as e:
            # Mark as failed but keep the record
            extraction.status = "FAILED"
            extraction.raw_llm_response = f"Error: {str(e)}"
            await self.db.commit()
            raise
    
    async def _find_by_hash(self, session_id: str, file_hash: str) -> Optional[ExtractionRecord]:
        """Find existing extraction by file hash"""
        stmt = select(Extraction).where(
            Extraction.session_id == session_id,
            Extraction.file_hash == file_hash,
            Extraction.status == "COMPLETE"
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            return self._db_to_schema(existing)
        return None
    
    def _structure_extraction(self, llm_data: dict, session_id: str, file_name: str) -> ExtractionRecord:
        """Structure LLM response into ExtractionRecord"""
        detection = llm_data.get("detection", {})
        holder = llm_data.get("holder", {})
        validity = llm_data.get("validity", {})
        compliance = llm_data.get("compliance", {})
        medical = llm_data.get("medicalData", {})
        flags = llm_data.get("flags", [])
        fields = llm_data.get("fields", [])
        
        # Calculate expiry info
        days_until_expiry = None
        is_expired = False
        if validity.get("dateOfExpiry"):
            try:
                from datetime import datetime
                expiry = datetime.strptime(validity["dateOfExpiry"], "%d/%m/%Y")
                delta = expiry - datetime.utcnow()
                days_until_expiry = delta.days
                is_expired = days_until_expiry < 0
            except:
                pass
        
        return ExtractionRecord(
            id=str(int(time.time())),
            sessionId=session_id,
            fileName=file_name,
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
    
    async def _update_extraction(self, extraction: Extraction, structured_data: ExtractionRecord, start_time: float):
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
    
    def _db_to_schema(self, db_extraction: Extraction) -> ExtractionRecord:
        """Convert database extraction to schema"""
        return ExtractionRecord(
            id=db_extraction.id,
            sessionId=db_extraction.session_id,
            fileName=db_extraction.file_name,
            documentType=db_extraction.document_type,
            applicableRole=db_extraction.applicable_role,
            confidence=db_extraction.confidence,
            holderName=db_extraction.holder_name,
            dateOfBirth=db_extraction.date_of_birth,
            sirbNumber=db_extraction.sirb_number,
            passportNumber=db_extraction.passport_number,
            fields=json.loads(db_extraction.fields_json) if db_extraction.fields_json else [],
            validity=json.loads(db_extraction.validity_json) if db_extraction.validity_json else None,
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
