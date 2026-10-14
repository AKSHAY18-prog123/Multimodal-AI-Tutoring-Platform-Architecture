import os
import hashlib
from typing import List, Optional, Dict, Any
import numpy as np
import httpx
from google import genai

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ai.embeddings.base import BaseEmbeddingProvider

class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider using sentence-transformers/all-MiniLM-L6-v2 (384-dimensional)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.dimension = 384
        self.model = None
        self.chroma_fn = None
        self._load_model()

    def _load_model(self):
        """Loads sentence-transformers model from local cache, supporting offline operation."""
        try:
            from sentence_transformers import SentenceTransformer
            try:
                self.model = SentenceTransformer(self.model_name, local_files_only=True)
                logger.info(f"Loaded embedding model {self.model_name} from local cache (offline mode).")
                return
            except Exception as e_cache:
                logger.info(f"Local cache load failed ({e_cache}), attempting standard SentenceTransformer load...")
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded embedding model {self.model_name} successfully.")
                return
        except Exception as e_st:
            logger.warning(f"Could not load SentenceTransformer: {e_st}.")

        try:
            import chromadb.utils.embedding_functions as ef
            self.chroma_fn = ef.DefaultEmbeddingFunction()
            logger.info("Using chromadb.utils.embedding_functions.DefaultEmbeddingFunction fallback.")
        except Exception as e_chroma:
            logger.error(f"Could not load Chroma DefaultEmbeddingFunction: {e_chroma}. Deterministic projection active.")
            self.chroma_fn = None

    async def embed_text(self, text: str) -> List[float]:
        """Generate 384-dimensional embedding for a single query text."""
        if self.model is not None:
            try:
                vec = self.model.encode(text, convert_to_numpy=True)
                return [float(x) for x in vec]
            except Exception as e:
                logger.warning(f"SentenceTransformer embed_text failed: {e}. Falling back.")
        if self.chroma_fn is not None:
            try:
                res = self.chroma_fn([text])
                return [float(x) for x in res[0]]
            except Exception as e:
                logger.warning(f"Chroma embedding failed: {e}. Falling back.")
        return self._hash_vector(text, dim=self.dimension)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate 384-dimensional embeddings for a list of document strings."""
        if not texts:
            return []
        if self.model is not None:
            try:
                vecs = self.model.encode(texts, convert_to_numpy=True)
                return [[float(x) for x in v] for v in vecs]
            except Exception as e:
                logger.warning(f"SentenceTransformer embed_documents failed: {e}. Falling back.")
        if self.chroma_fn is not None:
            try:
                res = self.chroma_fn(texts)
                return [[float(x) for x in v] for v in res]
            except Exception as e:
                logger.warning(f"Chroma embeddings failed: {e}. Falling back.")
        return [self._hash_vector(t, dim=self.dimension) for t in texts]

    def _hash_vector(self, text: str, dim: int = 384) -> List[float]:
        """Deterministic normalized dense embedding vector for zero-dependency operation."""
        np.random.seed(int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16))
        vec = np.random.randn(dim)
        vec /= np.linalg.norm(vec) + 1e-9
        return [float(x) for x in vec]


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """
    Ollama embedding provider for nomic-embed-text (768-dimensional).
    Applies recommended task prefixes:
      - 'search_query: ' for queries
      - 'search_document: ' for documents
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = (
            model_name
            or getattr(settings, "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
            or "nomic-embed-text"
        )
        self.dimension = 768
        self.embed_url = f"{self.base_url}/api/embed"
        self._fallback_provider: Optional[BaseEmbeddingProvider] = None

    def _get_fallback(self) -> BaseEmbeddingProvider:
        if self._fallback_provider is None:
            self._fallback_provider = LocalEmbeddingProvider()
        return self._fallback_provider

    async def verify_availability(self) -> Dict[str, Any]:
        """Verify that Ollama service is reachable and the embedding model is installed."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    has_model = any(
                        self.model_name == m or self.model_name == m.split(":")[0] or m.startswith(f"{self.model_name}:")
                        for m in models
                    )
                    return {
                        "available": has_model,
                        "server_online": True,
                        "model": self.model_name,
                        "installed_models": models,
                        "dimension": self.dimension,
                        "message": "Model is available in Ollama." if has_model else f"Model '{self.model_name}' not found in Ollama installed models: {models}"
                    }
                return {
                    "available": False,
                    "server_online": False,
                    "error": f"Ollama server returned HTTP {resp.status_code}"
                }
        except Exception as e:
            return {
                "available": False,
                "server_online": False,
                "error": f"Ollama connection error at {self.base_url}: {e}"
            }

    async def embed_text(self, text: str) -> List[float]:
        """Generate 768-dimensional embedding for a single query text."""
        if not text:
            return [0.0] * self.dimension

        prefix = "search_query: "
        formatted_text = text if (text.startswith(prefix) or text.startswith("search_document: ")) else f"{prefix}{text}"
        payload = {
            "model": self.model_name,
            "input": formatted_text
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self.embed_url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    embs = data.get("embeddings")
                    if embs and len(embs) > 0:
                        vec = embs[0]
                        self.dimension = len(vec)
                        return [float(x) for x in vec]
                # Fallback to legacy /api/embeddings endpoint if /api/embed returned 404
                if resp.status_code == 404:
                    legacy_url = f"{self.base_url}/api/embeddings"
                    legacy_payload = {"model": self.model_name, "prompt": formatted_text}
                    legacy_resp = await client.post(legacy_url, json=legacy_payload)
                    if legacy_resp.status_code == 200:
                        vec = legacy_resp.json().get("embedding", [])
                        if vec:
                            self.dimension = len(vec)
                            return [float(x) for x in vec]
                logger.warning(f"Ollama embed_text HTTP {resp.status_code}: {resp.text}. Using fallback.")
        except Exception as e:
            logger.warning(f"Ollama embed_text request failed: {e}. Using fallback.")

        return await self._get_fallback().embed_text(text)

    async def embed_documents(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        """Generate 768-dimensional embeddings for a list of document strings."""
        if not texts:
            return []

        prefix = "search_document: "
        prefixed_texts = [
            t if (t.startswith(prefix) or t.startswith("search_query: ")) else f"{prefix}{t}"
            for t in texts
        ]

        all_embeddings: List[List[float]] = []
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for i in range(0, len(prefixed_texts), batch_size):
                    batch = prefixed_texts[i : i + batch_size]
                    payload = {
                        "model": self.model_name,
                        "input": batch
                    }
                    resp = await client.post(self.embed_url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        batch_embs = data.get("embeddings", [])
                        if batch_embs:
                            all_embeddings.extend([[float(x) for x in v] for v in batch_embs])
                            continue

                    logger.warning(f"Ollama embed_documents batch failed (HTTP {resp.status_code}): {resp.text}. Falling back to sequential queries.")
                    for item in batch:
                        item_vec = await self.embed_text(item)
                        all_embeddings.append(item_vec)

            if len(all_embeddings) == len(texts):
                if all_embeddings and len(all_embeddings[0]) > 0:
                    self.dimension = len(all_embeddings[0])
                return all_embeddings
        except Exception as e:
            logger.warning(f"Ollama embed_documents failed: {e}. Using fallback.")

        return await self._get_fallback().embed_documents(texts)


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
    if provider in ["ollama", "nomic", "ollama_nomic"]:
        return OllamaEmbeddingProvider()
    if provider == "gemini" and settings.GEMINI_API_KEY:
        return GeminiEmbeddingProvider()
    return LocalEmbeddingProvider()

