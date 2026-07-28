import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

# Postgres (e.g. a free Neon database) with the pgvector extension enabled.
# Required — there is no local-file fallback, since Vercel's filesystem is
# read-only and doesn't persist between requests.
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    # SQLAlchemy's psycopg dialect requires "postgresql://", not the legacy
    # "postgres://" scheme that Neon/Heroku-style URLs use.
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
SQLALCHEMY_DATABASE_URI = DATABASE_URL

MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB — stays under Vercel's request body limit
ALLOWED_EXTENSIONS = {"pdf", "txt", "jpg", "jpeg", "png"}

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
VISION_MODEL = "gpt-4o-mini"
GROQ_MODEL = "llama-3.3-70b-versatile"

RETRIEVAL_TOP_K = 5
CHAT_HISTORY_LIMIT = 50
