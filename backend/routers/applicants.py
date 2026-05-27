
from database import get_db
from models import Applicant
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query,BackgroundTasks
from schemas import ApplicantCreate, ApplicantUpdate, ApplicantRead
from services.email_service import send_apply_notification_to_admin

router = APIRouter(prefix="/api/applicants", tags=["applicants"])

def _normalize_email(email: str) -> str:
    return email.strip().lower()
    
def _create_new_applicant_application(data: ApplicantCreate, db: Session) -> Applicant:
    payload = data.model_dump()
    payload["email"] = _normalize_email(payload["email"])

    applicant = Applicant(**payload)
    applicant.status = "pending"

    db.add(applicant)
    db.commit()
    db.refresh(applicant)

    return applicant

def _get_or_create_applicant_by_email(data: ApplicantCreate, db: Session) -> Applicant:
    payload = data.model_dump()
    normalized_email = _normalize_email(payload["email"])

    existing = db.query(Applicant).filter(
        Applicant.email == normalized_email
    ).first()

    if existing:
        # 같은 이메일이면 새 applicant를 만들지 않고 기존 응시자를 재사용한다.
        # 단, 사용자가 다시 입력한 최신 정보는 반영한다.
        existing.name = payload.get("name") or existing.name
        existing.email = normalized_email
        existing.phone = payload.get("phone")
        existing.target_role = payload.get("target_role")
        existing.experience_level = payload.get("experience_level")
        existing.tech_stack = payload.get("tech_stack")

        db.commit()
        db.refresh(existing)
        return existing

    payload["email"] = normalized_email
    applicant = Applicant(**payload)
    db.add(applicant)
    db.commit()
    db.refresh(applicant)
    return applicant

@router.get("", response_model=List[ApplicantRead])
def list_applicants(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    pass_yn: Optional[bool] = Query(None),
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
        
    if pass_yn is not None:
        results = [r for r in results if r.get("latest_pass_yn") is pass_yn]
        
    return results


@router.post("", response_model=ApplicantRead)
def create_applicant(data: ApplicantCreate, db: Session = Depends(get_db)):
    return _get_or_create_applicant_by_email(data=data, db=db)


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
    from models import Record
    applicant = db.query(Applicant).filter(Applicant.applicant_id == applicant_id).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="응시자를 찾을 수 없습니다.")
        
    records = db.query(Record).filter(Record.applicant_id == applicant_id).all()
    for r in records:
        db.delete(r)
        
    db.delete(applicant)
    db.commit()
    return {"message": "삭제되었습니다."}


# 응시자 시험 신청 (공개 엔드포인트)
@router.post("/apply", response_model=ApplicantRead)
def apply_exam(
    data: ApplicantCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    applicant = _create_new_applicant_application(data=data, db=db)

    background_tasks.add_task(
        send_apply_notification_to_admin,
        name=applicant.name,
        email=applicant.email,
        phone=applicant.phone,
        target_role=applicant.target_role,
        experience_level=applicant.experience_level,
        tech_stack=applicant.tech_stack,
    )

    return applicant