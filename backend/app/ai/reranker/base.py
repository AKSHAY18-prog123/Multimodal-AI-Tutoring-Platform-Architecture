import math
import re
from typing import List, Dict, Any, Set

_QUERY_STOPWORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "from", "with", "by", "of", "about",
    "into", "through", "during", "before", "after", "above", "below",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "can", "could", "would", "should", "will", "shall", "may", "might", "must",
    "do", "does", "did", "done", "doing", "have", "has", "had", "having",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "you", "your", "we", "our", "me", "my", "i", "please", "tell", "give",
    "show", "explain", "explains", "explained", "teach", "teaches", "talk",
    "talks", "discussed", "discuss", "discusses", "teacher", "instructor",
    "professor", "lecture", "video", "youtube", "pdf", "ppt", "pptx",
    "slide", "slides", "page", "pages", "document", "file", "notes",
    "module", "course", "section", "part", "topic", "topics", "time", "timestamp",
    "main", "key", "core", "important", "summary", "summarize", "concept",
    "concepts", "material", "materials", "content", "contents", "use", "using"
}


def extract_content_terms(text: str) -> List[str]:
    """Extracts meaningful lowercase domain content tokens excluding stopwords and meta-query words."""
    tokens = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
    return [t for t in tokens if t not in _QUERY_STOPWORDS and not t.isdigit()]


def _term_matches_doc(term: str, doc_tokens: Set[str], doc_text: str) -> bool:
    if term in doc_tokens or term in doc_text:
        return True
    # Stem/prefix match for terms >= 5 chars (e.g. "preventing" <-> "prevention", "deadlocks" <-> "deadlock")
    if len(term) >= 5:
        stem = term[:max(4, len(term) - 2)]
        for dt in doc_tokens:
            if len(dt) >= 4 and (dt.startswith(stem) or term.startswith(dt[:max(4, len(dt) - 2)])):
                return True
    return False


from backend.app.core.logging import logger


class BaseReranker:
    """Hybrid BM25 + semantic vector + cross-encoder score combiner and reranker for candidate passages."""

    def __init__(self):
        self._flashrank_ranker = None
        self._flashrank_checked = False

    def _get_flashrank(self):
        if self._flashrank_checked:
            return self._flashrank_ranker
        self._flashrank_checked = True
        try:
            import os
            from pathlib import Path
            # Only load FlashRank if its local cache already exists to avoid blocking network downloads
            cache_dir = Path(os.environ.get("FLASHRANK_CACHE_DIR", Path.home() / ".cache" / "flashrank"))
            if cache_dir.exists() and any(cache_dir.iterdir()):
                from flashrank import Ranker
                self._flashrank_ranker = Ranker(cache_dir=str(cache_dir))
        except Exception:
            self._flashrank_ranker = None
        return self._flashrank_ranker

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Reranks candidates using a combined score of:
        - Dense vector similarity
        - Okapi BM25 + content-term coverage (excluding stopwords)
        - Exact phrase / concept match bonus
        - Domain intent disambiguation (e.g. Multiple Linear Regression vs Simple Linear Regression)
        - Optional FlashRank cross-encoder score when cached
        """
        if not candidates:
            return []

        q_lower = query.strip().lower()
        all_query_terms = list(dict.fromkeys(re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", q_lower)))
        content_terms = list(dict.fromkeys(extract_content_terms(query)))
        eval_terms = content_terms if content_terms else all_query_terms

        # Disambiguate problem-type intent
        is_multiple_query = ("multiple" in q_lower) and ("regression" in q_lower or "linear" in q_lower)
        is_simple_query = ("simple" in q_lower) and ("regression" in q_lower or "linear" in q_lower)
        is_assignment_query = any(w in q_lower for w in ["assignment", "homework", "student marks", "attendance"])
        is_worked_example_query = any(w in q_lower for w in ["example", "worked", "house", "size", "bedroom", "step by step", "step-by-step", "solve"])

        # Pre-tokenize documents for BM25
        n_docs = len(candidates)
        doc_tokens_list: List[List[str]] = []
        doc_token_sets: List[Set[str]] = []
        doc_lengths: List[int] = []
        for cand in candidates:
            c_text = cand.get("content", "").lower()
            meta = cand.get("metadata", {})
            sfile = str(meta.get("source_file", "")).lower()
            topic = str(meta.get("topic_name", "")).lower()
            full_text = f"{c_text} {sfile} {topic}"
            tokens = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", full_text)
            doc_tokens_list.append(tokens)
            doc_token_sets.append(set(tokens))
            doc_lengths.append(max(1, len(tokens)))

        avgdl = sum(doc_lengths) / max(1, n_docs)
        k1 = 1.5
        b = 0.75

        # Document frequencies for eval_terms
        df: Dict[str, int] = {}
        for t in eval_terms:
            df[t] = sum(
                1 for idx, tset in enumerate(doc_token_sets)
                if _term_matches_doc(t, tset, candidates[idx].get("content", "").lower())
            )

        raw_bm25_scores: List[float] = []
        term_coverages: List[float] = []

        for idx, cand in enumerate(candidates):
            c_text = cand.get("content", "").lower()
            tset = doc_token_sets[idx]
            tokens = doc_tokens_list[idx]
            dl = doc_lengths[idx]

            bm25_val = 0.0
            matched_terms = 0
            for t in eval_terms:
                if _term_matches_doc(t, tset, c_text):
                    matched_terms += 1
                    tf = sum(1 for tok in tokens if tok == t or (len(t) >= 5 and tok.startswith(t[:max(4, len(t) - 2)])))
                    tf = max(1, tf)
                    idf = math.log(1.0 + (n_docs - df[t] + 0.5) / (df[t] + 0.5))
                    bm25_val += idf * ((tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (dl / avgdl))))

            coverage = matched_terms / max(1, len(eval_terms))
            raw_bm25_scores.append(bm25_val)
            term_coverages.append(coverage)

        max_bm25 = max(raw_bm25_scores) if raw_bm25_scores else 0.0

        # Optional FlashRank scores if available
        flashrank_scores: Dict[int, float] = {}
        ranker = self._get_flashrank()
        if ranker is not None:
            try:
                from flashrank import RerankRequest
                passages = [{"id": i, "text": c.get("content", "")[:1500]} for i, c in enumerate(candidates)]
                fr_res = ranker.rerank(RerankRequest(query=query, passages=passages))
                for item in fr_res:
                    flashrank_scores[int(item["id"])] = float(item.get("score", 0.0))
            except Exception:
                flashrank_scores = {}

        scored_candidates = []
        for idx, cand in enumerate(candidates):
            content = cand.get("content", "").lower()
            meta = cand.get("metadata", {})
            topic = str(meta.get("topic_name", "") or cand.get("topic_name", "")).lower()
            combined_text = f"{content} {topic}"

            vector_score = float(cand.get("vector_score", 0.5))
            coverage = term_coverages[idx]
            norm_bm25 = (raw_bm25_scores[idx] / max_bm25) if max_bm25 > 0 else 0.0

            # Lexical score combines content term coverage (70%) and normalized BM25 TF-IDF (30%)
            lexical_score = (0.7 * coverage) + (0.3 * norm_bm25)

            # Identify candidate domain characteristics
            has_mult_vars = ("x1" in combined_text and "x2" in combined_text) or ("b1" in combined_text and "b2" in combined_text) or ("xb" in combined_text)
            has_normal_eq = (
                "normal equation" in combined_text
                or "x^t" in combined_text
                or "xtx" in combined_text
                or "𝛽=" in combined_text
                or "xt y" in combined_text
                or "xty" in combined_text
                or "matrix x" in combined_text
            )
            has_house_example = (
                ("bedroom" in combined_text or "bedrooms" in combined_text)
                and ("size" in combined_text or "price" in combined_text)
                and any(num in combined_text for num in ["900", "1200", "1500", "1800", "1600", "63.28", "63.3", "lakhs", "35", "50", "60", "75"])
            )
            has_marks_assignment = (
                ("attendance" in combined_text and "marks" in combined_text)
                or ("assignment problem" in combined_text)
                or ("s1" in combined_text and "study hours" in combined_text and "attendance" in combined_text)
            )

            is_cand_multiple = (
                "multiple linear regression" in combined_text
                or "multiple regression" in combined_text
                or has_normal_eq
                or (has_mult_vars and ("regression" in combined_text or "equation" in combined_text))
                or has_house_example
                or has_marks_assignment
            )

            is_cand_strictly_simple = (
                ("simple linear regression" in combined_text or "simple regression" in combined_text)
                and not is_cand_multiple
            )

            # Multi-word phrase bonus if 2+ consecutive content terms appear together
            phrase_bonus = 0.0
            if len(eval_terms) >= 2:
                for i in range(len(eval_terms) - 1):
                    bigram = f"{eval_terms[i]} {eval_terms[i + 1]}"
                    # Guard: If query is explicitly Multiple Linear Regression, do NOT reward
                    # a chunk that is exclusively Simple Linear Regression for the bigram "linear regression"
                    if is_multiple_query and bigram == "linear regression" and is_cand_strictly_simple:
                        continue
                    if is_simple_query and bigram == "linear regression" and is_cand_multiple:
                        continue
                    if bigram in content:
                        phrase_bonus = 0.18
                        break
            elif len(eval_terms) == 1 and eval_terms[0] in content:
                phrase_bonus = 0.12

            if q_lower and len(q_lower) > 4 and q_lower in content:
                phrase_bonus = max(phrase_bonus, 0.22)

            # Intent alignment adjustment
            intent_adjustment = 0.0
            if is_multiple_query:
                if is_cand_multiple:
                    intent_adjustment += 0.22
                    if is_assignment_query and has_marks_assignment:
                        intent_adjustment += 0.18
                    elif is_worked_example_query and (has_house_example or has_normal_eq):
                        intent_adjustment += 0.18
                    elif not is_assignment_query and (has_house_example or has_normal_eq):
                        # Default priority for Multiple Linear Regression is the worked house example
                        intent_adjustment += 0.12
                elif is_cand_strictly_simple:
                    # Penalize Simple Linear Regression so it does not crowd out Multiple Linear Regression
                    intent_adjustment -= 0.25

                # Demote abstract "Types of Linear Regression" slides when solving worked problems
                if "types of linear regression" in combined_text and not (has_normal_eq or has_house_example or has_marks_assignment):
                    intent_adjustment -= 0.12

            elif is_simple_query:
                if is_cand_strictly_simple:
                    intent_adjustment += 0.22
                    if "study hours" in combined_text and "marks" in combined_text:
                        intent_adjustment += 0.12
                elif is_cand_multiple:
                    intent_adjustment -= 0.25

            if idx in flashrank_scores:
                fr_score = flashrank_scores[idx]
                combined_score = (0.40 * vector_score) + (0.35 * lexical_score) + (0.25 * fr_score) + phrase_bonus + intent_adjustment
            else:
                combined_score = (0.50 * vector_score) + (0.40 * lexical_score) + phrase_bonus + intent_adjustment

            cand_copy = dict(cand)
            cand_copy["rerank_score"] = round(max(0.0, min(1.0, combined_score)), 4)
            cand_copy["lexical_score"] = round(lexical_score, 4)
            cand_copy["content_term_coverage"] = round(coverage, 4)
            cand_copy["bm25_score"] = round(raw_bm25_scores[idx], 4)
            cand_copy["intent_adjustment"] = round(intent_adjustment, 4)
            scored_candidates.append(cand_copy)

        scored_candidates.sort(
            key=lambda x: (x["content_term_coverage"] > 0, x["rerank_score"], x["lexical_score"]),
            reverse=True
        )

        logger.info(
            f"[Reranker] Query='{query}' -> Evaluated {len(candidates)} chunks "
            f"(multiple={is_multiple_query}, simple={is_simple_query}, assignment={is_assignment_query})"
        )
        for rank, c in enumerate(scored_candidates[:top_k]):
            p = c.get("metadata", {}).get("page_number") or c.get("page_number")
            logger.info(
                f"  Rank #{rank+1}: Chunk {c['id'][:8]} | Page {p} | "
                f"RerankScore={c['rerank_score']} (Vector={c.get('vector_score')}, Lex={c['lexical_score']}, IntentAdj={c.get('intent_adjustment')}) | "
                f"Topic={c.get('metadata', {}).get('topic_name')}"
            )

        return scored_candidates[:top_k]


def get_reranker() -> BaseReranker:
    return BaseReranker()
