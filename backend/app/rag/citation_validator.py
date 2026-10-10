import re
from typing import List, Dict, Any
from pathlib import Path


class CitationValidator:
    """Validates citations strictly against retrieved chunks to prevent hallucinated citations."""

    def format_citation_label(self, meta: Dict[str, Any]) -> str:
        sfile = meta.get("source_file", "Course Material")
        clean_name = Path(sfile).stem.replace("_", " ")

        page = meta.get("page_number")
        slide = meta.get("slide_number")
        t_start = meta.get("timestamp_start_formatted")
        t_end = meta.get("timestamp_end_formatted")

        if page is not None:
            return f"[Source: {clean_name} • Page {page}]"
        elif slide is not None:
            return f"[Source: {clean_name} • Slide {slide}]"
        elif t_start is not None and t_start != "N/A":
            if t_end and t_end != t_start and t_end != "N/A":
                return f"[Source: {clean_name} • {t_start}-{t_end}]"
            return f"[Source: {clean_name} • {t_start}]"
        return f"[Source: {clean_name}]"

    def extract_and_validate_citations(
        self,
        response_text: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Cross-checks citations mentioned in response against actual retrieved chunks.
        Guarantees that EVERY citation emitted is backed by an actual retrieved chunk
        and includes the grounded text snippet and video timestamp URL when available.
        """
        if not retrieved_chunks or not response_text:
            return []

        resp_lower = response_text.lower()
        if "this topic is not covered in the uploaded course material" in resp_lower:
            return []

        valid_citations: List[Dict[str, Any]] = []
        seen_keys = set()

        for idx, chunk in enumerate(retrieved_chunks):
            meta = chunk.get("metadata", {})
            if meta.get("is_fallback"):
                continue

            stype = meta.get("source_type", "document")
            sfile = meta.get("source_file", "")
            page = meta.get("page_number")
            slide = meta.get("slide_number")
            t_start = meta.get("timestamp_start_formatted")
            t_end = meta.get("timestamp_end_formatted")
            video_url = meta.get("video_url")

            key = f"{sfile}_{page}_{slide}_{t_start}"
            if key in seen_keys:
                continue

            label = self.format_citation_label(meta)
            short_label = f"[Source: {Path(sfile).stem.replace('_', ' ')} • {t_start}]" if t_start else label
            rerank_score = float(chunk.get("rerank_score", 0.0))
            clean_stem = Path(sfile).stem.lower().replace("_", " ")

            in_text = (
                (clean_stem and clean_stem in resp_lower)
                or label.lower() in resp_lower
                or short_label.lower() in resp_lower
                or (t_start and str(t_start).lower() in resp_lower)
                or (page is not None and f"page {page}" in resp_lower)
                or (slide is not None and f"slide {slide}" in resp_lower)
            )

            # Emit citation if referenced in the answer or if it is a top-ranked supporting chunk
            if in_text or (idx < 3 and rerank_score >= 0.30):
                seen_keys.add(key)
                raw_content = chunk.get("content", "").strip()
                clean_snippet = re.sub(r"^\[(?:Video Segment|Table Summary|Visual Element)[^\]]*\]\s*", "", raw_content).strip()
                if len(clean_snippet) > 420:
                    clean_snippet = clean_snippet[:420].rsplit(" ", 1)[0] + "..."

                ts_display = f"{t_start} - {t_end}" if (t_start and t_end and t_end != t_start) else t_start

                valid_citations.append({
                    "chunk_id": chunk.get("id"),
                    "document_id": meta.get("document_id"),
                    "source_type": stype,
                    "source_file": sfile,
                    "page_number": page,
                    "slide_number": slide,
                    "timestamp_formatted": ts_display,
                    "timestamp_start": meta.get("timestamp_start"),
                    "timestamp_end": meta.get("timestamp_end"),
                    "video_url": video_url,
                    "snippet": clean_snippet,
                    "label": label,
                    "rerank_score": rerank_score
                })

        return valid_citations


citation_validator = CitationValidator()
