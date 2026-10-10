import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger

def format_timestamp(seconds: float) -> str:
    """Format seconds into MM:SS or HH:MM:SS."""
    seconds = max(0.0, float(seconds or 0.0))
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """Parse VTT/SRT or MM:SS / HH:MM:SS(.mmm) timestamp string into float seconds."""
    if not ts_str:
        return 0.0
    clean = ts_str.strip().replace(",", ".")
    clean = re.split(r"\s+", clean)[0]
    parts = clean.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 1:
            return float(parts[0])
    except (ValueError, TypeError):
        pass
    return 0.0


_STOP_CONCEPT_WORDS = {
    "welcome", "everyone", "today", "going", "about", "there", "their", "these",
    "those", "which", "where", "while", "would", "could", "should", "because",
    "through", "between", "after", "before", "under", "again", "further", "then",
    "once", "here", "when", "what", "this", "that", "with", "from", "have", "will",
    "your", "they", "them", "some", "into", "just", "like", "more", "very", "also",
    "thing", "things", "really", "actually", "basically", "right", "okay", "well"
}


def _extract_segment_concepts(text: str, max_concepts: int = 4) -> List[str]:
    """Extract meaningful concept keywords from a transcript segment."""
    clean = re.sub(r"\[\d{2}:\d{2}(?::\d{2})?\]", "", text)
    words = re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{4,}\b", clean)
    seen = set()
    concepts = []
    for w in words:
        wl = w.lower()
        if wl not in _STOP_CONCEPT_WORDS and wl not in seen:
            seen.add(wl)
            concepts.append(w.capitalize())
            if len(concepts) >= max_concepts:
                break
    return concepts or ["Lecture Concept"]


def _group_timed_utterances(
    utterances: List[Dict[str, Any]],
    video_id: Optional[str] = None,
    window_seconds: float = 120.0,
    max_words: int = 150
) -> List[Dict[str, Any]]:
    """
    Groups fine-grained timed utterances into coherent lecture segments while:
    1. Preserving the exact start timestamp of the first utterance in each group (no drift).
    2. Embedding inline [MM:SS] markers inside the transcript so exact sub-segment topic
       timestamps remain recoverable during retrieval and answer generation.
    """
    valid = []
    for u in utterances:
        text = str(u.get("text", "")).strip()
        if not text:
            continue
        start = max(0.0, float(u.get("start", 0.0)))
        if "end" in u and u["end"] is not None:
            end = max(start, float(u["end"]))
        else:
            dur = max(0.0, float(u.get("duration", 0.0)))
            end = start + (dur if dur > 0 else 3.0)
        valid.append({"start": start, "end": end, "text": text})

    if not valid:
        return []

    segments = []
    cur_items: List[Dict[str, Any]] = []
    cur_words = 0
    cur_start: Optional[float] = None
    cur_end: float = 0.0

    def _flush_group(items: List[Dict[str, Any]], g_start: float, g_end: float) -> Dict[str, Any]:
        # Build transcript with inline [MM:SS] markers at utterance intervals (~15s or first utterance)
        marked_parts = []
        plain_parts = []
        sub_segments = []
        last_marker_time = -999.0

        for it in items:
            it_start = it["start"]
            it_end = it["end"]
            it_text = it["text"]
            it_fmt = format_timestamp(it_start)
            plain_parts.append(it_text)
            sub_segments.append({
                "start": round(it_start, 2),
                "end": round(it_end, 2),
                "start_formatted": it_fmt,
                "end_formatted": format_timestamp(it_end),
                "text": it_text
            })
            if it_start - last_marker_time >= 15.0 or not marked_parts:
                marked_parts.append(f"[{it_fmt}] {it_text}")
                last_marker_time = it_start
            else:
                marked_parts.append(it_text)

        full_text = " ".join(marked_parts)
        plain_text = " ".join(plain_parts)
        seg_dict: Dict[str, Any] = {
            "timestamp_start": round(g_start, 2),
            "timestamp_end": round(g_end, 2),
            "timestamp_start_formatted": format_timestamp(g_start),
            "timestamp_end_formatted": format_timestamp(g_end),
            "transcript": full_text,
            "plain_transcript": plain_text,
            "sub_segments": sub_segments,
            "key_concepts": _extract_segment_concepts(plain_text),
            "is_fallback": False
        }
        if video_id:
            seg_dict["video_id"] = video_id
            seg_dict["video_url"] = f"https://www.youtube.com/watch?v={video_id}&t={int(g_start)}s"
        return seg_dict

    for item in valid:
        if cur_start is None:
            cur_start = item["start"]
        cur_items.append(item)
        cur_end = max(cur_end, item["end"])
        cur_words += len(item["text"].split())

        if (cur_end - cur_start) >= window_seconds or cur_words >= max_words:
            segments.append(_flush_group(cur_items, cur_start, cur_end))
            cur_items = []
            cur_words = 0
            cur_start = None

    if cur_items and cur_start is not None:
        segments.append(_flush_group(cur_items, cur_start, cur_end))

    return segments


class VideoIngestionService:
    """Extracts speech transcript, timestamps, and keyframe representations from video/audio lectures."""

    def __init__(self):
        self.output_dir = Path(settings.PROCESSED_DIR) / "video_frames"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_video_segments(self, file_path: str, document_id: str) -> List[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        # In production/prototype, check if a transcript file (.vtt/.srt/.txt) accompanies the video
        transcript_file = path.with_suffix(".vtt")
        if not transcript_file.exists():
            transcript_file = path.with_suffix(".srt")
        if not transcript_file.exists():
            transcript_file = path.with_suffix(".txt")

        segments = []
        if transcript_file.exists():
            logger.info(f"Found accompanying transcript file: {transcript_file.name}")
            segments = self._parse_transcript_file(transcript_file)
        else:
            # First attempt: Free, fast, local speech transcription via faster-whisper
            whisper_segments = self.transcribe_with_whisper(str(path))
            if whisper_segments:
                logger.info(f"Successfully transcribed {len(whisper_segments)} segments using local faster-whisper for {path.name}")
                segments = whisper_segments
            else:
                logger.warning(f"No speech transcript extracted for {path.name}; marking fallback segments with is_fallback=True")
                segments = self._generate_default_segments(path.name)

        return segments

    def transcribe_with_whisper(self, media_path: str, model_size: str = "tiny", video_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Transcribes local audio/video file using faster-whisper with zero mandatory API costs."""
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Starting local faster-whisper ({model_size}) transcription on {media_path}...")
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            segments_gen, info = model.transcribe(media_path, beam_size=1)
            
            raw_segments = []
            for seg in segments_gen:
                if seg.text.strip():
                    raw_segments.append({
                        "start": float(seg.start),
                        "end": float(seg.end),
                        "text": seg.text.strip()
                    })

            if not raw_segments:
                return []

            return _group_timed_utterances(raw_segments, video_id=video_id)
        except Exception as e:
            logger.warning(f"Local faster-whisper transcription encountered: {e}")
            return []

    def fetch_youtube_metadata(self, url_or_id: str) -> Dict[str, Any]:
        """Extracts rich metadata for any YouTube video using yt-dlp."""
        video_id = extract_youtube_video_id(url_or_id) or url_or_id
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            import yt_dlp
            ydl_opts = {'quiet': True, 'skip_download': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "video_id": video_id,
                    "title": info.get("title", f"YouTube Video ({video_id})"),
                    "channel": info.get("uploader", "YouTube"),
                    "duration": float(info.get("duration", 0)),
                    "duration_formatted": format_timestamp(float(info.get("duration", 0))),
                    "thumbnail": info.get("thumbnail") or f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                    "description": info.get("description", "")[:500],
                    "view_count": info.get("view_count", 0),
                    "upload_date": info.get("upload_date")
                }
        except Exception as e:
            logger.warning(f"yt-dlp metadata extraction fallback for {video_id}: {e}")
            return {
                "video_id": video_id,
                "title": f"YouTube Video ({video_id})",
                "channel": "YouTube",
                "duration": 0.0,
                "duration_formatted": "00:00",
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "description": "",
                "view_count": 0,
                "upload_date": None
            }

    def run_frame_ocr(self, frame_path: str) -> str:
        """Extracts readable on-screen slide text, equations, or code from a frame image using Tesseract."""
        try:
            import cv2
            import pytesseract
            img = cv2.imread(frame_path)
            if img is None:
                return ""
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            text = pytesseract.image_to_string(thresh, config="--psm 6")
            clean_lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 3]
            return "\n".join(clean_lines)
        except Exception as e:
            logger.warning(f"OCR failed for {frame_path}: {e}")
            return ""

    def extract_keyframes_and_ocr(self, video_path: str, interval_seconds: float = 60.0, max_keyframes: int = 15) -> List[Dict[str, Any]]:
        """
        Extracts keyframe slides from a local video file using OpenCV (zero FFmpeg dependency)
        and runs local Tesseract OCR on each keyframe to extract on-screen slide text.
        """
        try:
            import cv2
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.warning(f"Could not open video file with OpenCV: {video_path}")
                return []

            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_stride = int(fps * interval_seconds)
            if frame_stride <= 0:
                frame_stride = int(fps * 30)

            keyframes = []
            curr_frame = 0
            count = 0
            base_name = Path(video_path).stem

            while curr_frame < total_frames and count < max_keyframes:
                cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame)
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                t_sec = curr_frame / fps
                frame_filename = f"{base_name}_frame_{int(t_sec)}s.jpg"
                frame_save_path = self.output_dir / frame_filename
                cv2.imwrite(str(frame_save_path), frame)

                slide_text = self.run_frame_ocr(str(frame_save_path))

                keyframes.append({
                    "timestamp": t_sec,
                    "timestamp_formatted": format_timestamp(t_sec),
                    "frame_path": str(frame_save_path),
                    "slide_text": slide_text
                })

                count += 1
                curr_frame += frame_stride

            cap.release()
            logger.info(f"Extracted {len(keyframes)} keyframes via OpenCV with OCR for {video_path}")
            return keyframes
        except Exception as e:
            logger.warning(f"OpenCV keyframe extraction encountered an error: {e}")
            return []

    def _fetch_yt_dlp_subtitles(self, video_id: str) -> List[Dict[str, Any]]:
        """Fallback subtitle fetcher using yt-dlp when YouTubeTranscriptApi is unavailable."""
        try:
            import yt_dlp
            import httpx
            ydl_opts = {'quiet': True, 'skip_download': True}
            url = f"https://www.youtube.com/watch?v={video_id}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                subs = info.get("subtitles", {})
                auto_subs = info.get("automatic_captions", {})

                formats = subs.get("en") or auto_subs.get("en")
                if not formats:
                    for lang, fmts in {**subs, **auto_subs}.items():
                        if fmts:
                            formats = fmts
                            break
                if not formats:
                    return []

                json3_entry = next((s for s in formats if s.get("ext") == "json3"), None)
                if not json3_entry:
                    return []

                resp = httpx.get(json3_entry["url"], timeout=15.0)
                if resp.status_code != 200:
                    return []
                data = resp.json()
                events = data.get("events", [])

                items = []
                for ev in events:
                    if "segs" in ev:
                        text = "".join(s.get("utf8", "") for s in ev["segs"]).strip()
                        if text and text != "\n":
                            start_s = float(ev.get("tStartMs", 0)) / 1000.0
                            dur_s = float(ev.get("dDurationMs", 0)) / 1000.0
                            items.append({
                                "text": text,
                                "start": start_s,
                                "duration": dur_s
                            })
                return items
        except Exception as e:
            logger.warning(f"yt-dlp subtitle fallback failed for {video_id}: {e}")
            return []

    def _generate_default_segments(self, filename: str) -> List[Dict[str, Any]]:
        """
        Fallback placeholder segments when neither captions nor audio transcription succeeded.
        Explicitly marked with is_fallback=True so the tutor states the transcript limitation
        rather than fabricating specific lecture timestamps.
        """
        return [
            {
                "timestamp_start": 0.0,
                "timestamp_end": 0.0,
                "timestamp_start_formatted": "N/A",
                "timestamp_end_formatted": "N/A",
                "transcript": (
                    f"[Transcript Unavailable for {filename}] "
                    f"No caption track or speech transcript could be extracted for {filename}. "
                    f"Exact timestamps and spoken explanations from this video cannot be verified."
                ),
                "key_concepts": ["Transcript Unavailable"],
                "is_fallback": True
            }
        ]

    def _parse_transcript_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parses .vtt, .srt, or timestamped .txt files with exact start/end seconds."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_lines = [l.strip() for l in f]

        cues: List[Dict[str, Any]] = []
        i = 0
        n = len(raw_lines)
        while i < n:
            line = raw_lines[i]
            if "-->" in line:
                parts = line.split("-->")
                start_str = parts[0].strip()
                end_str = parts[1].strip().split(" ")[0]
                start_sec = parse_timestamp_to_seconds(start_str)
                end_sec = parse_timestamp_to_seconds(end_str)
                if end_sec < start_sec:
                    end_sec = start_sec + 5.0

                text_lines = []
                i += 1
                while i < n and raw_lines[i] and "-->" not in raw_lines[i]:
                    # Skip numeric SRT cue indices if the next line is a timestamp arrow
                    if raw_lines[i].isdigit() and (i + 1 < n and "-->" in raw_lines[i + 1]):
                        break
                    text_lines.append(raw_lines[i])
                    i += 1
                cue_text = " ".join(text_lines).strip()
                if cue_text:
                    cues.append({
                        "start": start_sec,
                        "end": end_sec,
                        "text": cue_text
                    })
            else:
                i += 1

        if not cues:
            # Plain text transcript fallback
            non_empty = [l for l in raw_lines if l and not l.upper().startswith("WEBVTT")]
            if non_empty:
                full_text = " ".join(non_empty)
                return [{
                    "timestamp_start": 0.0,
                    "timestamp_end": 60.0,
                    "timestamp_start_formatted": "00:00",
                    "timestamp_end_formatted": "01:00",
                    "transcript": full_text,
                    "key_concepts": _extract_segment_concepts(full_text),
                    "is_fallback": False
                }]
            return []

        # If cues are already topic-sized segments (e.g. <= 12 cues or average duration >= 20s),
        # preserve each cue's exact start/end boundaries directly while also attaching sub_segments.
        avg_dur = sum(max(0.0, c["end"] - c["start"]) for c in cues) / max(1, len(cues))
        if len(cues) <= 12 or avg_dur >= 20.0:
            segments = []
            for c in cues:
                s_sec = round(c["start"], 2)
                e_sec = round(c["end"], 2)
                s_fmt = format_timestamp(s_sec)
                e_fmt = format_timestamp(e_sec)
                segments.append({
                    "timestamp_start": s_sec,
                    "timestamp_end": e_sec,
                    "timestamp_start_formatted": s_fmt,
                    "timestamp_end_formatted": e_fmt,
                    "transcript": f"[{s_fmt}] {c['text']}",
                    "plain_transcript": c["text"],
                    "sub_segments": [{
                        "start": s_sec,
                        "end": e_sec,
                        "start_formatted": s_fmt,
                        "end_formatted": e_fmt,
                        "text": c["text"]
                    }],
                    "key_concepts": _extract_segment_concepts(c["text"]),
                    "is_fallback": False
                })
            return segments

        return _group_timed_utterances(cues)

    def _transcribe_youtube_audio_with_whisper(self, video_id: str) -> List[Dict[str, Any]]:
        """Downloads audio stream via yt-dlp and transcribes with local faster-whisper when captions are missing."""
        import tempfile
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            import yt_dlp
            with tempfile.TemporaryDirectory() as tmpdir:
                out_tmpl = str(Path(tmpdir) / f"{video_id}.%(ext)s")
                ydl_opts = {
                    "format": "worstaudio/worst",
                    "outtmpl": out_tmpl,
                    "quiet": True,
                    "no_warnings": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                downloaded = list(Path(tmpdir).glob(f"{video_id}.*"))
                if not downloaded:
                    return []
                return self.transcribe_with_whisper(str(downloaded[0]), video_id=video_id)
        except Exception as e:
            logger.warning(f"yt-dlp audio + faster-whisper fallback failed for {video_id}: {e}")
            return []

    def ingest_youtube_transcript(self, url_or_id: str) -> List[Dict[str, Any]]:
        """
        Extracts timestamped lecture segments from a YouTube video URL or ID.
        Groups speech into logical topic segments (e.g. 00:00 - 02:35, 02:35 - 04:40)
        with exact timestamp intervals and inline sub-timestamps for grounded pedagogical tutoring.
        """
        video_id = extract_youtube_video_id(url_or_id) or url_or_id
        if not video_id or len(video_id) < 11:
            raise ValueError(f"Invalid YouTube URL or ID: {url_or_id}")

        transcript_items = []
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            ytt = YouTubeTranscriptApi()
            
            # 1. Multi-language discovery & translation for ANY video globally
            raw_t = None
            try:
                transcript_list = ytt.list(video_id)
                target_transcript = None
                
                # Check for manual English
                try:
                    target_transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB', 'en-CA'])
                except Exception:
                    pass
                
                # Check for auto-generated English
                if not target_transcript:
                    try:
                        target_transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
                    except Exception:
                        pass
                
                # If non-English video, auto-translate to English
                if not target_transcript:
                    for t in transcript_list:
                        if getattr(t, 'is_translatable', False):
                            target_transcript = t.translate('en')
                            logger.info(f"Auto-translating foreign lecture transcript from {t.language} to English for {video_id}")
                            break
                        elif not target_transcript:
                            target_transcript = t
                
                if target_transcript:
                    raw_t = target_transcript.fetch()
            except Exception as list_err:
                logger.info(f"Direct transcript list unavailable ({list_err}), falling back to direct fetch")
                raw_t = ytt.fetch(video_id)
            
            if not raw_t:
                raw_t = ytt.fetch(video_id)

            transcript_items = [
                {
                    "text": getattr(s, "text", "") if not isinstance(s, dict) else s.get("text", ""),
                    "start": float(getattr(s, "start", 0.0)) if not isinstance(s, dict) else float(s.get("start", 0.0)),
                    "duration": float(getattr(s, "duration", 0.0)) if not isinstance(s, dict) else float(s.get("duration", 0.0))
                }
                for s in raw_t
            ]
        except Exception as e:
            logger.warning(f"Could not fetch automated YouTube transcript for {video_id}: {e}")
            transcript_items = []

        # Secondary fallback: use yt-dlp subtitle stream extraction
        if not transcript_items:
            logger.info(f"Attempting yt-dlp direct subtitle extraction fallback for {video_id}...")
            transcript_items = self._fetch_yt_dlp_subtitles(video_id)

        # Tertiary fallback: download lightweight audio stream via yt-dlp and transcribe with faster-whisper
        if not transcript_items:
            logger.info(f"Attempting yt-dlp audio + faster-whisper transcription for {video_id}...")
            whisper_segs = self._transcribe_youtube_audio_with_whisper(video_id)
            if whisper_segs:
                return whisper_segs

        # Final fallback: explicit unavailable-transcript marker (never fabricates fake timestamps)
        if not transcript_items:
            return self._generate_default_segments(f"YouTube_{video_id}")

        segments = _group_timed_utterances(transcript_items, video_id=video_id)
        logger.info(f"Successfully extracted {len(segments)} timestamped lecture segments from YouTube video {video_id}")
        return segments


def extract_youtube_video_id(url: str) -> Optional[str]:
    match = re.search(r'(?:v=|\/|youtu\.be\/|embed\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

video_ingestor = VideoIngestionService()
