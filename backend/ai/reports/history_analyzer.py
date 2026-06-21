from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import Record, Diagnosis, Question, Applicant
from ai.reports.evidence_builder import build_report_evidence


def get_previous_graded_record(db: Session, current_record: Record) -> Record | None:
    """
    현재 record의 바로 이전 graded record를 찾는다.

    주의:
    - applicants.email UNIQUE를 제거했기 때문에 같은 사람이 재신청하면 applicant_id가 달라질 수 있다.
    - 따라서 이전 기록 비교는 applicant_id가 아니라 같은 email을 가진 applicant들의 record 기준으로 조회한다.
    """

    # direct-cbt는 포트폴리오 체험용이므로 여러 사용자의 기록이 섞이지 않도록
    # 이전 기록 비교를 하지 않고 현재 결과 기준으로만 AI 리포트를 생성한다.
    if getattr(current_record, "entry_type", None) == "direct_cbt":
        return None

    current_applicant = db.query(Applicant).filter(
        Applicant.applicant_id == current_record.applicant_id
    ).first()

    if not current_applicant or not current_applicant.email:
        return None

    normalized_email = current_applicant.email.strip().lower()

    same_email_applicant_ids = [
        applicant_id
        for (applicant_id,) in db.query(Applicant.applicant_id)
        .filter(Applicant.email == normalized_email)
        .all()
    ]

    if not same_email_applicant_ids:
        return None

    query = db.query(Record).filter(
        Record.applicant_id.in_(same_email_applicant_ids),
        Record.diagnosis_id == current_record.diagnosis_id,
        Record.record_id != current_record.record_id,
        Record.status == "graded",
        Record.submitted_at.isnot(None),
    )

    if current_record.submitted_at:
        query = query.filter(Record.submitted_at < current_record.submitted_at)

    return query.order_by(Record.submitted_at.desc()).first()


def _load_record_questions(db: Session, record: Record) -> tuple[Diagnosis | None, list[Question]]:
    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.diagnosis_id == record.diagnosis_id
    ).first()

    if not diagnosis or not diagnosis.question_idxs:
        return diagnosis, []

    q_ids = [
        int(x.strip())
        for x in diagnosis.question_idxs.split(",")
        if x.strip().isdigit()
    ]

    if not q_ids:
        return diagnosis, []

    questions = db.query(Question).filter(
        Question.question_id.in_(q_ids)
    ).all()

    return diagnosis, questions


def _stats_to_map(stats: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        item["key"]: item
        for item in stats
        if item.get("key")
    }


def compare_with_previous_record(
    current_evidence: dict[str, Any],
    previous_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    current_summary = current_evidence.get("current_analysis", {}).get("summary", {})
    current_accuracy = float(current_summary.get("accuracy_rate", 0.0) or 0.0)

    if not previous_evidence:
        is_direct_cbt = current_evidence.get("entry_type") == "direct_cbt"

        return {
            "has_previous": False,
            "comparison_mode": "direct_cbt_current_only" if is_direct_cbt else "no_previous_same_diagnosis",
            "comparison_label": "체험형 진단은 현재 결과 기준으로만 분석합니다." if is_direct_cbt else "같은 시험지의 이전 응시 기록이 없어 현재 결과 기준으로 분석합니다.",
            "previous_record_id": None,
            "previous_accuracy": None,
            "current_accuracy": current_accuracy,
            "accuracy_delta": None,
            "improved_subtopics": [],
            "declined_subtopics": [],
            "persistent_weak_subtopics": [],
            "new_weak_subtopics": [],
        }

    previous_summary = previous_evidence.get("current_analysis", {}).get("summary", {})
    previous_accuracy = float(previous_summary.get("accuracy_rate", 0.0) or 0.0)

    current_map = _stats_to_map(current_evidence.get("subtopic_stats", []))
    previous_map = _stats_to_map(previous_evidence.get("subtopic_stats", []))

    improved = []
    declined = []
    persistent_weak = []
    new_weak = []

    all_keys = sorted(set(current_map.keys()) | set(previous_map.keys()))

    for key in all_keys:
        current_stat = current_map.get(key)
        previous_stat = previous_map.get(key)

        if not current_stat:
            continue

        cur_acc = float(current_stat.get("accuracy_rate", 0.0) or 0.0)
        prev_acc = float(previous_stat.get("accuracy_rate", 0.0) or 0.0) if previous_stat else None

        if previous_stat:
            delta = round(cur_acc - prev_acc, 1)

            item = {
                "key": key,
                "label": current_stat.get("label", key),
                "previous_accuracy": prev_acc,
                "current_accuracy": cur_acc,
                "delta": delta,
            }

            if delta >= 20:
                improved.append(item)
            elif delta <= -20:
                declined.append(item)

            if prev_acc < 60 and cur_acc < 60:
                persistent_weak.append(item)
        else:
            if cur_acc < 60:
                new_weak.append({
                    "key": key,
                    "label": current_stat.get("label", key),
                    "current_accuracy": cur_acc,
                })

    return {
        "has_previous": True,
        "comparison_mode": "same_email_same_diagnosis",
        "comparison_label": "같은 이메일과 같은 시험지의 이전 응시 기록을 기준으로 비교합니다.",
        "previous_record_id": previous_evidence.get("record_id"),
        "previous_accuracy": previous_accuracy,
        "current_accuracy": current_accuracy,
        "accuracy_delta": round(current_accuracy - previous_accuracy, 1),
        "improved_subtopics": improved,
        "declined_subtopics": declined,
        "persistent_weak_subtopics": persistent_weak,
        "new_weak_subtopics": new_weak,
    }


def build_previous_record_evidence(db: Session, current_record: Record) -> dict[str, Any] | None:
    previous_record = get_previous_graded_record(db, current_record)
    if not previous_record:
        return None

    previous_diagnosis, previous_questions = _load_record_questions(db, previous_record)
    if not previous_diagnosis or not previous_questions:
        return None

    return build_report_evidence(
        record=previous_record,
        diagnosis=previous_diagnosis,
        questions=previous_questions,
    )