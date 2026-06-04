import json
from enum import Enum
from datetime import datetime
from typing import Optional, List, Any, Literal
from pydantic import BaseModel, EmailStr, field_validator


# ──────────────────────────────────────────────
# Enum Schemas
# ──────────────────────────────────────────────

class AdminRoleEnum(str, Enum):
    super_admin = "super_admin"
    admin = "admin"

class ApplicantStatusEnum(str, Enum):
    pending = "pending"
    temp_saved = "temp_saved"
    ready = "ready"
    in_progress = "in_progress"
    completed = "completed"

class DiagnosisStatusEnum(str, Enum):
    draft = "draft"
    active = "active"
    inactive = "inactive"

class DiagnosisLevelEnum(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"

class SourceTypeEnum(str, Enum):
    manual = "manual"
    ai = "ai"

class QuestionTypeEnum(str, Enum):
    multiple_choice = "multiple_choice"
    essay = "essay"
    coding ="coding"

class ReviewStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class RecordStatusEnum(str, Enum):
    ready = "ready"
    in_progress = "in_progress"
    submitted = "submitted"
    graded = "graded"

class UserTypeEnum(str, Enum):
    admin = "admin"
    applicant = "applicant"
    common = "common"


# ──────────────────────────────────────────────
# Auth Schemas
# ──────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class AdminLogin(BaseModel):
    email: str
    password: str


# ──────────────────────────────────────────────
# Admin Schemas
# ──────────────────────────────────────────────

class AdminBase(BaseModel):
    email: str
    name: str
    role: AdminRoleEnum = AdminRoleEnum.admin

class AdminCreate(AdminBase):
    password: str

class AdminRead(AdminBase):
    admin_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Applicant Schemas
# ──────────────────────────────────────────────

class ApplicantBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    tech_stack: Optional[str] = None

class ApplicantCreate(ApplicantBase):
    pass

class EmailVerificationSendRequest(BaseModel):
    email: EmailStr
    purpose: str = "diagnosis_apply"


class EmailVerificationVerifyRequest(BaseModel):
    email: EmailStr
    code: str
    purpose: str = "diagnosis_apply"


class EmailVerificationResponse(BaseModel):
    success: bool
    message: str
    
class ApplicantUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    tech_stack: Optional[str] = None
    status: Optional[ApplicantStatusEnum] = None
    target_diagnosis_id: Optional[int] = None
    target_deadline_at: Optional[datetime] = None

class ApplicantRead(ApplicantBase):
    applicant_id: int
    status: ApplicantStatusEnum
    target_diagnosis_id: Optional[int] = None
    target_deadline_at: Optional[datetime] = None
    latest_score: Optional[float] = None
    latest_pass_yn: Optional[bool] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Diagnosis (시험/문제집) Schemas
# ──────────────────────────────────────────────

class DiagnosisBase(BaseModel):
    title: str
    description: Optional[str] = None
    target_role: Optional[str] = None
    level: DiagnosisLevelEnum = DiagnosisLevelEnum.intermediate
    question_count: int = 0
    duration_minutes: int = 60
    pass_score: int = 70
    status: DiagnosisStatusEnum = DiagnosisStatusEnum.draft
    question_idxs: Optional[str] = None
    result_points: Optional[str] = None
    result_texts: Optional[str] = None
    result_comments: Optional[str] = None
    is_direct_enabled: bool = False

class DiagnosisCreate(DiagnosisBase):
    pass

class DiagnosisUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_role: Optional[str] = None
    level: Optional[DiagnosisLevelEnum] = None
    question_count: Optional[int] = None
    duration_minutes: Optional[int] = None
    pass_score: Optional[int] = None
    status: Optional[DiagnosisStatusEnum] = None
    question_idxs: Optional[str] = None
    result_points: Optional[str] = None
    result_texts: Optional[str] = None
    result_comments: Optional[str] = None
    is_direct_enabled: Optional[bool] = None

class DiagnosisRead(DiagnosisBase):
    diagnosis_id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Question Schemas
# ──────────────────────────────────────────────

class QuestionBase(BaseModel):
    source_type: SourceTypeEnum = SourceTypeEnum.manual
    question_type: QuestionTypeEnum = QuestionTypeEnum.multiple_choice
    title: str
    body: Optional[str] = None
    choices_json: Optional[List[Any]] = None
    answer_json: Optional[Any] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    competency_type: Optional[str] = None
    competency_tags_json: Optional[List[str]] = None
    score: int = 1
    ai_generation_type: Optional[str] = None

    @field_validator("choices_json", mode="before")
    @classmethod
    def parse_choices_json(cls, value):
        if value is None:
            return None

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                return [parsed]
            except json.JSONDecodeError:
                return [value]

        return value

    @field_validator("competency_tags_json", mode="before")
    @classmethod
    def parse_competency_tags_json(cls, value):
        if value is None:
            return None

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
                return [str(parsed)]
            except json.JSONDecodeError:
                return [value]

        return value

    @field_validator("answer_json", mode="before")
    @classmethod
    def parse_answer_json(cls, value):
        if value is None:
            return None

        if isinstance(value, (int, float, list, dict, bool)):
            return value

        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return value

class QuestionCreate(QuestionBase):
    pass

class QuestionUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    choices_json: Optional[List[Any]] = None
    answer_json: Optional[Any] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    competency_type: Optional[str] = None
    competency_tags_json: Optional[List[str]] = None
    score: Optional[int] = None
    review_status: Optional[ReviewStatusEnum] = None

class QuestionRead(QuestionBase):
    question_id: int
    review_status: ReviewStatusEnum
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    has_rag_evidence: bool = False
    rag_evidence: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True



# ──────────────────────────────────────────────
# Record Schemas
# ──────────────────────────────────────────────

class RecordCreate(BaseModel):
    applicant_id: int
    diagnosis_id: int
    deadline_at: Optional[datetime] = None

class RecordUpdate(BaseModel):
    diagnosis_id: Optional[int] = None
    deadline_at: Optional[datetime] = None
    status: Optional[RecordStatusEnum] = None
    total_score: Optional[float] = None
    pass_yn: Optional[bool] = None
    competency_breakdown_json: Optional[Any] = None
    summary_comment: Optional[str] = None
    result_visible: Optional[bool] = None

class RecordRead(BaseModel):
    record_id: int
    applicant_id: int
    diagnosis_id: int
    login_token: Optional[str] = None
    status: RecordStatusEnum
    started_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    violation_count: int = 0
    violation_log_json: Optional[Any] = None
    total_score: Optional[float] = None
    pass_yn: Optional[bool] = None
    competency_breakdown_json: Optional[Any] = None
    summary_comment: Optional[str] = None
    result_visible: bool

    entry_type: Optional[str] = "admin_invite"
    ai_report_requested_at: Optional[datetime] = None
    ai_report_generated: bool = False

    created_at: datetime
    updated_at: datetime
    question_snapshot_json: Optional[Any] = None

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    question_id: int
    answer_text: Optional[str] = None
    answer_json: Optional[Any] = None

class ExamSubmit(BaseModel):
    record_id: int
    answers: List[AnswerSubmit]

class ExamProgressSave(BaseModel):
    record_id: int
    answers: List[AnswerSubmit]

class ExamViolationReport(BaseModel):
    record_id: int
    reason: str

# ──────────────────────────────────────────────
# PageContent Schemas
# ──────────────────────────────────────────────

class PageContentBase(BaseModel):
    page_key: str
    section_key: str
    content_key: str
    title: Optional[str] = None
    body: Optional[str] = None
    extra_json: Optional[Any] = None
    user_type: UserTypeEnum = UserTypeEnum.common
    is_active: bool = True

class PageContentCreate(PageContentBase):
    pass

class PageContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    extra_json: Optional[Any] = None
    is_active: Optional[bool] = None

class PageContentRead(PageContentBase):
    content_id: int
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ResultReportRead(BaseModel):
    report_id: int
    record_id: int
    applicant_id: int
    report_type: str
    model_name: Optional[str] = None
    current_analysis_json: Optional[Any] = None
    subtopic_stats_json: Optional[Any] = None
    history_comparison_json: Optional[Any] = None
    wrong_answer_summary_json: Optional[Any] = None
    report_text: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIResultReportResponse(BaseModel):
    record_id: int
    report_id: Optional[int] = None
    summary_comment: str
    subtopic_stats: Optional[Any] = None
    history_comparison: Optional[Any] = None


# ──────────────────────────────────────────────
# Exam Flow Schemas (응시자)
# ──────────────────────────────────────────────

class ExamLoginRequest(BaseModel):
    email: str
    login_token: str

class ExamLoginResponse(BaseModel):
    record_id: int
    applicant_name: str
    diagnosis_title: str
    duration_minutes: int
    question_count: int
    pass_score: int
    exam_token: str
    status: str
    started_at: Optional[datetime] = None
    server_now: datetime
    remaining_seconds: int
    violation_count: int = 0

class ExamStatusResponse(BaseModel):
    record_id: int
    status: str
    started_at: Optional[datetime] = None
    server_now: datetime
    remaining_seconds: int
    duration_minutes: int
    violation_count: int = 0

class QuestionForExam(BaseModel):
    question_id: int
    order_no: int
    question_type: QuestionTypeEnum
    title: str
    body: Optional[str] = None
    choices_json: Optional[List[Any]] = None
    score: int
    saved_answer_json: Optional[Any] = None
    saved_answer_text: Optional[str] = None

    @field_validator("choices_json", mode="before")
    @classmethod
    def parse_choices_json(cls, value):
        if value is None:
            return None

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                return [parsed]
            except json.JSONDecodeError:
                return [value]

        return value

class ResultSummary(BaseModel):
    total_questions: int
    correct_count: int
    wrong_count: int
    accuracy_rate: float
    total_score: float
    pass_score: int
    pass_yn: bool


class ResultStatItem(BaseModel):
    key: str
    label: str
    total_count: int
    correct_count: int
    wrong_count: int
    accuracy_rate: float
    earned_score: float
    total_score: float


class WrongAnswerItem(BaseModel):
    question_id: int
    question_title: str
    question_body: Optional[str] = None
    choices_json: Optional[List[Any]] = None
    competency_type: Optional[str] = None
    competency_label: Optional[str] = None
    difficulty: Optional[str] = None
    submitted_answer: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    score: Optional[float] = None


class ResultAnalysisReport(BaseModel):
    summary: ResultSummary
    competency_stats: List[ResultStatItem] = []
    difficulty_stats: List[ResultStatItem] = []
    weak_competencies: List[ResultStatItem] = []
    wrong_answers: List[WrongAnswerItem] = []
    recommendations: List[str] = []

class ExamResultResponse(BaseModel):
    record_id: int
    applicant_name: str
    diagnosis_title: str
    total_score: float
    pass_score: int
    pass_yn: bool
    competency_breakdown: Optional[Any] = None
    submitted_at: Optional[datetime] = None
    analysis_report: Optional[ResultAnalysisReport] = None
    summary_comment: Optional[str] = None

class DirectCbtLoginRequest(BaseModel):
    name: str
    email: EmailStr


class DirectCbtLoginResponse(BaseModel):
    applicant_id: int
    name: str
    email: str


class DirectCbtDiagnosisItem(BaseModel):
    diagnosis_id: int
    title: str
    description: Optional[str] = None
    level: Optional[DiagnosisLevelEnum] = None
    duration_minutes: int
    pass_score: int
    question_count: int


class DirectCbtStartRequest(BaseModel):
    diagnosis_id: int


class DirectCbtStartResponse(BaseModel):
    record_id: int
    diagnosis_id: int
    exam_token: str
    duration_minutes: int
    question_count: int


class DirectCbtSubmitResponse(BaseModel):
    message: str
    record_id: int
    total_score: float
    pass_yn: bool
    ai_report_generated: bool = False
    ai_report_limit_exceeded: bool = False
    ai_report_remaining_today: int = 0


# ──────────────────────────────────────────────
# Dashboard Schemas
# ──────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_applicants: int
    in_progress_exams: int
    pending_review_questions: int
    recent_question_count: int

class WeakCompetency(BaseModel):
    competency: str
    avg_score: float
    count: int

# ──────────────────────────────────────────────
# AI Document Schemas
# ──────────────────────────────────────────────

class AIDocumentRead(BaseModel):
    document_id: int
    title: str
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    source_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    uploaded_by: Optional[int] = None
    created_at: datetime
    embedding_status: Optional[str] = None
    embedding_error: Optional[str] = None

    class Config:
        from_attributes = True


class AIDocumentChunkRead(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    page_no: Optional[int] = None
    vector_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AIDocumentSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    category: str | None = None
    search_mode: Literal["vector", "keyword", "hybrid"] = "hybrid"


class GenerateQuestionsFromDocumentRequest(BaseModel):
    topic: str
    difficulty: Literal["초급", "중급", "고급"]
    count: int = 5
    top_k: int = 5

