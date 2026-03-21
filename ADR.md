# Architecture Decision Record (ADR)

**Date:** March 21, 2026  
**Project:** Smart Maritime Document Extractor (SMDE)

---

## Q1 — Sync vs Async Default

**Decision:** Default to **sync mode** for files under 5MB, force async for larger files.

**Rationale:**
- Most maritime certificates are single-page scans (200KB-2MB), making sync processing faster and simpler for users
- Immediate feedback improves UX for typical document sizes
- Async adds complexity (polling, job management) that's unnecessary for small files
- The 5MB threshold balances user experience with system stability

**Thresholds:**
- **< 5MB:** Sync (default) - processes in <10 seconds typically
- **5-10MB:** Force async - large PDFs or high-res images that may timeout
- **Concurrency threshold:** Would force async at >20 concurrent requests regardless of size to prevent LLM API saturation

**What changed from spec:** The spec suggested both modes but didn't specify default. Production systems need clear defaults to avoid user confusion.

---

## Q2 — Queue Choice

**Current Implementation:** In-memory asyncio.Queue

**Why:** 
- Simplest possible solution for MVP
- Zero external dependencies
- Works well for low-to-medium throughput (<50 jobs/min)
- Easy to test and debug

**Migration path to 500 concurrent extractions/min:**
1. **First migration:** Redis with BullMQ or aioredis
   - Provides persistence across restarts
   - Better monitoring and retry logic
   - Distributed worker support
   
2. **At scale:** PostgreSQL-based queue (pg-boss pattern)
   - Leverages existing database infrastructure
   - ACID guarantees for job state
   - Better integration with extraction records

**Failure modes of current approach:**
- **Server restart:** All queued jobs lost (mitigated by storing job metadata in DB)
- **No horizontal scaling:** Single process = single queue
- **Memory pressure:** Large queue buildup could impact performance
- **No visibility:** Hard to monitor queue depth or job age

**What I'd do differently in production today:** Use SQLite-based queue table since we're already using SQLite. Minimal complexity increase, provides persistence and basic monitoring.

---

## Q3 — LLM Provider Abstraction

**Decision:** Built a provider interface (`LLMProvider` abstract base class)

**Interface:**
```python
class LLMProvider(ABC):
    async def extract_document(file_data, mime_type, prompt) -> Dict
    async def validate_documents(extractions, prompt) -> Dict
```

**Implemented providers:**
- `GeminiProvider` - Primary (free tier, good vision support)
- `AnthropicProvider` - Alternative (paid, higher quality)
- `GroqProvider` - Placeholder (fast, but limited vision support)

**Why this matters:**
- **Cost optimization:** Can switch to cheapest provider during development
- **Risk mitigation:** If one provider has outage, failover to another
- **Evaluation:** Easy A/B test different models for accuracy
- **Compliance:** Some organizations may require specific providers

**Trade-offs:**
- **+150 LOC** for abstraction that may not be used
- Each provider needs separate testing
- Prompt tuning may differ per provider (not fully abstracted)

**Verdict:** Worth it. The eval criteria specifically mentions provider swapping as a requirement, and production systems always need this flexibility.

---

## Q4 — Schema Design & JSONB Risks

**Current approach:** Hybrid relational + JSON storage
- Core fields in columns (id, session_id, document_type, holder_name, etc.)
- Dynamic data in JSON columns (fields_json, validity_json, medical_data_json, flags_json)

**Risks at scale:**

1. **Query limitations:**
   - Can't efficiently query "all sessions with expired COC" without parsing JSON
   - No indexing on JSON fields = full table scans
   - Aggregations become expensive

2. **Data integrity:**
   - No schema validation on JSON content
   - Field names/values can drift over time
   - Harder to enforce consistency

3. **Full-text search:**
   - SQLite FTS5 doesn't work on JSON columns
   - Would need to extract searchable text separately

**What I'd change for search/query requirements:**

```sql
-- Add normalized tables for critical queries
CREATE TABLE document_validities (
    extraction_id TEXT PRIMARY KEY,
    date_of_issue DATE,
    date_of_expiry DATE,
    is_expired BOOLEAN,
    days_until_expiry INTEGER
);

CREATE INDEX idx_expiry_date ON document_validities(date_of_expiry);
CREATE INDEX idx_is_expired ON document_validities(is_expired) WHERE is_expired = true;

-- Query becomes trivial:
SELECT e.* FROM extractions e
JOIN document_validities v ON e.id = v.extraction_id
WHERE v.is_expired = true AND e.document_type = 'COC';
```

**Alternative:** PostgreSQL with proper JSONB indexes if query flexibility is paramount.

---

## Q5 — What I Skipped

### 1. **File Storage Security**
**Skipped:** Encrypted storage, virus scanning, PII access controls

**Why:** 
- MVP focuses on extraction pipeline
- Would triple the codebase
- Requires secure key management infrastructure

**Production requirement:** Absolutely mandatory. Uploaded documents contain passports, medical records, certificates - all highly sensitive PII.

### 2. **Webhook Support & Retry Logic**
**Skipped:** Webhook callbacks, exponential backoff, dead letter queue

**Why:**
- Adds significant complexity to job lifecycle
- Requires signature verification, retry scheduling
- Out of scope for core extraction flow

**Production requirement:** Essential for integration with agent systems. They need async notifications, not just polling.

### 3. **Comprehensive Error Handling**
**Skipped:** 
- Circuit breaker pattern for LLM API
- Graceful degradation (OCR fallback)
- Detailed error categorization beyond basic codes

**Why:**
- Focus on happy path first
- Each pattern adds 50-100 lines of code
- Can be layered in after core works

**Production requirement:** Critical. LLM APIs fail regularly, and users need actionable errors, not "something went wrong".

### 4. **Authentication & Authorization**
**Skipped:** API keys, JWT tokens, rate limiting per user (vs per IP)

**Why:**
- Assumed trusted internal network for demo
- Would require user management, permissions
- Distraction from document processing

**Production requirement:** Non-negotiable. Multiple agents upload to same system, need isolation and audit trails.

### 5. **Monitoring & Observability**
**Skipped:** Metrics (Prometheus), tracing (OpenTelemetry), structured logging

**Why:**
- Infrastructure overhead
- Premature for single-developer project
- Can add after proving concept

**Production requirement:** How else do you know it's broken? Need alerting on LLM failures, queue backup, extraction errors.

---

## Additional Decisions

### Why FastAPI + Python?
- **Async/await** native support crucial for I/O-bound LLM calls
- **Pydantic** gives free validation and serialization
- **Type hints** provide documentation and catch errors early
- **Ecosystem:** SQLAlchemy, httpx, aiofiles all have excellent async support

### Why SQLite over PostgreSQL?
- **Zero setup** for demo/evaluation
- **Single file** = easy to share test databases
- **Good enough** for <100K extractions
- **Upgrade path:** SQLite → PostgreSQL is mostly config change with SQLAlchemy

### Why in-memory rate limiting?
- **Simplicity:** SlowAPI works out of the box
- **Adequate** for single-instance deployment
- **Can migrate** to Redis when scaling horizontally

---

## Summary

This implementation prioritizes:
1. **Demonstrable functionality** over production hardening
2. **Clear abstractions** that can be extended
3. **Explicit trade-offs** documented for evaluator review

If building for actual production tomorrow, I'd start with: encryption at rest, authentication, PostgreSQL, Redis queue, and comprehensive logging. Everything else can iterate.
