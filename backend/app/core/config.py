import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "SynapseTutor AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/db/tutor.db"
    CHROMA_PERSIST_DIRECTORY: str = "./storage/db/chroma"
    CHROMA_COLLECTION_NAME: Optional[str] = None

    # AI Providers: 'ollama', 'gemini', 'mock'
    LLM_PROVIDER: str = "ollama"
    VISION_PROVIDER: str = "ollama"
    EMBEDDING_PROVIDER: str = "ollama"
    RERANKER_PROVIDER: str = "gte-modernbert"
    RERANKER_MODEL: str = "Alibaba-NLP/gte-reranker-modernbert-base"

    # Google Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "liquid/lfm-2.5-2.6b:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_VISION_MODEL: str = "qwen3-vl:4b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # Storage Dirs
    STORAGE_DIR: str = "./storage"
    UPLOAD_DIR: str = "./storage/uploads"
    PROCESSED_DIR: str = "./storage/processed"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    def ensure_directories(self):
        """Ensure necessary storage directories exist."""
        for path_str in [
            self.STORAGE_DIR,
            self.UPLOAD_DIR,
            self.PROCESSED_DIR,
            "./storage/db",
            self.CHROMA_PERSIST_DIRECTORY
        ]:
            p = BASE_DIR / path_str.lstrip("./")
            p.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
