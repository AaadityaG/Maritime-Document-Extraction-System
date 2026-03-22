# Code Review: feat: add document extraction endpoint

**Reviewed by:** Senior Engineer  
**Date:** March 22, 2026  
**Overall Assessment:** ⚠️ **Needs Significant Revisions** - Has critical security, reliability, and architectural issues that must be addressed before merging.

---

## Detailed Comments

### 🔴 CRITICAL: Security Issue

**Line 9:** `const client = new Anthropic({ apiKey: 'sk-ant-REDACTED' });`

**Issue:** Hardcoded API credentials in source code.

**Why this matters:** This will end up in git history and could be pushed to a public repo. Anyone with access to your codebase can use your API key and incur charges.

**Fix:** Use environment variables:
```typescript
const client = new Anthropic({ 
  apiKey: process.env.ANTHROPIC_API_KEY 
});
```

Add `.env` to your `.gitignore` and document required env vars in README.

---

### 🔴 CRITICAL: No Timeout Handling

**Lines 60-70:** The LLM call has no timeout configuration.

**Why this matters:** If the LLM provider hangs or responds slowly, your entire request will hang indefinitely, consuming server resources and eventually causing cascading failures.

**Fix:** Add a timeout wrapper:
```typescript
const timeout = (promise: Promise<any>, ms: number) =>
  Promise.race([
    promise,
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error(`Timeout after ${ms}ms`)), ms)
    )
  ]);

const response = await timeout(
  client.messages.create({...}),
  30000 // 30 second timeout
);
```

Mark failed jobs as `retryable: true` on timeout.

---

### 🔴 CRITICAL: Global State

**Lines 72-74:** `global.extractions = global.extractions || [];`

**Issue:** Using global variables for data persistence.

**Why this matters:**
- All data is lost when the server restarts
- Not thread-safe - concurrent requests will corrupt data
- No way to query, filter, or retrieve specific records
- Won't work in production with multiple server instances

**Fix:** Use the database properly:
```typescript
// Create an Extraction record in the database
const extraction = await db.extractions.create({
  session_id: sessionId,
  file_name: file.originalname,
  file_hash: fileHash,
  fields_json: JSON.stringify(result.fields),
  // ... other fields
});
```

Reference the existing database schema in `app/models/` and use proper ORM queries.

---

### 🔴 CRITICAL: No JSON Repair Logic

**Line 71:** `const result = JSON.parse(response.content[0].text);`

**Issue:** Blindly parsing LLM response without error handling.

**Why this matters:** LLMs frequently return malformed JSON - wrapped in markdown code fences, with explanatory text before/after, or with minor syntax errors. This will throw and lose the entire extraction.

**Fix:** Implement robust extraction:
```typescript
function extractJsonFromResponse(text: string): any {
  // Try direct parse first
  try { return JSON.parse(text); } catch {}
  
  // Find JSON boundaries
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start === -1 || end === -1) {
    throw new Error('No JSON found in response');
  }
  
  const jsonStr = text.slice(start, end + 1);
  try { return JSON.parse(jsonStr); } catch {}
  
  // Last resort: ask LLM to repair
  throw new Error('JSON parse failed after boundary extraction');
}
```

**Teaching Moment:** Always treat external API responses as untrusted. Parse defensively, especially with LLMs that generate probabilistic output. Store the raw response before any parsing attempt so you never lose data.

---

### 🔴 CRITICAL: Using Claude Opus Without Justification

**Line 61:** `model: 'claude-opus-4-6'`

**Issue:** Using the most expensive model (~$15/1M tokens) without cost-benefit analysis.

**Why this matters:** A single PEME document extraction might cost $0.50-1.00 with Opus. At scale (1000 documents/day), that's $500-1000/day vs ~$15/day with Haiku.

**Fix:** Either:
1. Use `claude-haiku-4-5-20251001` (recommended for cost efficiency)
2. Make the model configurable via `LLM_MODEL` env var
3. Document in ADR why Opus is necessary (if you have specific quality requirements)

---

### 🟡 MAJOR: Overly Simplistic Prompt

**Lines 66-68:** The prompt is just one sentence.

**Issue:** Missing structured prompt with document taxonomy, output schema, and compliance requirements.

**Why this matters:** Vague prompts produce inconsistent results. The reference specification provides a detailed prompt with exact JSON schema, document type codes, and compliance rules.

**Fix:** Use the provided prompt from `REFERENCE.md` section "The LLM Extraction Prompt". It includes:
- Specific document type taxonomy (COC, COP_BT, PEME, etc.)
- Complete output schema with detection, holder, fields, validity, compliance sections
- Confidence scoring
- Flag generation

Store this as a template in `app/utils/prompts.ts` for maintainability.

---

### 🟡 MAJOR: No File Validation

**Lines 52-53:** Only checks if file exists.

**Missing validations:**
- File size limit (10MB per spec)
- MIME type validation (only JPEG, PNG, PDF)
- Session ID validation (if provided)

**Fix:**
```typescript
const MAX_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'application/pdf'];

if (file.size > MAX_SIZE) {
  return res.status(413).json({ error: 'FILE_TOO_LARGE' });
}

if (!ALLOWED_TYPES.includes(file.mimetype)) {
  return res.status(400).json({ error: 'UNSUPPORTED_FORMAT' });
}
```

---

### 🟡 MAJOR: No Deduplication

**Missing:** SHA-256 hash check to avoid re-processing identical files.

**Why this matters:** If the same document is uploaded twice to the same session, you should return the cached result immediately instead of calling the LLM again (saves cost and time).

**Fix:**
```typescript
const fileHash = crypto.createHash('sha256').update(fileData).digest('hex');
const existing = await db.extractions.findOne({
  where: { file_hash: fileHash, session_id: sessionId }
});

if (existing) {
  res.setHeader('X-Deduplicated', 'true');
  return res.json(existing);
}
```

---

### 🟡 MAJOR: Improper File Storage

**Lines 57-59:** Saving files to disk with original names.

**Issues:**
- Exposes PII in filenames
- No cleanup strategy
- Files can accumulate indefinitely
- No encryption at rest

**Fix:** 
- Store files with UUID names
- Consider storing in S3/blob storage
- Implement retention policy
- Encrypt if storing sensitive documents

---

### 🟡 MINOR: Generic Error Handling

**Lines 76-78:** Catch-all error handler.

**Issue:** Returns generic 500 for all errors, losing important distinction between different failure types.

**Fix:** Categorize errors properly:
```typescript
catch (error) {
  if (error.code === 'TIMEOUT') {
    return res.status(504).json({ 
      error: 'LLM_TIMEOUT',
      retryable: true 
    });
  }
  
  if (error instanceof SyntaxError) {
    return res.status(422).json({ 
      error: 'LLM_JSON_PARSE_FAIL',
      message: error.message 
    });
  }
  
  // Log full error internally
  logger.error('Extraction failed:', error);
  return res.status(500).json({ 
    error: 'INTERNAL_ERROR',
    extractionId: savedRecord?.id 
  });
}
```

Follow the error response shape from the spec.

---

### 🟡 MINOR: No Rate Limiting

**Missing:** Rate limiting middleware on the endpoint.

**Why this matters:** Free-tier LLM APIs have strict limits. Even paid tiers need protection from abuse or runaway scripts.

**Fix:** Add rate limiter (see `main.py` for existing implementation using `slowapi`).

Spec requires: **10 requests per minute per IP** on `/api/extract`

---

### 🟢 NICE TO HAVE: Add Response Metadata

Consider adding to the response:
- `processingTimeMs`: How long the extraction took
- `createdAt`: ISO timestamp
- `id`: Unique extraction ID for reference

Helps with debugging and user experience.

---

## Architecture Concerns

### Missing Async Mode Support

The spec requires both sync and async modes. This implementation only supports sync. For large files (>5MB) or high concurrency, you'll need:
- Job queue (in-memory, BullMQ, or DB-backed)
- Status polling endpoint (`GET /api/jobs/:jobId`)
- State machine: QUEUED → PROCESSING → COMPLETE | FAILED

See `app/services/job_queue.py` for existing implementation.

### No Provider Abstraction

Hardcoded to Anthropic. The spec requires configurability via env vars (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`). Consider building a provider interface:

```typescript
interface LLMProvider {
  extract(document: ImageData): Promise<ExtractionResult>;
}

class AnthropicProvider implements LLMProvider { ... }
class GeminiProvider implements LLMProvider { ... }

const provider = getProvider(process.env.LLM_PROVIDER);
```

Makes swapping providers trivial without code changes.

---

## What Works Well ✅

1. **Basic flow is correct** - Upload → Base64 → LLM → Parse → Return
2. **File preservation** - Good instinct to save files permanently
3. **Clean structure** - Express router pattern is appropriate
4. **Tested with real data** - You validated with an actual PEME file

---

## Summary

**To the author:** You've built a working prototype that demonstrates the core concept - that's great! The issues above are mostly about production readiness, not fundamental flaws in your approach.

**Key learning areas:**
1. **Security first:** Never commit credentials. Ever.
2. **Defensive programming:** Assume external APIs will fail, return garbage, or timeout
3. **State management:** Globals are technical debt. Use proper persistence.
4. **Cost awareness:** Opus is cool, but Haiku might do the job for 1/60th the price

**Let's pair on:** Setting up the proper prompt structure and implementing the JSON repair logic. These are tricky and worth doing together.

**Estimated revision time:** 4-6 hours if you're familiar with TypeScript async patterns and environment configuration.

Please address the blockers and resubmit. Happy to help with any of these items - ping me if you want to pair on the timeout handling or prompt engineering!

