import uuid
import re
from typing import List, Dict, Any, Optional

def clean_text(text: str) -> str:
    """Normalize whitespace and remove junk characters."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

class ChunkingService:
    """
    Creates source-grounded knowledge chunks from pages, slides, video segments, and diagrams.
    Every chunk retains its strict canonical source anchor.
    """

    def __init__(self, target_chunk_size: int = 500, overlap_size: int = 80):
        self.target_chunk_size = target_chunk_size
        self.overlap_size = overlap_size

    def chunk_pdf_pages(
        self,
        pages: List[Dict[str, Any]],
        document_id: str,
        source_file: str,
        course_id: str
    ) -> List[Dict[str, Any]]:
        chunks = []
        for p in pages:
            page_num = p["page_number"]
            text = clean_text(p.get("text", ""))
            headings = p.get("headings", [])
            tables = p.get("tables", [])

            # Add table summaries as dedicated chunks if present
            for table_idx, table in enumerate(tables):
                table_str = "\n".join([" | ".join(str(cell) for cell in row) for row in table])
                chunk_id = str(uuid.uuid4())
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
                    "topic_name": headings[0] if headings else "Course Content",
                    "concept_name": headings[0] if headings else "Tabular Data",
                    "metadata": {
                        "course_id": course_id,
                        "document_id": document_id,
                        "source_type": "pdf",
                        "source_file": source_file,
                        "page_number": page_num,
                        "chunk_type": "table"
                    }
                })

            if not text:
                continue

            # Split text into sentences / paragraphs
            paragraphs = text.split("\n\n") if "\n\n" in text else [text]
            current_buffer = []
            current_length = 0

            for para in paragraphs:
                words = para.split(" ")
                if current_length + len(words) > self.target_chunk_size and current_buffer:
                    chunk_text = " ".join(current_buffer)
                    chunk_id = str(uuid.uuid4())
                    chunks.append({
                        "id": chunk_id,
                        "document_id": document_id,
                        "content": chunk_text,
                        "chunk_type": "text",
                        "source_type": "pdf",
                        "source_file": source_file,
                        "page_number": page_num,
                        "slide_number": None,
                        "timestamp_start": None,
                        "timestamp_end": None,
                        "topic_name": headings[0] if headings else "General",
                        "concept_name": headings[0] if headings else "General Concept",
                        "metadata": {
                            "course_id": course_id,
                            "document_id": document_id,
                            "source_type": "pdf",
                            "source_file": source_file,
                            "page_number": page_num,
                            "chunk_type": "text"
                        }
                    })
                    # Keep overlap
                    overlap_words = current_buffer[-self.overlap_size:] if len(current_buffer) > self.overlap_size else []
                    current_buffer = list(overlap_words)
                    current_length = len(current_buffer)

                current_buffer.extend(words)
                current_length += len(words)

            if current_buffer:
                chunk_text = " ".join(current_buffer)
                chunk_id = str(uuid.uuid4())
                chunks.append({
                    "id": chunk_id,
                    "document_id": document_id,
                    "content": chunk_text,
                    "chunk_type": "text",
                    "source_type": "pdf",
                    "source_file": source_file,
                    "page_number": page_num,
                    "slide_number": None,
                    "timestamp_start": None,
                    "timestamp_end": None,
                    "topic_name": headings[0] if headings else "General",
                    "concept_name": headings[0] if headings else "General Concept",
                    "metadata": {
                        "course_id": course_id,
                        "document_id": document_id,
                        "source_type": "pdf",
                        "source_file": source_file,
                        "page_number": page_num,
                        "chunk_type": "text"
                    }
                })

        return chunks

    def chunk_ppt_slides(
        self,
        slides: List[Dict[str, Any]],
        document_id: str,
        source_file: str,
        course_id: str
    ) -> List[Dict[str, Any]]:
        chunks = []
        for s in slides:
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
                    "chunk_type": "slide"
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
        for seg in segments:
            t_start = seg["timestamp_start"]
            t_end = seg["timestamp_end"]
            start_fmt = seg.get("timestamp_start_formatted", "00:00")
            end_fmt = seg.get("timestamp_end_formatted", "00:00")
            transcript = clean_text(seg.get("transcript", ""))
            concepts = seg.get("key_concepts", [])

            chunk_id = str(uuid.uuid4())
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
                "metadata": {
                    "course_id": course_id,
                    "document_id": document_id,
                    "source_type": "video",
                    "source_file": source_file,
                    "timestamp_start": t_start,
                    "timestamp_end": t_end,
                    "timestamp_start_formatted": start_fmt,
                    "timestamp_end_formatted": end_fmt,
                    "chunk_type": "video_transcript"
                }
            })

        # Add high-level hierarchical curriculum roadmap chunk for ANY video length
        if len(segments) >= 3:
            total_duration_fmt = segments[-1].get("timestamp_end_formatted", "00:00")
            step = max(1, len(segments) // 7)
            milestones = []
            for i in range(0, len(segments), step):
                s = segments[i]
                start_f = s.get("timestamp_start_formatted", "00:00")
                end_f = s.get("timestamp_end_formatted", "00:00")
                preview = s.get("transcript", "").strip()[:80]
                milestones.append(f"- {start_f} - {end_f}: {preview}...")

            curriculum_summary = (
                f"[Video Curriculum & Topic Roadmap: {source_file}]\n"
                f"Total Video Duration: {total_duration_fmt} ({len(segments)} timestamped lecture segments)\n\n"
                f"Chronological Lecture Progression:\n" + "\n".join(milestones)
            )
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
                "timestamp_end": segments[-1].get("timestamp_end", 0.0),
                "timestamp_start_formatted": "00:00",
                "timestamp_end_formatted": total_duration_fmt,
                "topic_name": "Course Overview & Lecture Roadmap",
                "concept_name": "Curriculum Syllabus",
                "metadata": {
                    "course_id": course_id,
                    "document_id": document_id,
                    "source_type": "video",
                    "source_file": source_file,
                    "timestamp_start": 0.0,
                    "timestamp_end": segments[-1].get("timestamp_end", 0.0),
                    "timestamp_start_formatted": "00:00",
                    "timestamp_end_formatted": total_duration_fmt,
                    "chunk_type": "video_curriculum_map"
                }
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
