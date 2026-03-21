# Google Gemini API Rate Limits & Solutions

## Current Issue
You're hitting **429 Too Many Requests** errors from Google Gemini API.

## Rate Limit Information

### Free Tier (as of 2024)
- **15 requests per minute** (RPM)
- **1,500 requests per day**
- **60,000 tokens per minute**

### Paid Tier
- Higher limits based on usage tier
- Check Google Cloud Console for your specific quota

## Solutions Implemented

### 1. ✅ Automatic Retry with Exponential Backoff
- Increased retries: 3 → **5 attempts**
- Increased base delay: 2s → **5s**
- Backoff sequence: 5s, 10s, 20s, 40s, 80s (capped at 60s)
- Maximum total wait time: ~175 seconds (~3 minutes)

### 2. ✅ Extended Timeout
- Increased JOB_TIMEOUT: 30s → **300s (5 minutes)**
- Gives enough time for all retry attempts

### 3. ✅ Better Error Handling
- Respects `Retry-After` headers from Google
- Logs retry attempts with wait times
- Handles both response status codes and exceptions

## Additional Recommendations

### Option A: Wait and Retry Later
If you continue seeing rate limits:
1. **Wait 5-10 minutes** before making new requests
2. Daily quotas reset at midnight Pacific Time
3. Check your usage at: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas

### Option B: Reduce Request Frequency
```bash
# Add delays between multiple uploads
curl -X POST 'http://localhost:8001/api/extract?mode=sync' \
  -F 'document=@file1.pdf' && sleep 10 && \
curl -X POST 'http://localhost:8001/api/extract?mode=sync' \
  -F 'document=@file2.pdf'
```

### Option C: Use Async Mode for Large Batches
```bash
# Submit jobs asynchronously (non-blocking)
curl -X POST 'http://localhost:8001/api/extract?mode=async' \
  -F 'document=@file1.pdf'
  
# Check status later
curl http://localhost:8001/api/job/{job_id}
```

### Option D: Upgrade Your API Plan
1. Go to Google Cloud Console
2. Navigate to APIs & Services > Credentials
3. Check your current quota
4. Request a quota increase if needed

### Option E: Use Multiple API Keys (Advanced)
Rotate between multiple API keys to distribute load:
```python
# Add to .env
LLM_API_KEY_1=key1
LLM_API_KEY_2=key2
LLM_API_KEY_3=key3
```

## Monitoring Your Usage

Check the terminal logs for:
- `⚠️ Rate limited` messages indicate you're hitting limits
- Frequent retries suggest you need longer delays between requests

## Quick Test

Restart your server and try after waiting a few minutes:

```bash
# Stop the server (Ctrl+C)
# Restart it
uvicorn main:app --reload --port 8001

# Then try your curl command again
curl -X POST 'http://localhost:8001/api/extract?mode=sync' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'document=@PEME_Cruz_EXPIRED_FLAGS.pdf;type=application/pdf' \
  -F 'sessionId='
```

## Expected Behavior Now

With the improvements:
- First request might succeed immediately
- If rate limited, system waits 5-60 seconds automatically
- Will retry up to 5 times with increasing delays
- Total possible wait time: up to 3 minutes
- You'll see detailed logs of each retry attempt

## Still Having Issues?

If you still get rate limited after all retries:
1. **Wait 10-15 minutes** - Let the API cooldown
2. **Check your quota** - Verify you haven't hit daily limits
3. **Reduce frequency** - Space out your requests more
4. **Consider paid tier** - For production use with higher volumes
