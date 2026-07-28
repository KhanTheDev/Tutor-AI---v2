import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

# Points at a mounted persistent volume in production (e.g. Railway); falls
# back to a local folder for dev, where the working directory is already persistent.
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR))

DATABASE_DIR = DATA_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "tutor_ai.db"
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"

UPLOAD_FOLDER = DATA_DIR / "uploads"
CHROMA_DATA_DIR = DATA_DIR / "chroma_data"

MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {"pdf", "txt", "jpg", "jpeg", "png"}

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

EMBEDDING_MODEL = "text-embedding-3-small"
VISION_MODEL = "gpt-4o-mini"
GROQ_MODEL = "llama-3.3-70b-versatile"

CHROMA_COLLECTION_NAME = "tutor_ai_chunks"
RETRIEVAL_TOP_K = 5
CHAT_HISTORY_LIMIT = 50
