from __future__ import annotations

import os
import json
from typing import Any

from sqlalchemy.orm import Session

from models import Record, Diagnosis, Question, ResultReport
from ai.reports.evidence_builder import build_report_evidence
from ai.reports.history_analyzer import build_previous_record_evidence, compare_with_previous_record
from ai.reports.report_renderer import render_result_report


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def _load_current_record_bundle(db: Session, record_id: int) -> tuple[Record, Diagnosis, list[Question]]:
    record = db.query(Record).filter(Record.record_id == record_id).first()
    if not record:
        raise ValueError("응시 기록을 찾을 수 없습니다.")

    if record.status != "graded":
        raise ValueError("채점 완료된 기록만 AI 리포트를 생성할 수 있습니다.")

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.diagnosis_id == record.diagnosis_id
    ).first()

    if not diagnosis or not diagnosis.question_idxs:
        raise ValueError("시험 정보를 찾을 수 없습니다.")

    q_ids = [
        int(x.strip())
        for x in diagnosis.question_idxs.split(",")
        if x.strip().isdigit()
    ]

    if not q_ids:
        raise ValueError("시험 문항 정보가 없습니다.")

    questions = db.query(Question).filter(
        Question.question_id.in_(q_ids)
    ).all()

    return record, diagnosis, questions


def _upsert_result_report(
    db: Session,
    record: Record,
    current_evidence: dict,
    history_comparison: dict,
    report_text: str,
) -> ResultReport:
    report = db.query(ResultReport).filter(
        ResultReport.record_id == record.record_id,
        ResultReport.report_type == "ai_result_analysis",
    ).first()

    if not report:
        report = ResultReport(
            record_id=record.record_id,
            applicant_id=record.applicant_id,
            report_type="ai_result_analysis",
        )
        db.add(report)

    report.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    report.current_analysis_json = _json_dumps(current_evidence.get("current_analysis", {}))
    report.subtopic_stats_json = _json_dumps(current_evidence.get("subtopic_stats", []))
    report.history_comparison_json = _json_dumps(history_comparison)
    report.wrong_answer_summary_json = _json_dumps(current_evidence.get("wrong_answer_summary", []))
    report.report_text = report_text

    record.summary_comment = report_text

    db.commit()
    db.refresh(report)
    db.refresh(record)

    return report


def generate_result_report_for_record(db: Session, record_id: int) -> dict[str, Any]:
    record, diagnosis, questions = _load_current_record_bundle(db, record_id)

    current_evidence = build_report_evidence(
        record=record,
        diagnosis=diagnosis,
        questions=questions,
    )

    previous_evidence = build_previous_record_evidence(db, record)

    history_comparison = compare_with_previous_record(
        current_evidence=current_evidence,
        previous_evidence=previous_evidence,
    )

    report_text = render_result_report(
        current_evidence=current_evidence,
        history_comparison=history_comparison,
    )

    if not report_text:
        raise ValueError("AI 리포트 생성에 실패했습니다.")

    report = _upsert_result_report(
        db=db,
        record=record,
        current_evidence=current_evidence,
        history_comparison=history_comparison,
        report_text=report_text,
    )

    return {
        "record_id": record.record_id,
        "report_id": report.report_id,
        "summary_comment": report.report_text,
        "subtopic_stats": current_evidence.get("subtopic_stats", []),
        "history_comparison": history_comparison,
    }


def get_result_report_for_record(db: Session, record_id: int) -> dict[str, Any] | None:
    report = db.query(ResultReport).filter(
        ResultReport.record_id == record_id,
        ResultReport.report_type == "ai_result_analysis",
    ).order_by(ResultReport.updated_at.desc()).first()

    if not report:
        return None

    def loads_or_default(value: str | None, default: Any):
        if not value:
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    return {
        "record_id": report.record_id,
        "report_id": report.report_id,
        "summary_comment": report.report_text,
        "subtopic_stats": loads_or_default(report.subtopic_stats_json, []),
        "history_comparison": loads_or_default(report.history_comparison_json, {}),
    }