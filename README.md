# Smart Maritime Document Extractor (SMDE)

Automated maritime document analysis and compliance validation using vision-capable LLMs.

## Quick Start (3 Commands)

### 1. Install Dependencies

```bash
# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file with your LLM API key:

```bash
# Copy the example
copy .env.example .env

# Edit .env and add your API key
# Get free Gemini key: https://aistudio.google.com/app/apikey
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
LLM_API_KEY=your_api_key_here
```

### 3. Run the Server

```bash
python main.py
```

Server starts on **http://localhost:8001**

---

## Project Structure

```
mari document system/
├── app/                          # Main application package
│   ├── __init__.py              # Package initialization
│   ├── core/                    # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py            # Settings & environment variables
│   │   └── database.py          # Database connection & session management
│   ├── models/                  # SQLAlchemy database models
│   │   └── __init__.py          # Session, Extraction, Job, Validation
│   ├── schemas/                 # Pydantic schemas for validation
│   │   └── __init__.py          # Request/Response schemas
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── extraction.py        # Document extraction service
│   │   ├── llm_provider.py      # LLM provider abstraction
│   │   └── job_queue.py         # Job queue management
│   ├── routers/                 # API route handlers
│   │   ├── __init__.py
│   │   ├── health.py            # Health check endpoint
│   │   └── extraction.py        # Document endpoints
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       └── prompts.py           # LLM prompts
├── uploads/                     # Temporary file storage
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Environment template
├── ADR.md                       # Architecture decisions
├── CODE_REVIEW.md               # Code review examples
└── README.md                    # This file
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with dependency status |
| `/api/extract?mode=sync` | POST | Upload document for extraction (default: sync) |
| `/api/extract?mode=async` | POST | Queue document for async processing |
| `/api/jobs/{jobId}` | GET | Poll async job status |
| `/api/sessions/{sessionId}` | GET | Get all documents in session |
| `/api/sessions/{sessionId}/validate` | POST | Cross-document compliance validation |
| `/api/sessions/{sessionId}/report` | GET | Generate compliance report |

---

## Testing the API

### 1. Health Check
```bash
curl http://localhost:8001/api/health
```

### 2. Upload a Document
```bash
curl -X POST "http://localhost:8001/api/extract" \
  -F "document=@path/to/your/certificate.pdf" \
  -F "sessionId=test-session-123"
```

### 3. Validate Session
```bash
curl -X POST "http://localhost:8001/api/sessions/test-session-123/validate"
```

### 4. Get Report
```bash
curl http://localhost:8001/api/sessions/test-session-123/report
```

---

## Interactive API Documentation

FastAPI provides automatic interactive docs:

- **Swagger UI:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc

---

## Architecture Highlights

### Modular Design
- **Separation of concerns**: Routes, services, models, schemas clearly separated
- **Dependency injection**: Database sessions managed via FastAPI dependencies
- **Provider abstraction**: Swap LLM providers without code changes

### Scalability Features
- **Async-first**: All I/O operations use async/await
- **Database pooling**: SQLAlchemy async session manager
- **Job queue**: In-memory queue ready for Redis migration
- **Rate limiting**: Per-IP rate limiting with SlowAPI

### Production Ready
- **Environment-based config**: Pydantic Settings with .env support
- **Error handling**: Structured error responses
- **Deduplication**: SHA-256 hash caching prevents re-processing
- **Raw response storage**: All LLM responses preserved for debugging

---

## Development

### Running Tests
```bash
pytest
```

### Hot Reload
```bash
uvicorn main:app --reload --port 8001
```

### Adding New Endpoints

1. Create router in `app/routers/my_feature.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["My Feature"])

@router.get("/endpoint")
async def my_endpoint():
    return {"message": "Hello"}
```

2. Include in `main.py`:
```python
from app.routers import my_feature
app.include_router(my_feature.router)
```

---

## Deployment

### Docker (Future)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Environment Variables for Production
```bash
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
LLM_API_KEY=production_key
RATE_LIMIT_REQUESTS=100
```

---

For more details, see:
- **Architecture Decisions:** [ADR.md](ADR.md)
- **Code Review Examples:** [CODE_REVIEW.md](CODE_REVIEW.md)
- **Full Specification:** [reference.md](reference.md)

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with dependency status |
| `/api/extract?mode=sync` | POST | Upload document for extraction (default: sync) |
| `/api/extract?mode=async` | POST | Queue document for async processing |
| `/api/jobs/{jobId}` | GET | Poll async job status |
| `/api/sessions/{sessionId}` | GET | Get all documents in session |
| `/api/sessions/{sessionId}/validate` | POST | Cross-document compliance validation |
| `/api/sessions/{sessionId}/report` | GET | Generate compliance report |

---

## Testing the API

### 1. Health Check
```bash
curl http://localhost:8001/api/health
```

### 2. Upload a Document
```bash
curl -X POST "http://localhost:8001/api/extract" \
  -F "document=@path/to/your/certificate.pdf" \
  -F "sessionId=test-session-123"
```

### 3. Validate Session
```bash
curl -X POST "http://localhost:8001/api/sessions/test-session-123/validate"
```

### 4. Get Report
```bash
curl http://localhost:8001/api/sessions/test-session-123/report
```

---

## Interactive API Documentation

FastAPI provides automatic interactive docs:

- **Swagger UI:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc

---

## Supported Document Types

**Identity Documents:**
- SIRB (Seafarer's Identification Record Book)
- PASSPORT

**Certificates of Competency:**
- COC (Certificate of Competency)
- COP_BT (Basic Training)
- COP_PSCRB (Survival Craft & Rescue Boats)
- COP_AFF (Advanced Fire Fighting)
- COP_MEFA (Medical First Aid)
- COP_MECA (Medical Care)
- COP_SSO (Ship Security Officer)
- COP_SDSD (Security Duties)

**Medical Certificates:**
- PEME (Pre-Employment Medical Examination)
- DRUG_TEST (Drug Test Result)
- YELLOW_FEVER (Vaccination Certificate)

**Training Certificates:**
- ECDIS_GENERIC (Electronic Chart Display)
- ERM (Engine Room Resource Management)
- BRM_SSBT (Bridge Resource Management)
- MARPOL, SULPHUR_CAP, BALLAST_WATER, HATCH_COVER, TRAIN_TRAINER, HAZMAT, FLAG_STATE

---

## LLM Provider Options

| Provider | Free Tier | Recommended Model | Get Key |
|----------|-----------|-------------------|---------|
| **Gemini** | ✅ Yes | gemini-2.0-flash | [Get Key](https://aistudio.google.com/app/apikey) |
| **Anthropic** | ❌ Paid | claude-haiku-4-5-20251001 | [Get Key](https://console.anthropic.com) |
| **Groq** | ✅ Limited | llama-3.2-11b-vision-preview | [Get Key](https://console.groq.com) |

Change provider in `.env`:
```bash
LLM_PROVIDER=gemini  # or anthropic, groq
LLM_MODEL=gemini-2.0-flash
```

---

## Project Structure

```
mari document system/
├── main.py                 # FastAPI application & routes
├── config.py               # Configuration & environment variables
├── database.py             # SQLAlchemy models & DB manager
├── schemas.py              # Pydantic schemas for validation
├── enums.py                # Type enumerations
├── llm_providers.py        # LLM provider abstraction layer
├── services.py             # Business logic (extraction, validation)
├── prompts.py              # LLM extraction & validation prompts
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create from .env.example)
├── .env.example            # Environment template
├── ADR.md                  # Architecture Decision Record
├── CODE_REVIEW.md          # Code review of junior engineer's PR
├── reference.md            # System specification
└── uploads/                # Temporary file storage (auto-created)
```

---

## Features

✅ **Vision-based LLM extraction** - Supports images (JPEG/PNG) and PDFs  
✅ **Sync & Async modes** - Auto-switch based on file size  
✅ **Deduplication** - SHA-256 hash caching prevents re-processing  
✅ **Cross-document validation** - Consistency checks across all uploaded docs  
✅ **Compliance reporting** - Structured hire/no-hire recommendations  
✅ **Rate limiting** - 10 requests/minute per IP  
✅ **Provider abstraction** - Swap LLM providers via environment variable  
✅ **SQLite database** - Zero-setup persistence (PostgreSQL compatible)  
✅ **Automatic API docs** - Swagger UI and ReDoc  

---

## Rate Limiting

- **Limit:** 10 requests per minute per IP address
- **Applies to:** `/api/extract` endpoint only
- **Response:** `429 Too Many Requests` with `Retry-After` header

---

## Database

Uses SQLite by default (`smde.db` file).

**Tables:**
- `sessions` - Upload sessions
- `extractions` - Extracted document data with JSON fields
- `jobs` - Async job queue
- `validations` - Cross-document validation results

**Migrate to PostgreSQL:**
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost/smde_db
```

---

## Error Handling

All errors follow this format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description",
  "extractionId": "uuid-if-applicable",
  "retryAfterMs": null
}
```

**Error codes:**
- `UNSUPPORTED_FORMAT` - File type not accepted
- `FILE_TOO_LARGE` - Exceeds 10MB limit
- `SESSION_NOT_FOUND` - Invalid session ID
- `JOB_NOT_FOUND` - Invalid job ID
- `INSUFFICIENT_DOCUMENTS` - Less than 2 docs for validation
- `LLM_JSON_PARSE_FAIL` - LLM returned invalid JSON
- `RATE_LIMITED` - Too many requests
- `INTERNAL_ERROR` - Unexpected server error

---

## Architecture Decisions

See **[ADR.md](ADR.md)** for detailed architecture decisions on:
- Sync vs Async default mode
- Queue mechanism choice
- LLM provider abstraction
- Schema design trade-offs
- Production readiness gaps

---

## Development

### Running Tests
```bash
pytest
```

### Hot Reload
```bash
uvicorn main:app --reload --port 8001
```

### View Logs
The server logs to console. For production, configure logging to file.

---

## Troubleshooting

**ModuleNotFoundError: No module named 'slowapi'**
```bash
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**LLM API returns 401**
- Check your API key in `.env`
- Verify you have credits/quota remaining

**Database locked error**
- Close any other processes using `smde.db`
- Delete `smde.db` to start fresh

**Port 8001 already in use**
```bash
# Change port in .env
PORT=8002
```

---

## License

MIT

---

## Support

For issues or questions, refer to:
- **Specification:** [reference.md](reference.md)
- **Architecture:** [ADR.md](ADR.md)
- **Code Review Examples:** [CODE_REVIEW.md](CODE_REVIEW.md)
