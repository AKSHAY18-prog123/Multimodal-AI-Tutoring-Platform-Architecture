# REST API Specification (v1)

Base URL: `http://localhost:8000/api/v1`

## Standard Envelope Format
All successful responses return:
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid-v4",
    "timestamp": "2026-10-05T12:00:00Z"
  },
  "error": null
}
```

All error responses return:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error description",
    "details": {}
  },
  "meta": {
    "request_id": "uuid-v4",
    "timestamp": "2026-10-05T12:00:00Z"
  }
}
```

---

## Endpoints

### 1. Users & Onboarding (First-Time Student Lifecycle)
- `GET /users/status?user_id={id}` — Detects if student profile exists in DB; returns `exists`, `onboarding_completed`, and profile metadata.
- `POST /users/onboard` — Onboards a first-time student with clean state (zero fake courses/mastery). Body: `{ name: string, email?: string }`.
- `GET /users/me` — Fetches current student profile.
- `GET /users` — Lists all registered students in the system.

### 2. Courses
- `POST /courses` — Create a new course.
- `GET /courses` — List all courses.
- `GET /courses/{course_id}` — Get course details with topics and concepts.
- `GET /courses/{course_id}/knowledge-graph` — Export concept nodes and prerequisite directed edges.

### 3. Documents & Multimodal Ingestion
- `POST /documents/upload` — Multipart upload for PDF, PPTX, Video (MP4/WebM), Audio, Images. Dispatches background worker.
- `GET /documents/{document_id}/status` — Poll background ingestion progress (0-100%) and stage (`extracting`, `vision_analysis`, `chunking`, `indexing`, `completed`).
- `GET /documents/course/{course_id}` — List all documents in a course.

### 4. Tutor & Multi-Chat
- `POST /chat/sessions` — Create a new conversation session.
- `GET /chat/sessions?user_id={id}` — List recent chat sessions (with pinning status).
- `GET /chat/sessions/{chat_id}` — Load message history.
- `PUT /chat/sessions/{chat_id}` — Rename or pin/unpin session.
- `DELETE /chat/sessions/{chat_id}` — Delete session.
- `POST /chat/sessions/{chat_id}/messages` — Send user question; returns grounded response, verified citations, and follow-ups.

### 5. Assessments
- `POST /assessments/generate` — Generate adaptive quiz based on BKT mastery weights or diagnostic baseline.
- `GET /assessments/{assessment_id}` — Retrieve assessment questions.
- `POST /assessments/{assessment_id}/submit` — Grade answers, update BKT mastery, and return diagnostic report.

### 6. Learner Modeling & Analytics
- `GET /learner/profile` — Retrieve status (`uncalibrated` vs `active`), mastery, and learning behavior profile.
- `GET /learner/mastery` — Topic and concept BKT mastery scores with confidence and evidence counts.
- `GET /learner/predictions` — Run scikit-learn Random Forest readiness classifier & GBR learning time regressor.
- `GET /learner/recommendations` — Personalized next learning actions.
- `GET /analytics/progress` — Mastery trajectory, study time allocation, and question novelty metrics.
- `GET /memory/relevant` — User-facing view of episodic learning events.
