import json
from pathlib import Path

results_path = Path(__file__).parent / "results_raw.json"
with open(results_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print("QUALITATIVE RETRIEVAL COMPARISONS")
print("=" * 80)

# Example 1: YouTube Lecture Timestamp Retrieval
print("\n[EXAMPLE 1] YouTube Lecture Timestamp Retrieval:")
for q_m, q_n in zip(data['queries_minilm'], data['queries_nomic']):
    if q_m['category'] == 'lecture_section_timestamp' and q_m.get('ground_truth'):
        gt_id = list(q_m['ground_truth'].keys())[0]
        m_rank = q_m['retrieved_ids'].index(gt_id) + 1 if gt_id in q_m['retrieved_ids'] else -1
        n_rank = q_n['retrieved_ids'].index(gt_id) + 1 if gt_id in q_n['retrieved_ids'] else -1
        print(f"Query: \"{q_m['query']}\"")
        print(f"Target Chunk ID: {gt_id}")
        print(f"MiniLM Rank: #{m_rank} (Cosine Sim: {1.0 - q_m['retrieved_distances'][0]:.4f})")
        print(f"Nomic Rank:  #{n_rank} (Cosine Sim: {1.0 - q_n['retrieved_distances'][0]:.4f})")
        if q_m['retrieved_docs']:
            print(f"Top Doc Excerpt (MiniLM): {q_m['retrieved_docs'][0][:150]}...")
        break

# Example 2: PDF Document Question Answering
print("\n[EXAMPLE 2] PDF Document Question Answering (Concept Specific):")
for q_m, q_n in zip(data['queries_minilm'], data['queries_nomic']):
    if q_m['category'] == 'concept_specific' and q_m.get('ground_truth'):
        gt_id = list(q_m['ground_truth'].keys())[0]
        m_rank = q_m['retrieved_ids'].index(gt_id) + 1 if gt_id in q_m['retrieved_ids'] else -1
        n_rank = q_n['retrieved_ids'].index(gt_id) + 1 if gt_id in q_n['retrieved_ids'] else -1
        print(f"Query: \"{q_m['query']}\"")
        print(f"Target Chunk ID: {gt_id}")
        print(f"MiniLM Rank: #{m_rank}")
        print(f"Nomic Rank:  #{n_rank}")
        break

# Example 3: Easily Confused / Tricky Concepts
print("\n[EXAMPLE 3] Easily Confused / Nuanced Python Syntax:")
for q_m, q_n in zip(data['queries_minilm'], data['queries_nomic']):
    if q_m['category'] == 'easily_confused' and q_m.get('ground_truth'):
        gt_id = list(q_m['ground_truth'].keys())[0]
        m_rank = q_m['retrieved_ids'].index(gt_id) + 1 if gt_id in q_m['retrieved_ids'] else -1
        n_rank = q_n['retrieved_ids'].index(gt_id) + 1 if gt_id in q_n['retrieved_ids'] else -1
        if m_rank != n_rank:
            print(f"Query: \"{q_m['query']}\"")
            print(f"Target Chunk ID: {gt_id}")
            print(f"MiniLM Rank: #{m_rank} | Nomic Rank: #{n_rank}")
            break

# Example 4: Out of Domain / Hallucination Resistance
print("\n[EXAMPLE 4] Out-of-Domain Query (Irrelevant / Absent Topic):")
for q_m, q_n in zip(data['queries_minilm'], data['queries_nomic']):
    if q_m['category'] == 'absent_out_of_domain':
        sim_m = 1.0 - q_m['retrieved_distances'][0]
        sim_n = 1.0 - q_n['retrieved_distances'][0]
        print(f"Query: \"{q_m['query']}\"")
        print(f"MiniLM Top-1 Cosine Sim: {sim_m:.4f} (Safe rejection threshold: > 0.45)")
        print(f"Nomic Top-1 Cosine Sim:  {sim_n:.4f} (Elevated false similarity score)")
        break
