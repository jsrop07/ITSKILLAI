import axios from "axios";
import type {
  Admin,
  Applicant,
  ApplicantCreate,
  Diagnosis,
  DiagnosisCreate,
  DiagnosisUpdate,
  Question,
  QuestionCreate,
  ExamRecord,
  RecordCreate,
  PageContent,
  PageContentUpdate,
  DashboardStats,
  RecentExamRecord,
  WeakCompetency,
  ExamLoginResponse,
  QuestionForExam,
  AnswerSubmit,
  ExamResultResponse,
  AnswerDetail,
} from "./types";

// ──────────────────────────────────────────────
// Axios 인스턴스
// ──────────────────────────────────────────────
const api = axios.create({
  baseURL: "http://localhost:8002",
  headers: { "Content-Type": "application/json" },
});

// JWT 토큰 자동 첨부
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("admin_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 시 로그인 페이지로 리다이렉트
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("admin_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ──────────────────────────────────────────────
// Auth
// ──────────────────────────────────────────────
export const authApi = {
  login: async (email: string, password: string) => {
    const res = await api.post<{ access_token: string; token_type: string }>(
      "/api/auth/login",
      { email, password }
    );
    return res.data;
  },
  me: async (): Promise<Admin> => {
    const res = await api.get<Admin>("/api/auth/me");
    return res.data;
  },
};

// ──────────────────────────────────────────────
// Dashboard
// ──────────────────────────────────────────────
export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const res = await api.get<DashboardStats>("/api/dashboard/stats");
    return res.data;
  },
  getRecentRecords: async (limit = 10): Promise<RecentExamRecord[]> => {
    const res = await api.get<RecentExamRecord[]>(`/api/dashboard/recent-records?limit=${limit}`);
    return res.data;
  },
  getWeakCompetencies: async (): Promise<WeakCompetency[]> => {
    const res = await api.get<WeakCompetency[]>("/api/dashboard/weak-competencies");
    return res.data;
  },
};

// ──────────────────────────────────────────────
// Applicants
// ──────────────────────────────────────────────
export const applicantsApi = {
  list: async (params?: {
    search?: string;
    status?: string;
    target_role?: string;
  }): Promise<Applicant[]> => {
    const res = await api.get<Applicant[]>("/api/applicants", { params });
    return res.data;
  },
  get: async (id: number): Promise<Applicant> => {
    const res = await api.get<Applicant>(`/api/applicants/${id}`);
    return res.data;
  },
  create: async (data: ApplicantCreate): Promise<Applicant> => {
    const res = await api.post<Applicant>("/api/applicants", data);
    return res.data;
  },
  update: async (id: number, data: Partial<ApplicantCreate>): Promise<Applicant> => {
    const res = await api.put<Applicant>(`/api/applicants/${id}`, data);
    return res.data;
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/applicants/${id}`);
  },
  // 공개 신청 API
  apply: async (data: ApplicantCreate): Promise<Applicant> => {
    const res = await api.post<Applicant>("/api/applicants/apply", data);
    return res.data;
  },
};

// ──────────────────────────────────────────────
// Diagnoses (시험/문제집)
// ──────────────────────────────────────────────
export const diagnosesApi = {
  list: async (params?: {
    search?: string;
    status?: string;
    target_role?: string;
  }): Promise<Diagnosis[]> => {
    const res = await api.get<Diagnosis[]>("/api/diagnoses", { params });
    return res.data;
  },
  get: async (id: number): Promise<Diagnosis> => {
    const res = await api.get<Diagnosis>(`/api/diagnoses/${id}`);
    return res.data;
  },
  create: async (data: DiagnosisCreate): Promise<Diagnosis> => {
    const res = await api.post<Diagnosis>("/api/diagnoses", data);
    return res.data;
  },
  update: async (id: number, data: DiagnosisUpdate): Promise<Diagnosis> => {
    const res = await api.put<Diagnosis>(`/api/diagnoses/${id}`, data);
    return res.data;
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/diagnoses/${id}`);
  },
  getQuestions: async (diagnosisId: number): Promise<any[]> => {
    const res = await api.get<any[]>(`/api/diagnoses/${diagnosisId}/questions`);
    return res.data;
  },
  addQuestion: async (diagnosisId: number, data: { question_id: number; order_no: number; score: number }) => {
    const res = await api.post(`/api/diagnoses/${diagnosisId}/questions`, {
      diagnosis_id: diagnosisId,
      ...data,
    });
    return res.data;
  },
};

// ──────────────────────────────────────────────
// Questions
// ──────────────────────────────────────────────
export const questionsApi = {
  list: async (params?: {
    search?: string;
    question_type?: string;
    review_status?: string;
    source_type?: string;
    competency_type?: string;
    difficulty?: string;
  }): Promise<Question[]> => {
    const res = await api.get("/api/questions", { params });
    const body = res.data;

    console.log("/api/questions 응답:", body);

    if (Array.isArray(body)) return body;
    if (Array.isArray(body?.data)) return body.data;
    if (Array.isArray(body?.questions)) return body.questions;
    if (Array.isArray(body?.data?.questions)) return body.data.questions;

    return [];
  },
  get: async (id: number): Promise<Question> => {
    const res = await api.get<Question>(`/api/questions/${id}`);
    return res.data;
  },
  create: async (data: QuestionCreate): Promise<Question> => {
    const res = await api.post<Question>("/api/questions", data);
    return res.data;
  },
  update: async (id: number, data: Partial<QuestionCreate>): Promise<Question> => {
    const res = await api.put<Question>(`/api/questions/${id}`, data);
    return res.data;
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/questions/${id}`);
  },
};

// ──────────────────────────────────────────────
// Records
// ──────────────────────────────────────────────
export const recordsApi = {
  list: async (params?: {
    applicant_id?: number;
    diagnosis_id?: number;
    status?: string;
  }): Promise<ExamRecord[]> => {
    const res = await api.get<ExamRecord[]>("/api/records", { params });
    return res.data;
  },

  get: async (id: number): Promise<ExamRecord> => {
    const res = await api.get<ExamRecord>(`/api/records/${id}`);
    return res.data;
  },

  create: async (data: RecordCreate): Promise<ExamRecord> => {
    const res = await api.post<ExamRecord>("/api/records", data);
    return res.data;
  },

  update: async (id: number, data: Partial<ExamRecord>): Promise<ExamRecord> => {
    const res = await api.put<ExamRecord>(`/api/records/${id}`, data);
    return res.data;
  },

  getAnswers: async (recordId: number): Promise<AnswerDetail[]> => {
    const res = await api.get<AnswerDetail[]>(`/api/records/${recordId}/answers`);
    return res.data;
  },

  getAnalyticsSummary: async () => {
    const res = await api.get("/api/records/analytics/summary");
    return res.data;
  },
};

// ──────────────────────────────────────────────
// Page Contents
// ──────────────────────────────────────────────
export const pageContentsApi = {
  list: async (params?: { page_key?: string; user_type?: string }): Promise<PageContent[]> => {
    const res = await api.get<PageContent[]>("/api/page-contents", { params });
    return res.data;
  },
  getByKey: async (
    page_key: string,
    section_key?: string
  ): Promise<Record<string, { content_id: number; title?: string; body?: string }>> => {
    const res = await api.get("/api/page-contents/by-key", {
      params: { page_key, section_key },
    });
    return res.data;
  },
  update: async (id: number, data: PageContentUpdate): Promise<PageContent> => {
    const res = await api.put<PageContent>(`/api/page-contents/${id}`, data);
    return res.data;
  },
};

// ──────────────────────────────────────────────
// Exam Flow (응시자 — 인증 불필요)
// ──────────────────────────────────────────────
export const examApi = {
  login: async (name: string, login_token: string): Promise<ExamLoginResponse> => {
    const res = await api.post<ExamLoginResponse>("/api/exam/login", { name, login_token });
    return res.data;
  },
  getQuestions: async (record_id: number, exam_token: string): Promise<QuestionForExam[]> => {
    const res = await api.get<QuestionForExam[]>(`/api/exam/questions/${record_id}`, {
      params: { exam_token },
    });
    return res.data;
  },
  submit: async (
    record_id: number,
    answers: AnswerSubmit[],
    exam_token: string
  ) => {
    const res = await api.post(
      "/api/exam/submit",
      { record_id, answers },
      { params: { exam_token } }
    );
    return res.data;
  },
  getResult: async (record_id: number): Promise<ExamResultResponse> => {
    const res = await api.get<ExamResultResponse>(`/api/exam/result/${record_id}`);
    return res.data;
  },
};

export default api;

export type EmbeddingStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed";

export interface AIDocument {
  document_id: number;
  title: string;
  file_name?: string;
  file_path?: string;
  source_type?: string;
  category?: string;
  description?: string;
  uploaded_by?: number | null;
  created_at?: string;
  embedding_status?: EmbeddingStatus;
  embedding_error?: string | null;
}

export type RAGSearchMode = "vector" | "keyword" | "hybrid";

export interface RAGSearchResult {
  content: string;
  metadata: {
    document_id?: number;
    chunk_id?: number;
    chunk_index?: number;
    file_name?: string;
    title?: string;
    category?: string;
    source_type?: string;
  };
  distance?: number | null;
  similarity?: number | null;
  vector_score?: number | null;
  keyword_score?: number | null;
  hybrid_score?: number | null;
  search_source?: "vector" | "keyword" | "hybrid";
  vector_rank?: number | null;
  keyword_rank?: number | null;
  rrf_score?: number | null;
  keyword_raw_score?: number | null;
  search_sources?: string[];
}

export interface AIDocumentSearchPayload {
  query: string;
  top_k?: number;
  category?: string;
  search_mode?: RAGSearchMode;
}

export type QuestionTypeValue = "multiple_choice" | "essay" | "coding";

export interface GenerateAIQuestionsPayload {
  topic: string;
  difficulty: "초급" | "중급" | "고급";
  count: number;
  question_type: QuestionTypeValue;
  competency_type?: string;
  search_query?: string;
  top_k?: number;
}

export interface GenerateQuestionsFromDocumentPayload {
  topic: string;
  difficulty: "초급" | "중급" | "고급";
  count: number;
  top_k: number;
  question_type: QuestionTypeValue;
  competency_type?: string;
  search_query?: string;
  search_mode?: RAGSearchMode;
}

export const aiDocumentApi = {
  list: async (): Promise<AIDocument[]> => {
    const res = await api.get("/api/ai/documents");
    const body = res.data;

    if (Array.isArray(body)) return body;
    if (Array.isArray(body?.data)) return body.data;
    if (Array.isArray(body?.data?.documents)) return body.data.documents;
    if (Array.isArray(body?.documents)) return body.documents;

    return [];
  },

  upload: async (formData: FormData) => {
    const res = await api.post("/api/ai/documents/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return res.data?.data ?? res.data;
  },

  embed: async (documentId: number) => {
    const res = await api.post(`/api/ai/documents/${documentId}/embed`);
    return res.data;
  },

  search: async (payload: AIDocumentSearchPayload) => {
    const res = await api.post("/api/ai/documents/search", {
      query: payload.query,
      top_k: payload.top_k ?? 5,
      category: payload.category || undefined,
      search_mode: payload.search_mode ?? "hybrid",
    });

    return res.data?.data ?? res.data;
  },

  generateQuestions: async (payload: GenerateQuestionsFromDocumentPayload) => {
    const res = await api.post(
      "/api/ai/generate-questions-from-document",
      payload
    );
    return res.data;
  },
};

export const aiQuestionApi = {
  generateGeneral: async (payload: GenerateAIQuestionsPayload) => {
    const res = await api.post("/api/ai/generate-questions", payload);
    return res.data;
  },

  generateFromDocument: async (payload: GenerateQuestionsFromDocumentPayload) => {
    const res = await api.post(
      "/api/ai/generate-questions-from-document",
      payload
    );
    return res.data;
  },
};