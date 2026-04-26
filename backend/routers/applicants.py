from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Applicant
from schemas import ApplicantCreate, ApplicantUpdate, ApplicantRead

router = APIRouter(prefix="/api/applicants", tags=["applicants"])


@router.get("", response_model=List[ApplicantRead])
def list_applicants(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    target_role: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Applicant)
    if search:
        query = query.filter(
            Applicant.name.ilike(f"%{search}%") | Applicant.email.ilike(f"%{search}%")
        )
    if status:
        query = query.filter(Applicant.status == status)
    if target_role:
        query = query.filter(Applicant.target_role == target_role)
    applicants = query.order_by(Applicant.created_at.desc()).offset(skip).limit(limit).all()
    results = []
    for app in applicants:
        app_dict = app.__dict__.copy()
        if app.records:
            latest = sorted(app.records, key=lambda r: r.created_at, reverse=True)[0]
            app_dict["latest_score"] = latest.total_score
            app_dict["latest_pass_yn"] = latest.pass_yn
        else:
            app_dict["latest_score"] = None
            app_dict["latest_pass_yn"] = None
        results.append(app_dict)
    return results


@router.post("", response_model=ApplicantRead)
def create_applicant(data: ApplicantCreate, db: Session = Depends(get_db)):
    applicant = Applicant(**data.model_dump())
    db.add(applicant)
    db.commit()
    db.refresh(applicant)
    return applicant


@router.get("/{applicant_id}", response_model=ApplicantRead)
def get_applicant(applicant_id: int, db: Session = Depends(get_db)):
    applicant = db.query(Applicant).filter(Applicant.applicant_id == applicant_id).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="응시자를 찾을 수 없습니다.")
    return applicant


@router.put("/{applicant_id}", response_model=ApplicantRead)
def update_applicant(applicant_id: int, data: ApplicantUpdate, db: Session = Depends(get_db)):
    applicant = db.query(Applicant).filter(Applicant.applicant_id == applicant_id).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="응시자를 찾을 수 없습니다.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(applicant, key, value)
    db.commit()
    db.refresh(applicant)
    return applicant


@router.delete("/{applicant_id}")
def delete_applicant(applicant_id: int, db: Session = Depends(get_db)):
    applicant = db.query(Applicant).filter(Applicant.applicant_id == applicant_id).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="응시자를 찾을 수 없습니다.")
    db.delete(applicant)
    db.commit()
    return {"message": "삭제되었습니다."}


# 응시자 시험 신청 (공개 엔드포인트)
@router.post("/apply", response_model=ApplicantRead)
def apply_exam(data: ApplicantCreate, db: Session = Depends(get_db)):
    applicant = Applicant(**data.model_dump())
    db.add(applicant)
    db.commit()
    db.refresh(applicant)
    return applicant
