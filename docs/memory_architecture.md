# Three-Tier Memory Architecture

SynapseTutor separates memory into three distinct architectural tiers to prevent vector store pollution while ensuring cross-session cognitive continuity:

```
┌────────────────────────────────────────────────────────────────┐
│                   THREE-TIER MEMORY ENGINE                     │
└────────────────────────────────────────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
1. SHORT-TERM MEMORY    2. LONG-TERM MEMORY     3. EPISODIC MEMORY
   (Session Working)       (Relational Profile)    (Learning Events)
   • Active topic          • Concept masteries     • Misconceptions
   • Current goal          • Behavioral traits     • Breakthroughs
   • Recent 6 turns        • Strengths/weaknesses  • Pedagogical log
```

## Tier 1: Short-Term Memory (Working Context)
- **Scope**: Single conversation session.
- **Storage**: In-memory session manager.
- **Data**: Active concept, immediate question, sliding window of 6 most recent dialogue turns.

## Tier 2: Long-Term Memory (Persistent Profile)
- **Scope**: Cross-session and lifelong.
- **Storage**: Relational SQLite database (`learner_profiles`, `topic_mastery`).
- **Data**:
  - Fine-grained Bayesian Knowledge Tracing parameters for every concept.
  - Non-sensitive **Learning Behavior Profile** (e.g. `prefers_examples_before_theory`, `explanation_preference`).

## Tier 3: Episodic Memory (Critical Learning Moments)
- **Scope**: Cross-session semantic event stream.
- **Storage**: SQLite `episodic_memories` table with semantic tagging.
- **Data Structure**:
  ```json
  {
    "student_id": "default-student",
    "topic": "Deadlocks",
    "concept": "Circular Wait",
    "event_type": "misconception_resolved",
    "evidence": "Confused Circular Wait with Hold & Wait; resolved after Resource Allocation Graph cycle analogy.",
    "result": "improved",
    "timestamp": "2026-10-05T10:15:00Z"
  }
  ```
- **Usage**: When a student revisits a topic in a new conversation weeks later, the system retrieves relevant episodes to avoid repeating past mistakes.
