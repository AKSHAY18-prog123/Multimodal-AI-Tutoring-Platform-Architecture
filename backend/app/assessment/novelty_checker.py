import hashlib
import re
from typing import List, Dict, Any, Tuple
import numpy as np
from backend.app.ai.embeddings.provider import get_embedding_provider
from backend.app.core.logging import logger

def compute_question_hash(question_text: str) -> str:
    """Normalized text hash (lowercased, alphanumeric only) for exact duplicate detection."""
    normalized = re.sub(r"[^a-zA-Z0-9]", "", question_text.lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

class NoveltyChecker:
    """Guarantees novelty by comparing hashes and semantic vector cosine similarities."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.embedding_provider = get_embedding_provider()
        self.total_checked = 0
        self.total_rejected = 0

    async def is_novel(
        self,
        candidate_question: str,
        existing_questions: List[Dict[str, Any]]
    ) -> Tuple[bool, float, str]:
        """
        Returns: (is_novel: bool, max_similarity: float, reason: str)
        """
        self.total_checked += 1
        cand_hash = compute_question_hash(candidate_question)

        # 1. Exact Hash Check
        for q in existing_questions:
            existing_hash = q.get("novelty_hash") or compute_question_hash(q.get("question_text", ""))
            if cand_hash == existing_hash:
                self.total_rejected += 1
                return False, 1.0, f"Exact duplicate question detected (Hash match: {cand_hash[:8]})."

        # 2. Semantic Embedding Cosine Similarity Check
        if existing_questions:
            cand_emb = np.array(await self.embedding_provider.embed_text(candidate_question))
            cand_norm = cand_emb / (np.linalg.norm(cand_emb) + 1e-9)

            max_sim = 0.0
            most_similar_text = ""

            for eq in existing_questions:
                eq_text = eq.get("question_text", "")
                eq_emb = np.array(await self.embedding_provider.embed_text(eq_text))
                eq_norm = eq_emb / (np.linalg.norm(eq_emb) + 1e-9)

                sim = float(np.dot(cand_norm, eq_norm))
                if sim > max_sim:
                    max_sim = sim
                    most_similar_text = eq_text

            if max_sim >= self.similarity_threshold:
                self.total_rejected += 1
                return False, round(max_sim, 3), f"High semantic similarity ({max_sim:.2f}) with existing question: '{most_similar_text[:60]}...'"

        return True, 0.0, "Question is novel."

    def get_novelty_metrics(self) -> Dict[str, Any]:
        """Calculates historical question generation repetition rate."""
        rate = (self.total_rejected / max(1, self.total_checked)) * 100.0
        return {
            "total_questions_checked": self.total_checked,
            "repeated_questions_rejected": self.total_rejected,
            "repetition_rate_percentage": round(rate, 2),
            "novelty_rate_percentage": round(100.0 - rate, 2)
        }

novelty_checker = NoveltyChecker()
