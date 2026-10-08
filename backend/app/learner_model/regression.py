import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from typing import Dict, Any

class LearningTimeRegressor:
    """
    ML Regressor (Gradient Boosting) predicting:
    1. Expected Quiz Score (0% - 100%)
    2. Estimated Learning Time (minutes) to reach target 80% mastery
    """

    def __init__(self):
        self.model_name = "learning_time_gbr"
        self.version = "1.1.0"
        self.score_model = GradientBoostingRegressor(n_estimators=30, random_state=42)
        self.time_model = GradientBoostingRegressor(n_estimators=30, random_state=42)
        self._bootstrap_models()

    def _bootstrap_models(self):
        """Train baseline regression models on pedagogical learning curves.
        Features: [current_mastery, target_mastery, concept_difficulty_num, prior_study_minutes, attempts_count]"""
        np.random.seed(42)
        X = []
        y_score = []
        y_time = []

        for _ in range(400):
            c_mast = np.random.uniform(0.1, 0.95)
            t_mast = np.random.uniform(0.7, 0.95)
            diff = np.random.choice([1.0, 2.0, 3.0]) # easy=1, med=2, hard=3
            prior_min = np.random.uniform(5, 120)
            attempts = np.random.randint(1, 15)

            # Expected score correlates with current mastery and inversely with difficulty
            score = (c_mast * 100.0) - (diff * 5.0) + np.random.normal(0, 5)
            score = max(10.0, min(100.0, score))

            # Expected time to bridge mastery gap
            gap = max(0.05, t_mast - c_mast)
            base_time = gap * 40.0 * diff + np.random.normal(0, 4)
            time_min = max(3.0, base_time)

            X.append([c_mast, t_mast, diff, prior_min, attempts])
            y_score.append(score)
            y_time.append(time_min)

        self.score_model.fit(np.array(X), np.array(y_score))
        self.time_model.fit(np.array(X), np.array(y_time))

    def predict(
        self,
        current_mastery: float,
        target_mastery: float = 0.80,
        difficulty: str = "medium",
        prior_study_minutes: float = 20.0,
        attempts_count: int = 3
    ) -> Dict[str, Any]:
        diff_num = {"easy": 1.0, "medium": 2.0, "hard": 3.0}.get(difficulty.lower(), 2.0)
        features = [current_mastery, target_mastery, diff_num, prior_study_minutes, attempts_count]

        pred_score = float(self.score_model.predict([features])[0])
        pred_time = float(self.time_model.predict([features])[0])

        return {
            "predicted_quiz_score": round(max(0.0, min(100.0, pred_score)), 1),
            "estimated_minutes_to_target": round(max(2.0, pred_time), 1),
            "target_mastery": target_mastery,
            "features_used": {
                "current_mastery": current_mastery,
                "target_mastery": target_mastery,
                "difficulty": difficulty,
                "prior_study_minutes": prior_study_minutes,
                "attempts": attempts_count
            },
            "model_name": self.model_name,
            "model_version": self.version
        }

learning_time_regressor = LearningTimeRegressor()
