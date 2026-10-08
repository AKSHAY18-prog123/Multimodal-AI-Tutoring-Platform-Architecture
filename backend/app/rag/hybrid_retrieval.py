from typing import List, Dict, Any, Optional
from backend.app.knowledge_base.vector_store import vector_store
from backend.app.ai.reranker.base import get_reranker
from backend.app.core.logging import logger

class HybridRetrievalService:
    """Performs dense vector retrieval + metadata filtering + hybrid score combination."""

    def __init__(self):
        self.reranker = get_reranker()

    async def retrieve_candidates(
        self,
        query: str,
        course_id: Optional[str] = None,
        source_type: Optional[str] = None,
        top_k: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Retrieves candidate knowledge chunks using Chroma vector search,
        then performs hybrid reranking against query keywords.
        """
        # 1. Dense Vector Search (pull slightly larger pool for reranking)
        raw_candidates = await vector_store.search(
            query=query,
            course_id=course_id,
            source_type=source_type,
            top_k=top_k * 2
        )

        if not raw_candidates:
            logger.info(f"No raw candidates returned from vector store for query: {query}")
            return []

        # 2. Hybrid Reranking (Combines dense similarity with BM25/keyword density)
        reranked = self.reranker.rerank(
            query=query,
            candidates=raw_candidates,
            top_k=top_k
        )

        return reranked

hybrid_retriever = HybridRetrievalService()
