from __future__ import annotations

import logging
from typing import Any

from services.result_analysis import build_result_analysis_report
from ai.reports.subtopic_classifier import classify_question_subtopic, build_subtopic_stats
from ai.rag.document_service import build_context_and_evidence_from_search_results

logger = logging.getLogger("uvicorn.info")
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
def _answer_number(value: Any) -> str:
    normalized = _normalize_answer(value)
    if not normalized:
        return "-"

    try:
        idx = int(normalized)
        return f"{idx}번"
    except (TypeError, ValueError):
        return normalized


def _choice_text(value: Any, choices: Any) -> str:
    normalized = _normalize_answer(value)
    if not normalized or not isinstance(choices, list):
        return ""

    try:
        idx = int(normalized)
        if 1 <= idx <= len(choices):
            return str(choices[idx - 1])
    except (TypeError, ValueError):
        pass

    return ""
def _is_negative_question(title: Any, body: Any) -> bool:
    text = f"{_normalize_answer(title)} {_normalize_answer(body)}"

    negative_keywords = [
        "옳지 않은",
        "옳지않은",
        "아닌 것은",
        "아닌것",
        "잘못된",
        "틀린",
        "부적절한",
        "맞지 않는",
        "적절하지 않은",
        "거리가 먼",
    ]

    return any(keyword in text for keyword in negative_keywords)

def _clean_explanation(value: Any) -> str:
    text = _normalize_answer(value)

    if not text:
        return ""

    replacements = {
        "정답은": "올바른 기준은",
        "정답입니다": "입니다",
        "정답 보기": "해당 보기",
        "오답으로 처리하였습니다": "정답을 맞추지 못했습니다",
        "하회": "낮음",
        "처리하였습니다": "나타났습니다",
        "올바른 기준은": "올바른 답은",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()

def _is_rag_related_text(*values: Any) -> bool:
    text = " ".join(_normalize_answer(value).lower() for value in values)

    rag_keywords = [
        "rag",
        "retrieval",
        "검색",
        "문서",
        "근거",
        "vector",
        "벡터",
        "keyword",
        "키워드",
        "embedding",
        "임베딩",
        "chunk",
        "청크",
        "context",
        "컨텍스트",
        "retrieval augmented generation",
        "외부 지식",
        "외부 문서",
    ]

    return any(keyword in text for keyword in rag_keywords)

def _build_safe_report_sentence(item: dict[str, Any]) -> str:
    subtopic = item.get("subtopic") or "기타"
    title = item.get("title") or "해당 문항"
    body = item.get("body") or ""
    explanation = _clean_explanation(item.get("explanation"))
    is_negative = bool(item.get("is_negative_question"))
    correct_choice_text = _normalize_answer(item.get("correct_choice_text"))

    is_rag_negative = (
        is_negative
        and (
            subtopic == "RAG"
            or _is_rag_related_text(title, body, explanation, correct_choice_text)
        )
    )

    if is_negative:
        # RAG negative 문항은 subtopic 분류가 흔들려도 반드시 안전 문장으로 고정
        if is_rag_negative:
            return (
                "RAG: RAG 관련 문항에서 오답이 있었습니다. "
                "RAG는 SQL 명령으로 데이터베이스 트랜잭션을 관리하는 기술이 아니라, "
                "외부 문서나 지식을 검색해 LLM의 답변 생성에 활용하는 방식입니다. "
                "이 차이를 다시 정리할 필요가 있습니다."
            )

        if explanation:
            return (
                f"{subtopic}: {title} 문항에서 오답이 있었습니다. "
                "이 문항은 옳지 않은 설명을 고르는 문제이므로, 선택지 문장을 그대로 올바른 개념으로 보면 안 됩니다. "
                f"{explanation}"
            )

        return (
            f"{subtopic}: {title} 문항에서 오답이 있었습니다. "
            "이 문항은 옳지 않은 설명을 고르는 문제입니다. "
            "해설 정보가 부족하므로 해당 개념을 다시 확인할 필요가 있습니다."
        )

    if explanation:
        return (
            f"{subtopic}: {title} 문항에서 오답이 있었습니다. "
            f"{explanation}"
        )

    if correct_choice_text:
        return (
            f"{subtopic}: {title} 문항에서 오답이 있었습니다. "
            f"해당 문항은 {correct_choice_text} 내용을 다시 정리할 필요가 있습니다."
        )

    return (
        f"{subtopic}: {title} 문항에서 오답이 있었습니다. "
        "해당 개념을 다시 정리할 필요가 있습니다."
    )

def _build_study_query_for_subtopic(
    subtopic: str,
    items: list[dict[str, Any]],
) -> str:
    """
    오답 subtopic과 오답 문항 내용을 기반으로 복습 문서 검색 query를 만든다.
    너무 긴 문제 본문 전체를 넣기보다 title/body/explanation 일부만 사용한다.
    """

    topic_keywords = {
        "RAG": "RAG vector search keyword search hybrid search embedding",
        "LLM": "LLM prompt structured output hallucination",
        "ModelOps": "serving latency monitoring inference",
        "ML": "train test validation overfitting data leakage",
        "DL": "deep learning overfitting validation loss dropout",
        "AI 기본": "지도학습 비지도학습 분류 예측 학습 추론",
    }

    parts: list[str] = [
        subtopic,
        topic_keywords.get(subtopic, ""),
    ]

    for item in items[:3]:
        title = str(item.get("title") or "").strip()
        body = str(item.get("body") or "").strip()
        explanation = str(item.get("explanation") or "").strip()

        if title:
            parts.append(title[:120])
        if body:
            parts.append(body[:200])
        if explanation:
            parts.append(explanation[:200])

    query = " ".join(part for part in parts if part)
    query = " ".join(query.split())

    return query[:800]

def _build_study_evidence_by_subtopic(
    db: Any,
    wrong_answers_by_subtopic: dict[str, list[dict[str, Any]]],
    category: str | None = "ai",
    top_k: int = 2,
) -> dict[str, list[dict[str, Any]]]:
    """
    오답 subtopic별로 관련 문서 chunk를 검색해 복습 근거를 만든다.
    검색 실패가 AI 리포트 생성을 막으면 안 되므로 subtopic 단위로 예외 처리한다.
    """

    result: dict[str, list[dict[str, Any]]] = {}

    if db is None:
        return result

    for subtopic, items in wrong_answers_by_subtopic.items():
        if not items:
            continue

        query = _build_study_query_for_subtopic(subtopic, items)

        if not query:
            continue

        try:
            search_result = build_context_and_evidence_from_search_results(
                db=db,
                query=query,
                top_k=top_k,
                category=category,
                search_mode="hybrid",
            )

            evidence = search_result.get("evidence", {}) or {}
            documents = evidence.get("documents", []) or []

            result[subtopic] = [
                {
                    "title": doc.get("title"),
                    "file_name": doc.get("file_name"),
                    "category": doc.get("category"),
                    "source_type": doc.get("source_type"),
                    "chunk_id": doc.get("chunk_id"),
                    "chunk_index": doc.get("chunk_index"),
                    "page_hint": doc.get("page_hint"),
                    "search_source": doc.get("search_source"),
                    "vector_score": doc.get("vector_score"),
                    "keyword_score": doc.get("keyword_score"),
                    "hybrid_score": doc.get("hybrid_score"),
                    "quality_score": doc.get("quality_score"),
                    "content_preview": doc.get("content_preview"),
                }
                for doc in documents[:top_k]
            ]

        except Exception as e:
            logger.warning(
                f"AI Report RAG Evidence: 복습 근거 검색 실패 "
                f"(subtopic={subtopic}, error={str(e)})"
            )
            result[subtopic] = []

    return result


def build_report_evidence(record: Any,diagnosis: Any,questions: list[Any],db: Any = None,) -> dict[str, Any]:
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

        title = getattr(question, "title", "") or ""
        body = getattr(question, "body", "") or ""
        is_negative_question = _is_negative_question(title, body)
        submitted_choice_text = _choice_text(submitted_answer, choices)
        correct_choice_text = _choice_text(correct_answer, choices)
        explanation = getattr(question, "explanation", None)

        safe_report_sentence = _build_safe_report_sentence({
            "subtopic": subtopic,
            "title": title,
            "body": body,
            "explanation": explanation,
            "is_negative_question": is_negative_question,
            "correct_choice_text": correct_choice_text,
        })

        answer_items.append({
            "question_id": question.question_id,
            "title": title,
            "body": body,
            "difficulty": getattr(question, "difficulty", None),
            "competency_type": getattr(question, "competency_type", None),
            "subtopic": subtopic,

            # 이 줄이 반드시 있어야 함
            "is_correct": is_correct,

            "is_negative_question": is_negative_question,
            "answer_rule": (
                "이 문항은 옳지 않은 설명을 고르는 문제입니다. correct_answer는 올바른 개념이 아니라 틀린 보기입니다."
                if is_negative_question
                else "이 문항은 옳은 답을 고르는 문제입니다. correct_answer는 올바른 보기입니다."
            ),
            "submitted_answer": _answer_number(submitted_answer),
            "submitted_choice_text": submitted_choice_text,
            "correct_answer": _answer_number(correct_answer),
            "correct_choice_text": correct_choice_text,
            "explanation": explanation,
            "report_caution": (
                "이 문항은 옳지 않은 설명을 고르는 문제입니다. correct_choice_text는 올바른 개념이 아니라 '틀린 보기'입니다. 리포트에서 correct_choice_text 내용을 사실처럼 설명하지 말고, explanation에 있는 올바른 개념을 기준으로 설명해야 합니다."
                if is_negative_question
                else "이 문항은 옳은 답을 고르는 문제입니다. correct_choice_text는 올바른 보기입니다."
            ),
            "safe_report_sentence": safe_report_sentence,
        })

    subtopic_stats = build_subtopic_stats(answer_items)

    wrong_answer_summary = [
        {
            "question_id": item["question_id"],
            "title": item["title"],
            "body": item["body"],
            "subtopic": item["subtopic"],
            "difficulty": item["difficulty"],
            "is_negative_question": item.get("is_negative_question", False),
            "answer_rule": item.get("answer_rule"),
            "submitted_answer": item["submitted_answer"],
            "submitted_choice_text": item.get("submitted_choice_text"),
            "correct_answer": item["correct_answer"],
            "correct_choice_text": item.get("correct_choice_text"),
            "explanation": item["explanation"],
            "report_caution": item.get("report_caution"),
            "safe_report_sentence": item.get("safe_report_sentence"),
        }
        for item in answer_items
        if not item.get("is_correct", False)
    ]
    wrong_answers_by_subtopic: dict[str, list[dict[str, Any]]] = {}

    for item in wrong_answer_summary:
        subtopic = item.get("subtopic") or "AI 기본"
        if subtopic not in wrong_answers_by_subtopic:
            wrong_answers_by_subtopic[subtopic] = []
        wrong_answers_by_subtopic[subtopic].append(item)
        
    study_evidence_by_subtopic = _build_study_evidence_by_subtopic(
        db=db,
        wrong_answers_by_subtopic=wrong_answers_by_subtopic,
        category="ai",
        top_k=2,
    )
    return {
        "record_id": record.record_id,
        "applicant_id": record.applicant_id,
        "diagnosis_id": record.diagnosis_id,
        "entry_type": getattr(record, "entry_type", None),
        "diagnosis_title": getattr(diagnosis, "title", "") if diagnosis else "",
        "current_analysis": analysis_report,
        "subtopic_stats": subtopic_stats,
        "wrong_answer_summary": wrong_answer_summary,
        "wrong_answers_by_subtopic": wrong_answers_by_subtopic,
        "study_evidence_by_subtopic": study_evidence_by_subtopic,
        "answer_items": answer_items,
    }