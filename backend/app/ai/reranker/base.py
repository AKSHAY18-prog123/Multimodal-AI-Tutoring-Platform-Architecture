from typing import List, Dict, Any

class BaseReranker:
    """Hybrid score combiner and reranker for candidate passages."""

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Reranks candidates using a combined score of vector similarity and lexical BM25/keyword density.
        candidates: List of dicts containing 'content', 'vector_score', 'metadata', etc.
        """
        if not candidates:
            return []

        query_terms = set(query.lower().split())

        scored_candidates = []
        for cand in candidates:
            content = cand.get("content", "").lower()
            vector_score = cand.get("vector_score", 0.5)

            # Lexical term overlap / BM25-style frequency proxy
            lexical_hits = sum(1 for term in query_terms if term in content)
            lexical_score = lexical_hits / (len(query_terms) + 1e-6)

            # Boost if exact phrase or title matches
            exact_phrase_bonus = 0.2 if query.lower() in content else 0.0

            # Combined hybrid score: 60% semantic vector, 30% lexical overlap, 10% phrase bonus
            combined_score = (0.6 * vector_score) + (0.3 * lexical_score) + exact_phrase_bonus

            cand_copy = dict(cand)
            cand_copy["rerank_score"] = round(combined_score, 4)
            cand_copy["lexical_score"] = round(lexical_score, 4)
            scored_candidates.append(cand_copy)

        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_k]

def get_reranker() -> BaseReranker:
    return BaseReranker()
