import re
from typing import List, Dict, Any, Optional
from backend.app.knowledge_base.vector_store import vector_store
from backend.app.knowledge_base.chunking import find_exact_timestamp_in_chunk
from backend.app.ai.reranker.base import get_reranker, extract_content_terms
from backend.app.core.logging import logger


class HybridRetrievalService:
    """Performs dense vector retrieval + BM25 lexical retrieval + metadata filtering + hybrid reranking."""

    def __init__(self):
        self.reranker = get_reranker()

    async def retrieve_candidates(
        self,
        query: str,
        course_id: Optional[str] = None,
        source_type: Optional[Any] = None,
        document_id: Optional[Any] = None,
        page_number: Optional[int] = None,
        slide_number: Optional[int] = None,
        top_k: int = 8,
        include_neighbors: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieves candidate knowledge chunks using:
        1. Dense vector search (ChromaDB)
        2. Lexical BM25/keyword scan over scoped chunks so exact terminology, page/slide,
           or video timestamp matches are never missed by dense top-K
        3. Hybrid reranking (vector + BM25 + FlashRank)
        4. Exact intra-segment timestamp refinement for video chunks
        5. Optional neighboring chunk expansion for topic continuity
        """
        # 1. Dense Vector Search (pull larger pool for reranking)
        dense_candidates = await vector_store.search(
            query=query,
            course_id=course_id,
            source_type=source_type,
            document_id=document_id,
            page_number=page_number,
            slide_number=slide_number,
            top_k=max(12, top_k * 3)
        )

        # 2. BM25 / Lexical Candidate Pool from scoped chunks
        scoped_chunks = vector_store.get_chunks_by_filter(
            course_id=course_id,
            source_type=source_type,
            document_id=document_id,
            page_number=page_number,
            slide_number=slide_number,
            limit=250
        )

        # Merge dense and lexical candidates without duplicates
        merged_by_id: Dict[str, Dict[str, Any]] = {}
        for c in dense_candidates:
            merged_by_id[c["id"]] = c

        content_terms = extract_content_terms(query)
        for sc in scoped_chunks:
            cid = sc["id"]
            if cid in merged_by_id:
                continue
            c_lower = sc.get("content", "").lower()
            # Include scoped chunk if it matches any content term or if page/slide filter was explicitly requested
            if (page_number is not None or slide_number is not None) or any(t in c_lower for t in content_terms):
                merged_by_id[cid] = sc
            elif not merged_by_id and len(scoped_chunks) <= top_k * 2:
                merged_by_id[cid] = sc

        raw_candidates = list(merged_by_id.values())
        if not raw_candidates:
            logger.info(f"No raw candidates returned from vector store for query: {query}")
            return []

        # Demote video_curriculum_map on specific topic/timestamp queries so real transcript segments rank first
        q_lower = query.lower()
        is_overview = any(p in q_lower for p in [
            "overview", "syllabus", "curriculum", "all topics", "what topics",
            "outline", "what does this video teach", "what is this video about",
            "entire", "whole"
        ])
        if not is_overview:
            non_map = [
                c for c in raw_candidates
                if c.get("metadata", {}).get("chunk_type") != "video_curriculum_map"
            ]
            if non_map:
                raw_candidates = non_map

        # 3. Hybrid Reranking
        reranked = self.reranker.rerank(
            query=query,
            candidates=raw_candidates,
            top_k=top_k
        )

        # 4. Refine intra-chunk video timestamps when inline [MM:SS] markers match the query
        for item in reranked:
            meta = dict(item.get("metadata", {}))
            if meta.get("source_type") == "video" and meta.get("chunk_type") == "video_transcript":
                exact_ts = find_exact_timestamp_in_chunk(item, query)
                if exact_ts.get("timestamp_start_formatted"):
                    meta["segment_start_formatted"] = meta.get("timestamp_start_formatted")
                    meta["segment_end_formatted"] = meta.get("timestamp_end_formatted")
                    meta["timestamp_start"] = exact_ts["timestamp_start"]
                    meta["timestamp_end"] = exact_ts["timestamp_end"]
                    meta["timestamp_start_formatted"] = exact_ts["timestamp_start_formatted"]
                    meta["timestamp_end_formatted"] = exact_ts["timestamp_end_formatted"]
                    if exact_ts.get("video_url"):
                        meta["video_url"] = exact_ts["video_url"]
                    item["metadata"] = meta

        # 5. Optional Neighbor Expansion (attach adjacent chunks from the same document for multi-step continuity)
        if include_neighbors and reranked and scoped_chunks:
            existing_ids = {c["id"] for c in reranked}
            existing_pages = {
                c.get("metadata", {}).get("page_number") or c.get("page_number")
                for c in reranked
                if (c.get("metadata", {}).get("page_number") or c.get("page_number")) is not None
            }
            # Check top 3 reranked chunks for document & page continuity
            expansion_candidates = []
            for seed in reranked[:3]:
                seed_meta = seed.get("metadata", {})
                seed_doc_id = seed_meta.get("document_id")
                seed_page = seed_meta.get("page_number") or seed.get("page_number")
                seed_idx = seed_meta.get("chunk_index")
                if seed_doc_id is None:
                    continue

                for sc in scoped_chunks:
                    s_meta = sc.get("metadata", {})
                    if s_meta.get("document_id") != seed_doc_id or sc["id"] in existing_ids:
                        continue
                    if s_meta.get("chunk_type") == "video_curriculum_map":
                        continue

                    s_page = s_meta.get("page_number") or sc.get("page_number")
                    s_idx = s_meta.get("chunk_index")

                    # Connect adjacent chunks by index (+-1) or consecutive slides (+-1 or +-2 pages for multi-slide problems)
                    is_neighbor = False
                    if seed_idx is not None and s_idx is not None and abs(int(s_idx) - int(seed_idx)) <= 2:
                        is_neighbor = True
                    elif seed_page is not None and s_page is not None and abs(int(s_page) - int(seed_page)) <= 2:
                        # Extra continuity check: if seed is part of a regression worked problem (e.g. pages 61-63 or 52-53)
                        seed_content = seed.get("content", "").lower()
                        sc_content = sc.get("content", "").lower()
                        if any(term in seed_content for term in ["regression", "normal equation", "step", "problem", "calculate"]):
                            is_neighbor = True

                    if is_neighbor:
                        sc_copy = dict(sc)
                        sc_copy["rerank_score"] = round(max(0.35, seed.get("rerank_score", 0.5) * 0.90), 4)
                        sc_copy["lexical_score"] = seed.get("lexical_score", 0.0)
                        sc_copy["content_term_coverage"] = seed.get("content_term_coverage", 0.0)
                        expansion_candidates.append(sc_copy)
                        existing_ids.add(sc["id"])

            for ec in expansion_candidates:
                reranked.append(ec)
                if len(reranked) >= top_k + 3:
                    break

        return reranked

    def retrieve_ordered_document_chunks(
        self,
        course_id: Optional[str] = None,
        document_id: Optional[Any] = None,
        source_type: Optional[Any] = None,
        max_chunks: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Retrieves chunks in natural syllabus/document progression order
        (by document_id, page_number, slide_number, timestamp_start, chunk_index)
        for whole-syllabus or full-module teaching.
        """
        chunks = vector_store.get_chunks_by_filter(
            course_id=course_id,
            document_id=document_id,
            source_type=source_type,
            limit=250
        )
        if not chunks:
            return []

        def _sort_key(c: Dict[str, Any]):
            m = c.get("metadata", {})
            is_map = 0 if m.get("chunk_type") == "video_curriculum_map" else 1
            doc_id = str(m.get("document_id", ""))
            idx = int(m.get("chunk_index", 0) or 0)
            page = int(m.get("page_number", 0) or 0)
            slide = int(m.get("slide_number", 0) or 0)
            ts = float(m.get("timestamp_start", 0.0) or 0.0)
            return (doc_id, is_map, page, slide, ts, idx)

        chunks.sort(key=_sort_key)

        # If more than max_chunks exist, sample evenly across the progression while always keeping the first chunks
        if len(chunks) > max_chunks:
            step = max(1, len(chunks) // max_chunks)
            selected = [chunks[i] for i in range(0, len(chunks), step)][:max_chunks]
        else:
            selected = chunks

        for c in selected:
            c["rerank_score"] = 0.85
            c["lexical_score"] = 0.80
            c["content_term_coverage"] = 1.0
        return selected


hybrid_retriever = HybridRetrievalService()
