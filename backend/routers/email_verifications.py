import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import EmailVerification
from schemas import (
    EmailVerificationSendRequest,
    EmailVerificationVerifyRequest,
    EmailVerificationResponse,
)
from services.email_service import send_email_verification_code


router = APIRouter(
    prefix="/api/email-verifications",
    tags=["email-verifications"],
)


ALLOWED_EMAIL_DOMAINS = {"gmail.com", "naver.com"}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_allowed_email_domain(email: str) -> None:
    domain = email.split("@")[-1].lower()

    if domain not in ALLOWED_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail="Gmail 또는 Naver 이메일만 사용할 수 있습니다.",
        )


@router.post("/send", response_model=EmailVerificationResponse)
def send_verification_code(
    data: EmailVerificationSendRequest,
    db: Session = Depends(get_db),
):
    email = _normalize_email(str(data.email))
    purpose = data.purpose or "diagnosis_apply"

    _validate_allowed_email_domain(email)

    code = f"{random.randint(0, 999999):06d}"
    expires_at = datetime.now() + timedelta(minutes=5)

    db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.purpose == purpose,
        EmailVerification.is_verified == False,
    ).delete(synchronize_session=False)

    verification = EmailVerification(
        email=email,
        code=code,
        purpose=purpose,
        is_verified=False,
        expires_at=expires_at,
    )

    db.add(verification)
    db.commit()

    try:
        send_email_verification_code(
            to_email=email,
            code=code,
        )
    except Exception as e:
        db.delete(verification)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"인증 메일 발송에 실패했습니다: {str(e)}",
        )

    return EmailVerificationResponse(
        success=True,
        message="인증코드가 이메일로 발송되었습니다.",
    )


@router.post("/verify", response_model=EmailVerificationResponse)
def verify_code(
    data: EmailVerificationVerifyRequest,
    db: Session = Depends(get_db),
):
    email = _normalize_email(str(data.email))
    purpose = data.purpose or "diagnosis_apply"

    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.email == email,
            EmailVerification.purpose == purpose,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    if not verification:
        raise HTTPException(
            status_code=400,
            detail="인증코드 발송 내역이 없습니다.",
        )

    if verification.is_verified:
        return EmailVerificationResponse(
            success=True,
            message="이미 이메일 인증이 완료되었습니다.",
        )

    if verification.expires_at < datetime.now():
        raise HTTPException(
            status_code=400,
            detail="인증코드가 만료되었습니다.",
        )

    if verification.code != data.code.strip():
        raise HTTPException(
            status_code=400,
            detail="인증코드가 일치하지 않습니다.",
        )

    verification.is_verified = True
    verification.verified_at = datetime.now()

    db.commit()

    return EmailVerificationResponse(
        success=True,
        message="이메일 인증이 완료되었습니다.",
    )