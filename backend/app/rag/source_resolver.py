import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.database.models.document import Document, DocumentPage, Slide, Video
from backend.app.database.models.course import Course
from backend.app.core.logging import logger


def _normalize_name(name: str) -> str:
    """Normalize a filename or title for fuzzy reference matching."""
    if not name:
        return ""
    s = name.lower().strip()
    # Strip trailing (video) or file extension
    s = re.sub(r"\s*\(video\)\s*$", "", s)
    s = re.sub(r"\.(pdf|pptx|ppt|mp4|webm|mkv|mp3|wav|txt|vtt|srt)$", "", s)
    s = re.sub(r"[_\-\.]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _format_type_label(file_type: str) -> str:
    ft = (file_type or "").lower()
    if ft == "pdf":
        return "PDF"
    if ft in ("pptx", "ppt"):
        return "PowerPoint"
    if ft == "youtube":
        return "YouTube Video"
    if ft in ("video", "mp4", "webm"):
        return "Video"
    if ft in ("audio", "mp3", "wav"):
        return "Audio"
    return ft.upper() or "Document"


def extract_structural_coordinates(query: str) -> Dict[str, Optional[Any]]:
    """Extracts explicit page number, slide number, or timestamp target from a student's query."""
    q_lower = query.lower()
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    timestamp_target: Optional[str] = None

    page_m = re.search(r"\b(?:page|pg|p\.)\s*(\d+)\b", q_lower)
    if page_m:
        page_number = int(page_m.group(1))

    slide_m = re.search(r"\b(?:slide|deck\s+slide)\s*#?(\d+)\b", q_lower)
    if slide_m:
        slide_number = int(slide_m.group(1))

    ts_m = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", q_lower)
    if ts_m:
        timestamp_target = ts_m.group(1)

    return {
        "page_number": page_number,
        "slide_number": slide_number,
        "timestamp_target": timestamp_target
    }


def is_whole_syllabus_request(query: str) -> bool:
    """Checks if the student is asking to teach/cover the entire syllabus, module, or uploaded material."""
    q_lower = query.lower()
    syllabus_phrases = [
        "entire syllabus", "whole syllabus", "full syllabus", "complete syllabus",
        "entire uploaded material", "all uploaded material", "all the uploaded material",
        "entire course material", "all course material", "whole course", "entire module",
        "whole module", "teach me everything", "teach the entire", "teach the whole",
        "cover the entire", "cover all topics", "all topics in order", "from start to finish"
    ]
    return any(p in q_lower for p in syllabus_phrases)


class SourceResolver:
    """
    Resolves student references to specific course library sources, detects duplicate/ambiguous
    source names, builds metadata-grounded clarification questions, and narrows retrieval scope.
    """

    async def load_available_sources(
        self,
        session: Optional[AsyncSession],
        course_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Loads uploaded documents with their course titles and real structural metadata from SQLite."""
        if session is None:
            return []

        try:
            stmt = select(Document, Course.title, Course.subject, Course.code).outerjoin(
                Course, Document.course_id == Course.id
            )
            res = await session.execute(stmt)
            rows = res.all()
        except Exception as e:
            logger.warning(f"SourceResolver could not query documents: {e}")
            return []

        all_docs: List[Dict[str, Any]] = []
        for doc, c_title, c_subject, c_code in rows:
            meta = dict(doc.metadata_json or {})
            page_count = meta.get("page_count")
            slide_count = meta.get("slide_count")
            duration_fmt = meta.get("duration_formatted")

            # Query counts from child tables if not cached in metadata_json
            if page_count is None and doc.file_type == "pdf":
                try:
                    p_res = await session.execute(
                        select(func.count()).select_from(DocumentPage).where(DocumentPage.document_id == doc.id)
                    )
                    page_count = p_res.scalar() or 0
                except Exception:
                    page_count = 0

            if slide_count is None and doc.file_type in ("pptx", "ppt"):
                try:
                    s_res = await session.execute(
                        select(func.count()).select_from(Slide).where(Slide.document_id == doc.id)
                    )
                    slide_count = s_res.scalar() or 0
                except Exception:
                    slide_count = 0

            if not duration_fmt and doc.file_type in ("youtube", "video"):
                try:
                    v_res = await session.execute(
                        select(Video).where(Video.document_id == doc.id)
                    )
                    v_obj = v_res.scalar_one_or_none()
                    if v_obj and v_obj.duration_seconds:
                        from backend.app.ingestion.video_ingestion import format_timestamp
                        duration_fmt = format_timestamp(v_obj.duration_seconds)
                except Exception:
                    pass

            norm_name = _normalize_name(doc.filename)
            yt_title = _normalize_name(meta.get("title", "")) if meta.get("title") else ""

            all_docs.append({
                "id": doc.id,
                "course_id": doc.course_id,
                "course_title": c_title or "",
                "course_subject": c_subject or "",
                "course_code": c_code or "",
                "filename": doc.filename,
                "norm_name": norm_name,
                "yt_title": yt_title,
                "file_type": doc.file_type,
                "type_label": _format_type_label(doc.file_type),
                "page_count": int(page_count) if page_count else None,
                "slide_count": int(slide_count) if slide_count else None,
                "duration_formatted": duration_fmt if duration_fmt and duration_fmt != "00:00" else None,
                "created_at": doc.created_at.strftime("%Y-%m-%d") if getattr(doc, "created_at", None) else None,
                "in_active_course": (course_id is None or course_id == "all" or doc.course_id == course_id)
            })

        return all_docs

    def _describe_candidate(self, cand: Dict[str, Any], include_date: bool = False) -> str:
        """Builds a concise description of a candidate source using ONLY real DB metadata."""
        parts = [f"the **{cand['type_label']}**"]
        if cand.get("course_title"):
            parts.append(f"from **{cand['course_title']}**")
        details = []
        if cand.get("page_count"):
            p = cand["page_count"]
            details.append(f"{p} page{'s' if p != 1 else ''}")
        if cand.get("slide_count"):
            s = cand["slide_count"]
            details.append(f"{s} slide{'s' if s != 1 else ''}")
        if cand.get("duration_formatted"):
            details.append(f"duration {cand['duration_formatted']}")
        if include_date and cand.get("created_at"):
            details.append(f"uploaded {cand['created_at']}")
        if details:
            parts.append(f"({', '.join(details)})")
        return " ".join(parts)

    def _filter_by_user_clues(
        self,
        candidates: List[Dict[str, Any]],
        query_lower: str,
        coords: Dict[str, Optional[Any]]
    ) -> List[Dict[str, Any]]:
        """Narrows duplicate candidates if the user already specified file type, course name, or page/slide."""
        if len(candidates) <= 1:
            return candidates

        filtered = list(candidates)

        # 1. Filter by explicit file type mention in query
        wants_pdf = any(w in query_lower for w in ["pdf", "textbook"])
        wants_ppt = any(w in query_lower for w in ["powerpoint", "ppt", "pptx", "slide", "slides", "presentation", "deck"])
        wants_video = any(w in query_lower for w in ["video", "youtube", "lecture video", "recording"])

        if wants_pdf and not wants_ppt and not wants_video:
            sub = [c for c in filtered if c["file_type"] == "pdf"]
            if sub:
                filtered = sub
        elif wants_ppt and not wants_pdf and not wants_video:
            sub = [c for c in filtered if c["file_type"] in ("pptx", "ppt")]
            if sub:
                filtered = sub
        elif wants_video and not wants_pdf and not wants_ppt:
            sub = [c for c in filtered if c["file_type"] in ("youtube", "video")]
            if sub:
                filtered = sub

        # 2. Filter by structural coordinate type (page -> pdf, slide -> pptx)
        if len(filtered) > 1 and coords.get("slide_number") is not None:
            sub = [c for c in filtered if c["file_type"] in ("pptx", "ppt")]
            if sub:
                filtered = sub
        elif len(filtered) > 1 and coords.get("page_number") is not None:
            sub = [c for c in filtered if c["file_type"] == "pdf"]
            if sub:
                filtered = sub

        # 3. Filter by course title / code mention in query
        if len(filtered) > 1:
            course_matched = []
            for c in filtered:
                ct = (c.get("course_title") or "").lower()
                cs = (c.get("course_subject") or "").lower()
                cc = (c.get("course_code") or "").lower()
                if (ct and ct in query_lower) or (cs and len(cs) > 3 and cs in query_lower) or (cc and len(cc) > 2 and cc in query_lower):
                    course_matched.append(c)
            if len(course_matched) == 1:
                filtered = course_matched

        # 4. Filter by page/slide count mention (e.g., "the 12-page one")
        if len(filtered) > 1:
            for c in filtered:
                if c.get("page_count") and f"{c['page_count']}" in query_lower:
                    return [c]
                if c.get("slide_count") and f"{c['slide_count']}" in query_lower:
                    return [c]

        return filtered

    async def resolve(
        self,
        query: str,
        course_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        available_docs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Resolves the student's source reference.
        Returns dict with:
          - status: 'resolved' | 'ambiguous' | 'no_specific_source'
          - document_id: Optional[str]
          - document_ids: Optional[List[str]]
          - course_id: Optional[str]
          - source_type: Optional[str]
          - page_number: Optional[int]
          - slide_number: Optional[int]
          - timestamp_target: Optional[str]
          - is_full_syllabus: bool
          - clarification_message: Optional[str]
          - suggested_options: List[str]
          - effective_query: str (recovered pending question if this turn resolved a clarification)
        """
        coords = extract_structural_coordinates(query)
        full_syllabus = is_whole_syllabus_request(query)
        q_lower = query.lower().strip()

        docs = available_docs if available_docs is not None else await self.load_available_sources(session, course_id)
        if not docs:
            return {
                "status": "no_specific_source",
                "document_id": None,
                "document_ids": None,
                "course_id": course_id,
                "source_type": None,
                "page_number": coords["page_number"],
                "slide_number": coords["slide_number"],
                "timestamp_target": coords["timestamp_target"],
                "is_full_syllabus": full_syllabus,
                "clarification_message": None,
                "suggested_options": [],
                "effective_query": query
            }

        # Check if the previous assistant turn was a duplicate-source clarification question!
        if chat_history and len(chat_history) >= 2:
            last_asst = next((t["content"] for t in reversed(chat_history) if t.get("role") == "assistant" and t.get("content")), "")
            if "which one do you mean" in last_asst.lower() or "i found multiple sources named" in last_asst.lower():
                # Extract the quoted source name from the assistant's clarification prompt
                name_m = re.search(r"named\s+['\"]([^'\"]+)['\"]", last_asst)
                ambig_norm = _normalize_name(name_m.group(1)) if name_m else ""
                if ambig_norm:
                    cand_pool = [d for d in docs if d["norm_name"] == ambig_norm or ambig_norm in d["norm_name"]]
                else:
                    cand_pool = docs

                narrowed = self._filter_by_user_clues(cand_pool, q_lower, coords)
                if len(narrowed) == 1:
                    chosen = narrowed[0]
                    # Recover the user's original question before the clarification prompt
                    user_turns = [t["content"] for t in chat_history if t.get("role") == "user" and t.get("content")]
                    original_q = user_turns[-1] if user_turns else query
                    resolved_stype = "video" if chosen["file_type"] in ("youtube", "video") else chosen["file_type"]
                    return {
                        "status": "resolved",
                        "document_id": chosen["id"],
                        "document_ids": [chosen["id"]],
                        "course_id": chosen["course_id"] or course_id,
                        "source_type": resolved_stype,
                        "source_file": chosen["filename"],
                        "page_number": coords["page_number"],
                        "slide_number": coords["slide_number"],
                        "timestamp_target": coords["timestamp_target"],
                        "is_full_syllabus": full_syllabus,
                        "clarification_message": None,
                        "suggested_options": [],
                        "effective_query": f"{original_q} ({chosen['filename']})"
                    }

        # Check if the user is asking to compare or combine multiple sources
        is_comparison = any(w in q_lower for w in ["compare both", "compare the two", "both files", "combine both", "across both"])

        # Match explicit source names mentioned in the query
        q_norm = _normalize_name(query)
        matched_docs: List[Dict[str, Any]] = []
        matched_name_label = ""

        for d in docs:
            n_name = d["norm_name"]
            yt_name = d["yt_title"]
            if not n_name:
                continue
            # Match full normalized name or filename
            if (len(n_name) >= 3 and n_name in q_norm) or (d["filename"].lower() in q_lower) or (yt_name and len(yt_name) >= 4 and yt_name in q_norm):
                matched_docs.append(d)
                if not matched_name_label or len(n_name) > len(_normalize_name(matched_name_label)):
                    matched_name_label = Path(d["filename"]).stem

        # If multiple distinct names matched, keep the longest/most specific name group
        if len(matched_docs) > 1:
            max_len = max(len(d["norm_name"]) for d in matched_docs)
            longest_norms = {d["norm_name"] for d in matched_docs if len(d["norm_name"]) == max_len}
            if len(longest_norms) == 1:
                target_norm = next(iter(longest_norms))
                matched_docs = [d for d in matched_docs if d["norm_name"] == target_norm]
                matched_name_label = Path(matched_docs[0]["filename"]).stem

        # Also check if no explicit source name was in query, but the active course itself has duplicate filenames
        # when the student refers to "the notes", "the file", or a generic name
        if len(matched_docs) > 1 and not is_comparison:
            # First try narrowing by explicit clues in the query (e.g. "Module 3 Notes PDF" or "from Operating Systems")
            narrowed = self._filter_by_user_clues(matched_docs, q_lower, coords)
            if len(narrowed) == 1:
                matched_docs = narrowed
            else:
                # Prefer active course candidates ONLY if the user did not ask across all courses AND only 1 is in the active course
                # Wait: Problem C Case 2 explicitly states:
                # "I found two files named 'Module 3 Notes'. Which one do you mean: the PDF from Operating Systems or the PowerPoint from Computer Networks?"
                # So if multiple files across the library share the exact name the student asked for, we MUST ask for clarification!
                include_dates = len({(c["type_label"], c["course_title"]) for c in narrowed}) < len(narrowed)
                descriptions = [self._describe_candidate(c, include_date=include_dates) for c in narrowed]
                if len(descriptions) == 2:
                    options_str = f"{descriptions[0]} or {descriptions[1]}"
                else:
                    options_str = ", ".join(descriptions[:-1]) + f", or {descriptions[-1]}"

                display_name = matched_name_label or Path(narrowed[0]["filename"]).stem
                clarification_msg = (
                    f"I found {len(narrowed)} files named '{display_name}'. "
                    f"Which one do you mean: {options_str}?"
                )
                suggested = []
                for c in narrowed[:3]:
                    opt = f"Use the {c['type_label']}"
                    if c.get("course_title"):
                        opt += f" from {c['course_title']}"
                    suggested.append(opt)

                return {
                    "status": "ambiguous",
                    "document_id": None,
                    "document_ids": [c["id"] for c in narrowed],
                    "course_id": course_id,
                    "source_type": None,
                    "page_number": coords["page_number"],
                    "slide_number": coords["slide_number"],
                    "timestamp_target": coords["timestamp_target"],
                    "is_full_syllabus": full_syllabus,
                    "clarification_message": clarification_msg,
                    "suggested_options": suggested,
                    "effective_query": query
                }

        # Case 1: Unique source matched explicitly!
        if len(matched_docs) == 1:
            chosen = matched_docs[0]
            resolved_stype = "video" if chosen["file_type"] in ("youtube", "video") else chosen["file_type"]
            return {
                "status": "resolved",
                "document_id": chosen["id"],
                "document_ids": [chosen["id"]],
                "course_id": chosen["course_id"] or course_id,
                "source_type": resolved_stype,
                "source_file": chosen["filename"],
                "page_number": coords["page_number"],
                "slide_number": coords["slide_number"],
                "timestamp_target": coords["timestamp_target"],
                "is_full_syllabus": full_syllabus,
                "clarification_message": None,
                "suggested_options": [],
                "effective_query": query
            }

        # Check if student referred to a course/module name (e.g. "from Operating Systems")
        course_docs = [d for d in docs if d["in_active_course"]]
        for d in docs:
            ct = (d.get("course_title") or "").lower()
            if ct and len(ct) >= 4 and ct in q_lower:
                course_docs = [x for x in docs if x["course_id"] == d["course_id"]]
                course_id = d["course_id"]
                break

        # Check if student referred to a specific modality ("this video", "the pdf", "the slides", or page/slide coordinate)
        detected_source_type: Optional[str] = None
        if any(w in q_lower for w in ["video", "youtube", "lecture video", "timestamp", "watch", "teacher explain", "instructor explain", "at what time"]):
            detected_source_type = "video"
        elif any(w in q_lower for w in ["ppt", "pptx", "powerpoint", "slide", "slides", "deck", "presentation"]) or coords["slide_number"] is not None:
            detected_source_type = "pptx"
        elif any(w in q_lower for w in ["pdf", "textbook", "page"]) or coords["page_number"] is not None:
            detected_source_type = "pdf"

        if detected_source_type:
            type_matches = [
                d for d in course_docs
                if (d["file_type"] in ("youtube", "video") if detected_source_type == "video" else d["file_type"] == detected_source_type)
            ]
            if len(type_matches) == 1:
                chosen = type_matches[0]
                return {
                    "status": "resolved",
                    "document_id": chosen["id"],
                    "document_ids": [chosen["id"]],
                    "course_id": chosen["course_id"] or course_id,
                    "source_type": detected_source_type,
                    "source_file": chosen["filename"],
                    "page_number": coords["page_number"],
                    "slide_number": coords["slide_number"],
                    "timestamp_target": coords["timestamp_target"],
                    "is_full_syllabus": full_syllabus,
                    "clarification_message": None,
                    "suggested_options": [],
                    "effective_query": query
                }

        # Check conversational continuity (e.g. "in this", "from that lecture", or continuing a single-source discussion)
        if chat_history:
            for turn in reversed(chat_history):
                if turn.get("role") == "assistant" and turn.get("content"):
                    src_m = re.search(r"\[Source:\s*([^•\]]+?)(?:\s*•|\])", turn["content"])
                    if src_m:
                        prev_src_norm = _normalize_name(src_m.group(1))
                        prev_matches = [d for d in course_docs if d["norm_name"] == prev_src_norm or prev_src_norm in d["norm_name"]]
                        if len(prev_matches) == 1 and any(p in q_lower for p in ["in this", "in that", "this lecture", "this video", "this document", "this pdf", "same file", "from it"]):
                            chosen = prev_matches[0]
                            resolved_stype = "video" if chosen["file_type"] in ("youtube", "video") else chosen["file_type"]
                            return {
                                "status": "resolved",
                                "document_id": chosen["id"],
                                "document_ids": [chosen["id"]],
                                "course_id": chosen["course_id"] or course_id,
                                "source_type": resolved_stype,
                                "source_file": chosen["filename"],
                                "page_number": coords["page_number"],
                                "slide_number": coords["slide_number"],
                                "timestamp_target": coords["timestamp_target"],
                                "is_full_syllabus": full_syllabus,
                                "clarification_message": None,
                                "suggested_options": [],
                                "effective_query": query
                            }
                    break

        return {
            "status": "no_specific_source",
            "document_id": None,
            "document_ids": [d["id"] for d in course_docs] if is_comparison else None,
            "course_id": course_id,
            "source_type": detected_source_type,
            "page_number": coords["page_number"],
            "slide_number": coords["slide_number"],
            "timestamp_target": coords["timestamp_target"],
            "is_full_syllabus": full_syllabus,
            "clarification_message": None,
            "suggested_options": [],
            "effective_query": query
        }


source_resolver = SourceResolver()
