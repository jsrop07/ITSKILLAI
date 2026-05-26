from __future__ import annotations

from typing import Any

from services.result_analysis import build_result_analysis_report
from ai.reports.subtopic_classifier import classify_question_subtopic, build_subtopic_stats


def _normalize_answer(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_question_ids(diagnosis: Any) -> list[int]:
    if not diagnosis or not getattr(diagnosis, "question_idxs", None):
        return []

    result = []
    for raw in str(diagnosis.question_idxs).split(","):
        raw = raw.strip()
        if raw.isdigit():
            result.append(int(raw))
    return result


def _parse_answer_data(record: Any) -> list[str]:
    if not record or not getattr(record, "answer_data", None):
        return []
    return [x.strip() for x in str(record.answer_data).split(",")]


def _readable_choice_answer(value: Any, choices: Any) -> str:
    normalized = _normalize_answer(value)
    if not normalized:
        return "-"

    if not isinstance(choices, list):
        return normalized

    try:
        idx = int(normalized)
        if 1 <= idx <= len(choices):
            return f"{idx}번. {choices[idx - 1]}"
    except (TypeError, ValueError):
        pass

    return normalized


def build_report_evidence(record: Any, diagnosis: Any, questions: list[Any]) -> dict[str, Any]:
    analysis_report = build_result_analysis_report(
        record=record,
        diagnosis=diagnosis,
        questions=questions,
    )

    question_ids = _parse_question_ids(diagnosis)
    submitted_answers = _parse_answer_data(record)

    question_map = {
        int(q.question_id): q
        for q in questions
        if getattr(q, "question_id", None) is not None
    }

    answer_items: list[dict[str, Any]] = []

    for index, question_id in enumerate(question_ids):
        question = question_map.get(question_id)
        if not question:
            continue

        submitted_answer = submitted_answers[index] if index < len(submitted_answers) else ""
        correct_answer = _normalize_answer(getattr(question, "answer_json", None))
        is_correct = bool(submitted_answer) and submitted_answer == correct_answer
        choices = getattr(question, "choices_json", None)
        subtopic = classify_question_subtopic(question)

        answer_items.append({
            "question_id": question.question_id,
            "title": getattr(question, "title", "") or "",
            "body": getattr(question, "body", "") or "",
            "difficulty": getattr(question, "difficulty", None),
            "competency_type": getattr(question, "competency_type", None),
            "subtopic": subtopic,
            "is_correct": is_correct,
            "submitted_answer": _readable_choice_answer(submitted_answer, choices),
            "correct_answer": _readable_choice_answer(correct_answer, choices),
            "explanation": getattr(question, "explanation", None),
        })

    subtopic_stats = build_subtopic_stats(answer_items)

    wrong_answer_summary = [
        {
            "question_id": item["question_id"],
            "title": item["title"],
            "subtopic": item["subtopic"],
            "difficulty": item["difficulty"],
            "submitted_answer": item["submitted_answer"],
            "correct_answer": item["correct_answer"],
            "explanation": item["explanation"],
        }
        for item in answer_items
        if not item["is_correct"]
    ]

    return {
        "record_id": record.record_id,
        "applicant_id": record.applicant_id,
        "diagnosis_id": record.diagnosis_id,
        "diagnosis_title": getattr(diagnosis, "title", "") if diagnosis else "",
        "current_analysis": analysis_report,
        "subtopic_stats": subtopic_stats,
        "wrong_answer_summary": wrong_answer_summary,
        "answer_items": answer_items,
    }