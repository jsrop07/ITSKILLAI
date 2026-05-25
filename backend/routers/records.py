from database import get_db
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Record, Applicant, Diagnosis, Question
from fastapi import APIRouter, Depends, HTTPException, Query
from services.ai_result_report import generate_ai_result_report
from schemas import RecordCreate, RecordUpdate, RecordRead, AIResultReportResponse

router = APIRouter(prefix="/api/records", tags=["records"])


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
def create_record(data: RecordCreate, db: Session = Depends(get_db)):
    import secrets
    token = secrets.token_urlsafe(16)
    record = Record(
        applicant_id=data.applicant_id,
        diagnosis_id=data.diagnosis_id,
        login_token=token,
        deadline_at=data.deadline_at,
    )
    db.add(record)
    # Update applicant status to ready
    applicant = db.query(Applicant).filter(Applicant.applicant_id == data.applicant_id).first()
    if applicant:
        applicant.status = "ready"
    db.commit()
    db.refresh(record)
    return record

@router.post("/{record_id}/ai-report", response_model=AIResultReportResponse)
def generate_record_ai_report(record_id: int, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")

    if record.status != "graded":
        raise HTTPException(status_code=400, detail="채점 완료된 기록만 AI 리포트를 생성할 수 있습니다.")

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.diagnosis_id == record.diagnosis_id
    ).first()

    if not diagnosis or not diagnosis.question_idxs:
        raise HTTPException(status_code=404, detail="시험 정보를 찾을 수 없습니다.")

    q_idxs = [
        int(x.strip())
        for x in diagnosis.question_idxs.split(",")
        if x.strip().isdigit()
    ]

    if not q_idxs:
        raise HTTPException(status_code=400, detail="시험 문항 정보가 없습니다.")

    questions = db.query(Question).filter(
        Question.question_id.in_(q_idxs)
    ).all()

    summary_comment = generate_ai_result_report(
        record=record,
        diagnosis=diagnosis,
        questions=questions,
    )

    if not summary_comment:
        raise HTTPException(status_code=500, detail="AI 리포트 생성에 실패했습니다.")

    record.summary_comment = summary_comment
    db.commit()
    db.refresh(record)

    return AIResultReportResponse(
        record_id=record.record_id,
        summary_comment=record.summary_comment,
    )
    
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
    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == record.diagnosis_id).first()
    if not diagnosis or not diagnosis.question_idxs:
        return []

    # question_idxs 순서대로 파싱
    q_idxs = [int(x.strip()) for x in diagnosis.question_idxs.split(',') if x.strip().isdigit()]
    if not q_idxs:
        return []

    # answer_data는 question_idxs 순서대로 저장된 콤마 구분 문자열
    raw_answers = str(record.answer_data or "").split(',')

    questions = db.query(Question).filter(Question.question_id.in_(q_idxs)).all()
    q_map = {q.question_id: q for q in questions}

    result = []
    for i, q_id in enumerate(q_idxs):
        q = q_map.get(q_id)
        if not q:
            continue

        # 응시자 답변 값 (빈 문자열 처리)
        my_ans_raw = raw_answers[i].strip() if i < len(raw_answers) else ""

        # 정답 값
        correct_ans_val = q.answer_json  # 원본 그대로 (숫자 인덱스 or 문자열)

        # 채점: 둘 다 문자열로 변환해서 비교
        if my_ans_raw and correct_ans_val is not None:
            is_correct = my_ans_raw == str(correct_ans_val)
        else:
            is_correct = False

        # 객관식이면 choices_json 기준 사람이 읽을 수 있는 텍스트로 변환
        def readable(val, choices):
            if val is None or val == "" or val == "-":
                return "-"
            try:
                idx = int(val)
                if choices and 1 <= idx <= len(choices):
                    return f"{idx}번. {choices[idx - 1]}"
            except (ValueError, TypeError):
                pass
            return str(val)

        choices = q.choices_json if q.question_type == "multiple_choice" else None
        if isinstance(choices, str):
            import json
            try:
                choices = json.loads(choices)
            except Exception:
                pass
        display_answer = readable(my_ans_raw, choices)
        display_correct = readable(str(correct_ans_val) if correct_ans_val is not None else None, choices)

        result.append({
            "answer_id": i + 1,
            "question_id": q.question_id,
            "question_title": q.title,
            "question_type": q.question_type,
            "choices_json": choices,
            "competency_type": q.competency_type,
            "difficulty": q.difficulty,
            "answer_text": display_answer,
            "answer_json": my_ans_raw,
            "correct_answer_json": display_correct,
            "is_correct": is_correct,
            "earned_score": float(q.score) if is_correct else 0.0,
        })
    return result



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
