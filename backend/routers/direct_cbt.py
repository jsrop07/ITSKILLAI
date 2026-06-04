import json
import secrets
from database import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from services.result_analysis import build_result_analysis_report
from models import Applicant, Diagnosis, Record, Question, ResultReport
from ai.reports.report_service import generate_result_report_for_record
from routers.exam import build_question_snapshot, create_exam_token, get_or_create_question_snapshot, get_snapshot_question_ids, grade_record_from_answers
from schemas import (DirectCbtLoginRequest,DirectCbtLoginResponse,DirectCbtDiagnosisItem,DirectCbtStartRequest,DirectCbtStartResponse,DirectCbtSubmitResponse,ExamSubmit,ExamResultResponse,)


router = APIRouter(prefix="/api/direct-cbt", tags=["direct-cbt"])


DIRECT_CBT_AI_REPORT_DAILY_LIMIT = 3


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _get_today_range_utc() -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    return today_start, today_end


def _count_today_direct_cbt_ai_reports_by_email(db: Session, email: str) -> int:
    today_start, today_end = _get_today_range_utc()
    normalized_email = _normalize_email(email)

    return (
        db.query(ResultReport)
        .join(Record, ResultReport.record_id == Record.record_id)
        .join(Applicant, Record.applicant_id == Applicant.applicant_id)
        .filter(
            Applicant.email == normalized_email,
            Record.entry_type == "direct_cbt",
            ResultReport.report_type == "ai_result_analysis",
            ResultReport.created_at >= today_start,
            ResultReport.created_at < today_end,
        )
        .count()
    )


def _get_or_create_direct_applicant(
    db: Session,
    name: str,
    email: str,
) -> Applicant:
    normalized_email = _normalize_email(email)

    applicant = (
        db.query(Applicant)
        .filter(Applicant.email == normalized_email)
        .order_by(Applicant.created_at.desc())
        .first()
    )

    if applicant:
        applicant.name = name.strip() or applicant.name
        applicant.email = normalized_email
        db.commit()
        db.refresh(applicant)
        return applicant

    applicant = Applicant(
        name=name.strip(),
        email=normalized_email,
        status="ready",
    )

    db.add(applicant)
    db.commit()
    db.refresh(applicant)

    return applicant


@router.post("/login", response_model=DirectCbtLoginResponse)
def direct_cbt_login(
    data: DirectCbtLoginRequest,
    db: Session = Depends(get_db),
):
    applicant = _get_or_create_direct_applicant(
        db=db,
        name=data.name,
        email=data.email,
    )

    return DirectCbtLoginResponse(
        applicant_id=applicant.applicant_id,
        name=applicant.name,
        email=applicant.email,
    )


@router.get("/diagnoses", response_model=list[DirectCbtDiagnosisItem])
def list_direct_cbt_diagnoses(db: Session = Depends(get_db)):
    diagnoses = (
        db.query(Diagnosis)
        .filter(
            Diagnosis.is_direct_enabled == True,
            Diagnosis.status == "active",
        )
        .order_by(Diagnosis.created_at.desc())
        .all()
    )

    return [
        DirectCbtDiagnosisItem(
            diagnosis_id=d.diagnosis_id,
            title=d.title,
            description=d.description,
            level=d.level,
            duration_minutes=d.duration_minutes,
            pass_score=d.pass_score,
            question_count=d.question_count,
        )
        for d in diagnoses
    ]


@router.post("/records", response_model=DirectCbtStartResponse)
def start_direct_cbt_record(
    data: DirectCbtStartRequest,
    applicant_id: int,
    db: Session = Depends(get_db),
):
    applicant = (
        db.query(Applicant)
        .filter(Applicant.applicant_id == applicant_id)
        .first()
    )

    if not applicant:
        raise HTTPException(status_code=404, detail="응시자를 찾을 수 없습니다.")

    diagnosis = (
        db.query(Diagnosis)
        .filter(Diagnosis.diagnosis_id == data.diagnosis_id)
        .first()
    )

    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험지를 찾을 수 없습니다.")

    if not diagnosis.is_direct_enabled:
        raise HTTPException(status_code=403, detail="직접 응시가 허용되지 않은 시험지입니다.")

    if str(diagnosis.status) not in ("active", "DiagnosisStatus.active"):
        raise HTTPException(status_code=400, detail="활성화된 시험지만 응시할 수 있습니다.")

    record = Record(
        applicant_id=applicant.applicant_id,
        diagnosis_id=diagnosis.diagnosis_id,
        login_token=secrets.token_urlsafe(16),
        status="ready",
        result_visible=True,
        entry_type="direct_cbt",
    )

    snapshot = build_question_snapshot(db, diagnosis)
    record.question_snapshot_json = json.dumps(snapshot, ensure_ascii=False)

    db.add(record)
    applicant.status = "ready"
    db.commit()
    db.refresh(record)

    exam_token = create_exam_token(record.record_id)

    return DirectCbtStartResponse(
        record_id=record.record_id,
        diagnosis_id=diagnosis.diagnosis_id,
        exam_token=exam_token,
        duration_minutes=diagnosis.duration_minutes,
        question_count=len(snapshot),
    )


@router.post("/submit", response_model=DirectCbtSubmitResponse)
def submit_direct_cbt_exam(
    data: ExamSubmit,
    applicant_id: int,
    db: Session = Depends(get_db),
):
    record = (
        db.query(Record)
        .filter(
            Record.record_id == data.record_id,
            Record.applicant_id == applicant_id,
            Record.entry_type == "direct_cbt",
        )
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="직접 응시 기록을 찾을 수 없습니다.")
    
    applicant = (
        db.query(Applicant)
        .filter(Applicant.applicant_id == record.applicant_id)
        .first()
    )
    
    if not applicant:
        raise HTTPException(status_code=404, detail="응시자를 찾을 수 없습니다.")
    
    if record.status in ("submitted", "graded"):
        raise HTTPException(status_code=400, detail="이미 제출된 시험입니다.")

    diagnosis = (
        db.query(Diagnosis)
        .filter(Diagnosis.diagnosis_id == record.diagnosis_id)
        .first()
    )

    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험 정보를 찾을 수 없습니다.")

    result = grade_record_from_answers(
        db=db,
        record=record,
        diagnosis=diagnosis,
        answers=data.answers,
    )

    record.result_visible = True

    ai_report_generated = False
    ai_report_limit_exceeded = False

    today_count = _count_today_direct_cbt_ai_reports_by_email(
        db=db,
        email=applicant.email,
    )

    if today_count < DIRECT_CBT_AI_REPORT_DAILY_LIMIT:
        db.commit()
        db.refresh(record)

        try:
            generate_result_report_for_record(
                db=db,
                record_id=record.record_id,
            )
            record.ai_report_generated = True
            record.ai_report_requested_at = datetime.utcnow()
            ai_report_generated = True
            db.commit()
            db.refresh(record)
        except Exception:
            record.ai_report_generated = False
            record.ai_report_requested_at = datetime.utcnow()
            db.commit()
            db.refresh(record)
    else:
        record.ai_report_generated = False
        record.ai_report_requested_at = datetime.utcnow()
        ai_report_limit_exceeded = True
        db.commit()
        db.refresh(record)

    after_count = _count_today_direct_cbt_ai_reports_by_email(
        db=db,
        email=applicant.email,
    )
    remaining = max(0, DIRECT_CBT_AI_REPORT_DAILY_LIMIT - after_count)

    return DirectCbtSubmitResponse(
        message="제출이 완료되었습니다.",
        record_id=record.record_id,
        total_score=record.total_score or 0,
        pass_yn=bool(record.pass_yn),
        ai_report_generated=ai_report_generated,
        ai_report_limit_exceeded=ai_report_limit_exceeded,
        ai_report_remaining_today=remaining,
    )


@router.get("/result/{record_id}", response_model=ExamResultResponse)
def get_direct_cbt_result(
    record_id: int,
    applicant_id: int,
    db: Session = Depends(get_db),
):
    record = (
        db.query(Record)
        .filter(
            Record.record_id == record_id,
            Record.applicant_id == applicant_id,
            Record.entry_type == "direct_cbt",
        )
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="직접 응시 기록을 찾을 수 없습니다.")

    if record.status != "graded":
        raise HTTPException(status_code=400, detail="아직 채점이 완료되지 않았습니다.")

    applicant = (
        db.query(Applicant)
        .filter(Applicant.applicant_id == record.applicant_id)
        .first()
    )

    diagnosis = (
        db.query(Diagnosis)
        .filter(Diagnosis.diagnosis_id == record.diagnosis_id)
        .first()
    )

    analysis_report = None

    if diagnosis:
        snapshot = get_or_create_question_snapshot(db, record, diagnosis)
        q_idxs = get_snapshot_question_ids(snapshot)

        questions = []
        if q_idxs:
            questions = (
                db.query(Question)
                .filter(Question.question_id.in_(q_idxs))
                .all()
            )

        analysis_report = build_result_analysis_report(
            record=record,
            diagnosis=diagnosis,
            questions=questions,
        )

    return ExamResultResponse(
        record_id=record.record_id,
        applicant_name=applicant.name if applicant else "",
        diagnosis_title=diagnosis.title if diagnosis else "",
        total_score=record.total_score or 0,
        pass_score=diagnosis.pass_score if diagnosis else 70,
        pass_yn=bool(record.pass_yn),
        competency_breakdown=record.competency_breakdown_json,
        submitted_at=record.submitted_at,
        analysis_report=analysis_report,
        summary_comment=record.summary_comment,
    )