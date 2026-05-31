from database import get_db
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Question, Admin
from routers.auth import get_current_admin
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import QuestionCreate, QuestionUpdate, QuestionRead
from services.question_review_service import build_question_review_result

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=List[QuestionRead])
def list_questions(
    search: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    competency_type: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    ai_generation_type: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Question)
    if search:
        query = query.filter(Question.title.ilike(f"%{search}%"))
    if review_status:
        query = query.filter(Question.review_status == review_status)
    if source_type:
        query = query.filter(Question.source_type == source_type)
    if competency_type:
        query = query.filter(Question.competency_type == competency_type)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if ai_generation_type:
        query = query.filter(Question.ai_generation_type == ai_generation_type)
    if question_type:
        query = query.filter(Question.question_type == question_type)
    return query.order_by(Question.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=QuestionRead)
def create_question(data: QuestionCreate, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    question = Question(**data.model_dump(), created_by=current_admin.admin_id)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return question


@router.put("/{question_id}", response_model=QuestionRead)
def update_question(question_id: int, data: QuestionUpdate, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(question, key, value)
    db.commit()
    db.refresh(question)
    return question


@router.delete("/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    db.delete(question)
    db.commit()
    return {"message": "삭제되었습니다."}
@router.get("/review/generated")

def review_generated_questions(
    limit: int = Query(default=100, ge=1, le=500),
    competency_type: str = Query(default="ai"),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Question)
    if status and hasattr(Question, "review_status"):
        query = query.filter(Question.review_status == status)

    if competency_type:
        query = query.filter(Question.competency_type == competency_type)

    if status and hasattr(Question, "status"):
        query = query.filter(Question.status == status)

    if hasattr(Question, "created_at"):
        query = query.order_by(Question.created_at.desc())
    else:
        query = query.order_by(Question.question_id.desc())

    questions = query.limit(limit).all()

    return build_question_review_result(questions)