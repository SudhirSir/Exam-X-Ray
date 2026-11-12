export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "student" | "teacher" | "admin";
  is_active: boolean;
  analytics_pseudo_id: string;
  is_minor: boolean;
  guardian_consent_verified: boolean;
  created_at: string;
}

export interface Subject {
  id: string;
  code: string;
  name: string;
  stream?: string | null;
  max_marks?: number | null;
  subject_code_in_exam?: string | null;
}

export interface Exam {
  id: string;
  exam_body_id: string;
  exam_body_code?: string | null;
  exam_body_name?: string | null;
  code: string;
  name: string;
  category: string;
  class_level?: string | null;
  is_active: boolean;
  config_json?: { verified_subjects?: string[] } | null;
  subjects: Subject[];
}

export interface ExamDnaReport {
  exam_id: string;
  exam_name: string;
  subject_id: string;
  subject_name: string;
  year_from?: number | null;
  year_to?: number | null;
  has_data: boolean;
  total_analyzed_papers: number;
  total_verified_questions: number;
  total_questions_all_origins: number;
  data_confidence_score: number;
  computation_source: string;
  chapter_weightage: {
    chapter_name: string;
    total_marks: number;
    question_count: number;
    weightage_pct: number;
    avg_difficulty_score: number;
  }[];
  question_type_distribution: {
    question_type: string;
    question_count: number;
    total_marks: number;
    share_pct: number;
  }[];
  difficulty_distribution: {
    difficulty: string;
    question_count: number;
    total_marks: number;
    share_pct: number;
  }[];
  yearly_trends: {
    year: number;
    papers_count: number;
    questions_count: number;
    total_marks: number;
    competency_share_pct: number;
    avg_difficulty_score: number;
  }[];
  recurring_concepts: {
    topic_id?: string | null;
    chapter_name: string;
    topic_name: string;
    years_appeared: number[];
    occurrence_count: number;
    total_marks_across_years: number;
    source_references: string[];
  }[];
  sources: {
    paper_id: string;
    title: string;
    year: number;
    set_code: string;
    data_origin: string;
    is_verified: boolean;
    extraction_confidence: number;
    source_url?: string | null;
    question_count: number;
  }[];
  disclaimer: string;
}

export interface QuestionItem {
  id: string;
  question_paper_id: string;
  exam_id?: string | null;
  subject_id?: string | null;
  year?: number | null;
  set_code?: string | null;
  question_number: string;
  section_name?: string | null;
  question_text: string;
  math_expressions: string[];
  question_type: string;
  marks: number;
  difficulty: string;
  is_competency_based: boolean;
  verification_status: string;
  confidence_score: number;
  data_origin: string;
  source_reference?: string | null;
  chapter_name?: string | null;
  topic_name?: string | null;
  options: { id: string; option_label: string; option_text: string; is_correct: boolean }[];
  answers: { id: string; answer_text: string; solution_steps?: string | null }[];
}

export interface SimilarQuestionResult {
  question: QuestionItem;
  cosine_score: number;
  metadata_score: number;
  combined_confidence: number;
  relationship_type: string;
  explanation: string;
}

export interface XRayReport {
  diagnostic_test_id: string;
  exam_id: string;
  subject_id: string;
  status: string;
  submitted_at?: string | null;
  estimated_readiness_score: number;
  readiness_label: string;
  estimate_disclaimer: string;
  total_questions: number;
  correct_count: number;
  accuracy_pct: number;
  avg_time_per_question_seconds: number;
  difficulty_performance: { difficulty: string; correct: number; total: number; accuracy_pct: number }[];
  question_type_performance: { question_type: string; correct: number; total: number; accuracy_pct: number }[];
  mistake_breakdown: { mistake_type: string; count: number }[];
  chapter_heatmap: { chapter_name: string; avg_mastery_pct: number; topics_tested: number }[];
  topic_vulnerabilities: {
    topic_id: string;
    chapter_name: string;
    topic_name: string;
    accuracy_pct: number;
    mastery_score: number;
    avg_time_seconds: number;
    vulnerability_index: number;
    historical_weightage_marks: number;
    prerequisite_gaps: string[];
    mistake_patterns: string[];
  }[];
  recommendations: {
    topic_id: string;
    chapter_name: string;
    topic_name: string;
    priority_rank: number;
    priority_score: number;
    reason_explanation: string;
    estimated_hours: number;
    recommended_question_ids: string[];
  }[];
  next_practice_session?: {
    focus_chapter: string;
    focus_topic: string;
    recommended_question_count: number;
    suggested_minutes: number;
  } | null;
  historical_progress: {
    test_id: string;
    submitted_at: string;
    estimated_readiness_score: number;
  }[];
}

export interface GeneratedPaper {
  id: string;
  exam_id: string;
  subject_id: string;
  title: string;
  total_marks: number;
  actual_marks: number;
  time_limit_minutes: number;
  language: string;
  solver_status: string;
  contains_ai_questions: boolean;
  blueprint_config: Record<string, unknown>;
  created_at: string;
  questions: {
    question_id: string;
    section_name: string;
    order_index: number;
    allocated_marks: number;
    question_text: string;
    question_type: string;
    difficulty: string;
    chapter_name?: string | null;
    topic_name?: string | null;
    options: { option_label: string; option_text: string; is_correct: boolean }[];
    answer_text?: string | null;
    solution_steps?: string | null;
    data_origin: string;
  }[];
}
