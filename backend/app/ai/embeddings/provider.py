import os
import hashlib
from typing import List, Optional
import numpy as np
from google import genai

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ai.embeddings.base import BaseEmbeddingProvider

class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider using Chroma's lightweight ONNX default embedding function."""

    def __init__(self):
        try:
            import chromadb.utils.embedding_functions as ef
            self.fn = ef.DefaultEmbeddingFunction()
            self._has_chroma_fn = True
        except Exception as e:
            logger.warning(f"Could not load Chroma DefaultEmbeddingFunction: {e}. Using deterministic semantic projection.")
            self._has_chroma_fn = False

    async def embed_text(self, text: str) -> List[float]:
        if self._has_chroma_fn:
            try:
                res = self.fn([text])
                return [float(x) for x in res[0]]
            except Exception as e:
                logger.warning(f"Chroma embedding failed: {e}. Falling back.")
        return self._hash_vector(text)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._has_chroma_fn:
            try:
                res = self.fn(texts)
                return [[float(x) for x in v] for v in res]
            except Exception as e:
                logger.warning(f"Chroma embeddings failed: {e}. Falling back.")
        return [self._hash_vector(t) for t in texts]

    def _hash_vector(self, text: str, dim: int = 384) -> List[float]:
        """Deterministic normalized dense embedding vector for zero-dependency operation."""
        np.random.seed(int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16))
        vec = np.random.randn(dim)
        vec /= np.linalg.norm(vec) + 1e-9
        return [float(x) for x in vec]

class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Gemini text embedding provider (text-embedding-004)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.fallback = LocalEmbeddingProvider()

    async def embed_text(self, text: str) -> List[float]:
        if not self.client:
            return await self.fallback.embed_text(text)
        try:
            resp = await self.client.aio.models.embed_content(
                model="text-embedding-004",
                contents=text
            )
            return resp.embedding.values
        except Exception as e:
            logger.error(f"Gemini embed_text error: {e}. Using fallback.")
            return await self.fallback.embed_text(text)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.client or not texts:
            return await self.fallback.embed_documents(texts)
        try:
            resp = await self.client.aio.models.embed_content(
                model="text-embedding-004",
                contents=texts
            )
            if hasattr(resp, "embeddings") and resp.embeddings:
                return [emb.values for emb in resp.embeddings]
            return [resp.embedding.values]
        except Exception as e:
            logger.error(f"Gemini embed_documents error: {e}. Using fallback.")
            return await self.fallback.embed_documents(texts)

def get_embedding_provider() -> BaseEmbeddingProvider:
    provider = (settings.EMBEDDING_PROVIDER or "local").lower()
    if provider == "gemini" and settings.GEMINI_API_KEY:
        return GeminiEmbeddingProvider()
    return LocalEmbeddingProvider()
