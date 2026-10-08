import numpy as np
from sklearn.ensemble import RandomForestClassifier
from typing import Dict, Any, List

class LearnerReadinessClassifier:
    """
    ML Classifier (Random Forest) predicting whether a student is:
    - 'ready_for_next': Mastered prerequisites, ready to advance.
    - 'needs_practice': Partially understands, needs reinforcement problems.
    - 'needs_prerequisite_review': Foundational prerequisite gap detected.
    """

    def __init__(self):
        self.model_name = "learner_readiness_rf"
        self.version = "1.2.0"
        self.classes = ["needs_prerequisite_review", "needs_practice", "ready_for_next"]
        self.model = RandomForestClassifier(n_estimators=30, random_state=42, max_depth=5)
        self._bootstrap_model()

    def _bootstrap_model(self):
        """Train baseline pedagogical readiness model on feature space:
        [current_mastery, prereq_mastery, accuracy_rate, avg_time_per_q, slip_rate]"""
        np.random.seed(42)
        X = []
        y = []

        # Synthetic pedagogical ground truth distribution
        for _ in range(300):
            # Cluster 0: Prerequisite gap
            c_mast = np.random.uniform(0.1, 0.45)
            p_mast = np.random.uniform(0.1, 0.5)
            acc = np.random.uniform(0.1, 0.4)
            time_q = np.random.uniform(60, 180)
            slip = np.random.uniform(0.1, 0.3)
            X.append([c_mast, p_mast, acc, time_q, slip])
            y.append(0) # needs_prerequisite_review

            # Cluster 1: Needs practice
            c_mast = np.random.uniform(0.45, 0.75)
            p_mast = np.random.uniform(0.6, 0.9)
            acc = np.random.uniform(0.5, 0.75)
            time_q = np.random.uniform(40, 100)
            slip = np.random.uniform(0.05, 0.2)
            X.append([c_mast, p_mast, acc, time_q, slip])
            y.append(1) # needs_practice

            # Cluster 2: Ready for next
            c_mast = np.random.uniform(0.75, 0.98)
            p_mast = np.random.uniform(0.75, 1.0)
            acc = np.random.uniform(0.8, 1.0)
            time_q = np.random.uniform(20, 50)
            slip = np.random.uniform(0.01, 0.1)
            X.append([c_mast, p_mast, acc, time_q, slip])
            y.append(2) # ready_for_next

        self.model.fit(np.array(X), np.array(y))

    def predict_readiness(
        self,
        current_mastery: float,
        prereq_mastery: float,
        accuracy_rate: float,
        avg_time_per_q_seconds: float = 45.0,
        slip_rate: float = 0.1
    ) -> Dict[str, Any]:
        """Runs classification and returns predicted readiness state with class probabilities."""
        features = [current_mastery, prereq_mastery, accuracy_rate, avg_time_per_q_seconds, slip_rate]
        probs = self.model.predict_proba([features])[0]
        pred_idx = int(np.argmax(probs))
        pred_label = self.classes[pred_idx]

        return {
            "prediction": pred_label,
            "confidence": round(float(probs[pred_idx]), 3),
            "class_probabilities": {
                self.classes[i]: round(float(probs[i]), 3) for i in range(len(self.classes))
            },
            "features_used": {
                "current_mastery": current_mastery,
                "prereq_mastery": prereq_mastery,
                "accuracy_rate": accuracy_rate,
                "avg_time_seconds": avg_time_per_q_seconds,
                "slip_rate": slip_rate
            },
            "model_name": self.model_name,
            "model_version": self.version
        }

readiness_classifier = LearnerReadinessClassifier()
