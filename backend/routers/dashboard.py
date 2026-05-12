from sqlalchemy import func
from database import get_db
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Record, Question, Diagnosis
from schemas import DashboardStats, WeakCompetency
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    from models import Applicant, Record as Rec, Question as Q

    total_applicants = db.query(func.count(Applicant.applicant_id)).scalar() or 0
    in_progress = db.query(func.count(Rec.record_id)).filter(
        Rec.status == "in_progress"
    ).scalar() or 0
    pending_review = db.query(func.count(Q.question_id)).filter(
        Q.review_status == "pending"
    ).scalar() or 0
    recent_questions = db.query(func.count(Q.question_id)).filter(
        Q.source_type == "ai"
    ).scalar() or 0

    return DashboardStats(
        total_applicants=total_applicants,
        in_progress_exams=in_progress,
        pending_review_questions=pending_review,
        recent_question_count=recent_questions,
    )


@router.get("/recent-records")
def get_recent_records(limit: int = 10, db: Session = Depends(get_db)):
    from models import Applicant

    records = (
        db.query(Record, Applicant, Diagnosis)
        .join(Applicant, Record.applicant_id == Applicant.applicant_id)
        .join(Diagnosis, Record.diagnosis_id == Diagnosis.diagnosis_id)
        .filter(Record.status == "graded")
        .order_by(Record.submitted_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for rec, app, diag in records:
        result.append({
            "record_id": rec.record_id,
            "applicant_id": app.applicant_id,
            "name": app.name,
            "role": app.target_role,
            "exam": diag.title,
            "score": rec.total_score,
            "pass_yn": rec.pass_yn,
            "status": rec.status,
            "submitted_at": rec.submitted_at.strftime("%Y-%m-%d") if rec.submitted_at else None,
        })
    return result


@router.get("/weak-competencies")
def get_weak_competencies(db: Session = Depends(get_db)):
    records = db.query(Record).filter(Record.status == "graded").all()
    comp_stats = {}
    for r in records:
        if r.competency_breakdown_json:
            for comp, score in r.competency_breakdown_json.items():
                if comp not in comp_stats:
                    comp_stats[comp] = {"total": 0, "count": 0}
                comp_stats[comp]["total"] += score
                comp_stats[comp]["count"] += 1
    
    results = []
    for comp, stats in comp_stats.items():
        results.append({
            "competency": comp,
            "avg_score": round(stats["total"] / stats["count"], 1),
            "count": stats["count"]
        })
    
    results.sort(key=lambda x: x["avg_score"])
    return results[:5]
