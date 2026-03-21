# SMDE - Quick Start Guide

## 🚀 Run in 3 Steps

### Step 1: Activate Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### Step 2: Set Your API Key
Edit `.env` file and add your Gemini API key:
```bash
LLM_API_KEY=your_actual_api_key_here
```

**Get free API key:** https://aistudio.google.com/app/apikey

### Step 3: Start Server
```powershell
python main.py
```

You'll see:
```
============================================================
Smart Maritime Document Extractor (SMDE)
============================================================
Starting server on http://0.0.0.0:8001
API Docs: http://0.0.0.0:8001/docs
Health Check: http://0.0.0.0:8001/api/health
============================================================
```

✅ **Server is running!** Open http://localhost:8001/docs in your browser.

---

## 📝 Quick Test

### Test 1: Health Check
```bash
curl http://localhost:8001/api/health
```

### Test 2: Upload Document
```bash
curl -X POST "http://localhost:8001/api/extract?mode=sync" ^
  -F "document=@C:\path\to\certificate.pdf" ^
  -F "sessionId=test-123"
```

### Test 3: Use Swagger UI (Easiest!)
1. Open http://localhost:8001/docs
2. Click **POST /api/extract**
3. Click **"Try it out"**
4. Upload your PDF
5. Click **"Execute"**

---

## ⚙️ Configuration (Optional)

Edit `.env` file to change settings:

```bash
# LLM Provider
LLM_PROVIDER=gemini              # gemini or anthropic
LLM_MODEL=gemini-2.0-flash

# Server
PORT=8001

# Rate Limits (for free tier)
RATE_LIMIT_REQUESTS=5            # Requests per minute
```

**Restart server after changing .env**

---

## 🐛 Troubleshooting

**"Connection refused"**
→ Make sure server is running: `python main.py`

**"Rate limited"**
→ Wait 30-60 seconds between requests (Gemini free tier limit)

**"Module not found"**
→ Activate venv: `.\venv\Scripts\Activate.ps1`

**"API key invalid"**
→ Check your key in `.env` file

---

## 📁 Project Structure

```
mari document system/
├── app/                    # Main application code
│   ├── core/              # Configuration
│   ├── models/            # Database models
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic
│   └── utils/             # Helpers
├── uploads/               # Temporary file storage
├── .env                   # Your configuration
├── main.py                # Entry point
└── requirements.txt       # Dependencies
```

---

## 🔗 More Documentation

- **Complete Guide:** [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)
- **Testing Guide:** [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Architecture:** [ADR.md](ADR.md)

---

**That's it! Start uploading documents! 🎉**
