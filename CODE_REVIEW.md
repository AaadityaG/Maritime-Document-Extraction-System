# Code Review: PR - "feat: add document extraction endpoint"

**Reviewed by:** [Your Name]  
**Date:** March 21, 2026  
**PR:** feat: add document extraction endpoint  
**Files changed:** `src/routes/extract.ts`

---

## Overall Assessment

**Status:** ❌ **Needs significant revisions before merge**

This PR implements the basic extraction flow but has several critical issues that block production readiness. The core functionality works (as evidenced by testing with a PEME file), but there are security vulnerabilities, architectural concerns, and reliability gaps that must be addressed.

**What's good:**
- ✅ Basic upload → base64 → LLM → parse flow is correct
- ✅ File preservation strategy shows awareness of data loss risks
- ✅ Tested with real document (PEME)

**Critical blockers:**
- 🔴 Hardcoded API key in source code
- 🔴 No timeout on LLM calls
- 🔴 In-memory global state
- 🔴 Overly broad prompt increases hallucination risk
- 🔴 No file cleanup after processing
- 🔴 Using Claude Opus (expensive) without justification

---

## Line-by-Line Comments

### Line 9: Hardcoded API Key
```typescript
const client = new Anthropic({ apiKey: 'sk-ant-REDACTED' });
```

**❌ BLOCKER - Security Vulnerability**

**Issue:** API keys must never be committed to source code, even redacted. This violates basic security practices and will fail any security audit.

**Impact:**
- Exposed credentials can be leaked via git history
- Unauthorized usage and billing charges
- Compromised system integrity

**Fix:**
```typescript
// Use environment variable
const client = new Anthropic({ 
  apiKey: process.env.ANTHROPIC_API_KEY 
});

// Add to .env.example:
ANTHROPIC_API_KEY=sk-ant-...
```

**Teaching moment:** This is one of the most common security mistakes developers make. Even if you think "it's just a test key" or "I'll remove it later," it WILL get committed eventually. Always use environment variables from day one. Your future self (and your security team) will thank you.

---

### Lines 15-16: File Reading Without Size Validation
```typescript
const fileData = fs.readFileSync(file.path);
const base64Data = fileData.toString('base64');
```

**❌ HIGH PRIORITY - Missing validation**

**Issues:**
1. No file size check before reading into memory (DoS vulnerability)
2. Synchronous file read blocks event loop
3. No error handling for file read failures

**Fix:**
```typescript
// Validate size first
const stats = fs.statSync(file.path);
if (stats.size > MAX_FILE_SIZE) {
  throw new Error('FILE_TOO_LARGE');
}

// Use async read
const fileData = await fs.promises.readFile(file.path);
```

---

### Lines 18-19: Permanent File Storage
```typescript
const savedPath = path.join('./uploads', file.originalname);
fs.copyFileSync(file.path, savedPath);
```

**⚠️ MEDIUM PRIORITY - Data privacy concern**

**Issues:**
- Files saved with original names (PII exposure)
- No encryption at rest
- No cleanup mechanism
- Predictable paths enable unauthorized access

**Questions for author:**
- What's the retention policy for these files?
- Who has access to the `/uploads` directory?
- Are we compliant with data protection regulations storing seafarer documents this way?

**Recommendation:** Either:
1. Delete immediately after processing (if persistence not needed)
2. Store with UUID filename + encryption + metadata tracking
3. Use secure object storage (S3 with bucket policies)

---

### Lines 20-29: LLM Call Without Timeout
```typescript
const response = await client.messages.create({
  model: 'claude-opus-4-6',
  max_tokens: 4096,
  messages: [...]
});
```

**❌ HIGH PRIORITY - Reliability issue**

**Issue:** No timeout configured. If Anthropic API hangs, this request hangs forever, blocking resources.

**Impact:**
- Memory leaks from accumulated hanging requests
- Degraded service under load
- Poor user experience (infinite loading)

**Fix:**
```typescript
// Add timeout wrapper
const timeout = (ms: number) => 
  new Promise((_, reject) => setTimeout(() => reject(new Error('TIMEOUT')), ms));

const response = await Promise.race([
  client.messages.create({...}),
  timeout(30000) // 30 second timeout
]);
```

Also: Why no retry logic? Network calls should always have retry-with-backoff.

---

### Line 21: Model Selection - Claude Opus
```typescript
model: 'claude-opus-4-6',
```

**⚠️ MEDIUM PRIORITY - Cost optimization needed**

**Question:** Why Opus instead of Haiku or Sonnet?

**Cost comparison (approximate):**
- Claude Opus: ~$15 per 1M tokens
- Claude Sonnet: ~$3 per 1M tokens  
- Claude Haiku: ~$0.25 per 1M tokens

**For context:** A typical certificate extraction uses ~2K tokens. At scale:
- 10,000 extractions = 20M tokens
- Opus: $300 vs Haiku: $5

**Request:** Please benchmark Haiku-4.5-20251001 against Opus for this use case. The spec mentions Haiku as recommended - did you test it? What specific quality differences did you observe that justify the 60x cost increase?

---

### Line 27: Generic Prompt
```typescript
{ type: 'text', text: 'Extract all information from this maritime document and return as JSON.' }
```

**❌ HIGH PRIORITY - Insufficient prompting**

**Issues:**
- No document taxonomy guidance
- No schema definition
- No role detection instruction
- No compliance flagging requirement
- "all information" is ambiguous - invites hallucination

**Why this matters:** Without strict prompting, the LLM will:
- Extract irrelevant fields
- Miss critical maritime-specific data (STCW references, validity dates)
- Inconsistent formatting across documents
- Higher hallucination rate

**Fix:** Use the provided extraction prompt from the spec. It's 150 lines for a reason - precision matters.

---

### Line 31: JSON Parsing Without Error Handling
```typescript
const result = JSON.parse(response.content[0].text);
```

**❌ HIGH PRIORITY - Fragile parsing**

**Issue:** LLMs frequently return markdown code fences, explanatory text, or malformed JSON. This will crash on any deviation.

**Real-world LLM responses:**
```markdown
Here's the extracted data:

```json
{
  "detection": {...}
}
```

As you can see, this certificate shows...
```

**Your parser:** 💥 `SyntaxError: Unexpected token H in JSON`

**Fix:**
```typescript
const rawText = response.content[0].text;

// Strip markdown fences
const cleanText = rawText.replace(/```(?:json)?\s*/g, '').replace(/```\s*$/g, '');

// Find JSON boundaries
const startIdx = cleanText.indexOf('{');
const endIdx = cleanText.lastIndexOf('}') + 1;
const jsonString = cleanText.slice(startIdx, endIdx);

try {
  const result = JSON.parse(jsonString);
} catch (error) {
  // Log raw response for debugging
  logger.error('LLM parse failed', { rawText, error });
  
  // Retry with repair prompt
  const repairedResult = await repairPrompt(rawText);
  return repairedResult;
}
```

Per the spec: **Never discard failed extractions**. Store the raw response even on parse failure.

---

### Lines 33-34: Global State
```typescript
global.extractions = global.extractions || [];
global.extractions.push(result);
```

**❌ BLOCKER - Architectural anti-pattern**

**Issues:**
- Lost on server restart
- No persistence = data loss
- No query capability (can't search, filter, aggregate)
- Race conditions with concurrent requests
- Impossible to scale horizontally

**Why databases exist:** This is literally what databases solve. We have SQLite/PostgreSQL available in the stack.

**Minimum fix:**
```typescript
// Use database
await db.extractions.create({
  id: uuid(),
  sessionId: sessionId,
  fileName: file.originalname,
  documentType: result.detection.documentType,
  // ... map all fields
});
```

**Better:** Use the provided schema in `database.py` which models relationships properly.

---

### Lines 36-38: Generic Error Handler
```typescript
} catch (error) {
  console.log('Error:', error);
  res.status(500).json({ error: 'Something went wrong' });
}
```

**⚠️ MEDIUM PRIORITY - Poor error handling**

**Issues:**
- Logs everything as "Error:" (no categorization)
- Returns same message for all errors (unhelpful for debugging)
- No distinction between user errors (bad file) vs system errors (LLM down)
- Doesn't follow the error response schema from spec

**Per spec, errors should be:**
```json
{
  "error": "LLM_JSON_PARSE_FAIL",
  "message": "Document extraction failed after retry. The raw response has been stored for review.",
  "extractionId": "uuid-of-failed-record",
  "retryAfterMs": null
}
```

**Fix:**
```typescript
catch (error) {
  if (error instanceof FileTooLargeError) {
    return res.status(413).json({ error: 'FILE_TOO_LARGE', ... });
  }
  if (error instanceof LLMTimeoutError) {
    return res.status(422).json({ error: 'LLM_TIMEOUT', ... });
  }
  
  // Log full error for debugging
  logger.error('Extraction failed', { error, file: file.originalname });
  
  return res.status(500).json({ 
    error: 'INTERNAL_ERROR',
    message: 'An unexpected error occurred during extraction'
  });
}
```

---

## Missing Components

### 1. No Deduplication Check
The spec requires SHA-256 hash-based deduplication. If the same file is uploaded twice, return cached result immediately without calling LLM again.

### 2. No Sync/Async Mode Support
Endpoint should support `?mode=sync` and `?mode=async` query parameters with different response shapes.

### 3. No Rate Limiting
Spec requires 10 requests/minute per IP. Currently unlimited - vulnerable to abuse.

### 4. No Validation Response Schema
Doesn't return the structured format from the spec (sessionId, pollUrl, etc. for async mode).

### 5. No File Type Validation
Accepts any file type. Should restrict to `image/jpeg`, `image/png`, `application/pdf`.

---

## Testing Gaps

**Tested:** One PEME file (happy path)

**Not tested:**
- Expired certificates
- Low-quality scans
- Non-PDF formats (images)
- Invalid/malformed documents
- LLM timeout scenarios
- LLM returning invalid JSON
- Large files (>5MB)
- Concurrent uploads
- Duplicate file uploads

**Required before merge:**
- Unit tests for JSON parsing logic (including repair)
- Integration test with at least 5 different document types
- Load test with 10 concurrent requests

---

## Action Items

### Before Merge (Blockers):
- [ ] Remove hardcoded API key, use environment variables
- [ ] Add 30-second timeout to LLM calls
- [ ] Replace global state with database persistence
- [ ] Implement proper error response schema
- [ ] Add file type and size validation

### Before Production (High Priority):
- [ ] Use the full extraction prompt from spec
- [ ] Implement JSON repair/retry logic
- [ ] Add deduplication check
- [ ] Implement sync/async modes
- [ ] Add rate limiting
- [ ] Benchmark Haiku vs Opus for cost/quality trade-off

### Nice to Have:
- [ ] Async file I/O throughout
- [ ] Structured logging
- [ ] Metrics collection (extraction duration, LLM latency, error rates)
- [ ] File cleanup strategy for temporary uploads

---

## Final Notes

**To the author:** You've built a working prototype that demonstrates the core concept - that's great! The issues above are mostly about production readiness, not fundamental flaws in your approach. 

**Key learning areas:**
1. **Security first:** Never commit credentials. Ever.
2. **Defensive programming:** Assume external APIs will fail, return garbage, or timeout
3. **State management:** Globals are technical debt. Use proper persistence.
4. **Cost awareness:** Opus is cool, but Haiku might do the job for 1/60th the price

**Let's pair on:** Setting up the proper prompt structure and implementing the JSON repair logic. These are tricky and worth doing together.

**Estimated revision time:** 4-6 hours if you're familiar with TypeScript async patterns and environment configuration.

Please address the blockers and resubmit. Happy to help with any of these items - ping me if you want to pair on the timeout handling or prompt engineering!

---

**Review checklist:**
- ✅ Functionality reviewed
- ✅ Security concerns identified
- ⚠️ Performance implications noted
- ✅ Test coverage gaps highlighted
- ✅ Teaching moments provided (see line 9, 31, 33)
- ✅ Actionable feedback given with code examples
