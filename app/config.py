import os
from dotenv import load_dotenv

load_dotenv()
PROVIDER = os.getenv("COOKED_PROVIDER", "ollama").strip().lower()
MODEL = os.getenv("COOKED_MODEL", "qwen2.5:3b").strip()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "60"))
