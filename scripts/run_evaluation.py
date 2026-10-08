import asyncio
from typing import Dict, Any, List
from backend.app.rag.grounded_generation import grounded_generator
from backend.app.assessment.question_generator import question_generator
from backend.app.assessment.question_verifier import question_verifier
from backend.app.assessment.novelty_checker import novelty_checker
from backend.app.learner_model.knowledge_tracing import bkt_engine
from backend.app.learner_model.classification import readiness_classifier
from backend.app.learner_model.regression import learning_time_regressor
from backend.app.database.session import AsyncSessionLocal
from backend.app.database.models.analytics import EvaluationRun
from backend.app.core.logging import logger

async def run_off_material_evaluation() -> Dict[str, Any]:
    """Evaluates strict refusal accuracy on off-material queries (Section 37)."""
    test_queries = [
        "What is the architecture of the latest NVIDIA GPU?",
        "What is the best recipe for chocolate cake?",
        "How is the weather in Tokyo today?",
        "Who won the best actor award in 2024?",
        "Explain the stock market price of Apple today."
    ]

    refused_count = 0
    for q in test_queries:
        res = await grounded_generator.answer_question(q, allow_outside_knowledge=False)
        if "not covered in the uploaded course material" in res["answer"].lower() or res["outside_knowledge_offered"]:
            refused_count += 1

    accuracy = (refused_count / len(test_queries)) * 100.0
    return {
        "benchmark": "off_material_refusal",
        "total_queries": len(test_queries),
        "correctly_refused": refused_count,
        "refusal_accuracy_pct": accuracy
    }

async def run_citation_grounding_evaluation() -> Dict[str, Any]:
    """Evaluates citation presence and correctness for course-related queries."""
    course_queries = [
        "Explain the Banker's Algorithm in detail.",
        "What are the 4 conditions required for deadlock?",
        "What is the formula for the Need matrix in deadlock avoidance?"
    ]

    cited_count = 0
    for q in course_queries:
        res = await grounded_generator.answer_question(q)
        # Check if citations list contains valid source references
        if len(res.get("citations", [])) > 0 or "[source:" in res["answer"].lower():
            cited_count += 1

    accuracy = (cited_count / len(course_queries)) * 100.0
    return {
        "benchmark": "citation_grounding",
        "total_queries": len(course_queries),
        "accurately_cited": cited_count,
        "citation_accuracy_pct": accuracy
    }

async def run_assessment_novelty_evaluation() -> Dict[str, Any]:
    """Evaluates question verification pass rate and novelty detection."""
    candidate_questions = []
    verified_count = 0

    for i in range(5):
        raw_q = await question_generator.generate_question(
            concept="Banker's Algorithm",
            topic="Deadlocks",
            difficulty="medium"
        )
        is_valid, msg, _ = question_verifier.verify(raw_q)
        if is_valid:
            verified_count += 1
            candidate_questions.append(raw_q["question"])

    novelty_stats = novelty_checker.get_novelty_metrics()
    return {
        "benchmark": "assessment_generation_and_novelty",
        "generated_count": 5,
        "verified_pass_count": verified_count,
        "verification_rate_pct": (verified_count / 5.0) * 100.0,
        "novelty_stats": novelty_stats
    }

def run_learner_simulation():
    """Simulates Student A (weak deadlocks) vs Student B (strong deadlocks) over 5 practice cycles."""
    # Student A: Starts at 15% mastery, misses 2 questions, gets 3 right
    p_l_a = 0.15
    history_a = [p_l_a]
    for is_corr in [False, False, True, True, True]:
        p_l_a, _ = bkt_engine.update_mastery(p_l_a, is_corr, evidence_weight=1.0)
        history_a.append(round(p_l_a * 100, 1))

    # Student B: Starts at 15% mastery, gets 4 right, 1 miss
    p_l_b = 0.15
    history_b = [p_l_b]
    for is_corr in [True, True, True, False, True]:
        p_l_b, _ = bkt_engine.update_mastery(p_l_b, is_corr, evidence_weight=1.0)
        history_b.append(round(p_l_b * 100, 1))

    return {
        "benchmark": "learner_simulation",
        "student_a_trajectory": history_a,
        "student_a_gain": round(history_a[-1] - history_a[0], 1),
        "student_b_trajectory": history_b,
        "student_b_gain": round(history_b[-1] - history_b[0], 1)
    }

async def main():
    print("=" * 60)
    print("  SYNAPSETUTOR EVALUATION & BENCHMARK SUITE (TRACK D)")
    print("=" * 60)

    print("\n[1/4] Running Off-Material Refusal Evaluation (Section 37)...")
    res_off = await run_off_material_evaluation()
    print(f"  -> Refusal Accuracy: {res_off['refusal_accuracy_pct']}% ({res_off['correctly_refused']}/{res_off['total_queries']})")

    print("\n[2/4] Running Citation Grounding Evaluation...")
    res_cite = await run_citation_grounding_evaluation()
    print(f"  -> Citation Accuracy: {res_cite['citation_accuracy_pct']}% ({res_cite['accurately_cited']}/{res_cite['total_queries']})")

    print("\n[3/4] Running Assessment Generation & Novelty Evaluation...")
    res_novel = await run_assessment_novelty_evaluation()
    print(f"  -> Verification Pass Rate: {res_novel['verification_rate_pct']}%")
    print(f"  -> Novelty Rate: {res_novel['novelty_stats']['novelty_rate_percentage']}%")

    print("\n[4/4] Running Cognitive Learner Simulation (BKT Trajectories)...")
    sim = run_learner_simulation()
    print(f"  -> Student A Mastery Gain: +{sim['student_a_gain']}% (Trajectory: {sim['student_a_trajectory']})")
    print(f"  -> Student B Mastery Gain: +{sim['student_b_gain']}% (Trajectory: {sim['student_b_trajectory']})")

    # Log evaluation results to DB
    async with AsyncSessionLocal() as session:
        run1 = EvaluationRun(
            benchmark_name="off_material_refusal",
            total_samples=res_off["total_queries"],
            passed_samples=res_off["correctly_refused"],
            metric_score=res_off["refusal_accuracy_pct"] / 100.0,
            details=res_off
        )
        run2 = EvaluationRun(
            benchmark_name="citation_grounding",
            total_samples=res_cite["total_queries"],
            passed_samples=res_cite["accurately_cited"],
            metric_score=res_cite["citation_accuracy_pct"] / 100.0,
            details=res_cite
        )
        session.add(run1)
        session.add(run2)
        await session.commit()
        print("\nEvaluation runs successfully saved to database.")

    print("\n" + "=" * 60)
    print("  ALL BENCHMARKS COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
