# Cognitive Learner Model & Knowledge Tracing

## 1. Bayesian Knowledge Tracing (BKT)

### Parameters
- $P(L_0) = 0.15$: Initial prior probability that a student knows the concept.
- $P(T) = 0.10$: Probability of acquiring the skill after an instructional step.
- $P(G) = 0.20$: Probability of guessing the correct answer without knowing.
- $P(S) = 0.10$: Probability of slipping (answering incorrectly despite knowing).

### Update Equations
Upon observing student evidence $E$:
- **If Correct ($E = 1$)**:
  $$P(L_t \mid E=1) = \frac{P(L_t) \cdot (1 - P(S))}{P(L_t) \cdot (1 - P(S)) + (1 - P(L_t)) \cdot P(G)}$$
- **If Incorrect ($E = 0$)**:
  $$P(L_t \mid E=0) = \frac{P(L_t) \cdot P(S)}{P(L_t) \cdot P(S) + (1 - P(L_t)) \cdot (1 - P(G))}$$

### Transition Step
$$P(L_{t+1}) = P(L_t \mid E) + (1 - P(L_t \mid E)) \cdot P(T)$$

### Evidence Weighting
- Formal Exam Question: weight = `1.0`
- Short Answer Exercise: weight = `0.7`
- Chat Dialogue Interaction: weight = `0.3`

### Asymptotic Confidence Function
Confidence scales with the number of observed interactions $n$:
$$C(n) = 1 - e^{-n / 5}$$

### Forgetting Model
Exponential half-life decay over inactive elapsed days $\Delta t$:
$$P(L) = P(L) \cdot 2^{-\Delta t / t_{\text{half}}}$$

---

## 2. Machine Learning Models (`scikit-learn`)

### A. Readiness Classifier (`RandomForestClassifier`)
- **Task**: Predicts student state:
  1. `ready_for_next`: Has mastered prerequisite concepts, ready to advance.
  2. `needs_practice`: Understands basics, needs reinforcement problems.
  3. `needs_prerequisite_review`: Foundational gap detected.
- **Features**: `[current_mastery, prereq_mastery, accuracy_rate, avg_time_per_q, slip_rate]`

### B. Learning Time Regressor (`GradientBoostingRegressor`)
- **Task**: Predicts expected test score (%) and estimated minutes to achieve 80% mastery.
- **Features**: `[current_mastery, target_mastery, difficulty_level, prior_study_minutes, attempts_count]`
