import os
import json
import secrets
from jose import jwt
from database import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models import Record, Applicant, Diagnosis, Question
from services.email_service import send_exam_submitted_to_admin
from services.result_analysis import build_result_analysis_report
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from schemas import (ExamLoginRequest,ExamLoginResponse,QuestionForExam,ExamSubmit,ExamResultResponse,ExamProgressSave,ExamStatusResponse,ExamViolationReport,)

router = APIRouter(prefix="/api/exam", tags=["exam"])

SECRET_KEY = os.getenv("SECRET_KEY", "itskill-super-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


def create_exam_token(record_id: int) -> str:
    payload = {"record_id": record_id, "type": "exam"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_exam_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "exam":
            raise ValueError("Invalid token type")
        return payload["record_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 시험 토큰입니다.")

def parse_question_idxs(question_idxs: str | None) -> list[int]:
    if not question_idxs:
        return []

    return [
        int(idx.strip())
        for idx in question_idxs.split(",")
        if idx.strip().isdigit()
    ]

def build_question_snapshot(db: Session, diagnosis: Diagnosis) -> list[dict]:
    q_idxs = parse_question_idxs(diagnosis.question_idxs)
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


def get_or_create_question_snapshot(db: Session, record: Record, diagnosis: Diagnosis) -> list[dict]:
    if getattr(record, "question_snapshot_json", None):
        try:
            parsed = json.loads(record.question_snapshot_json)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

    snapshot = build_question_snapshot(db, diagnosis)
    record.question_snapshot_json = json.dumps(snapshot, ensure_ascii=False)
    db.commit()
    db.refresh(record)
    return snapshot

def calculate_remaining_seconds(record: Record, diagnosis: Diagnosis) -> tuple[datetime, int]:
    now = datetime.utcnow()

    if not record.started_at:
        return now, diagnosis.duration_minutes * 60

    end_at = record.started_at + timedelta(minutes=diagnosis.duration_minutes)
    remaining_seconds = max(0, int((end_at - now).total_seconds()))
    return now, remaining_seconds


def is_exam_expired(record: Record, diagnosis: Diagnosis) -> bool:
    if not record.started_at:
        return False

    end_at = record.started_at + timedelta(minutes=diagnosis.duration_minutes)
    return datetime.utcnow() >= end_at

def get_snapshot_question_ids(snapshot: list[dict]) -> list[int]:
    return [
        int(item["question_id"])
        for item in snapshot
        if item.get("question_id") is not None
    ]

def build_answer_data_array(
    q_idxs: list[int],
    answers: list,
    existing_answer_data: str | None = None,
) -> list[str]:
    existing_values = str(existing_answer_data or "").split(",") if existing_answer_data else []

    answer_data_array = []
    for i, _q_id in enumerate(q_idxs):
        if i < len(existing_values):
            answer_data_array.append(existing_values[i].strip())
        else:
            answer_data_array.append("")

    for ans in answers:
        ans_val = str(ans.answer_json) if ans.answer_json is not None else ""
        if ans.question_id in q_idxs:
            idx = q_idxs.index(ans.question_id)
            answer_data_array[idx] = ans_val

    return answer_data_array

# ── 응시자 로그인 (이름 + login_token)
@router.post("/login", response_model=ExamLoginResponse)
def exam_login(data: ExamLoginRequest, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.login_token == data.login_token).first()
    if not record:
        raise HTTPException(status_code=404, detail="유효하지 않은 로그인 토큰입니다.")

    applicant = db.query(Applicant).filter(Applicant.applicant_id == record.applicant_id).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="응시자 정보를 찾을 수 없습니다.")

    if applicant.email.strip().lower() != data.email.strip().lower():
        raise HTTPException(status_code=401, detail="이메일이 일치하지 않습니다.")

    # 이미 완료된 시험이라도 로그인은 허용 (결과 조회를 위해)
    # 단, ready/in_progress가 아니면 시험 환경(test-room)으로는 못 가게 프론트에서 제어
    # if record.status not in ("ready", "in_progress"):
    #     raise HTTPException(status_code=400, detail="이미 완료된 시험이거나 접근할 수 없습니다.")

    # 마감일이 지났는지 확인 (KST 등으로 인해 frontend가 23:59:59로 보낸다고 가정)
    # 결과 조회는 마감일 지나도 가능해야 하므로, ready/in_progress 일 때만 체크
    if record.status in ("ready", "in_progress") and record.deadline_at and datetime.utcnow() > record.deadline_at:
        raise HTTPException(status_code=400, detail="시험 응시 기한이 만료되었습니다.")

    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == record.diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험 정보를 찾을 수 없습니다.")
    
    auto_grade_if_expired(db, record, diagnosis)
    db.refresh(record)
    
    exam_token = create_exam_token(record.record_id)

    snapshot = get_or_create_question_snapshot(db, record, diagnosis)
    server_now, remaining_seconds = calculate_remaining_seconds(record, diagnosis)

    return ExamLoginResponse(
        record_id=record.record_id,
        applicant_name=applicant.name,
        diagnosis_title=diagnosis.title,
        duration_minutes=diagnosis.duration_minutes,
        question_count=len(snapshot),
        pass_score=diagnosis.pass_score,
        exam_token=exam_token,
        status=record.status,
        started_at=record.started_at,
        server_now=server_now,
        remaining_seconds=remaining_seconds,
        violation_count=record.violation_count or 0,
    )

@router.get("/status/{record_id}", response_model=ExamStatusResponse)
def get_exam_status(record_id: int, exam_token: str, db: Session = Depends(get_db)):
    verified_id = verify_exam_token(exam_token)
    if verified_id != record_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    record = db.query(Record).filter(Record.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")

    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == record.diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험 정보를 찾을 수 없습니다.")

    auto_grade_if_expired(db, record, diagnosis)
    db.refresh(record)

    server_now, remaining_seconds = calculate_remaining_seconds(record, diagnosis)

    return ExamStatusResponse(
        record_id=record.record_id,
        status=record.status,
        started_at=record.started_at,
        server_now=server_now,
        remaining_seconds=remaining_seconds,
        duration_minutes=diagnosis.duration_minutes,
        violation_count=record.violation_count or 0,
    )

# ── 시험 문제 목록 조회
@router.get("/questions/{record_id}", response_model=list[QuestionForExam])
def get_exam_questions(record_id: int, exam_token: str, db: Session = Depends(get_db)):
    verified_id = verify_exam_token(exam_token)
    if verified_id != record_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    record = db.query(Record).filter(Record.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")

    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == record.diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험 정보를 찾을 수 없습니다.")

    # 시험 시작 처리
    if record.status == "ready":
        record.status = "in_progress"
        record.started_at = datetime.utcnow()
        # Update applicant status
        applicant = db.query(Applicant).filter(Applicant.applicant_id == record.applicant_id).first()
        if applicant:
            applicant.status = "in_progress"
        db.commit()

    expired = auto_grade_if_expired(db, record, diagnosis)
    if expired:
        return []

    snapshot = get_or_create_question_snapshot(db, record, diagnosis)
    saved_answers = str(record.answer_data or "").split(",") if record.answer_data else []

    result = []

    for i, item in enumerate(snapshot):
        saved_value = saved_answers[i].strip() if i < len(saved_answers) else ""

        saved_answer_json = None
        saved_answer_text = None

        if saved_value:
            if item.get("question_type") == "multiple_choice":
                try:
                    saved_answer_json = int(saved_value)
                except ValueError:
                    saved_answer_json = saved_value
            else:
                saved_answer_text = saved_value

        result.append(QuestionForExam(
            question_id=item.get("question_id"),
            order_no=i + 1,
            question_type=item.get("question_type"),
            title=item.get("title"),
            body=item.get("body"),
            choices_json=item.get("choices_json"),
            score=item.get("score") or 1,
            saved_answer_json=saved_answer_json,
            saved_answer_text=saved_answer_text,
        ))

    return result

@router.post("/save-progress")
def save_exam_progress(
    data: ExamProgressSave,
    exam_token: str,
    db: Session = Depends(get_db),
):
    verified_id = verify_exam_token(exam_token)
    if verified_id != data.record_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    record = db.query(Record).filter(Record.record_id == data.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")

    if record.status in ("submitted", "graded"):
        raise HTTPException(status_code=400, detail="이미 제출된 시험입니다.")

    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == record.diagnosis_id).first()
    if not diagnosis:
        return {"message": "시험 정보를 찾을 수 없습니다."}

    if auto_grade_if_expired(db, record, diagnosis):
        return {"message": "시험 시간이 만료되어 자동 제출되었습니다.", "expired": True}

    snapshot = get_or_create_question_snapshot(db, record, diagnosis)
    q_idxs = get_snapshot_question_ids(snapshot)
    answer_data_array = build_answer_data_array(
        q_idxs=q_idxs,
        answers=data.answers,
        existing_answer_data=record.answer_data,
    )

    record.answer_data = ",".join(answer_data_array)

    if record.status == "ready":
        record.status = "in_progress"
        record.started_at = datetime.utcnow()

    db.commit()

    return {"message": "답안이 임시 저장되었습니다.", "expired": False}

def grade_record_from_answers(
    db: Session,
    record: Record,
    diagnosis: Diagnosis,
    answers: list,
):
    snapshot = get_or_create_question_snapshot(db, record, diagnosis)
    q_idxs = get_snapshot_question_ids(snapshot)

    answer_data_array = build_answer_data_array(
        q_idxs=q_idxs,
        answers=answers,
        existing_answer_data=record.answer_data,
    )

    total_possible = 0.0
    total_earned = 0.0
    competency_scores: dict = {}

    for index, item in enumerate(snapshot):
        question_score = float(item.get("score") or 0)
        total_possible += question_score

        ans_val = answer_data_array[index] if index < len(answer_data_array) else ""

        correct_answer = item.get("answer_json")
        correct = str(correct_answer).strip() if correct_answer is not None else ""

        question_type = str(item.get("question_type") or "")

        is_correct = False
        earned = 0.0

        if question_type == "multiple_choice" and correct:
            is_correct = bool(ans_val) and ans_val == correct
            earned = question_score if is_correct else 0.0
            total_earned += earned

        comp = item.get("competency_type") or "기타"
        if comp not in competency_scores:
            competency_scores[comp] = {"earned": 0.0, "total": 0.0}

        competency_scores[comp]["earned"] += earned
        competency_scores[comp]["total"] += question_score

    competency_breakdown = {
        comp: round(v["earned"] / v["total"] * 100, 1) if v["total"] > 0 else 0
        for comp, v in competency_scores.items()
    }

    final_normalized_score = (
        round((total_earned / total_possible) * 100, 1)
        if total_possible > 0
        else 0.0
    )

    pass_score = diagnosis.pass_score if diagnosis else 70
    pass_yn = final_normalized_score >= pass_score

    record.status = "graded"
    record.submitted_at = datetime.utcnow()
    record.total_score = final_normalized_score
    record.pass_yn = pass_yn
    record.competency_breakdown_json = competency_breakdown
    record.answer_data = ",".join(answer_data_array)

    applicant = db.query(Applicant).filter(
        Applicant.applicant_id == record.applicant_id
    ).first()

    if applicant:
        applicant.status = "completed"

    return {
        "total_score": final_normalized_score,
        "pass_yn": pass_yn,
        "applicant": applicant,
    }

def fail_record_for_violation(db: Session, record: Record, diagnosis: Diagnosis):
    snapshot = get_or_create_question_snapshot(db, record, diagnosis)

    empty_answer_data = [""] * len(snapshot)

    competency_scores: dict = {}

    for item in snapshot:
        comp = item.get("competency_type") or "기타"
        score = float(item.get("score") or 0)

        if comp not in competency_scores:
            competency_scores[comp] = {"earned": 0.0, "total": 0.0}

        competency_scores[comp]["total"] += score

    competency_breakdown = {
        comp: 0
        for comp in competency_scores.keys()
    }

    record.status = "graded"
    record.submitted_at = datetime.utcnow()
    record.total_score = 0.0
    record.pass_yn = False
    record.competency_breakdown_json = competency_breakdown
    record.answer_data = ",".join(empty_answer_data)

    applicant = db.query(Applicant).filter(
        Applicant.applicant_id == record.applicant_id
    ).first()

    if applicant:
        applicant.status = "completed"

    return {
        "total_score": 0.0,
        "pass_yn": False,
        "applicant": applicant,
    }

def auto_grade_if_expired(db: Session, record: Record, diagnosis: Diagnosis) -> bool:
    if record.status not in ("in_progress", "ready"):
        return False

    if not is_exam_expired(record, diagnosis):
        return False

    grade_record_from_answers(
        db=db,
        record=record,
        diagnosis=diagnosis,
        answers=[],
    )
    db.commit()
    return True

@router.post("/violation")
def report_exam_violation(
    data: ExamViolationReport,
    exam_token: str,
    db: Session = Depends(get_db),
):
    verified_id = verify_exam_token(exam_token)
    if verified_id != data.record_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    record = db.query(Record).filter(Record.record_id == data.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")

    if record.status in ("submitted", "graded"):
        return {
            "message": "이미 제출된 시험입니다.",
            "violation_count": record.violation_count or 0,
        }

    logs = []
    if record.violation_log_json:
        try:
            logs = json.loads(record.violation_log_json)
        except Exception:
            logs = []

    logs.append({
        "reason": data.reason,
        "created_at": datetime.utcnow().isoformat(),
    })

    record.violation_count = (record.violation_count or 0) + 1
    record.violation_log_json = json.dumps(logs, ensure_ascii=False)

    disqualified = False

    if record.violation_count >= 3:
        diagnosis = db.query(Diagnosis).filter(
            Diagnosis.diagnosis_id == record.diagnosis_id
        ).first()

        if diagnosis:
            fail_record_for_violation(db, record, diagnosis)
            disqualified = True

    db.commit()
    db.refresh(record)

    if disqualified:
        return {
            "message": "화면 이탈 3회 이상으로 불합격 처리되었습니다.",
            "violation_count": record.violation_count,
            "disqualified": True,
        }

    return {
        "message": "화면 이탈이 기록되었습니다.",
        "violation_count": record.violation_count,
        "disqualified": False,
    }

# ── 답안 제출
@router.post("/submit")
def submit_exam(data: ExamSubmit,exam_token: str,background_tasks: BackgroundTasks,db: Session = Depends(get_db),):
    verified_id = verify_exam_token(exam_token)
    if verified_id != data.record_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    record = db.query(Record).filter(Record.record_id == data.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")

    if record.status == "submitted" or record.status == "graded":
        raise HTTPException(status_code=400, detail="이미 제출된 시험입니다.")

    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == record.diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험 정보를 찾을 수 없습니다.")

    result = grade_record_from_answers(
        db=db,
        record=record,
        diagnosis=diagnosis,
        answers=data.answers,
    )

    db.commit()
    db.refresh(record)

    applicant = result["applicant"]

    submitted_text = None
    if record.submitted_at:
        submitted_text = record.submitted_at.strftime("%Y-%m-%d %H:%M")

    if applicant:
        background_tasks.add_task(
            send_exam_submitted_to_admin,
            applicant_name=applicant.name,
            applicant_email=applicant.email,
            diagnosis_title=diagnosis.title if diagnosis else None,
            submitted_at=submitted_text,
            total_score=record.total_score,
            pass_yn=record.pass_yn,
        )

    return {
        "message": "제출이 완료되었습니다.",
        "record_id": data.record_id,
        "total_score": record.total_score,
        "pass_yn": record.pass_yn,
    }


# ── 결과 조회
@router.get("/result/{record_id}", response_model=ExamResultResponse)
def get_exam_result(record_id: int, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")

    if not record.result_visible:
        raise HTTPException(status_code=403, detail="결과가 아직 공개되지 않았습니다.")

    applicant = db.query(Applicant).filter(Applicant.applicant_id == record.applicant_id).first()
    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == record.diagnosis_id).first()
    analysis_report = None

    if diagnosis:
        snapshot = get_or_create_question_snapshot(db, record, diagnosis)
        q_idxs = get_snapshot_question_ids(snapshot)

        questions = []
        if q_idxs:
            questions = db.query(Question).filter(Question.question_id.in_(q_idxs)).all()

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
        pass_yn=record.pass_yn or False,
        competency_breakdown=record.competency_breakdown_json,
        submitted_at=record.submitted_at,
        analysis_report=analysis_report,
        summary_comment=record.summary_comment,
    )
