from abc import ABC, abstractmethod
from typing import List

class BaseEmbeddingProvider(ABC):
    """Abstract interface for text embeddings."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single string."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of strings."""
        pass
