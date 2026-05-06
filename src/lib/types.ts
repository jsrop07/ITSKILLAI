// ──────────────────────────────────────────────
// TypeScript 타입 정의 (백엔드 Pydantic 스키마와 대응)
// ──────────────────────────────────────────────

export type AdminRole = "super_admin" | "admin";
export type ApplicantStatus = "pending" | "temp_saved" | "ready" | "in_progress" | "completed";
export type DiagnosisStatus = "draft" | "active" | "inactive";
export type DiagnosisLevel = "beginner" | "intermediate" | "advanced";
export type QuestionType = "multiple_choice" | "essay" | "coding";
export type ReviewStatus = "pending" | "approved" | "rejected";
export type RecordStatus = "ready" | "in_progress" | "submitted" | "graded";
export type SourceType = "manual" | "ai";
export type UserType = "admin" | "applicant" | "common";

// 한글 레이블 매핑
export const LEVEL_LABELS: Record<DiagnosisLevel, string> = {
  beginner: "초급",
  intermediate: "중급",
  advanced: "고급",
};
export const STATUS_LABELS: Record<DiagnosisStatus, string> = {
  draft: "초안",
  active: "활성",
  inactive: "비활성",
};
export const APPLICANT_STATUS_LABELS: Record<ApplicantStatus, string> = {
  pending: "신청 대기중",
  temp_saved: "임시 저장됨",
  ready: "시험 준비",
  in_progress: "진행중",
  completed: "완료",
};
export const RECORD_STATUS_LABELS: Record<RecordStatus, string> = {
  ready: "준비",
  in_progress: "진행중",
  submitted: "제출됨",
  graded: "채점완료",
};
export const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  pending: "검토 대기",
  approved: "승인",
  rejected: "반려",
};

export const AI_GENERATION_TYPE_LABELS: Record<string, string> = {
  general: "설계서 기반",
  rag: "문서 기반 RAG",
  manual: "수동/기존",
};

// ──────────────────────────────────────────────
// Admin
// ──────────────────────────────────────────────
export interface Admin {
  admin_id: number;
  email: string;
  name: string;
  role: AdminRole;
  is_active: boolean;
  created_at: string;
}

// ──────────────────────────────────────────────
// Applicant
// ──────────────────────────────────────────────
export interface Applicant {
  applicant_id: number;
  name: string;
  email: string;
  phone?: string;
  target_role?: string;
  experience_level?: string;
  tech_stack?: string;
  status: ApplicantStatus;
  created_at: string;
  updated_at: string;
}

export interface ApplicantCreate {
  name: string;
  email: string;
  phone?: string;
  target_role?: string;
  experience_level?: string;
  tech_stack?: string;
}

// ──────────────────────────────────────────────
// Diagnosis (시험/문제집)
// ──────────────────────────────────────────────
export interface Diagnosis {
  diagnosis_id: number;
  title: string;
  description?: string;
  target_role?: string;
  level: DiagnosisLevel;
  question_count: number;
  duration_minutes: number;
  pass_score: number;
  status: DiagnosisStatus;
  question_idxs?: string;
  created_by?: number;
  created_at: string;
  updated_at: string;
}

export interface DiagnosisCreate {
  title: string;
  description?: string;
  target_role?: string;
  level?: DiagnosisLevel;
  duration_minutes?: number;
  pass_score?: number;
  status?: DiagnosisStatus;
  question_idxs?: string;
}

export interface DiagnosisUpdate extends Partial<DiagnosisCreate> {
  question_count?: number;
}

// ──────────────────────────────────────────────
// Question
// ──────────────────────────────────────────────
export interface Question {
  question_id: number;
  source_type: SourceType;
  question_type: QuestionType;
  title: string;
  body?: string;
  choices_json?: string[];
  answer_json?: any;
  explanation?: string;
  difficulty?: string;
  competency_type?: string;
  competency_tags_json?: string[];
  score: number;
  review_status: ReviewStatus;
  ai_generation_type?: string | null;
  created_by?: number;
  created_at: string;
  updated_at: string;
}

export interface QuestionCreate {
  source_type?: SourceType;
  question_type?: QuestionType;
  title: string;
  body?: string;
  choices_json?: string[];
  answer_json?: any;
  explanation?: string;
  difficulty?: string;
  competency_type?: string;
  competency_tags_json?: string[];
  score?: number;
  ai_generation_type?: string | null;
}

// ──────────────────────────────────────────────
// Record (응시 기록)
// ──────────────────────────────────────────────
export interface ExamRecord {
  record_id: number;
  applicant_id: number;
  diagnosis_id: number;
  login_token?: string;
  status: RecordStatus;
  deadline_at?: string;
  started_at?: string;
  submitted_at?: string;
  total_score?: number;
  pass_yn?: boolean;
  competency_breakdown_json?: Record<string, number>;
  summary_comment?: string;
  result_visible: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecordCreate {
  applicant_id: number;
  diagnosis_id: number;
  deadline_at?: string;
}

// ──────────────────────────────────────────────
// PageContent
// ──────────────────────────────────────────────
export interface PageContent {
  content_id: number;
  page_key: string;
  section_key: string;
  content_key: string;
  title?: string;
  body?: string;
  extra_json?: any;
  user_type: UserType;
  is_active: boolean;
  updated_by?: number;
  created_at: string;
  updated_at: string;
}

export interface PageContentUpdate {
  title?: string;
  body?: string;
  extra_json?: any;
  is_active?: boolean;
}

// ──────────────────────────────────────────────
// Dashboard
// ──────────────────────────────────────────────
export interface DashboardStats {
  total_applicants: number;
  in_progress_exams: number;
  pending_review_questions: number;
  recent_question_count: number;
}

export interface RecentExamRecord {
  record_id: number;
  applicant_id: number;
  name: string;
  role?: string;
  exam: string;
  score?: number;
  pass_yn?: boolean;
  status: string;
  submitted_at?: string;
}

export interface WeakCompetency {
  competency: string;
  avg_score: number;
  count: number;
}

// ──────────────────────────────────────────────
// Exam Flow (응시자)
// ──────────────────────────────────────────────
export interface ExamLoginResponse {
  record_id: number;
  applicant_name: string;
  diagnosis_title: string;
  duration_minutes: number;
  question_count: number;
  pass_score: number;
  exam_token: string;
}

export interface QuestionForExam {
  question_id: number;
  order_no: number;
  question_type: QuestionType;
  title: string;
  body?: string;
  choices_json?: string[];
  score: number;
}

export interface AnswerSubmit {
  question_id: number;
  answer_text?: string;
  answer_json?: any;
}

export interface ExamResultResponse {
  record_id: number;
  applicant_name: string;
  diagnosis_title: string;
  total_score: number;
  pass_score: number;
  pass_yn: boolean;
  competency_breakdown?: Record<string, number>;
  submitted_at?: string;
}

// ──────────────────────────────────────────────
// Answer Detail (관리자 결과 조회)
// ──────────────────────────────────────────────
export interface AnswerDetail {
  answer_id: number;
  question_id: number;
  question_title: string;
  competency_type?: string;
  difficulty?: string;
  answer_text?: string;
  answer_json?: any;
  correct_answer_json?: any;
  is_correct?: boolean;
  earned_score: number;
}

// ──────────────────────────────────────────────
// 역량 유형 공통 상수 (신규 8개 기준)
// ──────────────────────────────────────────────

export type CompetencyTypeValue =
  | "software_engineering"
  | "java"
  | "python"
  | "c_language"
  | "sql"
  | "data_structure_algorithm"
  | "security"
  | "ai";

export const COMPETENCY_OPTIONS: { value: CompetencyTypeValue; label: string }[] = [
  { value: "software_engineering", label: "소프트웨어공학" },
  { value: "java", label: "Java" },
  { value: "python", label: "Python" },
  { value: "c_language", label: "C언어" },
  { value: "sql", label: "SQL" },
  { value: "data_structure_algorithm", label: "자료구조/알고리즘" },
  { value: "security", label: "정보보안" },
  { value: "ai", label: "AI" },
];

export const COMPETENCY_LABEL_MAP: Record<string, string> = {
  // 신규 8개
  software_engineering: "소프트웨어공학",
  java: "Java",
  python: "Python",
  c_language: "C언어",
  sql: "SQL",
  data_structure_algorithm: "자료구조/알고리즘",
  security: "정보보안",
  ai: "AI",

  // legacy display only — 기존 DB 데이터 표시용
  programming: "프로그래밍",
  programming_language: "프로그래밍",
  database: "데이터베이스",
  ai_data: "인공지능/데이터",
  web_development: "웹 개발",
  os_network: "운영체제/네트워크",
  cloud_devops: "클라우드/DevOps",
};

export const TOPIC_PLACEHOLDER_MAP: Record<string, string> = {
  software_engineering: "예: 요구사항 분석, 테스트 전략, 형상관리, 변경관리",
  java: "예: Java 상속, 인터페이스, 예외 처리, 컬렉션, JVM",
  python: "예: Python 리스트/딕셔너리, 함수, 예외 처리, 클래스",
  c_language: "예: C 포인터, 배열, 문자열, 구조체, 메모리",
  sql: "예: SELECT/JOIN, GROUP BY, 인덱스, 실행 계획, 트랜잭션",
  data_structure_algorithm: "예: 스택/큐, DFS/BFS, 시간복잡도, 해시, 트리",
  security: "예: XSS, CSRF, SQL Injection, 인증/인가, 암호화",
  ai: "예: LLM, RAG, 임베딩, 모델 평가, 과적합, 데이터 전처리",
};

export function getCompetencyLabel(value?: string | null): string {
  if (!value) return "-";
  return COMPETENCY_LABEL_MAP[value] ?? value;
}
