import os
import smtplib
from datetime import datetime
from dotenv import load_dotenv
from email.header import Header
from email.utils import formataddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "AI-ITSkill 관리자")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:3000")


def send_email(to_email: str, subject: str, html: str) -> None:
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[Email] SMTP_USER 또는 SMTP_PASSWORD가 설정되지 않았습니다. 메일 발송을 건너뜁니다.")
        return

    if not to_email:
        print("[Email] 수신자 이메일이 없습니다. 메일 발송을 건너뜁니다.")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    sender_email = MAIL_FROM or SMTP_USER
    sender_name = str(Header(MAIL_FROM_NAME, "utf-8"))

    message["From"] = formataddr((sender_name, sender_email))
    message["To"] = to_email
    message.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(sender_email, to_email, message.as_string())


def send_apply_notification_to_admin(
    *,
    name: str,
    email: str,
    phone: str | None = None,
    target_role: str | None = None,
    experience_level: str | None = None,
    tech_stack: str | None = None,
) -> None:
    if not ADMIN_EMAIL:
        print("[Email] ADMIN_EMAIL이 설정되지 않았습니다.")
        return

    subject = f"[IT 역량진단] 신규 응시 신청: {name}"

    html = f"""
    <h2>신규 응시 신청이 접수되었습니다.</h2>
    <p><b>이름:</b> {name}</p>
    <p><b>이메일:</b> {email}</p>
    <p><b>전화번호:</b> {phone or "-"}</p>
    <p><b>지원 직무:</b> {target_role or "-"}</p>
    <p><b>경력 수준:</b> {experience_level or "-"}</p>
    <p><b>기술 스택:</b> {tech_stack or "-"}</p>
    <br />
    <p>관리자 화면에서 응시자를 확인하고 시험을 배정해 주세요.</p>
    """

    send_email(ADMIN_EMAIL, subject, html)


def send_exam_assignment_to_applicant(
    *,
    applicant_name: str,
    applicant_email: str,
    diagnosis_title: str | None,
    login_token: str,
    deadline_at,
) -> None:
    subject = "[IT 역량진단] 시험 응시 안내"
    test_login_url = f"{FRONTEND_BASE_URL}/test-login"
    deadline_text = format_deadline_korean(deadline_at)

    info_table = build_info_table([
        ("시 험 명", diagnosis_title or "-"),
        ("응시마감일", deadline_text),
        ("아 이 디", applicant_email),
        ("로그인토큰", login_token),
    ])

    html = f"""
    <h2>IT 역량진단 시험이 배정되었습니다.</h2>
    <p>{applicant_name}님, 아래 정보로 시험에 응시해 주세요.</p>

    <hr />

    {info_table}

    <br />

    <p>
      <a href="{test_login_url}" target="_blank">
        응시자 로그인 페이지로 이동
      </a>
    </p>
    """

    send_email(applicant_email, subject, html)


def send_exam_submitted_to_admin(
    *,
    applicant_name: str,
    applicant_email: str,
    diagnosis_title: str | None,
    submitted_at: str | None,
    total_score: float | int | None,
    pass_yn: bool | None,
) -> None:
    if not ADMIN_EMAIL:
        print("[Email] ADMIN_EMAIL이 설정되지 않았습니다.")
        return

    subject = f"[IT 역량진단] 응시 완료: {applicant_name}"
    pass_text = "합격" if pass_yn else "불합격"

    info_table = build_info_table([
        ("응 시 자", applicant_name),
        ("이 메 일", applicant_email),
        ("시 험 명", diagnosis_title or "-"),
        ("제출일시", submitted_at or "-"),
        ("총    점", f"{total_score}점" if total_score is not None else "-"),
        ("결    과", pass_text),
    ])

    html = f"""
    <h2>응시자가 시험을 제출했습니다.</h2>

    <hr />

    {info_table}

    <br />

    <p>관리자 화면에서 응시 결과를 확인해 주세요.</p>
    """

    send_email(ADMIN_EMAIL, subject, html)


def send_result_published_to_applicant(
    *,
    applicant_name: str,
    applicant_email: str,
    diagnosis_title: str | None,
    total_score: float | int | None,
    pass_yn: bool | None,
    record_id: int,
) -> None:
    subject = "[IT 역량진단] 진단 결과가 공개되었습니다."
    result_url = f"{FRONTEND_BASE_URL}/test-result?record_id={record_id}"

    pass_text = "합격" if pass_yn else "불합격"

    info_table = build_info_table([
        ("시 험 명", diagnosis_title or "-"),
        ("총    점", f"{total_score}점" if total_score is not None else "-"),
        ("결    과", pass_text),
    ])

    html = f"""
    <h2>IT 역량진단 결과가 공개되었습니다.</h2>
    <p>{applicant_name}님, 응시하신 진단 결과를 확인하실 수 있습니다.</p>

    <hr />

    {info_table}

    <br />

    <p>
      <a href="{result_url}" target="_blank">
        결과 확인 페이지로 이동
      </a>
    </p>
    """

    send_email(applicant_email, subject, html)

def format_deadline_korean(value) -> str:
    if not value:
        return "-"

    if isinstance(value, datetime):
        return f"{value.month}월 {value.day}일까지"

    text = str(value)

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return f"{parsed.month}월 {parsed.day}일까지"
    except Exception:
        return text

def build_info_table(rows: list[tuple[str, str]]) -> str:
    row_html = ""

    for label, value in rows:
        row_html += f"""
        <tr>
          <td style="width:110px; font-weight:700; padding:4px 8px 4px 0; white-space:nowrap;">
            {label}
          </td>
          <td style="width:12px; font-weight:700; padding:4px 8px;">:</td>
          <td style="padding:4px 0;">{value or "-"}</td>
        </tr>
        """

    return f"""
    <table style="border-collapse:collapse; font-size:15px; line-height:1.7;">
      {row_html}
    </table>
    """