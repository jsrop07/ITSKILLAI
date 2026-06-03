import json
from database import get_db
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Record, Applicant, Diagnosis, Question
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from ai.reports.report_service import (generate_result_report_for_record,get_result_report_for_record,)
from schemas import RecordCreate, RecordUpdate, RecordRead, AIResultReportResponse
from services.email_service import (send_exam_assignment_to_applicant,send_result_published_to_applicant,
)
router = APIRouter(prefix="/api/records", tags=["records"])

def _parse_question_idxs(question_idxs: str | None) -> list[int]:
    if not question_idxs:
        return []

    return [
        int(x.strip())
        for x in str(question_idxs).split(",")
        if x.strip().isdigit()
    ]


def _build_question_snapshot(db: Session, diagnosis: Diagnosis) -> list[dict]:
    q_idxs = _parse_question_idxs(diagnosis.question_idxs)
    if not q_idxs:
        return []

    questions = db.query(Question).filter(Question.question_id.in_(q_idxs)).all()
    q_map = {q.question_id: q for q in questions}

    snapshot = []
    for index, q_id in enumerate(q_idxs):
        q = q_map.get(q_id)
        if not q:
            continue

        snapshot.append({
            "question_id": q.question_id,
            "order_no": index + 1,
            "question_type": str(q.question_type.value if hasattr(q.question_type, "value") else q.question_type),
            "title": q.title,
            "body": q.body,
            "choices_json": q.choices_json,
            "answer_json": q.answer_json,
            "explanation": q.explanation,
            "difficulty": q.difficulty,
            "competency_type": q.competency_type,
            "score": q.score,
        })

    return snapshot


def _get_record_question_snapshot(
    db: Session,
    record: Record,
    diagnosis: Diagnosis | None,
) -> list[dict]:
    if getattr(record, "question_snapshot_json", None):
        try:
            parsed = json.loads(record.question_snapshot_json)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

    if not diagnosis:
        return []

    snapshot = _build_question_snapshot(db, diagnosis)
    record.question_snapshot_json = json.dumps(snapshot, ensure_ascii=False)
    db.commit()
    db.refresh(record)
    return snapshot


def _readable_answer(value, choices):
    if value is None or value == "" or value == "-":
        return "-"

    try:
        idx = int(value)
        if isinstance(choices, list) and 1 <= idx <= len(choices):
            return f"{idx}번. {choices[idx - 1]}"
    except (ValueError, TypeError):
        pass

    return str(value)

@router.get("", response_model=List[RecordRead])
def list_records(
    applicant_id: Optional[int] = Query(None),
    diagnosis_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Record)
    if applicant_id:
        query = query.filter(Record.applicant_id == applicant_id)
    if diagnosis_id:
        query = query.filter(Record.diagnosis_id == diagnosis_id)
    if status:
        query = query.filter(Record.status == status)
    return query.order_by(Record.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=RecordRead)
def create_record(
    data: RecordCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    import secrets

    applicant = db.query(Applicant).filter(
        Applicant.applicant_id == data.applicant_id
    ).first()

    if not applicant:
        raise HTTPException(status_code=404, detail="응시자를 찾을 수 없습니다.")

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.diagnosis_id == data.diagnosis_id
    ).first()

    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험지를 찾을 수 없습니다.")

    token = secrets.token_urlsafe(16)

    question_snapshot = _build_question_snapshot(db, diagnosis)

    record = Record(
        applicant_id=data.applicant_id,
        diagnosis_id=data.diagnosis_id,
        login_token=token,
        deadline_at=data.deadline_at,
        question_snapshot_json=json.dumps(question_snapshot, ensure_ascii=False),
    )

    db.add(record)

    applicant.status = "ready"

    db.commit()
    db.refresh(record)

    if record.deadline_at:
        background_tasks.add_task(
            send_exam_assignment_to_applicant,
            applicant_name=applicant.name,
            applicant_email=applicant.email,
            diagnosis_title=diagnosis.title,
            login_token=record.login_token,
            deadline_at=record.deadline_at,
        )

    return record

@router.get("/analytics/summary")
def get_analytics_summary(db: Session = Depends(get_db)):
    from sqlalchemy import func, text

    total_records = db.query(func.count(Record.record_id)).scalar() or 0
    graded_records = db.query(func.count(Record.record_id)).filter(
        Record.status == "graded"
    ).scalar() or 0
    pass_count = db.query(func.count(Record.record_id)).filter(
        Record.pass_yn == True
    ).scalar() or 0
    avg_score = db.query(func.avg(Record.total_score)).filter(
        Record.total_score.isnot(None)
    ).scalar()

    pass_rate = (pass_count / graded_records * 100) if graded_records > 0 else 0

    return {
        "total_records": total_records,
        "graded_records": graded_records,
        "pass_count": pass_count,
        "pass_rate": round(pass_rate, 1),
        "avg_score": round(float(avg_score), 1) if avg_score else None,
    }

@router.post("/{record_id}/publish-result", response_model=RecordRead)
def publish_result(
    record_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    record = db.query(Record).filter(
        Record.record_id == record_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")

    if record.status != "graded":
        raise HTTPException(
            status_code=400,
            detail="채점 완료된 응시 기록만 결과를 공개할 수 있습니다.",
        )

    applicant = db.query(Applicant).filter(
        Applicant.applicant_id == record.applicant_id
    ).first()

    if not applicant:
        raise HTTPException(status_code=404, detail="응시자를 찾을 수 없습니다.")

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.diagnosis_id == record.diagnosis_id
    ).first()

    already_visible = bool(record.result_visible)

    record.result_visible = True

    db.commit()
    db.refresh(record)

    if not already_visible:
        background_tasks.add_task(
            send_result_published_to_applicant,
            applicant_name=applicant.name,
            applicant_email=applicant.email,
            diagnosis_title=diagnosis.title if diagnosis else None,
            total_score=record.total_score,
            pass_yn=record.pass_yn,
            record_id=record.record_id,
        )

    return record

@router.post("/{record_id}/ai-report", response_model=AIResultReportResponse)
def generate_record_ai_report(record_id: int, db: Session = Depends(get_db)):
    try:
        result = generate_result_report_for_record(db=db, record_id=record_id)
        return AIResultReportResponse(**result)
    except ValueError as e:
        message = str(e)
        if "찾을 수 없습니다" in message:
            raise HTTPException(status_code=404, detail=message)
        if "채점 완료" in message or "문항 정보" in message:
            raise HTTPException(status_code=400, detail=message)
        raise HTTPException(status_code=500, detail=message)

@router.get("/{record_id}/ai-report", response_model=AIResultReportResponse)
def get_record_ai_report(record_id: int, db: Session = Depends(get_db)):
    result = get_result_report_for_record(db=db, record_id=record_id)
    if not result:
        raise HTTPException(status_code=404, detail="생성된 AI 리포트가 없습니다.")
    return AIResultReportResponse(**result)

@router.get("/{record_id}", response_model=RecordRead)
def get_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")
    return record


@router.put("/{record_id}", response_model=RecordRead)
def update_record(record_id: int, data: RecordUpdate, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{record_id}/answers")
def get_record_answers(record_id: int, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.record_id == record_id).first()
    if not record:
        return []

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.diagnosis_id == record.diagnosis_id
    ).first()

    snapshot = _get_record_question_snapshot(
        db=db,
        record=record,
        diagnosis=diagnosis,
    )

    raw_answers = str(record.answer_data or "").split(",") if record.answer_data else []

    result = []

    for index, item in enumerate(snapshot):
        my_ans_raw = raw_answers[index].strip() if index < len(raw_answers) else ""

        correct_ans_val = item.get("answer_json")
        correct_raw = str(correct_ans_val).strip() if correct_ans_val is not None else ""

        is_correct = bool(my_ans_raw) and my_ans_raw == correct_raw

        choices = item.get("choices_json")
        if isinstance(choices, str):
            try:
                choices = json.loads(choices)
            except Exception:
                choices = []

        score = float(item.get("score") or 0)

        result.append({
            "answer_id": index + 1,
            "question_id": item.get("question_id"),
            "question_title": item.get("title"),
            "question_body": item.get("body"),
            "question_type": item.get("question_type"),
            "choices_json": choices,
            "competency_type": item.get("competency_type"),
            "difficulty": item.get("difficulty"),
            "answer_text": _readable_answer(my_ans_raw, choices),
            "answer_json": my_ans_raw,
            "submitted_answer_raw": my_ans_raw,
            "correct_answer_json": _readable_answer(correct_raw, choices),
            "correct_answer_raw": correct_raw,
            "is_correct": is_correct,
            "earned_score": score if is_correct else 0.0,
            "score": score,
            "explanation": item.get("explanation"),
        })

    return result