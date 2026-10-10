import uuid
import re
from typing import List, Dict, Any, Optional

def clean_text(text: str) -> str:
    """Normalize whitespace and remove junk characters."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def find_exact_timestamp_in_chunk(chunk: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Inspects inline [MM:SS] markers inside a video chunk's content to find the most
    relevant sub-timestamp and range when a user asks about a specific topic or timestamp.
    """
    meta = dict(chunk.get("metadata", {}))
    content = chunk.get("content", "")
    default_start = meta.get("timestamp_start_formatted") or chunk.get("timestamp_start_formatted") or "00:00"
    default_end = meta.get("timestamp_end_formatted") or chunk.get("timestamp_end_formatted") or default_start
    default_start_sec = float(meta.get("timestamp_start") or chunk.get("timestamp_start") or 0.0)
    default_end_sec = float(meta.get("timestamp_end") or chunk.get("timestamp_end") or default_start_sec)
    video_url = meta.get("video_url") or ""

    # Parse inline [MM:SS] or [HH:MM:SS] spans from content
    pattern = r"\[(\d{2}:\d{2}(?::\d{2})?)\]\s*([^\[]+)"
    matches = list(re.finditer(pattern, content))
    if not matches:
        return {
            "timestamp_start": default_start_sec,
            "timestamp_end": default_end_sec,
            "timestamp_start_formatted": default_start,
            "timestamp_end_formatted": default_end,
            "video_url": video_url
        }

    stop_words = {
        "what", "when", "where", "which", "time", "does", "teacher", "instructor",
        "professor", "explain", "explains", "teach", "teaches", "talk", "talks",
        "about", "from", "this", "that", "lecture", "video", "topic", "section",
        "part", "the", "and", "for", "with", "into", "how", "why", "can", "you"
    }
    query_terms = [
        w.lower() for w in re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", query)
        if w.lower() not in stop_words
    ]
    if not query_terms:
        return {
            "timestamp_start": default_start_sec,
            "timestamp_end": default_end_sec,
            "timestamp_start_formatted": default_start,
            "timestamp_end_formatted": default_end,
            "video_url": video_url
        }

    def _to_sec(fmt: str) -> float:
        parts = [int(p) for p in fmt.split(":")]
        if len(parts) == 3:
            return float(parts[0] * 3600 + parts[1] * 60 + parts[2])
        return float(parts[0] * 60 + parts[1])

    best_idx = -1
    best_hits = 0
    for idx, m in enumerate(matches):
        span_text = m.group(2).lower()
        hits = sum(1 for t in query_terms if t in span_text)
        if hits > best_hits:
            best_hits = hits
            best_idx = idx

    if best_idx == -1 or best_hits == 0:
        return {
            "timestamp_start": default_start_sec,
            "timestamp_end": default_end_sec,
            "timestamp_start_formatted": default_start,
            "timestamp_end_formatted": default_end,
            "video_url": video_url
        }

    # Determine end of topic within chunk (include consecutive matching spans)
    end_idx = best_idx
    for j in range(best_idx + 1, len(matches)):
        span_text = matches[j].group(2).lower()
        if any(t in span_text for t in query_terms):
            end_idx = j
        else:
            break

    matched_start_fmt = matches[best_idx].group(1)
    matched_start_sec = _to_sec(matched_start_fmt)
    if end_idx + 1 < len(matches):
        matched_end_fmt = matches[end_idx + 1].group(1)
        matched_end_sec = _to_sec(matched_end_fmt)
    else:
        matched_end_fmt = default_end
        matched_end_sec = max(matched_start_sec, default_end_sec)

    updated_url = video_url
    if video_url and "youtube.com/watch" in video_url:
        updated_url = re.sub(r"&t=\d+s", f"&t={int(matched_start_sec)}s", video_url)
        if "&t=" not in updated_url:
            updated_url = f"{updated_url}&t={int(matched_start_sec)}s"

    return {
        "timestamp_start": matched_start_sec,
        "timestamp_end": matched_end_sec,
        "timestamp_start_formatted": matched_start_fmt,
        "timestamp_end_formatted": matched_end_fmt,
        "video_url": updated_url
    }


class ChunkingService:
    """
    Creates source-grounded knowledge chunks from pages, slides, video segments, and diagrams.
    Every chunk retains its strict canonical source anchor.
    """

    def __init__(self, target_chunk_size: int = 500, overlap_size: int = 80):
        self.target_chunk_size = target_chunk_size
        self.overlap_size = overlap_size

    def _emit_pdf_text_chunk(
        self,
        chunk_words: List[str],
        document_id: str,
        source_file: str,
        course_id: str,
        page_num: int,
        headings: List[str],
        chunk_index: int,
        active_section: Optional[str] = None
    ) -> Dict[str, Any]:
        chunk_text = " ".join(chunk_words).strip()
        chunk_id = str(uuid.uuid4())

        # Clean academic headers or slide numbers from candidate headings
        clean_headings = [
            h for h in headings
            if not any(stop in h.lower() for stop in ["professor", "scope", "assistant", "dr.", "faculty", "university", "department"])
            and not h.strip().isdigit()
        ]
        subhead = clean_headings[0] if clean_headings else (headings[0] if headings else "")

        if active_section:
            if subhead and subhead.lower() not in active_section.lower():
                topic = f"{active_section}: {subhead}"
            else:
                topic = active_section
        else:
            topic = subhead if subhead else "General"

        concept = subhead if subhead else topic

        # Context breadcrumb to ensure topical search and semantic embedding grounding
        content_with_context = chunk_text
        if active_section and active_section.lower() not in chunk_text.lower():
            content_with_context = f"[Topic: {active_section}]\n{chunk_text}"

        return {
            "id": chunk_id,
            "document_id": document_id,
            "content": content_with_context,
            "chunk_type": "text",
            "source_type": "pdf",
            "source_file": source_file,
            "page_number": page_num,
            "slide_number": None,
            "timestamp_start": None,
            "timestamp_end": None,
            "topic_name": topic,
            "concept_name": concept,
            "metadata": {
                "course_id": course_id,
                "document_id": document_id,
                "source_type": "pdf",
                "source_file": source_file,
                "page_number": page_num,
                "chunk_type": "text",
                "chunk_index": chunk_index,
                "topic_name": topic
            }
        }

    def chunk_pdf_pages(
        self,
        pages: List[Dict[str, Any]],
        document_id: str,
        source_file: str,
        course_id: str
    ) -> List[Dict[str, Any]]:
        chunks = []
        chunk_index = 0
        active_section: Optional[str] = None

        for p in pages:
            page_num = p["page_number"]
            raw_page_text = p.get("text", "") or ""
            headings = p.get("headings", [])
            tables = p.get("tables", [])

            # Track section/topic transitions across slide decks and course notes
            norm_text = raw_page_text.lower()
            clean_lines = [
                l.strip() for l in raw_page_text.split("\n")
                if l.strip() and not any(stop in l.lower() for stop in ["professor", "scope", "assistant", "dr. venkata"]) and not l.strip().isdigit()
            ]
            first_line = clean_lines[0].lower() if clean_lines else ""

            if page_num <= 3:
                pass  # Syllabus outline / title pages
            elif any(w in first_line for w in ["logistic regression"]) or ("logistic regression" in norm_text and "why not use" in norm_text):
                active_section = "Logistic Regression"
            elif any(w in first_line for w in ["neural network", "perceptron"]) or ("perceptron" in norm_text and "weight" in norm_text):
                active_section = "Perceptron & Neural Networks"
            elif any(w in first_line for w in ["activation function", "sigmoid", "relu", "tanh", "softmax", "gelu"]):
                active_section = "Activation Functions"
            elif any(w in first_line for w in ["loss function", "cross-entropy"]):
                active_section = "Loss Functions"
            elif "differentiation" in first_line:
                active_section = "Differentiation"
            elif "chain rule" in first_line:
                active_section = "Chain Rule"
            elif any(w in first_line for w in ["simple linear regression"]) or ("simple linear regression" in norm_text and page_num < 60):
                active_section = "Simple Linear Regression"
            elif (
                "multiple linear regression" in first_line
                or "normal equation" in norm_text
                or ("size" in norm_text and "bedrooms" in norm_text and "price" in norm_text)
                or ("study hours" in norm_text and "attendance" in norm_text and "marks" in norm_text)
            ) and page_num < 65:
                active_section = "Multiple Linear Regression"
            elif any(w in first_line for w in ["linear algebra", "vector", "matrix"]):
                active_section = "Linear Algebra"

            # Add table summaries as dedicated chunks if present
            for table_idx, table in enumerate(tables):
                table_str = "\n".join([" | ".join(str(cell) for cell in row) for row in table])
                chunk_id = str(uuid.uuid4())
                table_topic = f"{active_section}: Tabular Data" if active_section else (headings[0] if headings else "Course Content")
                chunks.append({
                    "id": chunk_id,
                    "document_id": document_id,
                    "content": f"[Table Summary - Page {page_num}]\n{table_str}",
                    "chunk_type": "table",
                    "source_type": "pdf",
                    "source_file": source_file,
                    "page_number": page_num,
                    "slide_number": None,
                    "timestamp_start": None,
                    "timestamp_end": None,
                    "topic_name": table_topic,
                    "concept_name": table_topic,
                    "metadata": {
                        "course_id": course_id,
                        "document_id": document_id,
                        "source_type": "pdf",
                        "source_file": source_file,
                        "page_number": page_num,
                        "chunk_type": "table",
                        "chunk_index": chunk_index,
                        "topic_name": table_topic
                    }
                })
                chunk_index += 1

            if not raw_page_text.strip():
                continue

            # Split into paragraphs BEFORE clean_text collapses newlines
            raw_paragraphs = [
                clean_text(block)
                for block in re.split(r"\n\s*\n|\r\n\s*\r\n", raw_page_text)
                if clean_text(block)
            ]
            if not raw_paragraphs:
                cleaned = clean_text(raw_page_text)
                if not cleaned:
                    continue
                raw_paragraphs = [cleaned]

            current_buffer: List[str] = []
            step = max(1, self.target_chunk_size - self.overlap_size)

            for para in raw_paragraphs:
                words = [w for w in para.split(" ") if w]
                if not words:
                    continue

                # If adding this paragraph exceeds target_chunk_size and we already have buffered words, flush buffer first
                if current_buffer and (len(current_buffer) + len(words) > self.target_chunk_size):
                    chunks.append(self._emit_pdf_text_chunk(
                        current_buffer, document_id, source_file, course_id, page_num, headings, chunk_index, active_section
                    ))
                    chunk_index += 1
                    overlap_words = current_buffer[-self.overlap_size:] if len(current_buffer) > self.overlap_size else []
                    current_buffer = list(overlap_words)

                current_buffer.extend(words)

                # If a single paragraph (plus overlap) exceeds target_chunk_size, slice with overlap windows
                while len(current_buffer) > self.target_chunk_size:
                    window = current_buffer[:self.target_chunk_size]
                    chunks.append(self._emit_pdf_text_chunk(
                        window, document_id, source_file, course_id, page_num, headings, chunk_index, active_section
                    ))
                    chunk_index += 1
                    current_buffer = current_buffer[step:]

            if current_buffer:
                chunks.append(self._emit_pdf_text_chunk(
                    current_buffer, document_id, source_file, course_id, page_num, headings, chunk_index, active_section
                ))
                chunk_index += 1

        return chunks

    def chunk_ppt_slides(
        self,
        slides: List[Dict[str, Any]],
        document_id: str,
        source_file: str,
        course_id: str
    ) -> List[Dict[str, Any]]:
        chunks = []
        for idx, s in enumerate(slides):
            slide_num = s["slide_number"]
            title = s.get("title") or f"Slide {slide_num}"
            raw_text = clean_text(s.get("raw_text", ""))
            bullets = s.get("bullet_points", [])
            notes = s.get("notes", "")

            content_lines = [f"Slide Title: {title}"]
            if bullets:
                content_lines.append("Key Points:\n" + "\n".join(f"- {b}" for b in bullets))
            elif raw_text:
                content_lines.append(raw_text)
            if notes:
                content_lines.append(f"Speaker Notes: {notes}")

            full_content = "\n\n".join(content_lines)
            chunk_id = str(uuid.uuid4())
            chunks.append({
                "id": chunk_id,
                "document_id": document_id,
                "content": full_content,
                "chunk_type": "slide",
                "source_type": "pptx",
                "source_file": source_file,
                "page_number": None,
                "slide_number": slide_num,
                "timestamp_start": None,
                "timestamp_end": None,
                "topic_name": title,
                "concept_name": title,
                "metadata": {
                    "course_id": course_id,
                    "document_id": document_id,
                    "source_type": "pptx",
                    "source_file": source_file,
                    "slide_number": slide_num,
                    "slide_title": title,
                    "chunk_type": "slide",
                    "chunk_index": idx
                }
            })
        return chunks

    def chunk_video_segments(
        self,
        segments: List[Dict[str, Any]],
        document_id: str,
        source_file: str,
        course_id: str
    ) -> List[Dict[str, Any]]:
        chunks = []
        for idx, seg in enumerate(segments):
            t_start = float(seg.get("timestamp_start", 0.0))
            t_end = float(seg.get("timestamp_end", t_start))
            start_fmt = seg.get("timestamp_start_formatted", "00:00")
            end_fmt = seg.get("timestamp_end_formatted", "00:00")
            transcript = clean_text(seg.get("transcript", ""))
            concepts = seg.get("key_concepts", [])
            video_id = seg.get("video_id")
            video_url = seg.get("video_url")
            is_fallback = bool(seg.get("is_fallback", False))

            chunk_id = str(uuid.uuid4())
            meta: Dict[str, Any] = {
                "course_id": course_id,
                "document_id": document_id,
                "source_type": "video",
                "source_file": source_file,
                "timestamp_start": t_start,
                "timestamp_end": t_end,
                "timestamp_start_formatted": start_fmt,
                "timestamp_end_formatted": end_fmt,
                "chunk_type": "video_transcript",
                "chunk_index": idx,
                "is_fallback": is_fallback
            }
            if video_id:
                meta["video_id"] = video_id
            if video_url:
                meta["video_url"] = video_url

            chunks.append({
                "id": chunk_id,
                "document_id": document_id,
                "content": f"[Video Segment: {start_fmt} - {end_fmt}]\n{transcript}",
                "chunk_type": "video_transcript",
                "source_type": "video",
                "source_file": source_file,
                "page_number": None,
                "slide_number": None,
                "timestamp_start": t_start,
                "timestamp_end": t_end,
                "timestamp_start_formatted": start_fmt,
                "timestamp_end_formatted": end_fmt,
                "topic_name": concepts[0] if concepts else "Lecture Video",
                "concept_name": concepts[0] if concepts else "Lecture Segment",
                "metadata": meta
            })

        # Add high-level hierarchical curriculum roadmap chunk only for real (non-fallback) transcripts
        non_fallback_segments = [s for s in segments if not s.get("is_fallback", False)]
        if len(non_fallback_segments) >= 3:
            total_duration_fmt = non_fallback_segments[-1].get("timestamp_end_formatted", "00:00")
            first_video_url = non_fallback_segments[0].get("video_url")
            first_video_id = non_fallback_segments[0].get("video_id")
            step = max(1, len(non_fallback_segments) // 7)
            milestones = []
            for i in range(0, len(non_fallback_segments), step):
                s = non_fallback_segments[i]
                start_f = s.get("timestamp_start_formatted", "00:00")
                end_f = s.get("timestamp_end_formatted", "00:00")
                preview = s.get("plain_transcript", s.get("transcript", "")).strip()[:80]
                milestones.append(f"- {start_f} - {end_f}: {preview}...")

            curriculum_summary = (
                f"[Video Curriculum & Topic Roadmap: {source_file}]\n"
                f"Total Video Duration: {total_duration_fmt} ({len(non_fallback_segments)} timestamped lecture segments)\n\n"
                f"Chronological Lecture Progression:\n" + "\n".join(milestones)
            )
            map_meta: Dict[str, Any] = {
                "course_id": course_id,
                "document_id": document_id,
                "source_type": "video",
                "source_file": source_file,
                "timestamp_start": 0.0,
                "timestamp_end": float(non_fallback_segments[-1].get("timestamp_end", 0.0)),
                "timestamp_start_formatted": "00:00",
                "timestamp_end_formatted": total_duration_fmt,
                "chunk_type": "video_curriculum_map",
                "chunk_index": len(segments),
                "is_overview_map": True,
                "is_fallback": False
            }
            if first_video_id:
                map_meta["video_id"] = first_video_id
            if first_video_url:
                map_meta["video_url"] = re.sub(r"&t=\d+s", "&t=0s", first_video_url)

            chunks.append({
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "content": curriculum_summary,
                "chunk_type": "video_curriculum_map",
                "source_type": "video",
                "source_file": source_file,
                "page_number": None,
                "slide_number": None,
                "timestamp_start": 0.0,
                "timestamp_end": float(non_fallback_segments[-1].get("timestamp_end", 0.0)),
                "timestamp_start_formatted": "00:00",
                "timestamp_end_formatted": total_duration_fmt,
                "topic_name": "Course Overview & Lecture Roadmap",
                "concept_name": "Curriculum Syllabus",
                "metadata": map_meta
            })
        return chunks

    def chunk_visual_element(
        self,
        visual_info: Dict[str, Any],
        document_id: str,
        source_file: str,
        course_id: str,
        page_number: Optional[int] = None,
        slide_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Creates a searchable knowledge chunk from a vision-analyzed diagram or figure."""
        v_type = visual_info.get("visual_type", "diagram")
        title = visual_info.get("title", "Visual Diagram")
        desc = visual_info.get("description", "")
        concept = visual_info.get("concept", "Visual Representation")
        entities = visual_info.get("entities", [])
        relationships = visual_info.get("relationships", [])

        content_parts = [
            f"[Visual Element: {v_type.capitalize()} - {title}]",
            f"Concept: {concept}",
            f"Description: {desc}"
        ]
        if entities:
            content_parts.append(f"Entities: {', '.join(entities)}")
        if relationships:
            content_parts.append(f"Relationships: {'; '.join(relationships)}")

        chunk_id = str(uuid.uuid4())
        source_type = "pdf" if page_number else ("pptx" if slide_number else "image")

        return {
            "id": chunk_id,
            "document_id": document_id,
            "content": "\n".join(content_parts),
            "chunk_type": "diagram_summary",
            "source_type": source_type,
            "source_file": source_file,
            "page_number": page_number,
            "slide_number": slide_number,
            "timestamp_start": None,
            "timestamp_end": None,
            "topic_name": concept,
            "concept_name": concept,
            "metadata": {
                "course_id": course_id,
                "document_id": document_id,
                "source_type": source_type,
                "source_file": source_file,
                "page_number": page_number,
                "slide_number": slide_number,
                "chunk_type": "diagram_summary",
                "visual_type": v_type
            }
        }

chunker = ChunkingService()
