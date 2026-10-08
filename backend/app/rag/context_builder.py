from typing import List, Dict, Any

class ContextBuilder:
    """Assembles retrieved multimodal knowledge chunks into a strictly source-attributed prompt context."""

    def build_grounded_context(self, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "No supporting course material chunks retrieved."

        context_blocks = []
        for idx, chunk in enumerate(chunks, 1):
            meta = chunk.get("metadata", {})
            stype = meta.get("source_type", "document")
            sfile = meta.get("source_file", "unknown")
            page = meta.get("page_number")
            slide = meta.get("slide_number")
            t_start = meta.get("timestamp_start_formatted")
            t_end = meta.get("timestamp_end_formatted")

            location_tag = ""
            if page is not None:
                location_tag = f"Page: {page}"
            elif slide is not None:
                location_tag = f"Slide: {slide}"
            elif t_start is not None:
                location_tag = f"Timestamp: {t_start} - {t_end}"

            header = f"--- [SOURCE #{idx} | Type: {stype.upper()} | File: {sfile} | {location_tag}] ---"
            body = chunk.get("content", "").strip()
            context_blocks.append(f"{header}\n{body}")

        return "\n\n".join(context_blocks)

context_builder = ContextBuilder()
