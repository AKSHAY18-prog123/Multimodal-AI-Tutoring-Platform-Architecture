import math
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

class BayesianKnowledgeTracing:
    """
    Standard Bayesian Knowledge Tracing (BKT) engine with evidence weighting,
    confidence scaling, and spaced-repetition forgetting decay.
    """

    def __init__(
        self,
        default_p_l0: float = 0.15, # Prior mastery for novice
        default_p_transit: float = 0.10, # Learning transition probability P(T)
        default_p_guess: float = 0.20, # Guess probability P(G)
        default_p_slip: float = 0.10, # Slip probability P(S)
    ):
        self.p_l0 = default_p_l0
        self.p_t = default_p_transit
        self.p_g = default_p_guess
        self.p_s = default_p_slip

    def update_mastery(
        self,
        current_p_l: float,
        is_correct: bool,
        evidence_weight: float = 1.0,
        p_transit: float = 0.10,
        p_guess: float = 0.20,
        p_slip: float = 0.10
    ) -> Tuple[float, float]:
        """
        Calculates updated mastery P(L_{t+1}) after observing an answer.
        evidence_weight: 1.0 for exam quiz, 0.7 for short answer, 0.3 for conversation.
        Returns: (new_mastery, delta)
        """
        p_l = max(0.01, min(0.99, current_p_l))

        # 1. Posterior calculation conditioned on evidence
        if is_correct:
            numerator = p_l * (1.0 - p_slip)
            denominator = numerator + ((1.0 - p_l) * p_guess)
            posterior = numerator / (denominator + 1e-9)
        else:
            numerator = p_l * p_slip
            denominator = numerator + ((1.0 - p_l) * (1.0 - p_guess))
            posterior = numerator / (denominator + 1e-9)

        # Apply evidence weighting (interpolate between prior and full posterior)
        weighted_posterior = p_l + (evidence_weight * (posterior - p_l))

        # 2. Knowledge acquisition / transition step
        # If incorrect, transition rate is lower; if correct, student has transitioned
        effective_p_t = p_transit * evidence_weight
        new_p_l = weighted_posterior + ((1.0 - weighted_posterior) * effective_p_t)
        new_p_l = max(0.05, min(0.98, new_p_l))

        delta = new_p_l - current_p_l
        return round(new_p_l, 4), round(delta, 4)

    def calculate_confidence(self, evidence_count: int) -> float:
        """
        Confidence in mastery estimate increases asymptotically with evidence count:
        C(n) = 1 - e^(-n / 5)
        n=0 -> 0.0, n=3 -> ~0.45, n=7 -> ~0.75, n=15 -> ~0.95
        """
        conf = 1.0 - math.exp(-max(0, evidence_count) / 5.0)
        return round(min(0.99, max(0.10, conf)), 3)

    def apply_forgetting_decay(
        self,
        current_p_l: float,
        last_interaction_time: datetime,
        half_life_days: float = 14.0
    ) -> Tuple[float, float]:
        """
        Ebbinghaus-style exponential decay over inactive days:
        P(L) = P(L) * 2^(-dt / half_life)
        Floor at novice baseline 0.15.
        """
        now = datetime.now(timezone.utc)
        if last_interaction_time.tzinfo is None:
            last_interaction_time = last_interaction_time.replace(tzinfo=timezone.utc)

        elapsed_days = max(0.0, (now - last_interaction_time).total_seconds() / 86400.0)
        if elapsed_days < 1.0:
            return current_p_l, 0.0

        decay_factor = math.pow(2.0, -elapsed_days / half_life_days)
        decayed_p_l = max(0.15, current_p_l * decay_factor)
        forgotten_amount = current_p_l - decayed_p_l

        return round(decayed_p_l, 4), round(forgotten_amount, 4)

bkt_engine = BayesianKnowledgeTracing()
