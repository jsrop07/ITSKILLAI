from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Diagnosis, Question, Admin
from schemas import (
    DiagnosisCreate, DiagnosisUpdate, DiagnosisRead,
)
from routers.auth import get_current_admin

router = APIRouter(prefix="/api/diagnoses", tags=["diagnoses"])


@router.get("", response_model=List[DiagnosisRead])
def list_diagnoses(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    target_role: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Diagnosis)
    if search:
        query = query.filter(Diagnosis.title.ilike(f"%{search}%"))
    if status:
        query = query.filter(Diagnosis.status == status)
    if target_role:
        query = query.filter(Diagnosis.target_role == target_role)
    return query.order_by(Diagnosis.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=DiagnosisRead)
def create_diagnosis(data: DiagnosisCreate, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    diagnosis = Diagnosis(**data.model_dump(), created_by=current_admin.admin_id)
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


@router.get("/{diagnosis_id}", response_model=DiagnosisRead)
def get_diagnosis(diagnosis_id: int, db: Session = Depends(get_db)):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험을 찾을 수 없습니다.")
    return diagnosis


@router.put("/{diagnosis_id}", response_model=DiagnosisRead)
def update_diagnosis(diagnosis_id: int, data: DiagnosisUpdate, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험을 찾을 수 없습니다.")
    
    update_data = data.model_dump(exclude_unset=True)
    if "question_idxs" in update_data and update_data["question_idxs"] is not None:
        idxs = [x for x in update_data["question_idxs"].split(',') if x.strip()]
        update_data["question_count"] = len(idxs)

    for key, value in update_data.items():
        setattr(diagnosis, key, value)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


@router.delete("/{diagnosis_id}")
def delete_diagnosis(diagnosis_id: int, db: Session = Depends(get_db)):
    from models import Record, Applicant
    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="시험을 찾을 수 없습니다.")
        
    # FK 제약조건 확인
    if db.query(Record).filter(Record.diagnosis_id == diagnosis_id).first():
        raise HTTPException(status_code=400, detail="이 시험에 연결된 응시 기록이 있어 삭제할 수 없습니다.")
    if db.query(Applicant).filter(Applicant.target_diagnosis_id == diagnosis_id).first():
        raise HTTPException(status_code=400, detail="이 시험이 배정된 응시자가 있어 삭제할 수 없습니다.")
        
    try:
        db.delete(diagnosis)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"삭제 중 오류가 발생했습니다: {str(e)}")
        
    return {"message": "삭제되었습니다."}


# 문제집-문제 연결
@router.get("/{diagnosis_id}/questions")
def get_diagnosis_questions(diagnosis_id: int, db: Session = Depends(get_db)):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == diagnosis_id).first()
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
            result.append({
                "order_no": i + 1,
                "score": q.score,
                "question_id": q.question_id,
                "title": q.title,
                "question_type": q.question_type,
                "difficulty": q.difficulty,
                "competency_type": q.competency_type,
            })
    return result
