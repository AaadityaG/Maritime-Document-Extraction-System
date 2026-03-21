# Smart Maritime Document Extractor (SMDE)

---

## What This System Does

Manning Agents upload seafarer certification documents (certificates, medical exams, passports, drug tests). The system uses a vision-capable LLM to automatically extract structured data from each document, then validates compliance across the full document set.

**Core flow:**
1. Agent uploads a document → LLM reads it → structured JSON saved to DB
2. Agent uploads all docs for a sailor → calls validate → LLM checks cross-document compliance
3. Agent calls report → gets a human-readable hire/no-hire summary

---

## Stack

- **Runtime:** Node.js with TypeScript (strongly preferred) or Python with FastAPI
- **Database:** SQLite (simple) or PostgreSQL (provide docker-compose.yml for DB only)
- **Queue:** Any — BullMQ, pg-boss, polling table, in-memory. Reasoning matters more than choice.
- **LLM:** Your choice — must support vision (image input) and base64-encoded documents

### LLM Provider Options

| Provider | Free Tier | Recommended Model |
|---|---|---|
| Anthropic Claude | Free credits at console.anthropic.com | claude-haiku-4-5-20251001 |
| Google Gemini | Generous free quota, no card | gemini-2.0-flash |
| Groq | Free tier at console.groq.com | llama-3.2-11b-vision-preview |
| Mistral | Free credits at console.mistral.ai | pixtral-12b-2409 |
| OpenAI | Paid only | gpt-4o-mini |
| Ollama | Completely free, runs locally | llava or llama3.2-vision |

> If you have nothing set up, Google AI Studio (Gemini) and Groq both offer free tiers with no credit card required.

**Hard requirement:** LLM provider, model, and API key must be configurable via environment variables (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`). The service must not require code changes to swap providers.

---

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/extract` | POST | Accept a document, extract structured data via LLM |
| `/api/jobs/:jobId` | GET | Poll the status and result of an async extraction job |
| `/api/sessions/:sessionId` | GET | Return all extraction records for a session |
| `/api/sessions/:sessionId/validate` | POST | Cross-document compliance validation |
| `/api/sessions/:sessionId/report` | GET | Return a structured compliance report |
| `/api/health` | GET | Health check with dependency status |

---

## Endpoint Specifications

### POST /api/extract

Supports two modes via query parameter:
- `?mode=sync` — process immediately, block until done, return full extraction result (default for small files)
- `?mode=async` — accept the upload, enqueue the job, return `202 Accepted` immediately with a `jobId`

**Request:**
- Content-Type: `multipart/form-data`
- Field: `document` (file)
- Field: `sessionId` (string, optional — if omitted, create a new session)
- Accepted types: `image/jpeg`, `image/png`, `application/pdf`
- Max size: 10MB

**Sync response — 200:**
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
  "passportNumber": null,
  "fields": [...],
  "validity": {
    "dateOfIssue": "06/01/2025",
    "dateOfExpiry": "06/01/2027",
    "isExpired": false,
    "daysUntilExpiry": 660,
    "revalidationRequired": false
  },
  "compliance": {...},
  "medicalData": {
    "fitnessResult": "FIT",
    "drugTestResult": "NEGATIVE",
    "restrictions": null,
    "specialNotes": "Schistosomiasis – cleared by hematologist.",
    "expiryDate": "06/01/2027"
  },
  "flags": [...],
  "isExpired": false,
  "processingTimeMs": 4230,
  "summary": "...",
  "createdAt": "2026-03-17T08:42:11Z"
}
```

**Async response — 202:**
```json
{
  "jobId": "uuid",
  "sessionId": "uuid",
  "status": "QUEUED",
  "pollUrl": "/api/jobs/uuid",
  "estimatedWaitMs": 6000
}
```

**Deduplication:** If the same file (matched by SHA-256 hash) is uploaded to the same session, return the existing extraction result immediately with a `200` and a header `X-Deduplicated: true`. Do not call the LLM again.

**Error responses:**

| Status | Code | Condition |
|---|---|---|
| 400 | UNSUPPORTED_FORMAT | File type not accepted |
| 400 | INSUFFICIENT_DOCUMENTS | Validate called with fewer than 2 documents |
| 413 | FILE_TOO_LARGE | File exceeds 10MB |
| 404 | SESSION_NOT_FOUND | Session ID does not exist |
| 404 | JOB_NOT_FOUND | Job ID does not exist |
| 422 | LLM_JSON_PARSE_FAIL | LLM returned unparseable response after retry |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Unexpected server error |

All errors follow this shape:
```json
{
  "error": "LLM_JSON_PARSE_FAIL",
  "message": "Document extraction failed after retry. The raw response has been stored for review.",
  "extractionId": "uuid-of-failed-record",
  "retryAfterMs": null
}
```

---

### GET /api/jobs/:jobId

States: `QUEUED` → `PROCESSING` → `COMPLETE` | `FAILED`

All states return 200 with different body shapes:

```json
// While processing
{ "jobId": "uuid", "status": "PROCESSING", "queuePosition": 2, "startedAt": "...", "estimatedCompleteMs": 3200 }

// Complete
{ "jobId": "uuid", "status": "COMPLETE", "extractionId": "uuid", "result": { ... }, "completedAt": "..." }

// Failed
{ "jobId": "uuid", "status": "FAILED", "error": "LLM_JSON_PARSE_FAIL", "message": "...", "failedAt": "...", "retryable": true }
```

---

### GET /api/sessions/:sessionId

Returns a summary of all documents in the session.

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
      "criticalFlagCount": 0,
      "createdAt": "2026-03-17T08:40:00Z"
    }
  ],
  "pendingJobs": []
}
```

`overallHealth` logic:
- `OK` — no expired certs and no CRITICAL flags
- `WARN` — any MEDIUM or HIGH flags, or certs expiring within 90 days
- `CRITICAL` — any CRITICAL flags or expired required certs

---

### POST /api/sessions/:sessionId/validate

Sends all extraction records from the session to the LLM for cross-document compliance assessment.

**You must write the LLM prompt for this endpoint yourself.** The extraction prompt for `/api/extract` is provided (see below), but the validation prompt is your design. This is intentional — the evaluators want to see how you instruct an LLM to reason about compliance across multiple heterogeneous documents.

Response must include:
```json
{
  "sessionId": "uuid",
  "holderProfile": { ... },
  "consistencyChecks": [ ... ],
  "missingDocuments": [ ... ],
  "expiringDocuments": [ ... ],
  "medicalFlags": [ ... ],
  "overallStatus": "APPROVED | CONDITIONAL | REJECTED",
  "overallScore": 74,
  "summary": "...",
  "recommendations": [ "...", "..." ],
  "validatedAt": "2026-03-17T08:45:00Z"
}
```

---

### GET /api/sessions/:sessionId/report

Returns a structured, human-readable compliance report. **This is NOT another LLM call** — derive entirely from data already in the database (extraction records + most recent validation result).

The schema is yours to design. Think about what a Manning Agent actually needs to see to make a hire/no-hire decision. The evaluators will assess the structure and completeness as a product thinking signal.

---

### GET /api/health

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
  "timestamp": "2026-03-17T08:45:00Z"
}
```

---

## Rate Limiting

Implement on `POST /api/extract` only. Limit: **10 requests per minute per IP**.

When exceeded, return `429 RATE_LIMITED` with:
- Header: `Retry-After`
- Body field: `retryAfterMs`

You may use any mechanism — in-memory token bucket, Redis counter, middleware library. Document your choice in the ADR.

---

## LLM Reliability Requirements

The LLM is the highest-risk component. Your implementation must handle all of the following:

1. **Malformed JSON** — LLMs sometimes wrap responses in markdown code fences or add explanation before the JSON. Extract valid JSON by locating the outermost `{` and `}` regardless of surrounding text.

2. **Parse failure recovery** — if extraction fails after the boundary approach, send a repair prompt to the LLM with the raw response and ask it to return clean JSON. Store the raw response regardless.

3. **Timeout handling** — set a 30-second timeout on the LLM API call. On timeout, mark the job `FAILED` with `retryable: true`. Do not hang the request.

4. **LOW confidence retry** — if the LLM returns `confidence: "LOW"`, automatically retry once with a more focused prompt that includes the file name and MIME type as hints. Use the higher-confidence result if the retry succeeds.

5. **Never discard** — even on total failure, store a record with `status: FAILED` and the raw LLM response (or error). Nothing uploaded by the user is ever silently lost.

---

## The LLM Extraction Prompt

Use the following prompt exactly for `POST /api/extract`. Do not modify it — consistent prompt usage across candidates lets the evaluators compare extraction quality.

```
You are an expert maritime document analyst with deep knowledge of STCW, MARINA, IMO, and international seafarer certification standards. A document has been provided. Perform the following in a single pass:
1. IDENTIFY the document type from the taxonomy below
2. DETERMINE if this belongs to a DECK officer, ENGINE officer, BOTH, or is role-agnostic (N/A)
3. EXTRACT all fields that are meaningful for this specific document type
4. FLAG any compliance issues, anomalies, or concerns

Document type taxonomy (use these exact codes):
COC | COP_BT | COP_PSCRB | COP_AFF | COP_MEFA | COP_MECA | COP_SSO | COP_SDSD | ECDIS_GENERIC | ECDIS_TYPE | SIRB | PASSPORT | PEME | DRUG_TEST | YELLOW_FEVER | ERM | MARPOL | SULPHUR_CAP | BALLAST_WATER | HATCH_COVER | BRM_SSBT | TRAIN_TRAINER | HAZMAT | FLAG_STATE | OTHER

Return ONLY a valid JSON object. No markdown. No code fences. No preamble.

{
  "detection": {
    "documentType": "SHORT_CODE",
    "documentName": "Full human-readable document name",
    "category": "IDENTITY | CERTIFICATION | STCW_ENDORSEMENT | MEDICAL | TRAINING | FLAG_STATE | OTHER",
    "applicableRole": "DECK | ENGINE | BOTH | N/A",
    "isRequired": true,
    "confidence": "HIGH | MEDIUM | LOW",
    "detectionReason": "One sentence explaining how you identified this document"
  },
  "holder": {
    "fullName": "string or null",
    "dateOfBirth": "DD/MM/YYYY or null",
    "nationality": "string or null",
    "passportNumber": "string or null",
    "sirbNumber": "string or null",
    "rank": "string or null",
    "photo": "PRESENT | ABSENT"
  },
  "fields": [
    {
      "key": "snake_case_key",
      "label": "Human-readable label",
      "value": "extracted value as string",
      "importance": "CRITICAL | HIGH | MEDIUM | LOW",
      "status": "OK | EXPIRED | WARNING | MISSING | N/A"
    }
  ],
  "validity": {
    "dateOfIssue": "string or null",
    "dateOfExpiry": "string | 'No Expiry' | 'Lifetime' | null",
    "isExpired": false,
    "daysUntilExpiry": null,
    "revalidationRequired": null
  },
  "compliance": {
    "issuingAuthority": "string",
    "regulationReference": "e.g. STCW Reg VI/1 or null",
    "imoModelCourse": "e.g. IMO 1.22 or null",
    "recognizedAuthority": true,
    "limitations": "string or null"
  },
  "medicalData": {
    "fitnessResult": "FIT | UNFIT | N/A",
    "drugTestResult": "NEGATIVE | POSITIVE | N/A",
    "restrictions": "string or null",
    "specialNotes": "string or null",
    "expiryDate": "string or null"
  },
  "flags": [
    {
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "message": "Description of issue or concern"
    }
  ],
  "summary": "Two-sentence plain English summary of what this document confirms about the holder."
}
```

---

## Database Schema

Design your own schema. The suggested schema below is a starting point only — the evaluators will assess your schema design as part of the technical review.

Consider: what indexes will you need? How do you model job state? How do you avoid JSONB columns becoming a dumping ground?

```sql
-- Starting point only — modify freely
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE extractions (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  file_name TEXT NOT NULL,
  file_hash TEXT NOT NULL,
  document_type TEXT,
  applicable_role TEXT,
  confidence TEXT,
  holder_name TEXT,
  date_of_birth TEXT,
  sirb_number TEXT,
  passport_number TEXT,
  fields_json TEXT,
  validity_json TEXT,
  medical_data_json TEXT,
  flags_json TEXT,
  is_expired INTEGER DEFAULT 0,
  summary TEXT,
  raw_llm_response TEXT,
  processing_time_ms INTEGER,
  status TEXT DEFAULT 'COMPLETE',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  session_id TEXT REFERENCES sessions(id),
  extraction_id TEXT REFERENCES extractions(id),
  status TEXT DEFAULT 'QUEUED',
  error_code TEXT,
  error_message TEXT,
  queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP
);

CREATE TABLE validations (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  result_json TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Part 2 — Architecture Decision Record (ADR.md)

Write a short ADR document (500–800 words, markdown) at `ADR.md` in the repo root. Answer each of the following directly — no hedged non-answers.

**Q1 — Sync vs Async default**
You implemented both `?mode=sync` and `?mode=async`. In production, which mode should be the default and why? At what file size or concurrency threshold would you force async regardless of the mode param?

**Q2 — Queue choice**
What queue mechanism did you use and why? What would you migrate to if this service needed to handle 500 concurrent extractions per minute? What are the failure modes of your current approach?

**Q3 — LLM provider abstraction**
Did you build a provider interface that makes swapping LLMs trivial, or did you implement against one provider directly? Justify the decision. If you did build the abstraction, describe its interface.

**Q4 — Schema design**
The suggested schema uses JSONB/TEXT columns for dynamic fields. What are the risks of that approach at scale? What would you change if this system needed to support full-text search across extracted field values, or querying "all sessions where any document has an expired COC"?

**Q5 — What you skipped**
What did you deliberately not implement that a production system would require? List at least three things and briefly explain why you deprioritized each.

---

## Part 3 — Code Review (CODE_REVIEW.md)

Review the following pull request submitted by a junior engineer. Write your review as `CODE_REVIEW.md` in the repo root. Address the junior engineer directly. Include: written comments on specific lines or sections, a summary comment at the top explaining your overall assessment, and at least one thing you would specifically call out as a teaching moment.

**The PR: "feat: add document extraction endpoint"**

```typescript
// src/routes/extract.ts
import express from 'express';
import Anthropic from '@anthropic-ai/sdk';
import fs from 'fs';
import path from 'path';

const router = express.Router();
const client = new Anthropic({ apiKey: 'sk-ant-REDACTED' });

router.post('/extract', async (req, res) => {
  const file = req.file;
  if (!file) { res.status(400).json({ error: 'No file uploaded' }); return; }
  try {
    const fileData = fs.readFileSync(file.path);
    const base64Data = fileData.toString('base64');
    // Save file to disk permanently for reference
    const savedPath = path.join('./uploads', file.originalname);
    fs.copyFileSync(file.path, savedPath);
    const response = await client.messages.create({
      model: 'claude-opus-4-6',
      max_tokens: 4096,
      messages: [{
        role: 'user',
        content: [
          { type: 'image', source: { type: 'base64', media_type: file.mimetype, data: base64Data } },
          { type: 'text', text: 'Extract all information from this maritime document and return as JSON.' }
        ]
      }]
    });
    const result = JSON.parse(response.content[0].text);
    // Store in memory for now
    global.extractions = global.extractions || [];
    global.extractions.push(result);
    res.json(result);
  } catch (error) {
    console.log('Error:', error);
    res.status(500).json({ error: 'Something went wrong' });
  }
});

export default router;
```

**PR description written by the junior engineer:**
> "Added the main extract endpoint. It reads the uploaded file, converts to base64, sends to Claude, parses the JSON back, and returns it. Also saves files to disk so we don't lose them. Tested with one PEME file and it worked. Using Opus because it gave better results in my testing."

---

## Evaluation Criteria

### Technical (50%)

| Area | What they look for |
|---|---|
| LLM reliability | JSON extraction robustness, repair strategy, no silent failures, raw response always stored |
| Async pipeline | Job state machine is correct, polling endpoint handles all states, queue does not drop jobs on restart |
| API design | Consistent error shapes, sync/async modes work correctly, deduplication works, rate limiting returns correct headers |
| Schema design | Indexes exist where needed, job table is correct, schema choices are defensible in the ADR |
| Code quality | TypeScript types are real (no `any` dumps), separation of concerns, no hardcoded credentials, README runs in 3 commands |
| Testing | At minimum: JSON repair logic has unit tests, happy path has an integration test or Postman collection |

### Architecture & Judgment (25%)

| Area | What they look for |
|---|---|
| ADR quality | Direct answers, real tradeoffs named, honest about what was skipped |
| Report endpoint design | Does the schema reflect genuine product thinking about what a Manning Agent needs? |
| Validation prompt | Is the cross-document compliance prompt precise, well-structured, and would it produce reliable output? |
| Schema evolution | Did you think about query patterns beyond just "store and retrieve"? |

### Leadership (25%)

| Area | What they look for |
|---|---|
| Code review tone | Constructive and specific — does not berate, does not approve bad code uncritically |
| Code review accuracy | Identifies the real issues (hardcoded key, Opus cost, global state, no timeout, broad prompt, saved files with PII) not just style nits |
| Teaching quality | At least one comment explains *why* something is wrong, not just *that* it is wrong |
| Loom walkthrough | Can you explain architectural decisions clearly to a non-technical audience in 2 minutes and a technical one in 5? |

---

## What a strong submission looks like

**A strong submission will:**
- Make a clear, justified call on sync vs async default and document it
- Have a job state machine that handles `QUEUED → PROCESSING → COMPLETE/FAILED` correctly with no orphaned jobs
- Write a cross-document validation prompt that would genuinely work in production — specific, structured, and resistant to hallucination
- Design a `/report` endpoint schema that a product manager could read without translation
- Deliver a code review that a junior engineer would actually learn from — specific line references, clear reasoning, one teaching moment they will remember
- Have an ADR that names what was skipped and why without defensiveness

**A strong submission will NOT:**
- Hardcode credentials anywhere in the source
- Use `any` types as a crutch in TypeScript
- Silently drop failed extractions
- Write a validation prompt that just asks the LLM to "check if the documents are valid"
- Write a code review that is only style comments
- Have a README that requires 20 minutes of setup

---

## Bonus (Optional)

These are not required. Each one is an opportunity to signal specific depth.

- **Webhook support** — add an optional `webhookUrl` field to the `POST /api/extract` request. When the async job completes, POST the result to that URL with an HMAC signature for verification.
- **Retry endpoint** — add `POST /api/jobs/:jobId/retry` that re-queues a failed job. Must reject if the job is not in `FAILED` state.
- **Expiry alerting query** — add `GET /api/sessions/:sessionId/expiring?withinDays=90` that returns all documents in the session that expire within the given window, sorted by urgency. Must be a database query, not an in-memory filter.

---

## Submission

Email your completed assignment (GitHub repo + demo video) to **hiring@skycladventures.com**

Include in the repo root:
- `README.md` — setup in 3 commands
- `ADR.md` — architecture decisions
- `CODE_REVIEW.md` — your review of the junior engineer's PR