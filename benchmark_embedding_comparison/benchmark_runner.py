"""
SynapseTutor AI - Fair, Complete Embedding Benchmark
Comparing:
  1. sentence-transformers/all-MiniLM-L6-v2 (Current Model)
  2. nomic-embed-text via Ollama (New Model)

Strict Isolation Rules:
- ZERO modification to existing collections, files, or .env.
- In-memory EphemeralClient for Chroma indexing.
- Preserves running backend and frontend untouched.
"""

import os
import sys
import time
import json
import csv
import subprocess
import threading
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import psutil
import urllib.request

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Paths
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent
CHROMA_PERSIST_DIR = str(WORKSPACE_ROOT / "storage" / "db" / "chroma")
DATASET_PATH = str(WORKSPACE_ROOT / "benchmark" / "dataset.json")
MODERNBERT_SNAPSHOT = r"C:\Users\surya\.cache\huggingface\hub\models--Alibaba-NLP--gte-reranker-modernbert-base\snapshots\f7481e6055501a30fb19d090657df9ec1f79ab2c"

OLLAMA_API_URL = "http://localhost:11434/api/embed"
OLLAMA_MODEL_NAME = "nomic-embed-text"
MINILM_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# ==============================================================================
# Hardware Monitor
# ==============================================================================
class HardwareMonitor:
    """Samples GPU (nvidia-smi) and System (psutil) metrics periodically."""
    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self.running = False
        self.thread = None
        self.samples: List[Dict[str, Any]] = []

    def _sample(self) -> Dict[str, Any]:
        s = {
            "time": time.time(),
            "cpu_pct": psutil.cpu_percent(interval=None),
            "ram_gb": psutil.virtual_memory().used / (1024**3),
            "gpu_temp_c": None,
            "vram_mib": None,
            "gpu_util_pct": None
        }
        try:
            cmd = "nvidia-smi --query-gpu=temperature.gpu,memory.used,utilization.gpu --format=csv,noheader,nounits"
            res = subprocess.check_output(cmd, shell=True, text=True, timeout=1).strip()
            parts = [p.strip() for p in res.split(',')]
            if len(parts) >= 3:
                s["gpu_temp_c"] = float(parts[0])
                s["vram_mib"] = float(parts[1])
                s["gpu_util_pct"] = float(parts[2])
        except Exception:
            pass
        return s

    def _loop(self):
        while self.running:
            self.samples.append(self._sample())
            time.sleep(self.interval)

    def start(self):
        self.samples.clear()
        self.running = True
        self.samples.append(self._sample())
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self) -> Dict[str, Any]:
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.samples.append(self._sample())
        
        cpu_vals = [s["cpu_pct"] for s in self.samples if s["cpu_pct"] is not None]
        ram_vals = [s["ram_gb"] for s in self.samples if s["ram_gb"] is not None]
        vram_vals = [s["vram_mib"] for s in self.samples if s["vram_mib"] is not None]
        gpu_util_vals = [s["gpu_util_pct"] for s in self.samples if s["gpu_util_pct"] is not None]
        gpu_temp_vals = [s["gpu_temp_c"] for s in self.samples if s["gpu_temp_c"] is not None]

        return {
            "avg_cpu_pct": float(np.mean(cpu_vals)) if cpu_vals else 0.0,
            "max_cpu_pct": float(np.max(cpu_vals)) if cpu_vals else 0.0,
            "avg_ram_gb": float(np.mean(ram_vals)) if ram_vals else 0.0,
            "peak_ram_gb": float(np.max(ram_vals)) if ram_vals else 0.0,
            "avg_vram_mib": float(np.mean(vram_vals)) if vram_vals else 0.0,
            "peak_vram_mib": float(np.max(vram_vals)) if vram_vals else 0.0,
            "avg_gpu_util_pct": float(np.mean(gpu_util_vals)) if gpu_util_vals else 0.0,
            "avg_gpu_temp_c": float(np.mean(gpu_temp_vals)) if gpu_temp_vals else 0.0,
        }


# ==============================================================================
# Model Wrapper: MiniLM
# ==============================================================================
class MiniLMModelWrapper:
    def __init__(self, model_name: str = MINILM_MODEL_NAME):
        self.model_name = model_name
        self.model = None
        self.dimension = 384
        self.load_time = 0.0

    def load(self):
        from sentence_transformers import SentenceTransformer
        t0 = time.time()
        self.model = SentenceTransformer(self.model_name)
        self.load_time = time.time() - t0
        return self.load_time

    def embed_documents(self, docs: List[str], batch_size: int = 32) -> List[List[float]]:
        # MiniLM does not require task prefix
        embeddings = self.model.encode(docs, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        vec = self.model.encode(query, show_progress_bar=False, convert_to_numpy=True)
        return vec.tolist()


# ==============================================================================
# Model Wrapper: Nomic Embed Text via Ollama
# ==============================================================================
class NomicOllamaModelWrapper:
    def __init__(self, model_name: str = OLLAMA_MODEL_NAME, api_url: str = OLLAMA_API_URL):
        self.model_name = model_name
        self.api_url = api_url
        self.dimension = 768
        self.load_time = 0.0

    def load(self):
        # Warmup and verify
        t0 = time.time()
        test_payload = {
            "model": self.model_name,
            "input": "search_query: ping warmup test"
        }
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(test_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            embs = data.get("embeddings", [])
            if not embs or len(embs[0]) != 768:
                raise ValueError(f"Unexpected Nomic embedding dimension: {len(embs[0]) if embs else 0}")
        self.load_time = time.time() - t0
        return self.load_time

    def embed_documents(self, docs: List[str], batch_size: int = 16) -> List[List[float]]:
        # Nomic uses 'search_document: ' prefix
        all_embeddings: List[List[float]] = []
        for i in range(0, len(docs), batch_size):
            chunk_slice = docs[i:i + batch_size]
            prefixed = [f"search_document: {text}" for text in chunk_slice]
            payload = {
                "model": self.model_name,
                "input": prefixed
            }
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                all_embeddings.extend(data["embeddings"])
        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        # Nomic uses 'search_query: ' prefix
        payload = {
            "model": self.model_name,
            "input": f"search_query: {query}"
        }
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data["embeddings"][0]


# ==============================================================================
# Metric Helpers
# ==============================================================================
def compute_retrieval_metrics(retrieved_ids: List[str], ground_truth: Dict[str, int]) -> Dict[str, float]:
    """Computes Recall@5, Recall@10, MRR@10, Precision@5 against ground truth IDs."""
    if not ground_truth:
        return {"recall@5": 0.0, "recall@10": 0.0, "mrr@10": 0.0, "precision@5": 0.0}

    relevant_ids = set(ground_truth.keys())
    total_relevant = len(relevant_ids)

    # Top 5
    top5 = retrieved_ids[:5]
    hits5 = len(relevant_ids.intersection(top5))
    recall_5 = hits5 / total_relevant if total_relevant > 0 else 0.0
    precision_5 = hits5 / 5.0

    # Top 10
    top10 = retrieved_ids[:10]
    hits10 = len(relevant_ids.intersection(top10))
    recall_10 = hits10 / total_relevant if total_relevant > 0 else 0.0

    # MRR@10
    mrr_10 = 0.0
    for rank_idx, doc_id in enumerate(top10, start=1):
        if doc_id in relevant_ids:
            mrr_10 = 1.0 / rank_idx
            break

    return {
        "recall@5": recall_5,
        "recall@10": recall_10,
        "mrr@10": mrr_10,
        "precision@5": precision_5
    }


def compute_ndcg_at_k(ranked_ids: List[str], ground_truth: Dict[str, int], k: int = 5) -> float:
    """Computes nDCG@k using graded relevance scores."""
    if not ground_truth:
        return 0.0
    
    # DCG
    dcg = 0.0
    for i, doc_id in enumerate(ranked_ids[:k], start=1):
        rel = ground_truth.get(doc_id, 0)
        dcg += (2**rel - 1) / np.log2(i + 1)
        
    # Ideal DCG
    ideal_rels = sorted(ground_truth.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_rels, start=1):
        idcg += (2**rel - 1) / np.log2(i + 1)
        
    return float(dcg / idcg) if idcg > 0 else 0.0


# ==============================================================================
# Main Benchmark Pipeline
# ==============================================================================
def main():
    print("=" * 80)
    print(" SYNAPSETUTOR AI - FAIR & COMPLETE EMBEDDING BENCHMARK")
    print(" Comparing: sentence-transformers/all-MiniLM-L6-v2 vs nomic-embed-text (Ollama)")
    print("=" * 80)

    # 1. Load Ground Truth Dataset
    print(f"\n[1/7] Loading dataset from: {DATASET_PATH}")
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        benchmark_queries = json.load(f)
    print(f"Loaded {len(benchmark_queries)} benchmark queries across categories:")
    cat_counts = {}
    for q in benchmark_queries:
        c = q.get("category", "unknown")
        cat_counts[c] = cat_counts.get(c, 0) + 1
    for c, cnt in cat_counts.items():
        print(f"  - {c}: {cnt} queries")

    # 2. Load Real Corpus from Chroma (Read-Only)
    print(f"\n[2/7] Reading existing corpus chunks from: {CHROMA_PERSIST_DIR}")
    import chromadb
    readonly_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    source_col = readonly_client.get_collection("course_knowledge_chunks")
    all_raw = source_col.get(include=["documents", "metadatas"])
    
    corpus_ids = all_raw["ids"]
    corpus_docs = all_raw["documents"]
    corpus_metas = all_raw["metadatas"]
    num_chunks = len(corpus_ids)
    print(f"Loaded {num_chunks} representative course chunks:")
    source_summary = {}
    for m in corpus_metas:
        st = m.get("source_type", "unknown")
        source_summary[st] = source_summary.get(st, 0) + 1
    for st, cnt in source_summary.items():
        print(f"  - {st.upper()}: {cnt} chunks")

    # 3. Initialize Ephemeral Chroma Client (Isolated, Memory-Only)
    print("\n[3/7] Setting up isolated ephemeral in-memory Chroma instance...")
    ephemeral_client = chromadb.EphemeralClient()

    # 4. Model 1 Benchmark: all-MiniLM-L6-v2
    print("\n" + "="*50)
    print(" [4/7] BENCHMARKING MODEL 1: sentence-transformers/all-MiniLM-L6-v2")
    print("="*50)
    monitor_minilm = HardwareMonitor(interval=0.5)
    monitor_minilm.start()

    minilm_wrapper = MiniLMModelWrapper()
    print("Loading MiniLM model...")
    minilm_load_time = minilm_wrapper.load()
    print(f"MiniLM load completed in {minilm_load_time:.2f}s (dim: {minilm_wrapper.dimension})")

    # Document embedding & indexing
    t_start_index = time.time()
    minilm_doc_embs = minilm_wrapper.embed_documents(corpus_docs, batch_size=32)
    minilm_emb_time = time.time() - t_start_index

    # Add to ephemeral collection
    minilm_col = ephemeral_client.create_collection("temp_eval_minilm", metadata={"hnsw:space": "cosine"})
    minilm_col.add(
        ids=corpus_ids,
        documents=corpus_docs,
        metadatas=corpus_metas,
        embeddings=minilm_doc_embs
    )
    minilm_total_index_time = time.time() - t_start_index
    minilm_chunks_per_sec = num_chunks / minilm_total_index_time
    print(f"MiniLM Indexed {num_chunks} chunks in {minilm_total_index_time:.2f}s ({minilm_chunks_per_sec:.1f} chunks/sec)")

    # Query embedding and retrieval
    print("Running 32 benchmark queries through MiniLM...")
    minilm_query_latencies = []
    minilm_dense_retrieval_latencies = []
    minilm_total_retrieval_latencies = []
    minilm_query_results = []

    for q_item in benchmark_queries:
        qid = q_item["id"]
        qtext = q_item["query"]
        q_gt = q_item.get("ground_truth", {})

        # Query embedding latency
        t_q0 = time.time()
        q_vec = minilm_wrapper.embed_query(qtext)
        t_q_emb = (time.time() - t_q0) * 1000.0
        minilm_query_latencies.append(t_q_emb)

        # Vector search latency
        t_r0 = time.time()
        res = minilm_col.query(query_embeddings=[q_vec], n_results=10)
        t_dense_search = (time.time() - t_r0) * 1000.0
        minilm_dense_retrieval_latencies.append(t_dense_search)
        minilm_total_retrieval_latencies.append(t_q_emb + t_dense_search)

        retrieved_ids = res["ids"][0] if res["ids"] else []
        retrieved_distances = res["distances"][0] if res["distances"] else []
        retrieved_docs = res["documents"][0] if res["documents"] else []
        retrieved_metas = res["metadatas"][0] if res["metadatas"] else []

        metrics = compute_retrieval_metrics(retrieved_ids, q_gt)
        ndcg_5 = compute_ndcg_at_k(retrieved_ids, q_gt, k=5)

        minilm_query_results.append({
            "id": qid,
            "category": q_item.get("category"),
            "query": qtext,
            "ground_truth": q_gt,
            "retrieved_ids": retrieved_ids,
            "retrieved_distances": [float(d) for d in retrieved_distances],
            "retrieved_docs": retrieved_docs[:3],
            "retrieved_metas": retrieved_metas[:3],
            "q_emb_latency_ms": t_q_emb,
            "dense_search_latency_ms": t_dense_search,
            "total_latency_ms": t_q_emb + t_dense_search,
            "recall@5": metrics["recall@5"],
            "recall@10": metrics["recall@10"],
            "mrr@10": metrics["mrr@10"],
            "precision@5": metrics["precision@5"],
            "ndcg@5": ndcg_5
        })

    minilm_hw_stats = monitor_minilm.stop()
    print("MiniLM Benchmark Complete.")

    # 5. Model 2 Benchmark: nomic-embed-text via Ollama
    print("\n" + "="*50)
    print(" [5/7] BENCHMARKING MODEL 2: nomic-embed-text (Ollama)")
    print("="*50)
    monitor_nomic = HardwareMonitor(interval=0.5)
    monitor_nomic.start()

    nomic_wrapper = NomicOllamaModelWrapper()
    print("Connecting to Ollama and warming up Nomic...")
    nomic_load_time = nomic_wrapper.load()
    print(f"Nomic loaded/connected in {nomic_load_time:.2f}s (dim: {nomic_wrapper.dimension})")

    # Document embedding & indexing
    t_start_nomic_index = time.time()
    nomic_doc_embs = nomic_wrapper.embed_documents(corpus_docs, batch_size=16)
    nomic_emb_time = time.time() - t_start_nomic_index

    nomic_col = ephemeral_client.create_collection("temp_eval_nomic", metadata={"hnsw:space": "cosine"})
    nomic_col.add(
        ids=corpus_ids,
        documents=corpus_docs,
        metadatas=corpus_metas,
        embeddings=nomic_doc_embs
    )
    nomic_total_index_time = time.time() - t_start_nomic_index
    nomic_chunks_per_sec = num_chunks / nomic_total_index_time
    print(f"Nomic Indexed {num_chunks} chunks in {nomic_total_index_time:.2f}s ({nomic_chunks_per_sec:.1f} chunks/sec)")

    # Query embedding and retrieval
    print("Running 32 benchmark queries through Nomic...")
    nomic_query_latencies = []
    nomic_dense_retrieval_latencies = []
    nomic_total_retrieval_latencies = []
    nomic_query_results = []

    for q_item in benchmark_queries:
        qid = q_item["id"]
        qtext = q_item["query"]
        q_gt = q_item.get("ground_truth", {})

        # Query embedding latency
        t_q0 = time.time()
        q_vec = nomic_wrapper.embed_query(qtext)
        t_q_emb = (time.time() - t_q0) * 1000.0
        nomic_query_latencies.append(t_q_emb)

        # Vector search latency
        t_r0 = time.time()
        res = nomic_col.query(query_embeddings=[q_vec], n_results=10)
        t_dense_search = (time.time() - t_r0) * 1000.0
        nomic_dense_retrieval_latencies.append(t_dense_search)
        nomic_total_retrieval_latencies.append(t_q_emb + t_dense_search)

        retrieved_ids = res["ids"][0] if res["ids"] else []
        retrieved_distances = res["distances"][0] if res["distances"] else []
        retrieved_docs = res["documents"][0] if res["documents"] else []
        retrieved_metas = res["metadatas"][0] if res["metadatas"] else []

        metrics = compute_retrieval_metrics(retrieved_ids, q_gt)
        ndcg_5 = compute_ndcg_at_k(retrieved_ids, q_gt, k=5)

        nomic_query_results.append({
            "id": qid,
            "category": q_item.get("category"),
            "query": qtext,
            "ground_truth": q_gt,
            "retrieved_ids": retrieved_ids,
            "retrieved_distances": [float(d) for d in retrieved_distances],
            "retrieved_docs": retrieved_docs[:3],
            "retrieved_metas": retrieved_metas[:3],
            "q_emb_latency_ms": t_q_emb,
            "dense_search_latency_ms": t_dense_search,
            "total_latency_ms": t_q_emb + t_dense_search,
            "recall@5": metrics["recall@5"],
            "recall@10": metrics["recall@10"],
            "mrr@10": metrics["mrr@10"],
            "precision@5": metrics["precision@5"],
            "ndcg@5": ndcg_5
        })

    nomic_hw_stats = monitor_nomic.stop()
    print("Nomic Benchmark Complete.")

    # 6. Reranking Synergy Evaluation (GTE-ModernBERT on top-10 candidates)
    print("\n" + "="*50)
    print(" [6/7] EVALUATING RERANKING SYNERGY (GTE-ModernBERT on Top-10)")
    print("="*50)
    from sentence_transformers import CrossEncoder
    print("Loading GTE-ModernBERT CrossEncoder...")
    t_ce0 = time.time()
    reranker = CrossEncoder(MODERNBERT_SNAPSHOT, max_length=512, local_files_only=True)
    t_ce_load = time.time() - t_ce0
    print(f"CrossEncoder loaded in {t_ce_load:.2f}s")

    # Evaluate reranked results on positive ground-truth queries (26 queries)
    minilm_reranked_r5 = []
    minilm_reranked_mrr5 = []
    minilm_reranked_ndcg5 = []
    nomic_reranked_r5 = []
    nomic_reranked_mrr5 = []
    nomic_reranked_ndcg5 = []

    for i in range(len(benchmark_queries)):
        q_gt = benchmark_queries[i].get("ground_truth", {})
        if not q_gt:
            continue
        qtext = benchmark_queries[i]["query"]

        # Rerank MiniLM top-10
        m_top10_ids = minilm_query_results[i]["retrieved_ids"]
        m_pairs = [(qtext, corpus_docs[corpus_ids.index(cid)]) for cid in m_top10_ids]
        m_scores = reranker.predict(m_pairs)
        m_reranked_order = np.argsort(m_scores)[::-1]
        m_reranked_ids = [m_top10_ids[idx] for idx in m_reranked_order]
        m_m = compute_retrieval_metrics(m_reranked_ids, q_gt)
        minilm_reranked_r5.append(m_m["recall@5"])
        minilm_reranked_mrr5.append(m_m["mrr@10"])
        minilm_reranked_ndcg5.append(compute_ndcg_at_k(m_reranked_ids, q_gt, k=5))

        # Rerank Nomic top-10
        n_top10_ids = nomic_query_results[i]["retrieved_ids"]
        n_pairs = [(qtext, corpus_docs[corpus_ids.index(cid)]) for cid in n_top10_ids]
        n_scores = reranker.predict(n_pairs)
        n_reranked_order = np.argsort(n_scores)[::-1]
        n_reranked_ids = [n_top10_ids[idx] for idx in n_reranked_order]
        n_m = compute_retrieval_metrics(n_reranked_ids, q_gt)
        nomic_reranked_r5.append(n_m["recall@5"])
        nomic_reranked_mrr5.append(n_m["mrr@10"])
        nomic_reranked_ndcg5.append(compute_ndcg_at_k(n_reranked_ids, q_gt, k=5))

    # 7. Aggregate Metrics & Category Breakdown
    print("\n" + "="*50)
    print(" [7/7] AGGREGATING FINAL METRICS & GENERATING ARTIFACTS")
    print("="*50)

    # Positive ground truth indices (26 queries)
    pos_indices = [idx for idx, q in enumerate(benchmark_queries) if q.get("ground_truth")]
    ood_indices = [idx for idx, q in enumerate(benchmark_queries) if not q.get("ground_truth")]

    # Quality aggregates on positive queries
    m_r5 = float(np.mean([minilm_query_results[i]["recall@5"] for i in pos_indices]))
    m_r10 = float(np.mean([minilm_query_results[i]["recall@10"] for i in pos_indices]))
    m_mrr10 = float(np.mean([minilm_query_results[i]["mrr@10"] for i in pos_indices]))
    m_p5 = float(np.mean([minilm_query_results[i]["precision@5"] for i in pos_indices]))
    m_ndcg5 = float(np.mean([minilm_query_results[i]["ndcg@5"] for i in pos_indices]))

    n_r5 = float(np.mean([nomic_query_results[i]["recall@5"] for i in pos_indices]))
    n_r10 = float(np.mean([nomic_query_results[i]["recall@10"] for i in pos_indices]))
    n_mrr10 = float(np.mean([nomic_query_results[i]["mrr@10"] for i in pos_indices]))
    n_p5 = float(np.mean([nomic_query_results[i]["precision@5"] for i in pos_indices]))
    n_ndcg5 = float(np.mean([nomic_query_results[i]["ndcg@5"] for i in pos_indices]))

    # Out of domain max cosine similarity analysis (1 - distance)
    # in Chroma with cosine space: distance = 1 - cosine_similarity, so similarity = 1 - distance
    m_ood_sims = [1.0 - minilm_query_results[i]["retrieved_distances"][0] for i in ood_indices]
    n_ood_sims = [1.0 - nomic_query_results[i]["retrieved_distances"][0] for i in ood_indices]

    # Latency aggregates
    m_lat_avg = float(np.mean(minilm_query_latencies))
    m_lat_p50 = float(np.median(minilm_query_latencies))
    m_lat_p95 = float(np.percentile(minilm_query_latencies, 95))

    n_lat_avg = float(np.mean(nomic_query_latencies))
    n_lat_p50 = float(np.median(nomic_query_latencies))
    n_lat_p95 = float(np.percentile(nomic_query_latencies, 95))

    # Dense vector query latency
    m_dense_avg = float(np.mean(minilm_dense_retrieval_latencies))
    n_dense_avg = float(np.mean(nomic_dense_retrieval_latencies))

    # Category Breakdown dictionary
    categories = list(cat_counts.keys())
    cat_summary = {}
    for c in categories:
        c_idxs = [i for i, q in enumerate(benchmark_queries) if q.get("category") == c and q.get("ground_truth")]
        if not c_idxs:
            continue
        cat_summary[c] = {
            "count": len(c_idxs),
            "minilm_recall@5": float(np.mean([minilm_query_results[i]["recall@5"] for i in c_idxs])),
            "nomic_recall@5": float(np.mean([nomic_query_results[i]["recall@5"] for i in c_idxs])),
            "minilm_mrr@10": float(np.mean([minilm_query_results[i]["mrr@10"] for i in c_idxs])),
            "nomic_mrr@10": float(np.mean([nomic_query_results[i]["mrr@10"] for i in c_idxs])),
            "minilm_ndcg@5": float(np.mean([minilm_query_results[i]["ndcg@5"] for i in c_idxs])),
            "nomic_ndcg@5": float(np.mean([nomic_query_results[i]["ndcg@5"] for i in c_idxs]))
        }

    # Summary table results dictionary
    summary_data = {
        "hardware": {
            "cpu": "Intel 20-thread (14 Physical Cores)",
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "gpu": "NVIDIA GeForce RTX 3050 Laptop GPU (6GB VRAM)"
        },
        "dataset": {
            "total_chunks": num_chunks,
            "source_distribution": source_summary,
            "total_queries": len(benchmark_queries),
            "labeled_queries": len(pos_indices),
            "out_of_domain_queries": len(ood_indices)
        },
        "models": {
            "minilm": {
                "name": MINILM_MODEL_NAME,
                "dimension": 384,
                "load_time_s": minilm_load_time,
                "index_time_s": minilm_total_index_time,
                "chunks_per_sec": minilm_chunks_per_sec,
                "avg_query_emb_ms": m_lat_avg,
                "p50_query_emb_ms": m_lat_p50,
                "p95_query_emb_ms": m_lat_p95,
                "avg_dense_search_ms": m_dense_avg,
                "total_query_latency_ms": m_lat_avg + m_dense_avg,
                "recall@5": m_r5,
                "recall@10": m_r10,
                "mrr@10": m_mrr10,
                "precision@5": m_p5,
                "ndcg@5": m_ndcg5,
                "ood_max_sim_avg": float(np.mean(m_ood_sims)),
                "reranked_recall@5": float(np.mean(minilm_reranked_r5)),
                "reranked_mrr@5": float(np.mean(minilm_reranked_mrr5)),
                "reranked_ndcg@5": float(np.mean(minilm_reranked_ndcg5)),
                "hardware": minilm_hw_stats
            },
            "nomic": {
                "name": OLLAMA_MODEL_NAME,
                "dimension": 768,
                "load_time_s": nomic_load_time,
                "index_time_s": nomic_total_index_time,
                "chunks_per_sec": nomic_chunks_per_sec,
                "avg_query_emb_ms": n_lat_avg,
                "p50_query_emb_ms": n_lat_p50,
                "p95_query_emb_ms": n_lat_p95,
                "avg_dense_search_ms": n_dense_avg,
                "total_query_latency_ms": n_lat_avg + n_dense_avg,
                "recall@5": n_r5,
                "recall@10": n_r10,
                "mrr@10": n_mrr10,
                "precision@5": n_p5,
                "ndcg@5": n_ndcg5,
                "ood_max_sim_avg": float(np.mean(n_ood_sims)),
                "reranked_recall@5": float(np.mean(nomic_reranked_r5)),
                "reranked_mrr@5": float(np.mean(nomic_reranked_mrr5)),
                "reranked_ndcg@5": float(np.mean(nomic_reranked_ndcg5)),
                "hardware": nomic_hw_stats
            }
        },
        "category_breakdown": cat_summary,
        "queries_minilm": minilm_query_results,
        "queries_nomic": nomic_query_results
    }

    # Save JSON raw results
    raw_json_path = OUTPUT_DIR / "results_raw.json"
    with open(raw_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Saved raw results to: {raw_json_path}")

    # Save CSV comparison
    csv_path = OUTPUT_DIR / "results_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Query ID", "Category", "Query Text",
            "MiniLM Recall@5", "MiniLM MRR@10", "MiniLM Latency (ms)",
            "Nomic Recall@5", "Nomic MRR@10", "Nomic Latency (ms)",
            "Winner Recall@5"
        ])
        for i, q in enumerate(benchmark_queries):
            qid = q["id"]
            cat = q.get("category", "")
            qtxt = q["query"]
            mr5 = minilm_query_results[i]["recall@5"]
            mmrr = minilm_query_results[i]["mrr@10"]
            mlat = round(minilm_query_results[i]["total_latency_ms"], 1)
            nr5 = nomic_query_results[i]["recall@5"]
            nmrr = nomic_query_results[i]["mrr@10"]
            nlat = round(nomic_query_results[i]["total_latency_ms"], 1)
            if mr5 > nr5:
                winner = "MiniLM"
            elif nr5 > mr5:
                winner = "Nomic"
            else:
                winner = "Tie" if q.get("ground_truth") else "N/A (OOD)"
            writer.writerow([qid, cat, qtxt, mr5, mmrr, mlat, nr5, nmrr, nlat, winner])
    print(f"Saved summary CSV to: {csv_path}")

    # Print Final Terminal Table
    print("\n" + "=" * 80)
    print(f"{'Metric':<35} | {'MiniLM (Current)':<20} | {'Nomic (Ollama)':<20} | {'Winner':<12}")
    print("-" * 80)
    
    rows = [
        ("Embedding dimensions", f"{minilm_wrapper.dimension}", f"{nomic_wrapper.dimension}", "Nomic (768d)"),
        ("Model loading time (s)", f"{minilm_load_time:.2f} s", f"{nomic_load_time:.2f} s", "MiniLM" if minilm_load_time < nomic_load_time else "Nomic"),
        ("Indexing time (258 chunks)", f"{minilm_total_index_time:.2f} s", f"{nomic_total_index_time:.2f} s", "MiniLM" if minilm_total_index_time < nomic_total_index_time else "Nomic"),
        ("Chunks per second", f"{minilm_chunks_per_sec:.1f} c/s", f"{nomic_chunks_per_sec:.1f} c/s", "MiniLM" if minilm_chunks_per_sec > nomic_chunks_per_sec else "Nomic"),
        ("Average query embedding latency", f"{m_lat_avg:.2f} ms", f"{n_lat_avg:.2f} ms", "MiniLM" if m_lat_avg < n_lat_avg else "Nomic"),
        ("P50 query embedding latency", f"{m_lat_p50:.2f} ms", f"{n_lat_p50:.2f} ms", "MiniLM" if m_lat_p50 < n_lat_p50 else "Nomic"),
        ("P95 query embedding latency", f"{m_lat_p95:.2f} ms", f"{n_lat_p95:.2f} ms", "MiniLM" if m_lat_p95 < n_lat_p95 else "Nomic"),
        ("Recall@5 (Dense Only)", f"{m_r5:.4f}", f"{n_r5:.4f}", "MiniLM" if m_r5 > n_r5 else ("Nomic" if n_r5 > m_r5 else "Tie")),
        ("Recall@10 (Dense Only)", f"{m_r10:.4f}", f"{n_r10:.4f}", "MiniLM" if m_r10 > n_r10 else ("Nomic" if n_r10 > m_r10 else "Tie")),
        ("MRR@10 (Dense Only)", f"{m_mrr10:.4f}", f"{n_mrr10:.4f}", "MiniLM" if m_mrr10 > n_mrr10 else ("Nomic" if n_mrr10 > m_mrr10 else "Tie")),
        ("Precision@5 (Dense Only)", f"{m_p5:.4f}", f"{n_p5:.4f}", "MiniLM" if m_p5 > n_p5 else ("Nomic" if n_p5 > m_p5 else "Tie")),
        ("Recall@5 (+ GTE Reranker)", f"{np.mean(minilm_reranked_r5):.4f}", f"{np.mean(nomic_reranked_r5):.4f}", "MiniLM" if np.mean(minilm_reranked_r5) > np.mean(nomic_reranked_r5) else "Nomic"),
        ("MRR@5 (+ GTE Reranker)", f"{np.mean(minilm_reranked_mrr5):.4f}", f"{np.mean(nomic_reranked_mrr5):.4f}", "MiniLM" if np.mean(minilm_reranked_mrr5) > np.mean(nomic_reranked_mrr5) else "Nomic"),
        ("Peak System RAM (GB)", f"{minilm_hw_stats['peak_ram_gb']:.2f} GB", f"{nomic_hw_stats['peak_ram_gb']:.2f} GB", "MiniLM" if minilm_hw_stats['peak_ram_gb'] < nomic_hw_stats['peak_ram_gb'] else "Nomic"),
        ("Peak GPU VRAM (MiB)", f"{minilm_hw_stats['peak_vram_mib']:.0f} MiB", f"{nomic_hw_stats['peak_vram_mib']:.0f} MiB", "MiniLM" if minilm_hw_stats['peak_vram_mib'] < nomic_hw_stats['peak_vram_mib'] else "Nomic"),
    ]

    for title, v1, v2, win in rows:
        print(f"{title:<35} | {v1:<20} | {v2:<20} | {win:<12}")
    print("=" * 80)

    # Clean up ephemeral collections
    try:
        ephemeral_client.delete_collection("temp_eval_minilm")
        ephemeral_client.delete_collection("temp_eval_nomic")
        print("\nCleaned up ephemeral Chroma collections successfully.")
    except Exception as e:
        print(f"Cleanup note: {e}")

    print("\nBenchmark completed cleanly! All artifacts ready.")

if __name__ == "__main__":
    main()
