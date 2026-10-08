export interface Citation {
  chunk_id: string;
  source_type: 'pdf' | 'pptx' | 'video' | 'image' | 'document';
  source_file: string;
  page_number?: number | null;
  slide_number?: number | null;
  timestamp_formatted?: string | null;
  label: string;
  rerank_score?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations: Citation[];
  is_outside_knowledge: boolean;
  outside_knowledge_offered: boolean;
  suggested_followups: string[];
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  topic?: string;
  summary?: string;
  pinned: boolean;
  course_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Course {
  id: string;
  title: string;
  code?: string;
  description?: string;
  subject?: string;
  created_at: string;
  topics?: any[];
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  source_category: string;
  file_size_bytes: number;
  status: string;
  progress: number;
  created_at: string;
}

export interface TopicMastery {
  id: string;
  concept_name: string;
  topic_title: string;
  difficulty: string;
  mastery_score: number;
  raw_mastery: number;
  confidence: number;
  evidence_count: number;
  correct_count: number;
  incorrect_count: number;
  last_interaction?: string;
}

export interface LearnerProfile {
  user_id: string;
  status: 'uncalibrated' | 'active' | 'advanced';
  overall_mastery: number;
  learning_behavior: {
    explanation_preference: string;
    prefers_examples_before_theory: boolean;
    prefers_formal_math: boolean;
    pacing: string;
  };
  total_active_study_minutes: number;
  total_questions_answered: number;
  total_assessments_completed: number;
  is_cold_start: boolean;
}

export interface AssessmentQuestion {
  id: string;
  question_text: string;
  question_type: string;
  difficulty: string;
  options: { id: string; text: string }[];
  topic_name: string;
  concept_name: string;
  correct_answer?: string;
  explanation?: string;
}

export interface AssessmentReport {
  assessment_id: string;
  total_questions: number;
  correct_answers: number;
  accuracy_percentage: number;
  score_percentage: number;
  total_time_seconds: number;
  concept_performance: Record<string, { accuracy: number; total: number }>;
  difficulty_performance: Record<string, { accuracy: number; total: number }>;
  mastery_changes: {
    concept: string;
    before: number;
    after: number;
    improvement: number;
    direction: 'up' | 'down';
  }[];
  weak_concepts: string[];
  strong_concepts: string[];
  misconception_diagnostic?: {
    detected: boolean;
    concept: string;
    misconception_title: string;
    remediation_guidance: string;
  } | null;
  recommendations: {
    action: string;
    title: string;
    guidance: string;
  }[];
}
