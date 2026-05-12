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
    total_score: Optional[float] = None
    pass_yn: Optional[bool] = None
    competency_breakdown_json: Optional[Any] = None
    summary_comment: Optional[str] = None
    result_visible: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    question_id: int
    answer_text: Optional[str] = None
    answer_json: Optional[Any] = None

class ExamSubmit(BaseModel):
    record_id: int
    answers: List[AnswerSubmit]


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


# ──────────────────────────────────────────────
# Exam Flow Schemas (응시자)
# ──────────────────────────────────────────────

class ExamLoginRequest(BaseModel):
    name: str
    login_token: str

class ExamLoginResponse(BaseModel):
    record_id: int
    applicant_name: str
    diagnosis_title: str
    duration_minutes: int
    question_count: int
    pass_score: int
    exam_token: str  # 시험 진행용 임시 토큰
    status: str

class QuestionForExam(BaseModel):
    question_id: int
    order_no: int
    question_type: QuestionTypeEnum
    title: str
    body: Optional[str] = None
    choices_json: Optional[List[Any]] = None
    score: int

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

class ExamResultResponse(BaseModel):
    record_id: int
    applicant_name: str
    diagnosis_title: str
    total_score: float
    pass_score: int
    pass_yn: bool
    competency_breakdown: Optional[Any] = None
    submitted_at: Optional[datetime] = None


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