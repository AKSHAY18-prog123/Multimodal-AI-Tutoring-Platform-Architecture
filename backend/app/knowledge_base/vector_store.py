import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ai.embeddings.provider import get_embedding_provider

class VectorStoreManager:
    """Manages embedded ChromaDB vector storage with rich metadata filtering."""

    def __init__(self):
        self.persist_dir = settings.CHROMA_PERSIST_DIRECTORY
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Initialize persistent Chroma client
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        # Determine collection name based on configuration or provider to prevent mixing vector dimensions
        provider_name = (settings.EMBEDDING_PROVIDER or "local").lower()
        if settings.CHROMA_COLLECTION_NAME:
            self.collection_name = settings.CHROMA_COLLECTION_NAME
        elif provider_name in ["ollama", "nomic", "ollama_nomic"]:
            self.collection_name = "course_knowledge_chunks_nomic"
        else:
            self.collection_name = "course_knowledge_chunks"

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Multimodal course knowledge chunks with strict source anchors"}
        )
        self.embedding_provider = get_embedding_provider()
        self._verify_collection_compatibility()

    def _verify_collection_compatibility(self):
        """Verify that existing collection embedding dimensions match the configured provider."""
        try:
            count = self.collection.count()
            if count > 0:
                peek = self.collection.peek(limit=1)
                embeddings = peek.get("embeddings")
                if embeddings is not None and len(embeddings) > 0 and len(embeddings[0]) > 0:
                    existing_dim = len(embeddings[0])
                    expected_dim = getattr(self.embedding_provider, "dimension", 384)
                    if existing_dim != expected_dim:
                        logger.error(
                            f"CRITICAL EMBEDDING DIMENSION MISMATCH: ChromaDB collection '{self.collection_name}' "
                            f"has {existing_dim} dimensions, but embedding provider expects {expected_dim} dimensions! "
                            f"Never silently mix embeddings."
                        )
                    else:
                        logger.info(
                            f"ChromaDB collection '{self.collection_name}' verified: "
                            f"{count} records, {existing_dim} dimensions matching {self.embedding_provider.__class__.__name__}."
                        )
        except Exception as e:
            logger.warning(f"Could not verify collection dimensions: {e}")

    async def add_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Store a batch of knowledge chunks into Chroma with full metadata.
        Each chunk should have:
        - id
        - content
        - metadata: {course_id, document_id, source_type, source_file, page_number, slide_number, timestamp_start, timestamp_end, topic_name, concept_name}
        """
        if not chunks:
            return

        ids = [c["id"] for c in chunks]
        texts = [c["content"] for c in chunks]
        
        # Clean metadata for Chroma (Chroma accepts str, int, float, bool)
        metadatas = []
        for c in chunks:
            meta = c.get("metadata", {})
            clean_meta = {}
            for k, v in meta.items():
                if v is None:
                    continue
                elif isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            metadatas.append(clean_meta)

        embeddings = await self.embedding_provider.embed_documents(texts)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"Successfully upserted {len(chunks)} chunks into vector store.")

    def _build_where_filter(
        self,
        course_id: Optional[str] = None,
        source_type: Optional[Any] = None,
        document_id: Optional[Any] = None,
        page_number: Optional[int] = None,
        slide_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        filter_conditions = []
        if course_id and course_id != "all":
            filter_conditions.append({"course_id": course_id})
        if document_id:
            if isinstance(document_id, (list, tuple, set)):
                doc_ids = [str(d) for d in document_id if d]
                if len(doc_ids) == 1:
                    filter_conditions.append({"document_id": doc_ids[0]})
                elif len(doc_ids) > 1:
                    filter_conditions.append({"document_id": {"$in": doc_ids}})
            else:
                filter_conditions.append({"document_id": str(document_id)})
        if source_type:
            if source_type == "document":
                filter_conditions.append({"source_type": {"$in": ["pdf", "pptx"]}})
            elif source_type == "youtube":
                filter_conditions.append({"source_type": "video"})
            elif isinstance(source_type, (list, tuple, set)):
                stypes = [str(s) for s in source_type if s]
                if len(stypes) == 1:
                    filter_conditions.append({"source_type": stypes[0]})
                elif len(stypes) > 1:
                    filter_conditions.append({"source_type": {"$in": stypes}})
            else:
                filter_conditions.append({"source_type": str(source_type)})
        if page_number is not None:
            filter_conditions.append({"page_number": int(page_number)})
        if slide_number is not None:
            filter_conditions.append({"slide_number": int(slide_number)})

        if not filter_conditions:
            return None
        if len(filter_conditions) == 1:
            return filter_conditions[0]
        return {"$and": filter_conditions}

    async def search(
        self,
        query: str,
        course_id: Optional[str] = None,
        source_type: Optional[Any] = None,
        document_id: Optional[Any] = None,
        page_number: Optional[int] = None,
        slide_number: Optional[int] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query vector collection with optional metadata filter.
        Returns list of matched chunks with cosine similarity / relevance scores.
        """
        query_emb = await self.embedding_provider.embed_text(query)
        where_filter = self._build_where_filter(
            course_id=course_id,
            source_type=source_type,
            document_id=document_id,
            page_number=page_number,
            slide_number=slide_number
        )

        try:
            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=max(1, top_k),
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"Vector search query failed: {e}")
            return []

        hits = []
        if results and results["ids"] and len(results["ids"][0]) > 0:
            count = len(results["ids"][0])
            for i in range(count):
                chunk_id = results["ids"][0][i]
                doc_text = results["documents"][0][i] if results["documents"] else ""
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 1.0

                # Convert distance to normalized similarity score (0 to 1)
                vector_score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))

                hits.append({
                    "id": chunk_id,
                    "content": doc_text,
                    "metadata": meta,
                    "vector_score": round(vector_score, 4)
                })

        return hits

    def get_chunks_by_filter(
        self,
        course_id: Optional[str] = None,
        source_type: Optional[Any] = None,
        document_id: Optional[Any] = None,
        page_number: Optional[int] = None,
        slide_number: Optional[int] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Fetches chunks directly from ChromaDB by metadata filter (used for BM25 corpus scan,
        exact page/slide/timestamp lookup, neighbor expansion, and full-syllabus teaching).
        """
        where_filter = self._build_where_filter(
            course_id=course_id,
            source_type=source_type,
            document_id=document_id,
            page_number=page_number,
            slide_number=slide_number
        )
        try:
            res = self.collection.get(
                where=where_filter,
                limit=limit,
                include=["documents", "metadatas"]
            )
        except Exception as e:
            logger.error(f"Chroma collection.get failed: {e}")
            return []

        chunks = []
        if res and res.get("ids"):
            ids = res["ids"]
            docs = res.get("documents") or []
            metas = res.get("metadatas") or []
            for i, cid in enumerate(ids):
                chunks.append({
                    "id": cid,
                    "content": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "vector_score": 0.5
                })
        return chunks

    def delete_by_document_id(self, document_id: str) -> int:
        """Deletes all chunks associated with a specific document from ChromaDB."""
        try:
            self.collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted vector chunks for document_id={document_id}")
            return 1
        except Exception as e:
            logger.error(f"Failed to delete chunks for document_id={document_id}: {e}")
            return 0

    def delete_by_course_id(self, course_id: str) -> int:
        """Deletes all chunks associated with a specific course from ChromaDB."""
        try:
            self.collection.delete(where={"course_id": course_id})
            logger.info(f"Deleted vector chunks for course_id={course_id}")
            return 1
        except Exception as e:
            logger.error(f"Failed to delete chunks for course_id={course_id}: {e}")
            return 0

vector_store = VectorStoreManager()
