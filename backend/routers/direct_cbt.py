import os
import json
import uuid
import asyncio
import secrets
import traceback
from typing import Callable

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import get_db, SessionLocal
from fastapi.responses import StreamingResponse
from services.result_analysis import build_result_analysis_report
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from models import Applicant, Diagnosis, Record, Question, ResultReport
from ai.reports.report_service import generate_result_report_for_record
from routers.exam import build_question_snapshot, create_exam_token, get_or_create_question_snapshot, get_snapshot_question_ids, grade_record_from_answers
from schemas import (DirectCbtLoginRequest,DirectCbtLoginResponse,DirectCbtDiagnosisItem,DirectCbtStartRequest,DirectCbtStartResponse,DirectCbtSubmitResponse,ExamSubmit,ExamResultResponse,)


router = APIRouter(prefix="/api/direct-cbt", tags=["direct-cbt"])


DIRECT_CBT_AI_REPORT_DAILY_LIMIT = 20
DIRECT_CBT_ACCESS_CODE = os.getenv("DIRECT_CBT_ACCESS_CODE", "cbt2")

direct_cbt_submit_jobs: dict[str, dict] = {}

def _set_submit_job(
    job_id: str,
    status: str,
    message: str,
    record_id: int | None = None,
    total_score: float | None = None,
    pass_yn: bool | None = None,
    ai_report_generated: bool = False,
    ai_report_limit_exceeded: bool = False,
    ai_report_remaining_today: int = 0,
    error: str | None = None,
):
    previous = direct_cbt_submit_jobs.get(job_id, {})

    events = previous.get("events", [])

    event = {
        "status": status,
        "message": message,
        "record_id": record_id,
        "total_score": total_score,
        "pass_yn": pass_yn,
        "ai_report_generated": ai_report_generated,
        "ai_report_limit_exceeded": ai_report_limit_exceeded,
        "ai_report_remaining_today": ai_report_remaining_today,
        "error": error,
    }

    # 같은 메시지가 연속으로 중복 저장되는 것 방지
    if not events or events[-1].get("message") != message or events[-1].get("status") != status:
        events.append(event)

    direct_cbt_submit_jobs[job_id] = {
        **event,
        "events": events,
    }

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


def _create_direct_demo_applicant(db: Session) -> Applicant:
    unique_key = secrets.token_hex(8)

    applicant = Applicant(
        name=f"체험 응시자-{unique_key}",
        email=f"demo-{unique_key}@itskill-demo.local",
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
    if data.access_code.strip() != DIRECT_CBT_ACCESS_CODE:
        raise HTTPException(
            status_code=403,
            detail="유효하지 않은 체험 코드입니다.",
        )

    applicant = _create_direct_demo_applicant(db=db)

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

def _submit_direct_cbt_exam_core(
    data: ExamSubmit,
    applicant_id: int,
    db: Session,
    progress: Callable[[str], None] | None = None,
) -> DirectCbtSubmitResponse:
    def notify(message: str):
        if progress:
            progress(message)

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

    notify("제출한 답안을 확인하고 있습니다.")

    grade_record_from_answers(
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
            notify("AI 분석 리포트를 생성하고 있습니다.")

            generate_result_report_for_record(
                db=db,
                record_id=record.record_id,
            )

            record.ai_report_generated = True
            record.ai_report_requested_at = datetime.utcnow()
            ai_report_generated = True

            db.commit()
            db.refresh(record)

        except Exception as e:
            print("Direct CBT AI report generation failed:", str(e))
            traceback.print_exc()

            record.ai_report_generated = False
            record.ai_report_requested_at = datetime.utcnow()

            db.commit()
            db.refresh(record)
    else:
        notify("오늘의 AI 분석 가능 횟수를 초과하여 기본 결과만 저장하고 있습니다.")

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

    notify("결과 페이지를 준비하고 있습니다.")

    return DirectCbtSubmitResponse(
        message="제출이 완료되었습니다.",
        record_id=record.record_id,
        total_score=record.total_score or 0,
        pass_yn=bool(record.pass_yn),
        ai_report_generated=ai_report_generated,
        ai_report_limit_exceeded=ai_report_limit_exceeded,
        ai_report_remaining_today=remaining,
    )

@router.post("/submit", response_model=DirectCbtSubmitResponse)
def submit_direct_cbt_exam(
    data: ExamSubmit,
    applicant_id: int,
    db: Session = Depends(get_db),
):
    return _submit_direct_cbt_exam_core(
        data=data,
        applicant_id=applicant_id,
        db=db,
    )

@router.post("/submit/start")
def start_direct_cbt_submit_job(
    data: ExamSubmit,
    applicant_id: int,
    background_tasks: BackgroundTasks,
):
    job_id = str(uuid.uuid4())

    _set_submit_job(
        job_id=job_id,
        status="running",
        message="AI 분석 작업을 시작하고 있습니다.",
    )

    background_tasks.add_task(
        _run_direct_cbt_submit_job,
        job_id,
        data,
        applicant_id,
    )

    return {"job_id": job_id}

def _run_direct_cbt_submit_job(
    job_id: str,
    data: ExamSubmit,
    applicant_id: int,
):
    db = SessionLocal()

    try:
        def progress(message: str):
            current = direct_cbt_submit_jobs.get(job_id, {})
            _set_submit_job(
                job_id=job_id,
                status="running",
                message=message,
                record_id=current.get("record_id"),
                total_score=current.get("total_score"),
                pass_yn=current.get("pass_yn"),
                ai_report_generated=current.get("ai_report_generated", False),
                ai_report_limit_exceeded=current.get("ai_report_limit_exceeded", False),
                ai_report_remaining_today=current.get("ai_report_remaining_today", 0),
            )

        result = _submit_direct_cbt_exam_core(
            data=data,
            applicant_id=applicant_id,
            db=db,
            progress=progress,
        )

        _set_submit_job(
            job_id=job_id,
            status="completed",
            message="AI 분석이 완료되었습니다.",
            record_id=result.record_id,
            total_score=result.total_score,
            pass_yn=result.pass_yn,
            ai_report_generated=result.ai_report_generated,
            ai_report_limit_exceeded=result.ai_report_limit_exceeded,
            ai_report_remaining_today=result.ai_report_remaining_today,
        )

    except HTTPException as e:
        db.rollback()

        _set_submit_job(
            job_id=job_id,
            status="failed",
            message=e.detail if isinstance(e.detail, str) else "제출 중 오류가 발생했습니다.",
            error=str(e.detail),
        )

    except Exception as e:
        db.rollback()
        traceback.print_exc()

        _set_submit_job(
            job_id=job_id,
            status="failed",
            message="AI 분석 중 오류가 발생했습니다.",
            error=str(e),
        )

    finally:
        db.close()

@router.get("/submit/events/{job_id}")
async def direct_cbt_submit_events(job_id: str):
    async def event_generator():
        sent_index = 0

        while True:
            job = direct_cbt_submit_jobs.get(job_id)

            if not job:
                data = {
                    "status": "failed",
                    "message": "작업 정보를 찾을 수 없습니다.",
                    "record_id": None,
                    "error": "job_not_found",
                }

                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                break

            events = job.get("events", [])

            while sent_index < len(events):
                event = events[sent_index]
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                sent_index += 1

                # 너무 빠르게 한 번에 지나가지 않게 약간의 간격을 줌
                await asyncio.sleep(1.5)

            if job.get("status") in ("completed", "failed") and sent_index >= len(events):
                break

            await asyncio.sleep(0.2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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