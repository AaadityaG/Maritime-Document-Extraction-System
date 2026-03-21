from enum import Enum


class DocumentType(str, Enum):
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
    IDENTITY = "IDENTITY"
    CERTIFICATION = "CERTIFICATION"
    STCW_ENDORSEMENT = "STCW_ENDORSEMENT"
    MEDICAL = "MEDICAL"
    TRAINING = "TRAINING"
    FLAG_STATE = "FLAG_STATE"
    OTHER = "OTHER"


class ApplicableRole(str, Enum):
    DECK = "DECK"
    ENGINE = "ENGINE"
    BOTH = "BOTH"
    N_A = "N/A"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Importance(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FieldStatus(str, Enum):
    OK = "OK"
    EXPIRED = "EXPIRED"
    WARNING = "WARNING"
    MISSING = "MISSING"
    N_A = "N/A"


class FlagSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FitnessResult(str, Enum):
    FIT = "FIT"
    UNFIT = "UNFIT"
    N_A = "N/A"


class DrugTestResult(str, Enum):
    NEGATIVE = "NEGATIVE"
    POSITIVE = "POSITIVE"
    N_A = "N/A"


class OverallStatus(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONAL = "CONDITIONAL"
    REJECTED = "REJECTED"


class OverallHealth(str, Enum):
    OK = "OK"
    WARN = "WARN"
    CRITICAL = "CRITICAL"
