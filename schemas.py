from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enums import (
    DocumentType, DocumentCategory, ApplicableRole, Confidence,
    Importance, FieldStatus, FlagSeverity, FitnessResult,
    DrugTestResult, OverallStatus, OverallHealth
)


class FieldExtraction(BaseModel):
    key: str
    label: str
    value: Optional[str] = None
    importance: Importance = Importance.MEDIUM
    status: FieldStatus = FieldStatus.OK


class ValidityInfo(BaseModel):
    dateOfIssue: Optional[str] = None
    dateOfExpiry: Optional[str] = None
    isExpired: bool = False
    daysUntilExpiry: Optional[int] = None
    revalidationRequired: Optional[bool] = None


class ComplianceInfo(BaseModel):
    issuingAuthority: Optional[str] = None
    regulationReference: Optional[str] = None
    imoModelCourse: Optional[str] = None
    recognizedAuthority: bool = True
    limitations: Optional[str] = None


class MedicalData(BaseModel):
    fitnessResult: FitnessResult = FitnessResult.N_A
    drugTestResult: DrugTestResult = DrugTestResult.N_A
    restrictions: Optional[str] = None
    specialNotes: Optional[str] = None
    expiryDate: Optional[str] = None


class Flag(BaseModel):
    severity: FlagSeverity
    message: str


class HolderInfo(BaseModel):
    fullName: Optional[str] = None
    dateOfBirth: Optional[str] = None
    nationality: Optional[str] = None
    passportNumber: Optional[str] = None
    sirbNumber: Optional[str] = None
    rank: Optional[str] = None
    photo: str = "ABSENT"


class DetectionInfo(BaseModel):
    documentType: DocumentType
    documentName: str
    category: DocumentCategory
    applicableRole: ApplicableRole
    isRequired: bool = True
    confidence: Confidence
    detectionReason: str


class ExtractionRequest(BaseModel):
    detection: DetectionInfo
    holder: HolderInfo
    fields: List[FieldExtraction]
    validity: ValidityInfo
    compliance: ComplianceInfo
    medicalData: MedicalData = Field(default_factory=MedicalData)
    flags: List[Flag] = Field(default_factory=list)
    summary: str


class ExtractionRecord(BaseModel):
    id: str
    sessionId: str
    fileName: str
    documentType: Optional[DocumentType] = None
    documentName: Optional[str] = None
    applicableRole: Optional[ApplicableRole] = None
    category: Optional[DocumentCategory] = None
    confidence: Optional[Confidence] = None
    holderName: Optional[str] = None
    dateOfBirth: Optional[str] = None
    sirbNumber: Optional[str] = None
    passportNumber: Optional[str] = None
    fields: List[FieldExtraction] = Field(default_factory=list)
    validity: Optional[ValidityInfo] = None
    compliance: Optional[ComplianceInfo] = None
    medicalData: Optional[MedicalData] = None
    flags: List[Flag] = Field(default_factory=list)
    isExpired: bool = False
    processingTimeMs: int = 0
    summary: Optional[str] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    fileHash: Optional[str] = None
    rawLlmResponse: Optional[str] = None
    status: str = "COMPLETE"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class JobResponse(BaseModel):
    jobId: str
    status: JobStatus
    queuePosition: Optional[int] = None
    startedAt: Optional[datetime] = None
    estimatedCompleteMs: Optional[int] = None
    extractionId: Optional[str] = None
    result: Optional[ExtractionRecord] = None
    completedAt: Optional[datetime] = None
    error: Optional[str] = None
    message: Optional[str] = None
    failedAt: Optional[datetime] = None
    retryable: bool = False


class SessionSummary(BaseModel):
    sessionId: str
    documentCount: int
    detectedRole: Optional[ApplicableRole] = None
    overallHealth: OverallHealth = OverallHealth.OK
    documents: List[Dict[str, Any]]
    pendingJobs: List[str] = Field(default_factory=list)


class HolderProfile(BaseModel):
    fullName: Optional[str] = None
    dateOfBirth: Optional[str] = None
    sirbNumber: Optional[str] = None
    passportNumber: Optional[str] = None
    nationality: Optional[str] = None
    detectedRank: Optional[str] = None


class ConsistencyCheck(BaseModel):
    field: str
    status: str  # "CONSISTENT", "INCONSISTENT", "MISSING"
    details: str
    severity: Optional[FlagSeverity] = None


class ValidationResult(BaseModel):
    sessionId: str
    holderProfile: Holderprofile
    consistencyChecks: List[ConsistencyCheck]
    missingDocuments: List[str]
    expiringDocuments: List[str]
    medicalFlags: List[str]
    overallStatus: OverallStatus
    overallScore: int
    summary: str
    recommendations: List[str]
    validatedAt: datetime = Field(default_factory=datetime.utcnow)


class ComplianceReport(BaseModel):
    sessionId: str
    generatedAt: datetime
    candidateSummary: Dict[str, Any]
    documentOverview: List[Dict[str, Any]]
    complianceAssessment: Dict[str, Any]
    riskAnalysis: Dict[str, Any]
    hiringRecommendation: str
    actionItems: List[str]
    detailedFindings: List[Dict[str, Any]]
