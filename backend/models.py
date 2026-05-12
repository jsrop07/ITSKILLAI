import enum
from database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ( Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Enum, JSON)


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class AdminRole(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"

class ApplicantStatus(str, enum.Enum):
    pending = "pending"       # 신청 완료, 시험 미배정
    temp_saved = "temp_saved" # 임시 저장됨
    ready = "ready"           # 시험 배정됨
    in_progress = "in_progress"
    completed = "completed"

class DiagnosisStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    inactive = "inactive"

class DiagnosisLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"

class SourceType(str, enum.Enum):
    manual = "manual"
    ai = "ai"

class QuestionType(str, enum.Enum):
    multiple_choice = "multiple_choice"
    essay = "essay"
    coding = "coding"

class ReviewStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class RecordStatus(str, enum.Enum):
    ready = "ready"
    in_progress = "in_progress"
    submitted = "submitted"
    graded = "graded"

class UserType(str, enum.Enum):
    admin = "admin"
    applicant = "applicant"
    common = "common"


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(Enum(AdminRole), default=AdminRole.admin, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class Applicant(Base):
    __tablename__ = "applicants"

    applicant_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    target_role = Column(String(100), nullable=True)
    experience_level = Column(String(50), nullable=True)
    tech_stack = Column(Text, nullable=True)
    status = Column(Enum(ApplicantStatus), default=ApplicantStatus.pending, nullable=False)
    target_diagnosis_id = Column(Integer, ForeignKey("diagnoses.diagnosis_id"), nullable=True)
    target_deadline_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    records = relationship("Record", back_populates="applicant")
    target_diagnosis = relationship("Diagnosis", foreign_keys=[target_diagnosis_id])


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    diagnosis_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_role = Column(String(100), nullable=True)
    level = Column(Enum(DiagnosisLevel), default=DiagnosisLevel.intermediate, nullable=False)
    question_count = Column(Integer, default=0, nullable=False)
    duration_minutes = Column(Integer, default=60, nullable=False)
    pass_score = Column(Integer, default=70, nullable=False)
    status = Column(Enum(DiagnosisStatus), default=DiagnosisStatus.draft, nullable=False)
    question_idxs = Column(String(500), nullable=True) # e.g. "1,2,5"
    result_points = Column(String(50), nullable=True)
    result_texts = Column(String(255), nullable=True)
    result_comments = Column(String(510), nullable=True)
    created_by = Column(Integer, ForeignKey("admins.admin_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    records = relationship("Record", back_populates="diagnosis")


class Question(Base):
    __tablename__ = "questions"

    question_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_type = Column(Enum(SourceType), default=SourceType.manual, nullable=False)
    question_type = Column(Enum(QuestionType), default=QuestionType.multiple_choice, nullable=False)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    choices_json = Column(JSON, nullable=True)    # list of choice strings
    answer_json = Column(JSON, nullable=True)     # correct answer(s)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(50), nullable=True)
    competency_type = Column(String(100), nullable=True)
    competency_tags_json = Column(JSON, nullable=True)
    score = Column(Integer, default=1, nullable=False)
    review_status = Column(Enum(ReviewStatus), default=ReviewStatus.pending, nullable=False)
    ai_generation_type = Column(String(50), nullable=True) # "general", "rag", "manual"
    created_by = Column(Integer, ForeignKey("admins.admin_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class Record(Base):
    __tablename__ = "records"

    record_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    applicant_id = Column(Integer, ForeignKey("applicants.applicant_id"), nullable=False)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.diagnosis_id"), nullable=False)
    login_token = Column(String(255), unique=True, nullable=True, index=True)
    status = Column(Enum(RecordStatus), default=RecordStatus.ready, nullable=False)
    answer_data = Column(String(1000), nullable=True) # e.g. "1,2,4,4,1"
    deadline_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    total_score = Column(Float, nullable=True)
    pass_yn = Column(Boolean, nullable=True)
    competency_breakdown_json = Column(JSON, nullable=True)
    summary_comment = Column(Text, nullable=True)
    result_visible = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    applicant = relationship("Applicant", back_populates="records")
    diagnosis = relationship("Diagnosis", back_populates="records")

class PageContent(Base):
    __tablename__ = "page_contents"

    content_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    page_key = Column(String(100), nullable=False, index=True)
    section_key = Column(String(100), nullable=False)
    content_key = Column(String(100), nullable=False)
    title = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    extra_json = Column(JSON, nullable=True)
    user_type = Column(Enum(UserType), default=UserType.common, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    updated_by = Column(Integer, ForeignKey("admins.admin_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class AIDocument(Base):
    __tablename__ = "ai_documents"

    document_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    source_type = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("admins.admin_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    embedding_status = Column(String(20), default="pending")
    embedding_error = Column(Text, nullable=True)


class AIDocumentChunk(Base):
    __tablename__ = "ai_document_chunks"

    chunk_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("ai_documents.document_id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_no = Column(Integer, nullable=True)
    vector_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
