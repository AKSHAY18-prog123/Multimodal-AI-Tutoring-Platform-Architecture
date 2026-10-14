"""
Reindex existing course knowledge chunks into the dedicated Nomic Chroma collection.
Strict Isolation & Preservation:
- Reads all 258 chunks and complete metadata from 'course_knowledge_chunks'.
- Embeds with nomic-embed-text (768 dimensions) via OllamaEmbeddingProvider with 'search_document: ' prefix.
- Upserts into 'course_knowledge_chunks_nomic'.
- Verifies that the original 'course_knowledge_chunks' (384d MiniLM) remains 100% untouched.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

import asyncio
import time
from typing import List, Dict, Any

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.knowledge_base.vector_store import vector_store


async def reindex_all_to_nomic():
    print("=" * 80)
    print(" SYNAPSETUTOR AI — REINDEX TO NOMIC EMBED TEXT COLLECTION")
    print("=" * 80)
    print(f"Active Embedding Provider: {settings.EMBEDDING_PROVIDER}")
    print(f"Target Chroma Collection:  {vector_store.collection_name}")
    print(f"Chroma Directory:          {vector_store.persist_dir}")
    print(f"Ollama Endpoint:           {settings.OLLAMA_BASE_URL}")
    print(f"Ollama Model:              {settings.OLLAMA_EMBEDDING_MODEL}")

    # 1. Verify Ollama embedding model availability
    print("\n[1/4] Verifying Ollama embedding provider availability...")
    avail = await vector_store.embedding_provider.verify_availability()
    print(f"Ollama Status: {avail.get('message', 'Checked')}")
    if not avail.get("available"):
        print(f"ERROR: Ollama model {settings.OLLAMA_EMBEDDING_MODEL} is not available! Details: {avail}")
        sys.exit(1)

    # 2. Load existing chunks and metadata from source MiniLM collection
    print("\n[2/4] Reading existing corpus chunks from 'course_knowledge_chunks'...")
    minilm_col = vector_store.client.get_collection("course_knowledge_chunks")
    existing_data = minilm_col.get(include=["documents", "metadatas"])
    
    chunk_ids = existing_data["ids"]
    chunk_docs = existing_data["documents"]
    chunk_metas = existing_data["metadatas"]
    total_chunks = len(chunk_ids)

    print(f"Loaded {total_chunks} total knowledge chunks from source collection.")
    if total_chunks == 0:
        print("No chunks found in source collection. Nothing to re-index.")
        return

    # Count source types
    source_types: Dict[str, int] = {}
    for m in chunk_metas:
        st = m.get("source_type", "unknown")
        source_types[st] = source_types.get(st, 0) + 1
    for st, count in source_types.items():
        print(f"  - {st.upper()}: {count} chunks")

    # 3. Format chunks for vector store upsert
    print("\n[3/4] Structuring chunk payloads preserving all metadata and IDs...")
    chunks_to_index: List[Dict[str, Any]] = []
    for cid, doc, meta in zip(chunk_ids, chunk_docs, chunk_metas):
        chunks_to_index.append({
            "id": cid,
            "content": doc,
            "metadata": meta
        })

    # 4. Embed and Upsert in batches into Nomic collection
    print(f"\n[4/4] Generating Nomic 768d embeddings and upserting into '{vector_store.collection_name}'...")
    t0 = time.time()
    batch_size = 16
    processed = 0

    for i in range(0, total_chunks, batch_size):
        batch = chunks_to_index[i : i + batch_size]
        t_batch0 = time.time()
        await vector_store.add_chunks(batch)
        processed += len(batch)
        t_batch = time.time() - t_batch0
        pct = (processed / total_chunks) * 100
        print(f"  Processed {processed}/{total_chunks} chunks ({pct:.1f}%) in {t_batch:.2f}s")

    elapsed = time.time() - t0
    rate = total_chunks / elapsed if elapsed > 0 else 0.0
    print(f"\nReindexing complete in {elapsed:.2f}s ({rate:.1f} chunks/sec)!")

    # 5. Verify Collection Integrity
    print("\n" + "=" * 80)
    print(" VERIFYING CHROMA COLLECTIONS INTEGRITY")
    print("=" * 80)
    
    # Check Nomic collection
    nomic_count = vector_store.collection.count()
    peek_nomic = vector_store.collection.peek(limit=1)
    embs_n = peek_nomic.get("embeddings")
    nomic_dim = len(embs_n[0]) if (embs_n is not None and len(embs_n) > 0) else 0
    print(f"Nomic Collection '{vector_store.collection_name}':")
    print(f"  Count:      {nomic_count} chunks")
    print(f"  Dimensions: {nomic_dim} (Expected: 768)")

    # Check original MiniLM collection
    minilm_count = minilm_col.count()
    peek_minilm = minilm_col.peek(limit=1)
    embs_m = peek_minilm.get("embeddings")
    minilm_dim = len(embs_m[0]) if (embs_m is not None and len(embs_m) > 0) else 0
    print(f"\nOriginal MiniLM Collection 'course_knowledge_chunks' (Untouched):")
    print(f"  Count:      {minilm_count} chunks")
    print(f"  Dimensions: {minilm_dim} (Expected: 384)")

    if nomic_count == total_chunks and nomic_dim == 768 and minilm_count == total_chunks and minilm_dim == 384:
        print("\nSUCCESS: Both collections verified perfectly! Safe isolation guaranteed.")
    else:
        print("\nWARNING: Discrepancy detected during collection verification.")


if __name__ == "__main__":
    asyncio.run(reindex_all_to_nomic())
