import os
import secrets
from jose import jwt
from database import get_db
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from models import Record, Applicant, Diagnosis, Question
from services.result_analysis import build_result_analysis_report
from schemas import (ExamLoginRequest, ExamLoginResponse,QuestionForExam, ExamSubmit, ExamResultResponse,)

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


# ── 응시자 로그인 (이름 + login_token)
@router.post("/login", response_model=ExamLoginResponse)
def exam_login(data: ExamLoginRequest, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.login_token == data.login_token).first()
    if not record:
        raise HTTPException(status_code=404, detail="유효하지 않은 로그인 토큰입니다.")

    applicant = db.query(Applicant).filter(Applicant.applicant_id == record.applicant_id).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="응시자 정보를 찾을 수 없습니다.")

    if applicant.name.strip() != data.name.strip():
        raise HTTPException(status_code=401, detail="이름이 일치하지 않습니다.")

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

    exam_token = create_exam_token(record.record_id)

    return ExamLoginResponse(
        record_id=record.record_id,
        applicant_name=applicant.name,
        diagnosis_title=diagnosis.title,
        duration_minutes=diagnosis.duration_minutes,
        question_count=diagnosis.question_count,
        pass_score=diagnosis.pass_score,
        exam_token=exam_token,
        status=record.status
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

    # 시험 시작 처리
    if record.status == "ready":
        record.status = "in_progress"
        record.started_at = datetime.utcnow()
        # Update applicant status
        applicant = db.query(Applicant).filter(Applicant.applicant_id == record.applicant_id).first()
        if applicant:
            applicant.status = "in_progress"
        db.commit()

    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == record.diagnosis_id).first()
    if not diagnosis or not diagnosis.question_idxs:
        return []

    idxs = [int(idx.strip()) for idx in diagnosis.question_idxs.split(",") if idx.strip().isdigit()]
    if not idxs:
        return []

    questions = db.query(Question).filter(Question.question_id.in_(idxs)).all()
    q_map = {q.question_id: q for q in questions}

    result = []
    for i, q_id in enumerate(idxs):
        if q_id in q_map:
            q = q_map[q_id]
            result.append(QuestionForExam(
                question_id=q.question_id,
                order_no=i + 1,
                question_type=q.question_type,
                title=q.title,
                body=q.body,
                choices_json=q.choices_json,
                score=q.score,
            ))
    return result


# ── 답안 제출
@router.post("/submit")
def submit_exam(data: ExamSubmit, exam_token: str, db: Session = Depends(get_db)):
    verified_id = verify_exam_token(exam_token)
    if verified_id != data.record_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    record = db.query(Record).filter(Record.record_id == data.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="응시 기록을 찾을 수 없습니다.")

    if record.status == "submitted" or record.status == "graded":
        raise HTTPException(status_code=400, detail="이미 제출된 시험입니다.")

    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == record.diagnosis_id).first()
    
    # 해당 시험의 모든 문제 수집하여 만점(total_possible) 계산
    total_possible = 0.0
    q_idxs = []
    all_questions_map = {}
    if diagnosis and diagnosis.question_idxs:
        q_idxs = [int(idx.strip()) for idx in diagnosis.question_idxs.split(",") if idx.strip().isdigit()]
        if q_idxs:
            all_questions = db.query(Question).filter(Question.question_id.in_(q_idxs)).all()
            all_questions_map = {q.question_id: q for q in all_questions}
            for q in all_questions:
                total_possible += q.score

    total_earned = 0.0
    competency_scores: dict = {}

    # 응시자 답변을 question_id별로 딕셔너리로 먼저 정리
    answers_by_qid = {}
    for ans in data.answers:
        ans_val = str(ans.answer_json) if ans.answer_json is not None else ""
        answers_by_qid[ans.question_id] = ans_val

    # ★ question_idxs 순서대로 answer_data 배열 구성 → 조회 시 인덱스 매핑 보장
    answer_data_array = []
    for q_id in q_idxs:
        question = all_questions_map.get(q_id)
        if not question:
            answer_data_array.append("")
            continue

        ans_val = answers_by_qid.get(q_id, "")
        answer_data_array.append(ans_val)

        is_correct = False
        earned = 0.0

        # 객관식 자동 채점
        if question.question_type == "multiple_choice" and question.answer_json is not None:
            correct = str(question.answer_json)
            submitted = ans_val
            is_correct = (correct == submitted) if submitted else False
            earned = float(question.score) if is_correct else 0.0
            total_earned += earned

        # 역량별 점수 집계
        comp = question.competency_type or "기타"
        if comp not in competency_scores:
            competency_scores[comp] = {"earned": 0, "total": 0}
        competency_scores[comp]["earned"] += earned
        competency_scores[comp]["total"] += question.score

    # 역량별 퍼센트 계산
    competency_breakdown = {
        comp: round(v["earned"] / v["total"] * 100, 1) if v["total"] > 0 else 0
        for comp, v in competency_scores.items()
    }

    # 전체 만점 대비 100% 기준으로 환산 점수 계산
    if total_possible > 0:
        final_normalized_score = round((total_earned / total_possible) * 100, 1)
    else:
        final_normalized_score = 0.0

    # 합격 여부
    pass_score = diagnosis.pass_score if diagnosis else 70
    pass_yn = final_normalized_score >= pass_score

    record.status = "graded"
    record.submitted_at = datetime.utcnow()
    record.total_score = final_normalized_score
    record.pass_yn = pass_yn
    record.competency_breakdown_json = competency_breakdown
    record.answer_data = ",".join(answer_data_array)

    # 응시자 상태 완료
    applicant = db.query(Applicant).filter(Applicant.applicant_id == record.applicant_id).first()
    if applicant:
        applicant.status = "completed"

    db.commit()

    return {
        "message": "제출이 완료되었습니다.",
        "record_id": data.record_id,
        "total_score": final_normalized_score,
        "pass_yn": pass_yn,
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

    if diagnosis and diagnosis.question_idxs:
        q_idxs = [
            int(idx.strip())
            for idx in diagnosis.question_idxs.split(",")
            if idx.strip().isdigit()
        ]

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
