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
        self.collection_name = "course_knowledge_chunks"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Multimodal course knowledge chunks with strict source anchors"}
        )
        self.embedding_provider = get_embedding_provider()

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

    async def search(
        self,
        query: str,
        course_id: Optional[str] = None,
        source_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query vector collection with optional metadata filter.
        Returns list of matched chunks with cosine similarity / relevance scores.
        """
        query_emb = await self.embedding_provider.embed_text(query)

        where_filter = None
        filter_conditions = []
        if course_id:
            filter_conditions.append({"course_id": course_id})
        if source_type:
            filter_conditions.append({"source_type": source_type})

        if len(filter_conditions) == 1:
            where_filter = filter_conditions[0]
        elif len(filter_conditions) > 1:
            where_filter = {"$and": filter_conditions}

        try:
            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=top_k,
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

vector_store = VectorStoreManager()
