import json
import chromadb
from typing import List, Dict, Any

client = chromadb.PersistentClient(path='storage/db/chroma')
col = client.get_collection('course_knowledge_chunks')
all_raw = col.get()

chunks_by_id = {}
for i in range(len(all_raw['ids'])):
    cid = all_raw['ids'][i]
    chunks_by_id[cid] = {
        'id': cid,
        'content': all_raw['documents'][i],
        'metadata': all_raw['metadatas'][i]
    }

def get_candidates_for_query(query: str, ground_truth_ids: List[str], top_k: int = 15) -> List[Dict[str, Any]]:
    # Retrieve dense candidates from Chroma
    query_res = col.query(query_texts=[query], n_results=min(top_k + 5, len(chunks_by_id)))
    retrieved_ids = query_res['ids'][0] if query_res['ids'] else []

    final_ids = []
    # Ensure all ground truth IDs are present
    for g_id in ground_truth_ids:
        if g_id in chunks_by_id and g_id not in final_ids:
            final_ids.append(g_id)
            
    # Add retrieved candidates
    for r_id in retrieved_ids:
        if r_id not in final_ids and len(final_ids) < top_k:
            final_ids.append(r_id)
            
    # If still fewer than top_k, fill from collection
    for cid in chunks_by_id:
        if cid not in final_ids and len(final_ids) < top_k:
            final_ids.append(cid)
            
    return [chunks_by_id[cid] for cid in final_ids]

benchmark_queries = [
    # 1. CONCEPT SPECIFIC
    {
        "id": "Q01_CONCEPT",
        "category": "concept_specific",
        "query": "What built-in method replaces occurrences of a substring in a Python string?",
        "ground_truth": {"cf392f06-91de-419f-95db-5f417079c756": 2},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q02_CONCEPT",
        "category": "concept_specific",
        "query": "How does backpropagation update weights in a multilayer perceptron?",
        "ground_truth": {"b017ecc0-335e-4313-82b3-da43380e3e44": 2, "181c8d51-6b2c-494c-92ff-85da40aa8db3": 1},
        "target_sources": ["Module-2_DL .pptx"]
    },
    {
        "id": "Q03_CONCEPT",
        "category": "concept_specific",
        "query": "What is the XOR problem and why can't a single-layer perceptron solve it?",
        "ground_truth": {"665e7fb9-d0e1-49cd-9be3-2d0b08819232": 2, "579fe0ae-bf58-4e7e-8016-2701c14e2a1c": 1},
        "target_sources": ["Module-2_DL .pptx"]
    },
    {
        "id": "Q04_CONCEPT",
        "category": "concept_specific",
        "query": "What are augmented assignment operators in Python and how do you increment a variable?",
        "ground_truth": {"1d03ad35-3b14-44dc-b093-d9222acc6bd6": 2, "e84a8381-50eb-4fc0-b070-61b64e3e40e3": 1},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q05_CONCEPT",
        "category": "concept_specific",
        "query": "How do Python tuples differ from lists in terms of mutability and brackets?",
        "ground_truth": {"dd141f3a-8db9-42ec-9f49-4c7325023e9f": 2, "8ecd67f3-ea4c-4762-bc8c-f6e8ba5890cf": 1},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q06_CONCEPT",
        "category": "concept_specific",
        "query": "What does the range() function do in Python and how is it used in loops?",
        "ground_truth": {"4f77adda-4b87-45d8-b508-e71c70880ea6": 2, "65ede3bf-7fcc-4e57-a8b7-3ac378cf16a5": 1},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q07_CONCEPT",
        "category": "concept_specific",
        "query": "How does the greedy choice strategy work in the Knapsack problem?",
        "ground_truth": {"8cddcb08-c820-400a-9877-2eed41af1767": 2, "c7eeaad3-42df-48e6-a9e2-35873781e759": 1},
        "target_sources": ["Kna (Video)"]
    },

    # 2. EASILY CONFUSED
    {
        "id": "Q08_CONFUSED",
        "category": "easily_confused",
        "query": "What is the difference between single slash division and double slash integer division in Python?",
        "ground_truth": {"65c20a6e-d014-463a-9d3c-0764f723da8a": 2},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q09_CONFUSED",
        "category": "easily_confused",
        "query": "What is the difference between append and insert list methods in Python?",
        "ground_truth": {"de20a073-b876-43a9-a560-868e56c212d8": 2, "de2ea54c-4e63-4423-9032-7e90b80bd8d5": 1},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q10_CONFUSED",
        "category": "easily_confused",
        "query": "How does bias error compare to variance error in deep learning models?",
        "ground_truth": {"1fdfd8c3-e13c-48a1-9e93-e015e8559d0d": 2, "78ace3b7-98b0-47fe-b0b3-ac21e98b5e96": 1},
        "target_sources": ["Module-2_DL .pptx"]
    },
    {
        "id": "Q11_CONFUSED",
        "category": "easily_confused",
        "query": "In the Knapsack problem, how does sorting by maximum profit compare to sorting by profit-to-weight ratio?",
        "ground_truth": {"c7eeaad3-42df-48e6-a9e2-35873781e759": 2, "1bbf296e-1c67-48ea-850a-d6a60477bfcb": 1},
        "target_sources": ["Kna (Video)"]
    },
    {
        "id": "Q12_CONFUSED",
        "category": "easily_confused",
        "query": "What is the difference between comparison operator equal equal and assignment operator in Python?",
        "ground_truth": {"65c20a6e-d014-463a-9d3c-0764f723da8a": 1, "1d03ad35-3b14-44dc-b093-d9222acc6bd6": 1},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q13_CONFUSED",
        "category": "easily_confused",
        "query": "What is the distinction between L1 regularization and L2 weight decay in neural networks?",
        "ground_truth": {"181c8d51-6b2c-494c-92ff-85da40aa8db3": 2},
        "target_sources": ["Module-2_DL .pptx"]
    },
    {
        "id": "Q14_CONFUSED",
        "category": "easily_confused",
        "query": "How does a while loop with a condition counter differ from a for loop iterating over a range?",
        "ground_truth": {"4f77adda-4b87-45d8-b508-e71c70880ea6": 2},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },

    # 3. FORMULAS & DEFINITIONS
    {
        "id": "Q15_FORMULA",
        "category": "formula_definition",
        "query": "What is the mathematical definition and formula for Cosine Similarity between two vectors?",
        "ground_truth": {"789f3f89-a39d-42fd-9cda-7cb4e27be097": 2, "8d3d6d3c-5be9-4caf-bdfc-a702f0385fd3": 1},
        "target_sources": ["Module-1_DL.pdf"]
    },
    {
        "id": "Q16_FORMULA",
        "category": "formula_definition",
        "query": "What is the mathematical formulation of Profit and Weight ratio in the Knapsack problem?",
        "ground_truth": {"1bbf296e-1c67-48ea-850a-d6a60477bfcb": 2, "c7eeaad3-42df-48e6-a9e2-35873781e759": 1},
        "target_sources": ["Kna (Video)"]
    },
    {
        "id": "Q17_FORMULA",
        "category": "formula_definition",
        "query": "What is the mathematical formula for the Chain Rule of calculus in deep learning derivatives?",
        "ground_truth": {"ab81f06a-a985-4046-80b1-42a4b1d291f8": 2, "e726151d-4a64-402d-b4ac-cdd1b76e20b9": 1},
        "target_sources": ["Module-1_DL.pdf"]
    },
    {
        "id": "Q18_FORMULA",
        "category": "formula_definition",
        "query": "What is the mathematical definition and activation rule of a single Perceptron unit?",
        "ground_truth": {"579fe0ae-bf58-4e7e-8016-2701c14e2a1c": 2},
        "target_sources": ["Module-2_DL .pptx"]
    },
    {
        "id": "Q19_FORMULA",
        "category": "formula_definition",
        "query": "What is the rule of operator precedence in Python arithmetic operations?",
        "ground_truth": {"0967f452-5d2b-46c1-ba17-06fc1ab6b298": 2},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q20_FORMULA",
        "category": "formula_definition",
        "query": "What is the definition of a Tensor in Linear Algebra for deep learning?",
        "ground_truth": {"8d3d6d3c-5be9-4caf-bdfc-a702f0385fd3": 2},
        "target_sources": ["Module-1_DL.pdf"]
    },

    # 4. LECTURE SECTION & TIMESTAMP SPECIFIC
    {
        "id": "Q21_TIMESTAMP",
        "category": "lecture_section_timestamp",
        "query": "What does the teacher discuss at timestamp 00:30 regarding what you can do with Python?",
        "ground_truth": {"1a38a7d7-c3ad-4969-aa13-b89bd0957abe": 2},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q22_TIMESTAMP",
        "category": "lecture_section_timestamp",
        "query": "What happens around 01:14 where the instructor explains downloading Python from python.org?",
        "ground_truth": {"32ddf2b0-cc88-4976-b776-25778e9296cb": 2},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q23_TIMESTAMP",
        "category": "lecture_section_timestamp",
        "query": "What does the instructor demonstrate around 05:16 regarding the hello world program in the terminal?",
        "ground_truth": {"42c133a0-f318-40e1-9909-13e6379f4d8f": 2, "8aea1d2f-aaf5-4be8-ae3d-1f227bc26260": 1},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q24_TIMESTAMP",
        "category": "lecture_section_timestamp",
        "query": "What is explained around 24:43 to 25:14 regarding the exponent operator 10 to power of three?",
        "ground_truth": {"1d03ad35-3b14-44dc-b093-d9222acc6bd6": 2},
        "target_sources": ["YouTube Lecture (kqtD5dpn9C8) (Video)"]
    },
    {
        "id": "Q25_TIMESTAMP",
        "category": "lecture_section_timestamp",
        "query": "What profit and weight values (25, 24, 15 and 18, 15) are introduced at 00:50 in the Knapsack video?",
        "ground_truth": {"1bbf296e-1c67-48ea-850a-d6a60477bfcb": 2},
        "target_sources": ["Kna (Video)"]
    },
    {
        "id": "Q26_TIMESTAMP",
        "category": "lecture_section_timestamp",
        "query": "Where in the Knapsack lecture at 01:50 to 02:43 is sorting by profit versus weight first analyzed?",
        "ground_truth": {"c7eeaad3-42df-48e6-a9e2-35873781e759": 2},
        "target_sources": ["Kna (Video)"]
    },

    # 5. NEGATIVE / OUT-OF-DOMAIN / ANSWER ABSENT
    {
        "id": "Q27_ABSENT",
        "category": "absent_out_of_domain",
        "query": "How does Shor's quantum algorithm factor prime numbers in polynomial time using quantum Fourier transform?",
        "ground_truth": {},
        "target_sources": []
    },
    {
        "id": "Q28_ABSENT",
        "category": "absent_out_of_domain",
        "query": "How do Docker container layers interact with Kubernetes cgroups and containerd runtime?",
        "ground_truth": {},
        "target_sources": []
    },
    {
        "id": "Q29_ABSENT",
        "category": "absent_out_of_domain",
        "query": "What are React functional components and how does the useEffect hook handle clean up on unmount?",
        "ground_truth": {},
        "target_sources": []
    },
    {
        "id": "Q30_ABSENT",
        "category": "absent_out_of_domain",
        "query": "How does the Transformer multi-head self-attention projection matrix compute Queries, Keys, and Values?",
        "ground_truth": {},
        "target_sources": []
    },
    {
        "id": "Q31_ABSENT",
        "category": "absent_out_of_domain",
        "query": "What is the difference between SQL pessimistic locking and optimistic locking with MVCC timestamps?",
        "ground_truth": {},
        "target_sources": []
    },
    {
        "id": "Q32_ABSENT",
        "category": "absent_out_of_domain",
        "query": "How do you configure a Redis cluster with Sentinel master-slave replication and quorum elections?",
        "ground_truth": {},
        "target_sources": []
    }
]

dataset = []
for q in benchmark_queries:
    gt_ids = list(q["ground_truth"].keys())
    cands = get_candidates_for_query(q["query"], gt_ids, top_k=15)
    
    # Store candidate info
    item = {
        "id": q["id"],
        "category": q["category"],
        "query": q["query"],
        "target_sources": q["target_sources"],
        "ground_truth": q["ground_truth"],
        "candidates": cands
    }
    dataset.append(item)

with open("benchmark/dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)

print(f"Successfully generated benchmark dataset with {len(dataset)} queries in benchmark/dataset.json.")
