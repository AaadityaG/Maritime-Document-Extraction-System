"""Pydantic schemas for request/response validation"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types"""
    COC = "COC"
    COP_BT = "COP_BT"
    COP_PSCRB = "COP_PSCRB"
    COP_AFF = "COP_AFF"
    COP_MEFA = "COP_MEFA"
    COP_MECA = "COP_MECA"
    COP_SSO = "COP_SSO"
    COP_SDSD = "COP_SDSD"
    ECDIS_GENERIC = "ECDIS_GENERIC"
    ECDIS_TYPE = "ECDIS_TYPE"
    SIRB = "SIRB"
    PASSPORT = "PASSPORT"
    PEME = "PEME"
    DRUG_TEST = "DRUG_TEST"
    YELLOW_FEVER = "YELLOW_FEVER"
    ERM = "ERM"
    MARPOL = "MARPOL"
    SULPHUR_CAP = "SULPHUR_CAP"
    BALLAST_WATER = "BALLAST_WATER"
    HATCH_COVER = "HATCH_COVER"
    BRM_SSBT = "BRM_SSBT"
    TRAIN_TRAINER = "TRAIN_TRAINER"
    HAZMAT = "HAZMAT"
    FLAG_STATE = "FLAG_STATE"
    OTHER = "OTHER"


class DocumentCategory(str, Enum):
    """Document categories"""
    IDENTITY = "IDENTITY"
    CERTIFICATION = "CERTIFICATION"
    STCW_ENDORSEMENT = "STCW_ENDORSEMENT"
    MEDICAL = "MEDICAL"
    TRAINING = "TRAINING"
    FLAG_STATE = "FLAG_STATE"
    OTHER = "OTHER"


class ApplicableRole(str, Enum):
    """Applicable roles"""
    DECK = "DECK"
    ENGINE = "ENGINE"
    BOTH = "BOTH"
    N_A = "N/A"


class Confidence(str, Enum):
    """Confidence levels"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Importance(str, Enum):
    """Importance levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FieldStatus(str, Enum):
    """Field status"""
    OK = "OK"
    EXPIRED = "EXPIRED"
    WARNING = "WARNING"
    MISSING = "MISSING"
    N_A = "N/A"


class FlagSeverity(str, Enum):
    """Flag severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FitnessResult(str, Enum):
    """Fitness result"""
    FIT = "FIT"
    UNFIT = "UNFIT"
    N_A = "N/A"


class DrugTestResult(str, Enum):
    """Drug test result"""
    NEGATIVE = "NEGATIVE"
    POSITIVE = "POSITIVE"
    N_A = "N/A"


class OverallStatus(str, Enum):
    """Overall validation status"""
    APPROVED = "APPROVED"
    CONDITIONAL = "CONDITIONAL"
    REJECTED = "REJECTED"


class OverallHealth(str, Enum):
    """Overall session health"""
    OK = "OK"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class JobStatus(str, Enum):
    """Job status"""
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# Request/Response Schemas

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
    rawOcrText: Optional[str] = None  # Raw OCR-extracted text
    status: str = "COMPLETE"


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


class Holderprofile(BaseModel):
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


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: int
    dependencies: Dict[str, str]
    timestamp: str
    error: Optional[str] = None
