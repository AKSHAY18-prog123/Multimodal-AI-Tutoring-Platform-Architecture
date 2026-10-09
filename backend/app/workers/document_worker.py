import asyncio
from typing import Dict, Any
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from backend.app.database.session import AsyncSessionLocal
from backend.app.database.models.document import Document, DocumentPage, Slide, Video, VideoSegment, VisualElement
from backend.app.database.models.knowledge import KnowledgeChunk, Topic, Concept, ConceptRelationship
from backend.app.ingestion.pdf_ingestion import pdf_ingestor
from backend.app.ingestion.ppt_ingestion import ppt_ingestor
from backend.app.ingestion.video_ingestion import video_ingestor
from backend.app.ingestion.visual_understanding import visual_understander
from backend.app.knowledge_base.chunking import chunker
from backend.app.knowledge_base.vector_store import vector_store
from backend.app.knowledge_base.topic_extraction import topic_extractor
from backend.app.core.logging import logger

async def process_document_background(document_id: str):
    """
    Background worker job processing uploaded documents across all pipeline stages:
    uploaded -> extracting -> vision_analysis -> chunking -> indexing -> knowledge_graph -> completed
    """
    logger.info(f"[Worker] Starting background processing for document: {document_id}")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            logger.error(f"[Worker] Document {document_id} not found.")
            return

        doc_file_path = doc.file_path
        doc_type = doc.file_type.lower()
        course_id = doc.course_id
        filename = doc.filename

        try:
            # Clean up any existing children and vector chunks if reprocessing
            await session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
            await session.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
            await session.execute(delete(Slide).where(Slide.document_id == document_id))
            await session.execute(delete(Video).where(Video.document_id == document_id))
            await session.execute(delete(VisualElement).where(VisualElement.document_id == document_id))
            vector_store.delete_by_document_id(document_id)
            await session.commit()

            # Stage 1: Extracting (20%)
            doc.status = "extracting"
            doc.processing_progress = 20
            await session.commit()

            raw_chunks = []
            extracted_text_corpus = []

            if doc_type == "pdf":
                pages = pdf_ingestor.extract_pdf(doc_file_path, document_id)
                for p in pages:
                    db_page = DocumentPage(
                        document_id=doc.id,
                        page_number=p["page_number"],
                        raw_text=p["text"],
                        headings=p["headings"],
                        tables=p["tables"],
                        equations=p["equations"],
                        image_count=len(p["images"])
                    )
                    session.add(db_page)
                    extracted_text_corpus.append(p["text"])
                await session.flush()

                # Stage 2: Vision Analysis (45%)
                doc.status = "vision_analysis"
                doc.processing_progress = 45
                await session.commit()

                # Process extracted images
                for p in pages:
                    for img in p["images"]:
                        vision_result = await visual_understander.analyze_visual(
                            img["image_path"],
                            context_hint=p["headings"][0] if p["headings"] else ""
                        )
                        v_elem = VisualElement(
                            document_id=doc.id,
                            visual_type=vision_result.get("visual_type", "diagram"),
                            image_path=img["image_path"],
                            page_number=p["page_number"],
                            caption=vision_result.get("title"),
                            description=vision_result.get("description"),
                            concept=vision_result.get("concept"),
                            entities=vision_result.get("entities", []),
                            relationships=vision_result.get("relationships", []),
                            vision_understanding_json=vision_result
                        )
                        session.add(v_elem)

                        # Create searchable chunk for the visual element ONLY if verified by real multimodal vision model
                        if not vision_result.get("is_mock", True):
                            v_chunk = chunker.chunk_visual_element(
                                visual_info=vision_result,
                                document_id=doc.id,
                                source_file=filename,
                                course_id=course_id,
                                page_number=p["page_number"]
                            )
                            raw_chunks.append(v_chunk)
                        else:
                            logger.info(f"[Worker] Skipping vector chunking for unverified/mock image on page {p['page_number']}.")

                # Stage 3: Chunking (65%)
                doc.status = "chunking"
                doc.processing_progress = 65
                await session.commit()
                text_chunks = chunker.chunk_pdf_pages(pages, doc.id, filename, course_id)
                raw_chunks.extend(text_chunks)

            elif doc_type in ["pptx", "ppt"]:
                slides = ppt_ingestor.extract_pptx(doc_file_path, document_id)
                for s in slides:
                    db_slide = Slide(
                        document_id=doc.id,
                        slide_number=s["slide_number"],
                        title=s["title"],
                        bullet_points=s["bullet_points"],
                        raw_text=s["raw_text"],
                        notes=s["notes"],
                        tables=s["tables"],
                        shape_count=s["shape_count"]
                    )
                    session.add(db_slide)
                    extracted_text_corpus.append(s["raw_text"])
                await session.flush()

                doc.status = "chunking"
                doc.processing_progress = 65
                await session.commit()
                slide_chunks = chunker.chunk_ppt_slides(slides, doc.id, filename, course_id)
                raw_chunks.extend(slide_chunks)

            elif doc_type == "youtube":
                meta = video_ingestor.fetch_youtube_metadata(doc_file_path)
                if meta and meta.get("title"):
                    if doc.filename in ["YouTube Video", "Video", "Python (Video)", ""] or "http" in doc.filename:
                        doc.filename = meta["title"]
                if meta:
                    doc.metadata_json = {
                        **(doc.metadata_json or {}),
                        "title": meta.get("title"),
                        "thumbnail": meta.get("thumbnail"),
                        "channel": meta.get("channel"),
                        "duration": meta.get("duration"),
                        "duration_formatted": meta.get("duration_formatted")
                    }

                segments = video_ingestor.ingest_youtube_transcript(doc_file_path)
                vid = Video(
                    document_id=doc.id,
                    duration_seconds=meta.get("duration") or (segments[-1]["timestamp_end"] if segments else 0.0),
                    resolution="1080p"
                )
                session.add(vid)
                await session.flush()

                for seg in segments:
                    db_seg = VideoSegment(
                        video_id=vid.id,
                        timestamp_start=seg["timestamp_start"],
                        timestamp_end=seg["timestamp_end"],
                        timestamp_start_formatted=seg["timestamp_start_formatted"],
                        timestamp_end_formatted=seg["timestamp_end_formatted"],
                        transcript_text=seg["transcript"],
                        key_concepts=seg.get("key_concepts", [])
                    )
                    session.add(db_seg)
                    extracted_text_corpus.append(seg["transcript"])
                await session.flush()

                doc.status = "chunking"
                doc.processing_progress = 65
                await session.commit()
                v_chunks = chunker.chunk_video_segments(segments, doc.id, doc.filename, course_id)
                raw_chunks.extend(v_chunks)

            elif doc_type in ["video", "mp4", "webm", "audio", "mp3"]:
                segments = video_ingestor.extract_video_segments(doc_file_path, document_id)
                vid = Video(
                    document_id=doc.id,
                    duration_seconds=segments[-1]["timestamp_end"] if segments else 0.0,
                    resolution="1080p"
                )
                session.add(vid)
                await session.flush()

                for seg in segments:
                    db_seg = VideoSegment(
                        video_id=vid.id,
                        timestamp_start=seg["timestamp_start"],
                        timestamp_end=seg["timestamp_end"],
                        timestamp_start_formatted=seg["timestamp_start_formatted"],
                        timestamp_end_formatted=seg["timestamp_end_formatted"],
                        transcript_text=seg["transcript"],
                        key_concepts=seg.get("key_concepts", [])
                    )
                    session.add(db_seg)
                    extracted_text_corpus.append(seg["transcript"])
                await session.flush()

                doc.status = "chunking"
                doc.processing_progress = 65
                await session.commit()
                v_chunks = chunker.chunk_video_segments(segments, doc.id, filename, course_id)
                raw_chunks.extend(v_chunks)

            # Stage 4: Indexing in Vector Store & Relational DB (85%)
            doc.status = "indexing"
            doc.processing_progress = 85
            await session.commit()

            # Store KnowledgeChunk records in DB
            for c in raw_chunks:
                db_chunk = KnowledgeChunk(
                    id=c["id"],
                    document_id=doc.id,
                    content=c["content"],
                    chunk_type=c.get("chunk_type", "text"),
                    source_type=c["source_type"],
                    source_file=c["source_file"],
                    page_number=c.get("page_number"),
                    slide_number=c.get("slide_number"),
                    timestamp_start=c.get("timestamp_start"),
                    timestamp_end=c.get("timestamp_end"),
                    timestamp_start_formatted=c.get("timestamp_start_formatted"),
                    timestamp_end_formatted=c.get("timestamp_end_formatted"),
                    topic_name=c.get("topic_name"),
                    concept_name=c.get("concept_name"),
                    metadata_json=c.get("metadata", {})
                )
                session.add(db_chunk)

            # Upsert into Chroma vector store
            await vector_store.add_chunks(raw_chunks)
            await session.commit()

            # Stage 5: Knowledge Graph & Concept Taxonomy (95%)
            doc.status = "knowledge_graph"
            doc.processing_progress = 95
            await session.commit()

            combined_text = "\n\n".join(extracted_text_corpus[:10])
            if combined_text:
                taxonomy = await topic_extractor.extract_course_taxonomy(combined_text)
                concept_id_map = {}

                for top_idx, t_data in enumerate(taxonomy.get("topics", [])):
                    topic = Topic(
                        course_id=course_id,
                        title=t_data["title"],
                        description=t_data.get("description"),
                        order_index=top_idx
                    )
                    session.add(topic)
                    await session.flush()

                    for c_idx, c_data in enumerate(t_data.get("concepts", [])):
                        concept = Concept(
                            topic_id=topic.id,
                            name=c_data["name"],
                            subtopic=c_data.get("subtopic"),
                            definition=c_data.get("definition"),
                            difficulty_level=c_data.get("difficulty", "medium"),
                            order_index=c_idx
                        )
                        session.add(concept)
                        await session.flush()
                        concept_id_map[c_data["name"].lower()] = concept.id

                for rel in taxonomy.get("relationships", []):
                    src_name = rel.get("source_concept", "").lower()
                    dst_name = rel.get("target_concept", "").lower()
                    if src_name in concept_id_map and dst_name in concept_id_map:
                        crel = ConceptRelationship(
                            source_concept_id=concept_id_map[src_name],
                            target_concept_id=concept_id_map[dst_name],
                            relationship_type=rel.get("relationship_type", "prerequisite"),
                            strength=rel.get("strength", 1.0)
                        )
                        session.add(crel)

            # Stage 6: Completed (100%)
            doc.status = "completed"
            doc.processing_progress = 100
            await session.commit()
            logger.info(f"[Worker] Document {document_id} ({filename}) processing completed successfully.")

        except Exception as e:
            logger.exception(f"[Worker] Processing failed for document {document_id}: {e}")
            doc.status = "failed"
            doc.error_message = str(e)
            await session.commit()
