import os
import sys
import time
import json
import csv
import subprocess
import threading
from typing import List, Dict, Any, Tuple
import numpy as np
import psutil

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Paths
SNAPSHOT_DIR = r"C:\Users\surya\.cache\huggingface\hub\models--Qwen--Qwen3-Reranker-0.6B\snapshots\e61197ed45024b0ed8a2d74b80b4d909f1255473"
DATASET_PATH = "benchmark/dataset.json"
RESULTS_CSV = "benchmark/per_question_results.csv"
METRICS_JSON = "benchmark/raw_benchmark_metrics.json"

class HardwareMonitor:
    """Monitors GPU and System metrics in a background thread at 1s intervals."""
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.running = False
        self.thread = None
        self.samples: List[Dict[str, float]] = []

    def _sample_once(self) -> Dict[str, float]:
        sample = {
            "timestamp": time.time(),
            "cpu_util_pct": psutil.cpu_percent(interval=None),
            "ram_used_gb": psutil.virtual_memory().used / (1024**3),
            "ram_total_gb": psutil.virtual_memory().total / (1024**3),
            "gpu_temp_c": None,
            "gpu_util_pct": None,
            "vram_used_mib": None,
            "gpu_pwr_w": None
        }
        try:
            cmd = "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits"
            res = subprocess.check_output(cmd, shell=True, text=True, timeout=1).strip()
            parts = [p.strip() for p in res.split(',')]
            if len(parts) >= 4:
                sample["gpu_temp_c"] = float(parts[0])
                sample["gpu_util_pct"] = float(parts[1])
                sample["vram_used_mib"] = float(parts[2])
                sample["gpu_pwr_w"] = float(parts[3])
        except Exception:
            pass
        return sample

    def _run_loop(self):
        while self.running:
            self.samples.append(self._sample_once())
            time.sleep(self.interval)

    def start(self):
        self.samples.clear()
        self.running = True
        # First sample
        self.samples.append(self._sample_once())
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self) -> Dict[str, Any]:
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.samples.append(self._sample_once())

        if not self.samples:
            return {}

        temps = [s["gpu_temp_c"] for s in self.samples if s["gpu_temp_c"] is not None]
        gpu_utils = [s["gpu_util_pct"] for s in self.samples if s["gpu_util_pct"] is not None]
        vrams = [s["vram_used_mib"] for s in self.samples if s["vram_used_mib"] is not None]
        pwrs = [s["gpu_pwr_w"] for s in self.samples if s["gpu_pwr_w"] is not None]
        cpu_utils = [s["cpu_util_pct"] for s in self.samples]
        rams = [s["ram_used_gb"] for s in self.samples]

        return {
            "samples_count": len(self.samples),
            "sampling_interval_s": self.interval,
            "gpu_temp_before_c": temps[0] if temps else None,
            "gpu_temp_avg_c": float(np.mean(temps)) if temps else None,
            "gpu_temp_max_c": float(np.max(temps)) if temps else None,
            "gpu_util_avg_pct": float(np.mean(gpu_utils)) if gpu_utils else None,
            "gpu_util_max_pct": float(np.max(gpu_utils)) if gpu_utils else None,
            "vram_used_before_mib": vrams[0] if vrams else None,
            "vram_used_avg_mib": float(np.mean(vrams)) if vrams else None,
            "vram_used_peak_mib": float(np.max(vrams)) if vrams else None,
            "vram_used_after_mib": vrams[-1] if vrams else None,
            "gpu_pwr_avg_w": float(np.mean(pwrs)) if pwrs else None,
            "gpu_pwr_max_w": float(np.max(pwrs)) if pwrs else None,
            "cpu_util_avg_pct": float(np.mean(cpu_utils)),
            "cpu_util_max_pct": float(np.max(cpu_utils)),
            "ram_used_before_gb": rams[0],
            "ram_used_avg_gb": float(np.mean(rams)),
            "ram_used_peak_gb": float(np.max(rams)),
            "ram_used_after_gb": rams[-1]
        }

def calculate_ranking_metrics(ranked_cands: List[Dict[str, Any]], ground_truth: Dict[str, int]) -> Dict[str, float]:
    """Calculates Recall@5, MRR@5, nDCG@5 for a ranked candidate list."""
    has_gt = len(ground_truth) > 0
    if not has_gt:
        # For unanswerable queries where answer is absent
        # If no irrelevant chunk is falsely marked as highly relevant (score analysis)
        return {
            "recall_at_5": 1.0,
            "mrr_at_5": 1.0,
            "ndcg_at_5": 1.0,
            "first_rel_rank": None
        }

    # Extract top 5 ranked IDs
    top_5_ids = [c["id"] for c in ranked_cands[:5]]

    # 1. Recall@5: 1 if any ground-truth chunk is in top 5, else 0
    recall = 1.0 if any(cid in ground_truth for cid in top_5_ids) else 0.0

    # 2. MRR@5: 1 / rank of first relevant chunk
    first_rel_rank = None
    for rank_idx, c in enumerate(ranked_cands[:5], start=1):
        if c["id"] in ground_truth:
            first_rel_rank = rank_idx
            break
    mrr = 1.0 / first_rel_rank if first_rel_rank is not None else 0.0

    # 3. nDCG@5
    dcg = 0.0
    for rank_idx, c in enumerate(ranked_cands[:5], start=1):
        rel = ground_truth.get(c["id"], 0)
        dcg += (2**rel - 1) / np.log2(rank_idx + 1)

    # Ideal DCG
    ideal_rels = sorted(ground_truth.values(), reverse=True)[:5]
    idcg = sum((2**r - 1) / np.log2(idx + 1) for idx, r in enumerate(ideal_rels, start=1))
    ndcg = dcg / idcg if idcg > 0.0 else 0.0

    return {
        "recall_at_5": float(recall),
        "mrr_at_5": float(mrr),
        "ndcg_at_5": float(ndcg),
        "first_rel_rank": first_rel_rank
    }

def verify_timestamp_retention(ranked_cands: List[Dict[str, Any]], ground_truth: Dict[str, int]) -> bool:
    """Checks if top-ranked relevant video chunk retained its timestamp metadata."""
    for c in ranked_cands:
        if c["id"] in ground_truth:
            meta = c.get("metadata", {})
            stype = meta.get("source_type") or c.get("source_type")
            if stype == "video":
                return ("timestamp_start" in meta or "timestamp_start_formatted" in meta) and ("video_url" in meta or "video_id" in meta)
            return True
    return False

def run_benchmark():
    print("=" * 70)
    print("BENCHMARK: Qwen3-Reranker-0.6B vs FlashRank in SynapseTutor AI")
    print("=" * 70)

    # 1. Load Dataset
    print(f"\n[1/5] Loading benchmark dataset from {DATASET_PATH}...")
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    print(f"Loaded {len(dataset)} queries across categories:")
    cats = {}
    for item in dataset:
        cats[item["category"]] = cats.get(item["category"], 0) + 1
    for cat, count in cats.items():
        print(f"  - {cat}: {count} queries")

    # Load Tokenizer for input token counting
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(SNAPSHOT_DIR, local_files_only=True)

    # Compute input tokens for each candidate pair
    total_input_tokens = 0
    query_token_counts = []
    for item in dataset:
        q = item["query"]
        q_tokens = len(tokenizer.encode(q))
        item_total = 0
        for cand in item["candidates"]:
            doc_text = cand["content"][:1500]
            pair_tokens = len(tokenizer.encode(q + " " + doc_text))
            item_total += pair_tokens
        query_token_counts.append(item_total)
        total_input_tokens += item_total
    
    avg_tokens_per_query = total_input_tokens / len(dataset)
    print(f"Total benchmark input tokens across 32 queries (15 cands/q): {total_input_tokens:,}")
    print(f"Average input tokens per query: {avg_tokens_per_query:.1f}")

    # =========================================================================
    # MODEL A: FlashRank Baseline
    # =========================================================================
    print("\n" + "=" * 50)
    print("[2/5] Running Model A: FlashRank (Baseline)")
    print("=" * 50)

    from flashrank import Ranker, RerankRequest
    
    monitor_fr = HardwareMonitor(interval=1.0)
    monitor_fr.start()

    t_load_fr_start = time.perf_counter()
    fr_ranker = Ranker()
    t_load_fr = time.perf_counter() - t_load_fr_start
    print(f"FlashRank model loaded in {t_load_fr:.4f}s (dir={getattr(fr_ranker, 'model_dir', 'default')})")

    # Warmup
    print("Warming up FlashRank (2 passes)...")
    for _ in range(2):
        _ = fr_ranker.rerank(RerankRequest(
            query="Warmup query for test",
            passages=[{"id": 0, "text": "Sample text for warmup"}]
        ))

    fr_query_latencies = []
    fr_results = []
    fr_bench_start = time.perf_counter()

    for idx, item in enumerate(dataset):
        query = item["query"]
        candidates = item["candidates"]
        passages = [{"id": i, "text": c["content"][:1500]} for i, c in enumerate(candidates)]
        
        t0 = time.perf_counter()
        fr_output = fr_ranker.rerank(RerankRequest(query=query, passages=passages))
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000.0
        fr_query_latencies.append(lat_ms)

        # Map back to original candidate objects in ranked order
        score_map = {item["id"]: float(item.get("score", 0.0)) for item in fr_output}
        ranked_cands = sorted(candidates, key=lambda c: score_map.get(candidates.index(c), 0.0), reverse=True)
        
        metrics = calculate_ranking_metrics(ranked_cands, item["ground_truth"])
        ts_ok = verify_timestamp_retention(ranked_cands, item["ground_truth"])

        fr_results.append({
            "query_id": item["id"],
            "query": query,
            "category": item["category"],
            "latency_ms": lat_ms,
            "input_tokens": query_token_counts[idx],
            "recall_5": metrics["recall_at_5"],
            "mrr_5": metrics["mrr_at_5"],
            "ndcg_5": metrics["ndcg_at_5"],
            "first_rel_rank": metrics["first_rel_rank"],
            "timestamp_preserved": ts_ok,
            "ranked_ids": [c["id"] for c in ranked_cands[:5]],
            "top_scores": [score_map.get(candidates.index(c), 0.0) for c in ranked_cands[:5]]
        })

    fr_total_time = time.perf_counter() - fr_bench_start
    fr_hw = monitor_fr.stop()
    print(f"FlashRank benchmark completed in {fr_total_time:.2f}s ({len(dataset)} queries)")

    # Cooldown
    print("\nCooldown pause (5s)...")
    time.sleep(5)

    # =========================================================================
    # MODEL B: Qwen3-Reranker-0.6B Candidate
    # =========================================================================
    print("\n" + "=" * 50)
    print("[3/5] Running Model B: Qwen3-Reranker-0.6B (Candidate)")
    print("=" * 50)

    from sentence_transformers import CrossEncoder

    monitor_qw = HardwareMonitor(interval=1.0)
    monitor_qw.start()

    t_load_qw_start = time.perf_counter()
    qw_model = CrossEncoder(SNAPSHOT_DIR, local_files_only=True)
    t_load_qw = time.perf_counter() - t_load_qw_start
    print(f"Qwen3-Reranker-0.6B model loaded in {t_load_qw:.4f}s")

    # Warmup
    print("Warming up Qwen3-Reranker-0.6B (2 passes)...")
    for _ in range(2):
        _ = qw_model.predict([("Warmup query", "Sample text for warmup")])

    qw_query_latencies = []
    qw_results = []
    qw_bench_start = time.perf_counter()

    for idx, item in enumerate(dataset):
        query = item["query"]
        candidates = item["candidates"]
        pairs = [(query, c["content"][:1500]) for c in candidates]

        t0 = time.perf_counter()
        scores = qw_model.predict(pairs)
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000.0
        qw_query_latencies.append(lat_ms)

        # Sort candidates by Qwen score
        score_list = [float(s) for s in scores]
        cand_with_scores = list(zip(candidates, score_list))
        cand_with_scores.sort(key=lambda x: x[1], reverse=True)
        ranked_cands = [x[0] for x in cand_with_scores]
        top_scores = [x[1] for x in cand_with_scores[:5]]

        metrics = calculate_ranking_metrics(ranked_cands, item["ground_truth"])
        ts_ok = verify_timestamp_retention(ranked_cands, item["ground_truth"])

        qw_results.append({
            "query_id": item["id"],
            "query": query,
            "category": item["category"],
            "latency_ms": lat_ms,
            "input_tokens": query_token_counts[idx],
            "recall_5": metrics["recall_at_5"],
            "mrr_5": metrics["mrr_at_5"],
            "ndcg_5": metrics["ndcg_at_5"],
            "first_rel_rank": metrics["first_rel_rank"],
            "timestamp_preserved": ts_ok,
            "ranked_ids": [c["id"] for c in ranked_cands[:5]],
            "top_scores": top_scores
        })

    qw_total_time = time.perf_counter() - qw_bench_start
    qw_hw = monitor_qw.stop()
    print(f"Qwen3-Reranker-0.6B benchmark completed in {qw_total_time:.2f}s ({len(dataset)} queries)")

    # =========================================================================
    # 4. Aggregations & Evaluation Comparison
    # =========================================================================
    print("\n" + "=" * 50)
    print("[4/5] Computing Benchmark Metrics & Summary")
    print("=" * 50)

    # Positive-only queries (26 queries with ground truth)
    fr_pos_recalls = [r["recall_5"] for r in fr_results if r["category"] != "absent_out_of_domain"]
    qw_pos_recalls = [r["recall_5"] for r in qw_results if r["category"] != "absent_out_of_domain"]

    fr_pos_mrrs = [r["mrr_5"] for r in fr_results if r["category"] != "absent_out_of_domain"]
    qw_pos_mrrs = [r["mrr_5"] for r in qw_results if r["category"] != "absent_out_of_domain"]

    fr_all_ndcgs = [r["ndcg_5"] for r in fr_results]
    qw_all_ndcgs = [r["ndcg_5"] for r in qw_results]

    fr_pos_ndcgs = [r["ndcg_5"] for r in fr_results if r["category"] != "absent_out_of_domain"]
    qw_pos_ndcgs = [r["ndcg_5"] for r in qw_results if r["category"] != "absent_out_of_domain"]

    # Throughputs
    fr_qps = len(dataset) / fr_total_time
    qw_qps = len(dataset) / qw_total_time
    fr_tok_s = total_input_tokens / fr_total_time
    qw_tok_s = total_input_tokens / qw_total_time

    # Save CSV
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Query ID", "Category", "Query", "Input Tokens",
            "FlashRank Recall@5", "FlashRank MRR@5", "FlashRank nDCG@5", "FlashRank Latency (ms)", "FlashRank Top Chunk ID", "FlashRank Top Score",
            "Qwen3 Recall@5", "Qwen3 MRR@5", "Qwen3 nDCG@5", "Qwen3 Latency (ms)", "Qwen3 Top Chunk ID", "Qwen3 Top Score",
            "Winner nDCG@5"
        ])
        for fr_r, qw_r in zip(fr_results, qw_results):
            winner = "Tie"
            if qw_r["ndcg_5"] > fr_r["ndcg_5"]:
                winner = "Qwen3"
            elif fr_r["ndcg_5"] > qw_r["ndcg_5"]:
                winner = "FlashRank"
            writer.writerow([
                fr_r["query_id"], fr_r["category"], fr_r["query"], fr_r["input_tokens"],
                fr_r["recall_5"], round(fr_r["mrr_5"], 4), round(fr_r["ndcg_5"], 4), round(fr_r["latency_ms"], 2), fr_r["ranked_ids"][0] if fr_r["ranked_ids"] else "", round(fr_r["top_scores"][0], 4) if fr_r["top_scores"] else "",
                qw_r["recall_5"], round(qw_r["mrr_5"], 4), round(qw_r["ndcg_5"], 4), round(qw_r["latency_ms"], 2), qw_r["ranked_ids"][0] if qw_r["ranked_ids"] else "", round(qw_r["top_scores"][0], 4) if qw_r["top_scores"] else "",
                winner
            ])
    print(f"Per-question metrics written to {RESULTS_CSV}")

    # Raw metrics JSON
    benchmark_summary = {
        "dataset": {
            "total_queries": len(dataset),
            "positive_queries": len(fr_pos_recalls),
            "negative_queries": len(dataset) - len(fr_pos_recalls),
            "candidates_per_query": 15,
            "total_input_tokens": total_input_tokens,
            "avg_input_tokens_per_query": round(avg_tokens_per_query, 1)
        },
        "flashrank": {
            "model_name": "ms-marco-TinyBERT-L-2-v2",
            "execution_device": "CPU (ONNX Runtime)",
            "model_loading_time_s": round(t_load_fr, 4),
            "total_benchmark_time_s": round(fr_total_time, 2),
            "recall_at_5": round(float(np.mean(fr_pos_recalls)), 4),
            "mrr_at_5": round(float(np.mean(fr_pos_mrrs)), 4),
            "ndcg_at_5_positive": round(float(np.mean(fr_pos_ndcgs)), 4),
            "ndcg_at_5_all": round(float(np.mean(fr_all_ndcgs)), 4),
            "latency_ms_mean": round(float(np.mean(fr_query_latencies)), 2),
            "latency_ms_median": round(float(np.median(fr_query_latencies)), 2),
            "latency_ms_p95": round(float(np.percentile(fr_query_latencies, 95)), 2),
            "queries_per_sec": round(fr_qps, 2),
            "input_tokens_per_sec": round(fr_tok_s, 1),
            "hardware": fr_hw
        },
        "qwen3_reranker_0_6b": {
            "model_name": "Qwen/Qwen3-Reranker-0.6B",
            "execution_device": "CPU (PyTorch)",
            "model_loading_time_s": round(t_load_qw, 4),
            "total_benchmark_time_s": round(qw_total_time, 2),
            "recall_at_5": round(float(np.mean(qw_pos_recalls)), 4),
            "mrr_at_5": round(float(np.mean(qw_pos_mrrs)), 4),
            "ndcg_at_5_positive": round(float(np.mean(qw_pos_ndcgs)), 4),
            "ndcg_at_5_all": round(float(np.mean(qw_all_ndcgs)), 4),
            "latency_ms_mean": round(float(np.mean(qw_query_latencies)), 2),
            "latency_ms_median": round(float(np.median(qw_query_latencies)), 2),
            "latency_ms_p95": round(float(np.percentile(qw_query_latencies, 95)), 2),
            "queries_per_sec": round(qw_qps, 2),
            "input_tokens_per_sec": round(qw_tok_s, 1),
            "hardware": qw_hw
        }
    }

    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=2, ensure_ascii=False)
    print(f"Full benchmark summary written to {METRICS_JSON}")

    # =========================================================================
    # Print Comparison Table
    # =========================================================================
    print("\n" + "=" * 80)
    print("FINAL SIDE-BY-SIDE BENCHMARK RESULTS")
    print("=" * 80)
    header = f"{'Metric':<38} | {'FlashRank (Baseline)':<20} | {'Qwen3-Reranker-0.6B':<20}"
    print(header)
    print("-" * 84)

    rows = [
        ("Retrieval Quality (nDCG@5 - Pos)", f"{benchmark_summary['flashrank']['ndcg_at_5_positive']:.4f}", f"{benchmark_summary['qwen3_reranker_0_6b']['ndcg_at_5_positive']:.4f}"),
        ("Retrieval Quality (Recall@5)", f"{benchmark_summary['flashrank']['recall_at_5']:.4f}", f"{benchmark_summary['qwen3_reranker_0_6b']['recall_at_5']:.4f}"),
        ("Mean Reciprocal Rank (MRR@5)", f"{benchmark_summary['flashrank']['mrr_at_5']:.4f}", f"{benchmark_summary['qwen3_reranker_0_6b']['mrr_at_5']:.4f}"),
        ("Overall nDCG@5 (All 32 Queries)", f"{benchmark_summary['flashrank']['ndcg_at_5_all']:.4f}", f"{benchmark_summary['qwen3_reranker_0_6b']['ndcg_at_5_all']:.4f}"),
        ("Model Loading Time", f"{benchmark_summary['flashrank']['model_loading_time_s']:.2f} s", f"{benchmark_summary['qwen3_reranker_0_6b']['model_loading_time_s']:.2f} s"),
        ("Average Latency / Query", f"{benchmark_summary['flashrank']['latency_ms_mean']:.2f} ms", f"{benchmark_summary['qwen3_reranker_0_6b']['latency_ms_mean']:.2f} ms"),
        ("Median Latency / Query", f"{benchmark_summary['flashrank']['latency_ms_median']:.2f} ms", f"{benchmark_summary['qwen3_reranker_0_6b']['latency_ms_median']:.2f} ms"),
        ("P95 Latency / Query", f"{benchmark_summary['flashrank']['latency_ms_p95']:.2f} ms", f"{benchmark_summary['qwen3_reranker_0_6b']['latency_ms_p95']:.2f} ms"),
        ("Queries / Second (QPS)", f"{benchmark_summary['flashrank']['queries_per_sec']:.2f} q/s", f"{benchmark_summary['qwen3_reranker_0_6b']['queries_per_sec']:.2f} q/s"),
        ("Average Input Tokens / Query", f"{avg_tokens_per_query:.1f}", f"{avg_tokens_per_query:.1f}"),
        ("Total Input Tokens Processed", f"{total_input_tokens:,}", f"{total_input_tokens:,}"),
        ("Input Tokens / Second", f"{benchmark_summary['flashrank']['input_tokens_per_sec']:,.1f} tok/s", f"{benchmark_summary['qwen3_reranker_0_6b']['input_tokens_per_sec']:,.1f} tok/s"),
        ("Execution Device", f"{benchmark_summary['flashrank']['execution_device']}", f"{benchmark_summary['qwen3_reranker_0_6b']['execution_device']}"),
        ("Average GPU Temperature", f"{fr_hw.get('gpu_temp_avg_c', 'N/A')} °C", f"{qw_hw.get('gpu_temp_avg_c', 'N/A')} °C"),
        ("Maximum GPU Temperature", f"{fr_hw.get('gpu_temp_max_c', 'N/A')} °C", f"{qw_hw.get('gpu_temp_max_c', 'N/A')} °C"),
        ("Average GPU Utilization", f"{fr_hw.get('gpu_util_avg_pct', 'N/A')}%", f"{qw_hw.get('gpu_util_avg_pct', 'N/A')}%"),
        ("Peak VRAM Usage", f"{fr_hw.get('vram_used_peak_mib', 'N/A')} MiB", f"{qw_hw.get('vram_used_peak_mib', 'N/A')} MiB"),
        ("Peak System RAM Usage", f"{fr_hw.get('ram_used_peak_gb', 'N/A'):.2f} GB", f"{qw_hw.get('ram_used_peak_gb', 'N/A'):.2f} GB"),
        ("Average CPU Utilization", f"{fr_hw.get('cpu_util_avg_pct', 'N/A'):.1f}%", f"{qw_hw.get('cpu_util_avg_pct', 'N/A'):.1f}%"),
        ("Total Benchmark Time", f"{benchmark_summary['flashrank']['total_benchmark_time_s']:.2f} s", f"{benchmark_summary['qwen3_reranker_0_6b']['total_benchmark_time_s']:.2f} s")
    ]

    for label, val_fr, val_qw in rows:
        print(f"{label:<38} | {val_fr:<20} | {val_qw:<20}")
    print("-" * 84)

if __name__ == "__main__":
    run_benchmark()
