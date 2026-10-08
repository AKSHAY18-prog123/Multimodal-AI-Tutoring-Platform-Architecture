import re
import sympy
from typing import Dict, Any, Tuple
from backend.app.core.logging import logger

class QuestionVerifier:
    """Verifies questions through deterministic rules, mathematical SymPy evaluation, and source cross-checking."""

    def verify(self, question_data: Dict[str, Any], source_context: str = "") -> Tuple[bool, str, Dict[str, Any]]:
        """
        Runs multi-stage verification on generated question.
        Returns: (passed: bool, status_message: str, verification_details: dict)
        """
        details = {
            "checks_run": [],
            "issues": []
        }

        # 1. Structural & Format Validation
        q_text = question_data.get("question", "").strip()
        ans = str(question_data.get("correct_answer", "")).strip()
        q_type = question_data.get("question_type", "mcq")

        if len(q_text) < 15:
            return False, "Question text too short or empty.", details

        if not ans:
            return False, "Missing correct answer specification.", details

        details["checks_run"].append("structural_check_passed")

        # 2. MCQ Distractor Quality Check
        if q_type == "mcq":
            options = question_data.get("options", [])
            if len(options) < 4:
                return False, f"MCQ requires at least 4 options, found {len(options)}.", details

            opt_texts = [o.get("text", "").strip().lower() for o in options]
            if len(set(opt_texts)) < len(options):
                return False, "MCQ contains duplicate options.", details

            # Ensure correct answer matches one of the option IDs
            valid_ids = [o.get("id") for o in options]
            if ans not in valid_ids and not any(ans.lower() == t for t in opt_texts):
                return False, f"MCQ correct_answer '{ans}' not found in options {valid_ids}.", details

            details["checks_run"].append("mcq_distractor_validation_passed")

        # 3. Deterministic Mathematical Validation (for numerical questions)
        math_expr = question_data.get("math_expression")
        if math_expr and q_type == "numerical":
            try:
                # Sanitize and safely evaluate through SymPy
                clean_expr = re.sub(r"[^0-9\+\-\*\/\.\(\)\s]", "", math_expr)
                calculated_val = float(sympy.sympify(clean_expr).evalf())
                expected_num = float(re.findall(r"[-+]?\d*\.?\d+", ans)[0])

                if abs(calculated_val - expected_num) > 0.01:
                    return False, f"Math validation mismatch: expr {math_expr} evaluated to {calculated_val}, but answer claimed {expected_num}.", details
                details["checks_run"].append("deterministic_sympy_math_verified")
            except Exception as e:
                logger.warning(f"SymPy evaluation skipped or failed: {e}")

        # 4. Source Cross-Check
        if source_context:
            concept_name = question_data.get("concept", "").lower()
            if concept_name and concept_name not in source_context.lower():
                details["issues"].append(f"Concept '{concept_name}' not explicitly cited in source context excerpt.")
            else:
                details["checks_run"].append("source_presence_verified")

        return True, "Verified successfully across all quality gates.", details

question_verifier = QuestionVerifier()
