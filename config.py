import os
from dotenv import load_dotenv

load_dotenv()

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))

# File Upload Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "application/pdf"}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

# Rate Limiting
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_PERIOD = 60  # seconds

# Job Processing
JOB_TIMEOUT = 30  # seconds
ASYNC_THRESHOLD = 5 * 1024 * 1024  # 5MB - files larger than this force async mode

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./smde.db")
