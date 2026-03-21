# Smart Maritime Document Extractor (SMDE) - Complete Project Documentation

**Version:** 1.0.0  
**Last Updated:** March 21, 2026  
**Project Root:** `c:\Users\ADITYA\OneDrive\Desktop\mari document system`

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Folder Structure](#folder-structure)
4. [Technology Stack](#technology-stack)
5. [Environment Configuration](#environment-configuration)
6. [Database Schema](#database-schema)
7. [API Endpoints](#api-endpoints)
8. [LLM Integration](#llm-integration)
9. [Setup Instructions](#setup-instructions)
10. [Development Guide](#development-guide)

---

## 🎯 Project Overview

**Smart Maritime Document Extractor (SMDE)** is an AI-powered system for automated analysis of maritime seafarer documents using vision-capable Large Language Models (LLMs).

### Core Functionality
- **Document Upload:** Accept PDF/image uploads of maritime certificates
- **Automated Extraction:** Use LLM to extract structured data from documents
- **Cross-Validation:** Validate consistency across multiple documents
- **Compliance Reporting:** Generate hire/no-hire recommendations
- **Async Processing:** Support both synchronous and asynchronous processing

### Key Features
✅ Vision-based LLM extraction (supports images + PDFs)  
✅ Sync & async processing modes  
✅ SHA-256 deduplication caching  
✅ Rate limiting (configurable per IP)  
✅ Provider abstraction (swap LLM providers via config)  
✅ SQLite database with async support  
✅ Automatic API documentation  
✅ Comprehensive error handling  

---

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────┐
│   Client    │
│ (Browser/   │
│   Postman)  │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  ┌───────────────────────────────┐  │
│  │  Rate Limiter (SlowAPI)       │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  API Routers                  │  │
│  │  - health.py                  │  │
│  │  - extraction.py              │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  Services Layer               │  │
│  │  - ExtractionService          │  │
│  │  - LLM Provider (abstracted)  │  │
│  │  - Job Queue                  │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  Database Layer               │  │
│  │  - SQLAlchemy ORM             │  │
│  │  - AsyncSession               │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐
│   SQLite    │      │  LLM Provider│
│   (smde.db) │      │  (Gemini/    │
│             │      │   Anthropic) │
└─────────────┘      └──────────────┘
```

### Request Flow

1. **Upload Document** → POST `/api/extract`
2. **Rate Limit Check** → SlowAPI middleware
3. **File Validation** → Type, size checks
4. **Deduplication Check** → SHA-256 hash lookup
5. **LLM Processing**:
   - Convert to base64
   - Call LLM provider with prompt
   - Parse JSON response
   - Handle rate limits with retry
6. **Database Storage** → Save extraction record
7. **Response** → Structured JSON

---

## 📁 Folder Structure

```
mari document system/
│
├── app/                              # Main application package
│   ├── __init__.py                  # Package initialization
│   │
│   ├── core/                        # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py                # Pydantic Settings
│   │   │   - Settings class
│   │   │   - Environment variables
│   │   │   - Constants
│   │   └── database.py              # Database connection
│   │       - DatabaseManager class
│   │       - get_db() dependency
│   │       - Base model
│   │
│   ├── models/                      # SQLAlchemy ORM models
│   │   └── __init__.py
│   │       - Session model
│   │       - Extraction model
│   │       - Job model
│   │       - Validation model
│   │
│   ├── schemas/                     # Pydantic schemas
│   │   └── __init__.py
│   │       - Enums (DocumentType, Confidence, etc.)
│   │       - Request schemas
│   │       - Response schemas
│   │
│   ├── services/                    # Business logic
│   │   ├── __init__.py
│   │   ├── extraction.py            # ExtractionService
│   │   ├── llm_provider.py          # LLM abstraction
│   │   │   - LLMProvider (ABC)
│   │   │   - GeminiProvider
│   │   │   - AnthropicProvider
│   │   └── job_queue.py             # Async job queue
│   │
│   ├── routers/                     # API route handlers
│   │   ├── __init__.py
│   │   ├── health.py                # Health endpoint
│   │   └── extraction.py            # All document endpoints
│   │
│   └── utils/                       # Utility functions
│       ├── __init__.py
│       └── prompts.py               # LLM prompts
│           - EXTRACTION_PROMPT
│           - VALIDATION_PROMPT
│
├── uploads/                         # Temporary file storage
│   └── (auto-created on startup)
│
├── main.py                          # Application entry point
│   - FastAPI app initialization
│   - Middleware configuration
│   - Router inclusion
│   - Startup/shutdown events
│
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (gitignored)
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore rules
├── README.md                        # Quick start guide
├── ADR.md                           # Architecture decisions
├── CODE_REVIEW.md                   # Code review examples
└── reference.md                     # Original specification
```

---

## 💻 Technology Stack

### Runtime & Framework
- **Python:** 3.14+
- **Web Framework:** FastAPI 0.109.0
- **ASGI Server:** Uvicorn 0.27.0

### Database & ORM
- **Database:** SQLite (default) / PostgreSQL (optional)
- **ORM:** SQLAlchemy 2.0.48
- **Async Driver:** aiosqlite 0.22.1

### Validation & Serialization
- **Pydantic:** 2.12.5
- **Pydantic Settings:** 2.13.1

### File Handling
- **Image Processing:** Pillow 12.1.1
- **Async File I/O:** aiofiles 25.1.0
- **OCR (Optional):** pytesseract 0.3.13
- **PDF Processing:** pdf2image 1.17.0

### HTTP & APIs
- **HTTP Client:** httpx 0.28.1
- **Multipart Forms:** python-multipart 0.0.6

### Security & Auth
- **Rate Limiting:** slowapi 0.1.9
- **JWT (Optional):** python-jose 3.3.0
- **Password Hashing:** passlib 1.7.4, bcrypt 4.1.2

### Environment
- **Dotenv:** python-dotenv 1.2.2

---

## ⚙️ Environment Configuration

### Required Variables (.env)

```bash
# LLM Provider Configuration
LLM_PROVIDER=gemini              # Options: gemini, anthropic
LLM_MODEL=gemini-2.0-flash       # Model name
LLM_API_KEY=your_api_key_here    # Get from https://aistudio.google.com/app/apikey

# Server Configuration
HOST=0.0.0.0                     # Network interface
PORT=8001                        # Server port
DEBUG=true                       # Enable auto-reload

# Database
DATABASE_URL=sqlite+aiosqlite:///./smde.db

# File Upload Configuration
MAX_FILE_SIZE=10485760           # 10MB in bytes
ALLOWED_EXTENSIONS=image/jpeg,image/png,application/pdf
UPLOAD_DIR=./uploads

# Rate Limiting
RATE_LIMIT_REQUESTS=5            # Requests per period (reduced for free tier LLMs)
RATE_LIMIT_PERIOD=60             # Period in seconds

# Job Processing
JOB_TIMEOUT=300                  # LLM call timeout in seconds
ASYNC_THRESHOLD=5242880          # 5MB - files larger force async mode
```

### Optional Variables

```bash
# For production deployment
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Alternative LLM providers
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
```

---

## 🗄️ Database Schema

### Tables

#### 1. sessions
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose:** Groups related document extractions (one sailor's complete set)

#### 2. extractions
```sql
CREATE TABLE extractions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL,              -- SHA-256 for deduplication
    document_type TEXT,                   -- COC, PEME, etc.
    applicable_role TEXT,                 -- DECK, ENGINE, BOTH
    confidence TEXT,                      -- HIGH, MEDIUM, LOW
    holder_name TEXT,
    date_of_birth TEXT,
    sirb_number TEXT,
    passport_number TEXT,
    fields_json TEXT,                     -- Extracted fields as JSON
    validity_json TEXT,                   -- Issue/expiry dates
    medical_data_json TEXT,               -- Medical results
    flags_json TEXT,                      -- Compliance flags
    is_expired BOOLEAN DEFAULT 0,
    summary TEXT,
    raw_llm_response TEXT,                -- Store original LLM response
    processing_time_ms INTEGER,
    status TEXT DEFAULT 'COMPLETE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_file_hash ON extractions(file_hash);
CREATE INDEX idx_created_at ON extractions(created_at);
```

**Purpose:** Stores extracted document data with full audit trail

#### 3. jobs
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    extraction_id TEXT REFERENCES extractions(id),
    status TEXT DEFAULT 'QUEUED',         -- QUEUED, PROCESSING, COMPLETE, FAILED
    error_code TEXT,
    error_message TEXT,
    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**Purpose:** Tracks async job processing state

#### 4. validations
```sql
CREATE TABLE validations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    result_json TEXT NOT NULL,            -- Validation result as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose:** Stores cross-document validation results

---

## 🔌 API Endpoints

### Health Check

#### GET `/api/health`

**Response:**
```json
{
  "status": "OK",
  "version": "1.0.0",
  "uptime": 3612,
  "dependencies": {
    "database": "OK",
    "llmProvider": "OK",
    "queue": "OK"
  },
  "timestamp": "2026-03-21T15:30:00Z"
}
```

---

### Document Extraction

#### POST `/api/extract?mode=sync`

**Request:**
- Content-Type: `multipart/form-data`
- Parameters:
  - `document` (file): PDF or image
  - `sessionId` (string, optional): Group documents together
  - `mode` (string): "sync" or "async"

**Sync Response (200):**
```json
{
  "id": "uuid",
  "sessionId": "uuid",
  "fileName": "PEME_Samoya.pdf",
  "documentType": "PEME",
  "documentName": "Pre-Employment Medical Examination",
  "applicableRole": "ENGINE",
  "category": "MEDICAL",
  "confidence": "HIGH",
  "holderName": "Samuel P. Samoya",
  "dateOfBirth": "12/03/1988",
  "sirbNumber": "C0869326",
  "fields": [...],
  "validity": {
    "dateOfIssue": "06/01/2025",
    "dateOfExpiry": "06/01/2027",
    "isExpired": false,
    "daysUntilExpiry": 660
  },
  "medicalData": {
    "fitnessResult": "FIT",
    "drugTestResult": "NEGATIVE"
  },
  "flags": [],
  "isExpired": false,
  "processingTimeMs": 4230,
  "summary": "...",
  "createdAt": "2026-03-21T15:30:00Z"
}
```

**Async Response (202):**
```json
{
  "jobId": "uuid",
  "sessionId": "uuid",
  "status": "QUEUED",
  "pollUrl": "/api/jobs/uuid",
  "estimatedWaitMs": 6000
}
```

**Error Responses:**
- `400 UNSUPPORTED_FORMAT`: File type not accepted
- `413 FILE_TOO_LARGE`: Exceeds 10MB limit
- `429 RATE_LIMITED`: Too many requests

---

### Job Polling

#### GET `/api/jobs/{jobId}`

**Response:**
```json
{
  "jobId": "uuid",
  "status": "PROCESSING",
  "queuePosition": 2,
  "startedAt": "2026-03-21T15:30:00Z",
  "estimatedCompleteMs": 3200
}
```

**States:** `QUEUED` → `PROCESSING` → `COMPLETE` | `FAILED`

---

### Session Summary

#### GET `/api/sessions/{sessionId}`

**Response:**
```json
{
  "sessionId": "uuid",
  "documentCount": 5,
  "detectedRole": "DECK",
  "overallHealth": "WARN",
  "documents": [
    {
      "id": "uuid",
      "fileName": "COC_Salonoy.jpg",
      "documentType": "COC",
      "applicableRole": "DECK",
      "holderName": "Francisco J. Salonoy",
      "confidence": "HIGH",
      "isExpired": false,
      "flagCount": 0,
      "createdAt": "2026-03-21T15:30:00Z"
    }
  ],
  "pendingJobs": []
}
```

**overallHealth Values:**
- `OK`: No expired certs, no CRITICAL flags
- `WARN`: Expiring within 90 days or MEDIUM/HIGH flags
- `CRITICAL`: Expired required certs or CRITICAL flags

---

### Cross-Document Validation

#### POST `/api/sessions/{sessionId}/validate`

**Requirements:** Minimum 2 documents in session

**Response:**
```json
{
  "sessionId": "uuid",
  "holderProfile": {
    "fullName": "Samuel P. Samoya",
    "dateOfBirth": "12/03/1988",
    "sirbNumber": "C0869326",
    "nationality": "Filipino",
    "detectedRank": "Engine Officer"
  },
  "consistencyChecks": [
    {
      "field": "fullName",
      "status": "CONSISTENT",
      "details": "Name matches across all documents"
    }
  ],
  "missingDocuments": ["COP_SDSD"],
  "expiringDocuments": ["COC"],
  "medicalFlags": ["Schistosomiasis history noted"],
  "overallStatus": "CONDITIONAL",
  "overallScore": 74,
  "summary": "Candidate has most required documents with minor gaps...",
  "recommendations": [
    "Obtain COP_SDSD certificate",
    "Monitor COC expiry (expires in 85 days)"
  ],
  "validatedAt": "2026-03-21T15:35:00Z"
}
```

**overallStatus Values:**
- `APPROVED`: Score 90-100, all docs present and valid
- `CONDITIONAL`: Score 70-89, minor issues
- `REJECTED`: Score <70, critical issues

---

### Compliance Report

#### GET `/api/sessions/{sessionId}/report`

**Response:**
```json
{
  "sessionId": "uuid",
  "generatedAt": "2026-03-21T15:36:00Z",
  "candidateSummary": {
    "name": "Samuel P. Samoya",
    "nationality": "Filipino",
    "detectedRank": "Engine Officer"
  },
  "documentOverview": [
    {
      "type": "COC",
      "fileName": "COC_Samoya.pdf",
      "status": "VALID",
      "confidence": "HIGH"
    }
  ],
  "complianceAssessment": {
    "overallStatus": "CONDITIONAL",
    "overallScore": 74,
    "missingDocuments": ["COP_SDSD"],
    "expiringDocuments": ["COC"]
  },
  "riskAnalysis": {
    "criticalIssues": 0,
    "medicalConcerns": ["Schistosomiasis history"],
    "consistencyIssues": []
  },
  "hiringRecommendation": "CONDITIONAL - Minor issues require attention before hire",
  "actionItems": [
    "Obtain COP_SDSD certificate",
    "Monitor COC expiry date"
  ],
  "detailedFindings": [...]
}
```

---

## 🤖 LLM Integration

### Supported Providers

#### 1. Google Gemini (Default - Free Tier)
- **Model:** `gemini-2.0-flash`
- **Rate Limit:** ~5 requests/minute (free tier)
- **Vision Support:** ✅ Native
- **Get Key:** https://aistudio.google.com/app/apikey

#### 2. Anthropic Claude (Paid)
- **Model:** `claude-haiku-4-5-20251001`
- **Rate Limit:** Higher limits
- **Vision Support:** ✅ Native
- **Get Key:** https://console.anthropic.com

### Provider Abstraction

```python
# app/services/llm_provider.py

class LLMProvider(ABC):
    @abstractmethod
    async def extract_document(file_data, mime_type, prompt) -> Dict
    @abstractmethod
    async def validate_documents(extractions, prompt) -> Dict

class GeminiProvider(LLMProvider):
    # Implements Google Gemini API

class AnthropicProvider(LLMProvider):
    # Implements Anthropic Claude API

def get_llm_provider() -> LLMProvider:
    # Factory function based on config
```

### Retry Logic

All LLM calls include:
- **Max Retries:** 5 attempts
- **Backoff Strategy:** Exponential (5s, 10s, 20s, 40s, 80s)
- **Rate Limit Handling:** Respects `Retry-After` header
- **Timeout:** Configurable (default 300s)

### Prompts

Two main prompts are used:

1. **EXTRACTION_PROMPT** (`app/utils/prompts.py`)
   - Identifies document type
   - Extracts structured fields
   - Detects compliance flags
   - Returns strict JSON schema

2. **VALIDATION_PROMPT** (`app/utils/prompts.py`)
   - Cross-document consistency checks
   - Missing document detection
   - Expiry timeline analysis
   - Scoring & recommendations

---

## 🚀 Setup Instructions

### Step 1: Install Python Dependencies

```bash
# Navigate to project directory
cd "c:\Users\ADITYA\OneDrive\Desktop\mari document system"

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install all packages
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env file
notepad .env
```

**Required changes:**
```bash
LLM_API_KEY=your_actual_api_key_here
```

**Get Gemini API key:**
1. Go to https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy and paste into `.env`

### Step 3: Initialize Database

Database auto-initializes on first run. No manual step needed.

### Step 4: Run the Server

```bash
python main.py
```

**Expected output:**
```
============================================================
Smart Maritime Document Extractor (SMDE)
============================================================
Starting server on http://0.0.0.0:8001
API Docs: http://0.0.0.0:8001/docs
Health Check: http://0.0.0.0:8001/api/health
============================================================
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Step 5: Test the API

**Option 1: Browser**
- Open: http://localhost:8001/docs
- Try the interactive Swagger UI

**Option 2: cURL**
```bash
# Health check
curl http://localhost:8001/api/health

# Upload document
curl -X POST "http://localhost:8001/api/extract" \
  -F "document=@path/to/certificate.pdf" \
  -F "sessionId=test-123"
```

**Option 3: Postman**
- Import collection from Swagger UI
- Or manually create requests

---

## 👨‍💻 Development Guide

### Running in Development Mode

```bash
# Auto-reload on code changes
uvicorn main:app --reload --port 8001
```

### Adding New Endpoints

1. **Create new router:**
```python
# app/routers/my_feature.py
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["My Feature"])

@router.get("/endpoint")
async def my_endpoint():
    return {"message": "Hello"}
```

2. **Include in main.py:**
```python
from app.routers import my_feature
app.include_router(my_feature.router)
```

### Adding New Models

1. **Define SQLAlchemy model:**
```python
# app/models/my_model.py
from app.core.database import Base
from sqlalchemy import Column, String

class MyModel(Base):
    __tablename__ = "my_table"
    id = Column(String, primary_key=True)
```

2. **Update `app/models/__init__.py`:**
```python
from app.models.my_model import MyModel
```

### Adding New Schemas

1. **Define Pydantic schema:**
```python
# app/schemas/my_schema.py
from pydantic import BaseModel

class MyResponse(BaseModel):
    message: str
```

2. **Export from `app/schemas/__init__.py`**

### Testing

```bash
# Install pytest
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Debugging

**Common Issues:**

1. **ModuleNotFoundError:**
```bash
# Ensure you're in project root and venv is activated
pwd
.\venv\Scripts\Activate.ps1
```

2. **Port already in use:**
```bash
# Change port in .env
PORT=8002
```

3. **Database locked:**
```bash
# Close other processes using smde.db
# Or delete and recreate
rm smde.db
```

4. **LLM rate limiting:**
- Reduce `RATE_LIMIT_REQUESTS` to 5
- Wait between requests
- Use paid tier for higher limits

---

## 📊 Monitoring & Observability

### Logs

Application logs to console. For production:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Metrics to Track

- API request latency
- LLM call duration
- Error rates by endpoint
- Queue depth (async jobs)
- Database query performance

---

## 🔒 Security Considerations

### Current Implementation

✅ Rate limiting per IP  
✅ File type validation  
✅ File size limits  
✅ Environment variable config  

### Production Requirements

❌ Authentication & Authorization  
❌ HTTPS/TLS encryption  
❌ File encryption at rest  
❌ PII data protection  
❌ Audit logging  
❌ Input sanitization  

**Note:** This is a demo/prototype system. Do NOT deploy to production without implementing these security features.

---

## 📈 Performance Optimization

### Current Bottlenecks

1. **LLM Calls:** 2-10 seconds per extraction
2. **Rate Limiting:** Free tier limits throughput
3. **Database:** SQLite single-writer limitation

### Optimization Strategies

1. **Caching:** Already implemented (SHA-256 deduplication)
2. **Async Processing:** Implemented for large files
3. **Database Migration:** PostgreSQL for concurrent writes
4. **Queue System:** Redis for distributed job processing

---

## 🎓 Learning Resources

### FastAPI
- Official Docs: https://fastapi.tiangolo.com
- Tutorial: https://fastapi.tiangolo.com/tutorial

### SQLAlchemy
- ORM Tutorial: https://docs.sqlalchemy.org/en/20/tutorial

### LLM Best Practices
- Prompt Engineering: https://platform.openai.com/docs/guides/prompt-engineering
- Vision Models: https://ai.google.dev/docs/vision

---

## 📞 Support & Troubleshooting

### Getting Help

1. Check logs for detailed error messages
2. Review `.env` configuration
3. Verify LLM API key is valid
4. Test with small files first

### Common Errors

**"Rate limited"**
- Normal for free tier
- Wait or reduce request frequency

**"No module named..."**
- Activate venv: `.\venv\Scripts\Activate.ps1`
- Reinstall: `pip install -r requirements.txt`

**"Database locked"**
- Close other processes
- Delete `smde.db` and restart

---

## 📝 License

MIT License - See project for details

---

## 🙏 Acknowledgments

- FastAPI framework
- SQLAlchemy ORM
- Google Gemini / Anthropic Claude
- Maritime industry stakeholders

---

**End of Documentation**

For questions or issues, refer to:
- **Architecture Decisions:** [ADR.md](ADR.md)
- **Code Review Examples:** [CODE_REVIEW.md](CODE_REVIEW.md)
- **Original Specification:** [reference.md](reference.md)
