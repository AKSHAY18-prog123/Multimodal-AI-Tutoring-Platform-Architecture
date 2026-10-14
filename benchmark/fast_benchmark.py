import os
import sys
import time
import json
import csv
import subprocess
import threading
from typing import List, Dict, Any
import numpy as np
import psutil

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

MODERNBERT_SNAPSHOT = r"C:\Users\surya\.cache\huggingface\hub\models--Alibaba-NLP--gte-reranker-modernbert-base\snapshots\f7481e6055501a30fb19d090657df9ec1f79ab2c"
QWEN_SNAPSHOT = r"C:\Users\surya\.cache\huggingface\hub\models--Qwen--Qwen3-Reranker-0.6B\snapshots\e61197ed45024b0ed8a2d74b80b4d909f1255473"
DATASET_PATH = "benchmark/dataset.json"
RESULTS_CSV = "benchmark/fast_benchmark_results.csv"

class HardwareMonitor:
    """Samples GPU (nvidia-smi) and System (psutil) metrics once per second."""
    def __init__(self, interval: float = 1.0):
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
            self.thread.join(timeout=1.5)
        self.samples.append(self._sample())
        if not self.samples:
            return {}
        
        gpu_temps = [s["gpu_temp_c"] for s in self.samples if s["gpu_temp_c"] is not None]
        vrams = [s["vram_mib"] for s in self.samples if s["vram_mib"] is not None]
        gpu_utils = [s["gpu_util_pct"] for s in self.samples if s["gpu_util_pct"] is not None]
        cpus = [s["cpu_pct"] for s in self.samples]
        rams = [s["ram_gb"] for s in self.samples]

        return {
            "peak_gpu_temp_c": max(gpu_temps) if gpu_temps else "N/A",
            "avg_gpu_temp_c": round(float(np.mean(gpu_temps)), 1) if gpu_temps else "N/A",
            "peak_vram_mib": max(vrams) if vrams else "N/A",
            "avg_gpu_util_pct": round(float(np.mean(gpu_utils)), 1) if gpu_utils else "N/A",
            "peak_ram_gb": round(max(rams), 2) if rams else "N/A",
            "avg_cpu_pct": round(float(np.mean(cpus)), 1) if cpus else "N/A"
        }

def calc_metrics(ranked_cands: List[Dict[str, Any]], ground_truth: Dict[str, int]) -> Dict[str, float]:
    if not ground_truth:
        return {"recall_5": 1.0, "mrr_5": 1.0, "ndcg_5": 1.0}
    top_5_ids = [c["id"] for c in ranked_cands[:5]]
    recall = 1.0 if any(cid in ground_truth for cid in top_5_ids) else 0.0
    
    first_rank = None
    for r, c in enumerate(ranked_cands[:5], 1):
        if c["id"] in ground_truth:
            first_rank = r
            break
    mrr = 1.0 / first_rank if first_rank else 0.0

    dcg = sum((2**ground_truth.get(c["id"], 0) - 1) / np.log2(i + 1) for i, c in enumerate(ranked_cands[:5], 1))
    ideal = sorted(ground_truth.values(), reverse=True)[:5]
    idcg = sum((2**r - 1) / np.log2(i + 1) for i, r in enumerate(ideal, 1))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    return {"recall_5": float(recall), "mrr_5": float(mrr), "ndcg_5": float(ndcg)}

def main():
    print("=" * 80)
    print("FAST BENCHMARK: FlashRank vs GTE-ModernBERT vs Qwen3-0.6B (10 Questions)")
    print("=" * 80)

    # 1. Select 10 Representative Questions
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    selected_ids = [
        "Q01_CONCEPT", "Q02_CONCEPT",
        "Q08_CONFUSED", "Q10_CONFUSED",
        "Q15_FORMULA", "Q16_FORMULA",
        "Q21_TIMESTAMP", "Q25_TIMESTAMP",
        "Q27_ABSENT", "Q29_ABSENT"
    ]
    dataset = [q for q in full_data if q["id"] in selected_ids]
    print(f"Loaded {len(dataset)} representative questions (15 candidates per question).")

    # Token counting
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODERNBERT_SNAPSHOT, local_files_only=True)
    query_tokens = []
    total_tokens = 0
    for q in dataset:
        q_cnt = 0
        for c in q["candidates"]:
            t_cnt = len(tok.encode(q["query"] + " " + c["content"][:1000]))
            q_cnt += t_cnt
        query_tokens.append(q_cnt)
        total_tokens += q_cnt
    print(f"Total benchmark input tokens: {total_tokens:,} (~{total_tokens/len(dataset):.0f} tokens/query)")

    # =========================================================================
    # MODEL 1: FlashRank (Baseline)
    # =========================================================================
    print("\n--- [1/3] Benchmarking FlashRank (Baseline) ---")
    from flashrank import Ranker, RerankRequest
    
    mon_fr = HardwareMonitor(interval=1.0)
    mon_fr.start()

    t0_load = time.perf_counter()
    fr_ranker = Ranker()
    load_fr = time.perf_counter() - t0_load

    # Warmup query
    _ = fr_ranker.rerank(RerankRequest(query="Warmup query", passages=[{"id": 0, "text": "Warmup chunk content"}]))

    fr_lats = []
    fr_results = []
    t_start_fr = time.perf_counter()

    for idx, item in enumerate(dataset):
        passages = [{"id": i, "text": c["content"][:1000]} for i, c in enumerate(item["candidates"])]
        t0 = time.perf_counter()
        fr_out = fr_ranker.rerank(RerankRequest(query=item["query"], passages=passages))
        lat = (time.perf_counter() - t0) * 1000.0
        fr_lats.append(lat)

        score_map = {p["id"]: float(p.get("score", 0.0)) for p in fr_out}
        ranked = sorted(item["candidates"], key=lambda c: score_map.get(item["candidates"].index(c), 0.0), reverse=True)
        m = calc_metrics(ranked, item["ground_truth"])
        fr_results.append({
            "id": item["id"], "query": item["query"], "category": item["category"],
            "lat_ms": lat, "recall_5": m["recall_5"], "mrr_5": m["mrr_5"], "ndcg_5": m["ndcg_5"],
            "top_chunk": ranked[0]["id"], "top_score": score_map.get(item["candidates"].index(ranked[0]), 0.0)
        })

    dur_fr = time.perf_counter() - t_start_fr
    hw_fr = mon_fr.stop()
    print(f"FlashRank finished in {dur_fr:.2f}s (Avg latency: {np.mean(fr_lats):.1f} ms)")

    time.sleep(2)

    # =========================================================================
    # MODEL 2: GTE-Reranker-ModernBERT-base (Candidate 1)
    # =========================================================================
    print("\n--- [2/3] Benchmarking GTE-Reranker-ModernBERT-base ---")
    from sentence_transformers import CrossEncoder

    mon_mb = HardwareMonitor(interval=1.0)
    mon_mb.start()

    t0_load = time.perf_counter()
    mb_model = CrossEncoder(MODERNBERT_SNAPSHOT, max_length=512, local_files_only=True)
    load_mb = time.perf_counter() - t0_load

    # Warmup query
    _ = mb_model.predict([("Warmup query", "Warmup chunk content")])

    mb_lats = []
    mb_results = []
    t_start_mb = time.perf_counter()

    for idx, item in enumerate(dataset):
        pairs = [(item["query"], c["content"][:1000]) for c in item["candidates"]]
        t0 = time.perf_counter()
        scores = mb_model.predict(pairs, batch_size=16)
        lat = (time.perf_counter() - t0) * 1000.0
        mb_lats.append(lat)

        score_list = [float(s) for s in scores]
        cand_scores = list(zip(item["candidates"], score_list))
        cand_scores.sort(key=lambda x: x[1], reverse=True)
        ranked = [x[0] for x in cand_scores]
        m = calc_metrics(ranked, item["ground_truth"])

        mb_results.append({
            "id": item["id"], "query": item["query"], "category": item["category"],
            "lat_ms": lat, "recall_5": m["recall_5"], "mrr_5": m["mrr_5"], "ndcg_5": m["ndcg_5"],
            "top_chunk": ranked[0]["id"], "top_score": cand_scores[0][1]
        })
        print(f"  Q{idx+1}/10 [{item['id']}]: {lat:.1f}ms | Recall@5={m['recall_5']} | nDCG@5={m['ndcg_5']:.3f}")

    dur_mb = time.perf_counter() - t_start_mb
    hw_mb = mon_mb.stop()
    print(f"GTE-ModernBERT finished in {dur_mb:.2f}s (Avg latency: {np.mean(mb_lats):.1f} ms)")

    time.sleep(2)

    # =========================================================================
    # MODEL 3: Qwen3-Reranker-0.6B (Candidate 2)
    # =========================================================================
    print("\n--- [3/3] Benchmarking Qwen3-Reranker-0.6B ---")
    mon_qw = HardwareMonitor(interval=1.0)
    mon_qw.start()

    t0_load = time.perf_counter()
    qw_model = CrossEncoder(QWEN_SNAPSHOT, max_length=256, local_files_only=True)
    load_qw = time.perf_counter() - t0_load

    # Warmup query
    _ = qw_model.predict([("Warmup query", "Warmup chunk content")])

    qw_lats = []
    qw_results = []
    t_start_qw = time.perf_counter()
    completed_qw = 0

    # 4.5-minute timeout guard
    for idx, item in enumerate(dataset):
        elapsed_now = time.perf_counter() - t_start_qw
        if elapsed_now > 240.0:  # Stop before 4m00s to respect strict 5m total target
            print(f"[TIMEOUT GUARD] Approaching 5-minute target ({elapsed_now:.1f}s elapsed). Stopping Qwen safely at {completed_qw}/10 queries.")
            break

        pairs = [(item["query"], c["content"][:1000]) for c in item["candidates"]]
        t0 = time.perf_counter()
        scores = qw_model.predict(pairs, batch_size=8)
        lat = (time.perf_counter() - t0) * 1000.0
        qw_lats.append(lat)

        score_list = [float(s) for s in scores]
        cand_scores = list(zip(item["candidates"], score_list))
        cand_scores.sort(key=lambda x: x[1], reverse=True)
        ranked = [x[0] for x in cand_scores]
        m = calc_metrics(ranked, item["ground_truth"])

        qw_results.append({
            "id": item["id"], "query": item["query"], "category": item["category"],
            "lat_ms": lat, "recall_5": m["recall_5"], "mrr_5": m["mrr_5"], "ndcg_5": m["ndcg_5"],
            "top_chunk": ranked[0]["id"], "top_score": cand_scores[0][1]
        })
        completed_qw += 1
        print(f"  Q{idx+1}/10 [{item['id']}]: {lat/1000:.1f}s | Recall@5={m['recall_5']} | nDCG@5={m['ndcg_5']:.3f}")

    dur_qw = time.perf_counter() - t_start_qw
    hw_qw = mon_qw.stop()
    print(f"Qwen3 completed {completed_qw} queries in {dur_qw:.2f}s (Avg latency: {np.mean(qw_lats)/1000:.1f}s)")

    # =========================================================================
    # Save CSV Results
    # =========================================================================
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Query ID", "Category", "Query",
            "FlashRank Recall@5", "FlashRank MRR@5", "FlashRank nDCG@5", "FlashRank Latency (ms)",
            "GTE-ModernBERT Recall@5", "GTE-ModernBERT MRR@5", "GTE-ModernBERT nDCG@5", "GTE-ModernBERT Latency (ms)",
            "Qwen3 Recall@5", "Qwen3 MRR@5", "Qwen3 nDCG@5", "Qwen3 Latency (ms)",
            "Winner nDCG@5"
        ])
        for idx in range(len(dataset)):
            fr_r = fr_results[idx]
            mb_r = mb_results[idx]
            qw_r = qw_results[idx] if idx < len(qw_results) else None

            # Determine winner between FR and ModernBERT
            if mb_r["ndcg_5"] > fr_r["ndcg_5"]:
                winner = "GTE-ModernBERT"
            elif fr_r["ndcg_5"] > mb_r["ndcg_5"]:
                winner = "FlashRank"
            else:
                winner = "Tie"

            writer.writerow([
                fr_r["id"], fr_r["category"], fr_r["query"],
                fr_r["recall_5"], round(fr_r["mrr_5"], 4), round(fr_r["ndcg_5"], 4), round(fr_r["lat_ms"], 2),
                mb_r["recall_5"], round(mb_r["mrr_5"], 4), round(mb_r["ndcg_5"], 4), round(mb_r["lat_ms"], 2),
                qw_r["recall_5"] if qw_r else "N/A",
                round(qw_r["mrr_5"], 4) if qw_r else "N/A",
                round(qw_r["ndcg_5"], 4) if qw_r else "N/A",
                round(qw_r["lat_ms"], 2) if qw_r else "N/A",
                winner
            ])
    print(f"\nSaved CSV results to {RESULTS_CSV}")

    # =========================================================================
    # Comparison Summary Table
    # =========================================================================
    pos_count = len([q for q in dataset if q["ground_truth"]])
    fr_rec = np.mean([r["recall_5"] for r in fr_results[:pos_count]])
    mb_rec = np.mean([r["recall_5"] for r in mb_results[:pos_count]])
    fr_mrr = np.mean([r["mrr_5"] for r in fr_results[:pos_count]])
    mb_mrr = np.mean([r["mrr_5"] for r in mb_results[:pos_count]])
    fr_ndcg = np.mean([r["ndcg_5"] for r in fr_results])
    mb_ndcg = np.mean([r["ndcg_5"] for r in mb_results])

    fr_tok_s = total_tokens / dur_fr
    mb_tok_s = total_tokens / dur_mb

    if qw_results:
        pos_qw = len([q for q in dataset[:completed_qw] if q["ground_truth"]])
        qw_rec = np.mean([r["recall_5"] for r in qw_results[:pos_qw]])
        qw_mrr = np.mean([r["mrr_5"] for r in qw_results[:pos_qw]])
        qw_ndcg = np.mean([r["ndcg_5"] for r in qw_results])
        qw_tok_s = (sum(query_tokens[:completed_qw])) / dur_qw
        qw_lat_str = f"{np.mean(qw_lats):.1f} ms ({np.mean(qw_lats)/1000:.1f}s)"
        qw_rec_str = f"{qw_rec:.4f}"
        qw_mrr_str = f"{qw_mrr:.4f}"
        qw_ndcg_str = f"{qw_ndcg:.4f}"
        qw_tok_s_str = f"{qw_tok_s:,.1f} tok/s"
        qw_dur_str = f"{dur_qw:.2f} s"
    else:
        qw_lat_str = "N/A"
        qw_rec_str = "N/A"
        qw_mrr_str = "N/A"
        qw_ndcg_str = "N/A"
        qw_tok_s_str = "N/A"
        qw_dur_str = "N/A"

    print("\n" + "=" * 98)
    print("CONCISE BENCHMARK COMPARISON TABLE (FlashRank vs GTE-ModernBERT vs Qwen3-0.6B)")
    print("=" * 98)
    print(f"{'Metric':<32} | {'FlashRank (Baseline)':<20} | {'GTE-ModernBERT':<18} | {'Qwen3-Reranker-0.6B':<20}")
    print("-" * 98)
    rows = [
        ("Retrieval Quality (nDCG@5)", f"{fr_ndcg:.4f}", f"{mb_ndcg:.4f}", qw_ndcg_str),
        ("Recall@5 (Targeted Queries)", f"{fr_rec:.4f}", f"{mb_rec:.4f}", qw_rec_str),
        ("MRR@5 (Targeted Queries)", f"{fr_mrr:.4f}", f"{mb_mrr:.4f}", qw_mrr_str),
        ("Average Latency / Query", f"{np.mean(fr_lats):.2f} ms", f"{np.mean(mb_lats):.2f} ms", qw_lat_str),
        ("Total Benchmark Runtime", f"{dur_fr:.2f} s", f"{dur_mb:.2f} s", qw_dur_str),
        ("Model Load Time", f"{load_fr:.4f} s", f"{load_mb:.4f} s", f"{load_qw:.4f} s"),
        ("Input Tokens / Second", f"{fr_tok_s:,.1f} tok/s", f"{mb_tok_s:,.1f} tok/s", qw_tok_s_str),
        ("Execution Engine", "ONNX Runtime (CPU)", "PyTorch (CPU)", "PyTorch (CPU)"),
        ("Model Size / Params", "4.4M (ms-marco-TinyBERT)", "149M (ModernBERT-base)", "596M (Qwen3-0.6B)"),
        ("Peak GPU Temperature", f"{hw_fr.get('peak_gpu_temp_c')} °C", f"{hw_mb.get('peak_gpu_temp_c')} °C", f"{hw_qw.get('peak_gpu_temp_c')} °C"),
        ("Peak VRAM Usage", f"{hw_fr.get('peak_vram_mib')} MiB", f"{hw_mb.get('peak_vram_mib')} MiB", f"{hw_qw.get('peak_vram_mib')} MiB"),
        ("Peak System RAM", f"{hw_fr.get('peak_ram_gb')} GB", f"{hw_mb.get('peak_ram_gb')} GB", f"{hw_qw.get('peak_ram_gb')} GB"),
        ("Average CPU Utilization", f"{hw_fr.get('avg_cpu_pct')}%", f"{hw_mb.get('avg_cpu_pct')}%", f"{hw_qw.get('avg_cpu_pct')}%")
    ]
    for m_label, fr_val, mb_val, qw_val in rows:
        print(f"{m_label:<32} | {fr_val:<20} | {mb_val:<18} | {qw_val:<20}")
    print("=" * 98)

if __name__ == "__main__":
    main()
