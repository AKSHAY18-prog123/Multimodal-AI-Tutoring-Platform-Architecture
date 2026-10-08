# SynapseTutor Frontend

Modern, high-performance UI built with **React 19**, **TypeScript**, and **Tailwind CSS**, designed for the Multimodal Adaptive Tutoring Platform (Track D).

---

## 🏗️ Architecture & Component Hierarchy

```
frontend/src/
├── components/
│   ├── layout/
│   │   └── Navbar.tsx               # Top navigation bar, learner identity indicator, connection state
│   ├── onboarding/
│   │   └── OnboardingModal.tsx       # First-visit learner identification modal ("What should we call you?")
│   ├── courses/
│   │   └── CreateCourseModal.tsx     # Dynamic course creation & multimodal upload (PDF, PPTX, MP4, images)
│   └── sources/
│       └── SourceViewerDrawer.tsx    # Slide-over citation viewer with canonical source anchoring
├── pages/
│   ├── Dashboard/
│   │   └── Dashboard.tsx             # Learner home, quick-actions, zero-data empty state, active recommendations
│   ├── Tutor/
│   │   └── Tutor.tsx                 # Multi-session conversational AI tutor with grounded citations
│   ├── Assessments/
│   │   └── Assessments.tsx           # Adaptive quizzes, novelty checks, SymPy verified questions, diagnostic mode
│   ├── KnowledgeExplorer/
│   │   └── KnowledgeExplorer.tsx     # Prerequisite DAG graph, concept discovery, mastery overlays
│   ├── Courses/
│   │   └── Courses.tsx               # Course library, uploaded document inspection, ingestion status tracking
│   ├── LearnerProfile/
│   │   └── LearnerProfile.tsx        # BKT mastery distributions, ML readiness classification & time prediction
│   └── Analytics/
│       └── Analytics.tsx             # Learning velocity, score histories, pedagogical feedback submission
├── services/
│   └── api.ts                        # Centralized Axios API client with active learner identification headers
├── types/
│   └── index.ts                      # Full TypeScript interfaces for learner, courses, assessments, RAG citations
└── responses/
    └── index.ts                      # Re-exported client-side response contract schemas
```

---

## 🚀 Development Scripts

```bash
# Install dependencies
npm install

# Start Vite development server (HMR enabled)
npm run dev

# Run TypeScript type check and production build
npm run build

# Preview production build locally
npm run preview
```

---

## 🎨 Design System & Highlights
* **Clean Dark-Mode Theme**: Built with Tailwind CSS and Lucide React icons.
* **Cold-Start Compliance**: Detects new learners dynamically, starting with zero fake courses, zero fake mastery, and empty state cues.
* **Multimodal Source Grounding**: Clickable citation chips reveal exact page numbers, slide indices, or video timestamps inside the slide-over source drawer.
