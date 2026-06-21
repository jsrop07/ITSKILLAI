from __future__ import annotations

import os
import json
from typing import Any
from types import SimpleNamespace
from sqlalchemy.orm import Session

from models import Record, Diagnosis, Question, ResultReport
from ai.reports.evidence_builder import build_report_evidence
from ai.reports.history_analyzer import build_previous_record_evidence, compare_with_previous_record
from ai.reports.report_renderer import render_result_report

def _load_questions_from_record_snapshot(record: Record) -> list[Any]:
    if not record.question_snapshot_json:
        return []

    try:
        snapshot = json.loads(record.question_snapshot_json)
    except Exception:
        return []

    if not isinstance(snapshot, list):
        return []

    questions = []

    for item in snapshot:
        if not isinstance(item, dict):
            continue

        questions.append(SimpleNamespace(
            question_id=item.get("question_id"),
            title=item.get("title") or "",
            body=item.get("body") or "",
            choices_json=item.get("choices_json"),
            answer_json=item.get("answer_json"),
            explanation=item.get("explanation"),
            difficulty=item.get("difficulty"),
            competency_type=item.get("competency_type"),
            competency_tags_json=item.get("competency_tags_json"),
            ai_generation_type=item.get("ai_generation_type"),
            score=item.get("score"),
        ))

    return questions

def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)

REPORT_SECTION_TITLES = [
    "[종합 진단]",
    "[체험형 분석 기준]",
    "[이전 대비 변화]",
    "[부족한 세부 영역]",
    "[관련 복습 근거]",
]

def _format_score(value: Any) -> str:
    if value is None:
        return "-"

    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _clean_evidence_preview(value: Any, max_len: int = 120) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    text = " ".join(text.split())

    if len(text) >= 80 and " " not in text[:80]:
        return ""

    noisy_patterns = [
        "나는 ",
        "나는인공지능",
        "할수있다",
        "할 수 있다",
        "제시할수있다",
        "제시할 수 있다",
        "선정할수있다",
        "선정할 수 있다",
        "파악할 수 있다",
        "분석할 수 있다",
        "수립할 수 있다",
        "작성할 수 있다",
        "검증할 수 있다",
        "수행할 수 있다",
        "평가자 체크리스트",
        "자기진단",
        "평가지",
        "수행준거",
        "학습자",
        "교수자",
    ]

    if any(pattern in text for pattern in noisy_patterns):
        return ""

    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."

    return text

def _build_study_point_for_subtopic(
    subtopic: str,
    items: list[dict[str, Any]],
) -> str:
    combined_text = " ".join(
        f"{item.get('title') or ''} {item.get('body') or ''} {item.get('explanation') or ''}"
        for item in items
    )

    if subtopic == "RAG":
        if _contains_any(combined_text, ["vector", "벡터", "keyword", "키워드"]):
            return "RAG의 역할과 Vector Search / Keyword Search의 차이를 다시 확인하세요."
        if _contains_any(combined_text, ["chunk", "청크", "embedding", "임베딩", "metadata", "메타데이터"]):
            return "Chunk, Embedding, Metadata가 RAG 검색에서 어떤 역할을 하는지 정리하세요."
        return "외부 문서 검색 결과를 LLM 답변 생성에 활용하는 RAG 흐름을 복습하세요."

    if subtopic == "ML":
        if _contains_any(combined_text, ["overfitting", "과적합", "train/test", "validation", "검증"]):
            return "train/test 데이터 분리와 과적합 판단 기준을 다시 확인하세요."
        if _contains_any(combined_text, ["데이터 누수", "전처리", "학습 데이터"]):
            return "데이터 누수를 막기 위한 전처리 기준과 학습 데이터 분리 방식을 복습하세요."
        if _contains_any(combined_text, ["recall", "precision", "f1", "accuracy", "정확도", "재현율", "정밀도"]):
            return "Accuracy, Precision, Recall, F1의 차이를 다시 정리하세요."
        return "모델 학습 절차와 평가 기준을 다시 정리하세요."

    if subtopic == "AI 기본":
        if _contains_any(combined_text, ["지도학습", "비지도학습", "분류", "예측"]):
            return "지도학습, 비지도학습, 분류, 예측의 차이를 다시 정리하세요."
        return "AI 기본 용어와 학습·추론의 차이를 복습하세요."

    if subtopic == "LLM":
        return "프롬프트, 구조화 출력, 환각 방지 방식의 차이를 복습하세요."

    if subtopic == "ModelOps":
        return "모델 서빙, Latency, Monitoring의 역할을 다시 확인하세요."

    if subtopic == "DL":
        return "학습 손실, 검증 손실, 과적합 판단 기준을 다시 확인하세요."

    return f"{subtopic} 핵심 개념과 오답 문항 해설을 다시 확인하세요."

def _build_external_search_keywords(
    subtopic: str,
    items: list[dict[str, Any]],
) -> str:
    combined_text = " ".join(
        f"{item.get('title') or ''} {item.get('body') or ''} {item.get('explanation') or ''}"
        for item in items
    )

    if subtopic == "RAG":
        keywords = ["RAG"]

        if _contains_any(combined_text, ["vector", "벡터", "keyword", "키워드"]):
            keywords.extend(["Vector Search", "Keyword Search", "Embedding"])
        elif _contains_any(combined_text, ["chunk", "청크", "metadata", "메타데이터"]):
            keywords.extend(["Chunking", "Embedding", "Metadata"])
        else:
            keywords.extend(["Retrieval Augmented Generation", "LLM 검색 증강"])

        return ", ".join(dict.fromkeys(keywords))

    if subtopic == "ML":
        keywords = ["Machine Learning"]

        if _contains_any(combined_text, ["overfitting", "과적합", "train/test", "validation", "검증"]):
            keywords.extend(["Overfitting", "Train Test Split", "Validation Set"])
        if _contains_any(combined_text, ["데이터 누수", "data leakage", "전처리", "학습 데이터"]):
            keywords.extend(["Data Leakage", "Preprocessing", "Train Test Split"])
        if _contains_any(combined_text, ["recall", "precision", "f1", "accuracy", "정확도", "재현율", "정밀도"]):
            keywords.extend(["Accuracy", "Precision", "Recall", "F1 Score"])

        return ", ".join(list(dict.fromkeys(keywords))[:5])

    if subtopic == "AI 기본":
        keywords = ["AI 기본 개념"]

        if _contains_any(combined_text, ["지도학습", "비지도학습", "분류", "예측"]):
            keywords.extend(["지도학습", "비지도학습", "분류", "예측"])
        else:
            keywords.extend(["학습", "추론", "모델"])

        return ", ".join(dict.fromkeys(keywords))

    if subtopic == "LLM":
        return "LLM, Prompt Engineering, Structured Output, Hallucination"

    if subtopic == "ModelOps":
        return "ModelOps, Model Serving, Latency, Monitoring, Drift"

    if subtopic == "DL":
        return "Deep Learning, Overfitting, Validation Loss, Dropout"

    return subtopic

def _build_study_evidence_section(current_evidence: dict[str, Any]) -> str:
    evidence_map = current_evidence.get("study_evidence_by_subtopic", {}) or {}
    grouped = current_evidence.get("wrong_answers_by_subtopic", {}) or {}

    lines: list[str] = ["[복습 참고 방향]"]

    if not grouped:
        lines.append("- 현재 결과에서 별도로 제안할 복습 방향이 없습니다.")
        return "\n".join(lines)

    has_any = False

    for subtopic, items in grouped.items():
        if not items:
            continue

        has_any = True

        study_point = _build_study_point_for_subtopic(subtopic, items)
        keywords = _build_external_search_keywords(subtopic, items)

        lines.append(f"- {subtopic}: {study_point}")

        if keywords:
            lines.append(f"  - 참고 키워드: {keywords}")

    if not has_any:
        lines.append("- 현재 결과에서 별도로 제안할 복습 방향이 없습니다.")

    return "\n".join(lines)

def _normalize_short_text(value: Any, max_len: int = 120) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    text = " ".join(text.split())

    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."

    return text


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = str(text or "").lower()
    return any(keyword.lower() in lowered for keyword in keywords)

def _ensure_period(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return ""

    if text.endswith((".", "!", "?")):
        return text

    return text + "."

def _summarize_subtopic_wrong_answers(subtopic: str, items: list[dict[str, Any]]) -> str:
    """
    같은 subtopic의 오답 문항들을 1~2문장으로 요약한다.

    핵심 원칙:
    - 문항별 safe_report_sentence를 그대로 나열하지 않는다.
    - negative 문항의 correct_choice_text를 올바른 개념처럼 설명하지 않는다.
    - RAG negative는 반드시 안전 문장으로 고정한다.
    """

    titles = [
        _normalize_short_text(item.get("title"), 80)
        for item in items
        if item.get("title")
    ]

    bodies = [
        _normalize_short_text(item.get("body"), 120)
        for item in items
        if item.get("body")
    ]

    explanations = [
        _normalize_short_text(item.get("explanation"), 140)
        for item in items
        if item.get("explanation")
    ]

    combined_text = " ".join(titles + bodies + explanations)

    has_negative = any(bool(item.get("is_negative_question")) for item in items)

    # 1) RAG는 가장 강하게 방어
    if subtopic == "RAG":
        focus_parts: list[str] = []

        if _contains_any(combined_text, ["vector", "벡터", "semantic", "의미 유사도"]):
            focus_parts.append("Vector Search")
        if _contains_any(combined_text, ["keyword", "키워드", "단어 일치"]):
            focus_parts.append("Keyword Search")
        if _contains_any(combined_text, ["hybrid", "하이브리드", "rrf", "rerank", "reranker"]):
            focus_parts.append("하이브리드 검색")
        if _contains_any(combined_text, ["chunk", "청크", "metadata", "메타데이터", "embedding", "임베딩"]):
            focus_parts.append("문서 검색 구성 요소")

        if not focus_parts:
            focus_parts.append("RAG의 역할과 검색 방식")

        focus_text = "과 ".join(focus_parts[:2])

        if has_negative:
            return (
                f"- RAG: {focus_text} 관련 문항에서 오답이 있었습니다. "
                "RAG는 SQL 명령으로 데이터베이스 트랜잭션을 관리하는 기술이 아니라, "
                "외부 문서나 지식을 검색해 LLM의 답변 생성에 활용하는 방식입니다. "
                "Vector Search는 의미 유사도 기반 검색이고, Keyword Search는 단어 일치 기반 검색이라는 차이도 함께 정리할 필요가 있습니다."
            )

        return (
            f"- RAG: {focus_text} 관련 문항에서 오답이 있었습니다. "
            "RAG는 외부 문서나 지식을 검색해 LLM 답변 생성에 활용하는 방식입니다. "
            "검색 방식, 근거 문서 활용, 임베딩과 키워드 검색의 차이를 함께 정리할 필요가 있습니다."
        )

    # 2) ML 요약
    if subtopic == "ML":
        points: list[str] = []

        if _contains_any(combined_text, ["overfitting", "과적합", "train/test", "train test", "validation", "검증"]):
            points.append("train/test 성능 차이가 큰 경우 과적합 가능성을 점검해야 합니다")
        if _contains_any(combined_text, ["data leakage", "데이터 누수", "전처리", "학습 데이터"]):
            points.append("데이터 누수를 막기 위해 학습 데이터 기준으로 전처리 기준을 정해야 합니다")
        if _contains_any(combined_text, ["recall", "precision", "f1", "accuracy", "정확도", "재현율", "정밀도"]):
            points.append("모델 평가는 accuracy만 보지 말고 precision, recall, F1을 함께 확인해야 합니다")
        if _contains_any(combined_text, ["imbalance", "불균형", "threshold", "임계값"]):
            points.append("클래스 불균형이나 임계값 변화가 평가 결과에 미치는 영향도 함께 확인해야 합니다")

        if not points:
            points.append("모델 학습 절차와 평가 기준을 다시 정리할 필요가 있습니다")

        return (
            "- ML: 모델 성능 점검과 학습 절차 관련 문항에서 오답이 있었습니다. "
            + " ".join(_ensure_period(point) for point in points[:2])
        )

    # 3) DL 요약
    if subtopic == "DL":
        points: list[str] = []

        if _contains_any(combined_text, ["overfitting", "과적합", "validation loss", "train loss"]):
            points.append("학습 손실과 검증 손실의 차이를 보고 과적합 가능성을 점검해야 합니다")
        if _contains_any(combined_text, ["dropout", "드롭아웃", "learning rate", "학습률", "epoch", "에폭"]):
            points.append("드롭아웃, 학습률, 에폭 같은 학습 조정 요소의 역할을 정리할 필요가 있습니다")
        if _contains_any(combined_text, ["cnn", "rnn", "transformer", "attention", "역전파", "backpropagation"]):
            points.append("딥러닝 모델 구조와 학습 방식의 차이를 구분할 필요가 있습니다")

        if not points:
            points.append("딥러닝 학습 과정과 모델 구조 관련 개념을 다시 정리할 필요가 있습니다")

        return (
            "- DL: 딥러닝 학습 과정과 모델 구조 관련 문항에서 오답이 있었습니다. "
            + " ".join(_ensure_period(point) for point in points[:2])
        )

    # 4) LLM 요약
    if subtopic == "LLM":
        points: list[str] = []

        if _contains_any(combined_text, ["prompt", "프롬프트", "system prompt", "few-shot", "few shot"]):
            points.append("프롬프트 구성과 지시문 역할을 구분해 정리할 필요가 있습니다")
        if _contains_any(combined_text, ["json", "schema", "structured output", "구조화"]):
            points.append("LLM 출력은 JSON schema나 structured output으로 형식을 제한할 수 있습니다")
        if _contains_any(combined_text, ["hallucination", "환각", "근거", "검증"]):
            points.append("환각을 줄이기 위해 근거 확인과 출력 검증 절차가 필요합니다")
        if _contains_any(combined_text, ["tool", "function", "함수 호출", "tool calling"]):
            points.append("Tool calling은 모델이 외부 기능을 호출하도록 연결하는 방식입니다")

        if not points:
            points.append("LLM의 입력, 출력, 검증 흐름을 다시 정리할 필요가 있습니다")

        return (
            "- LLM: LLM 활용 방식과 출력 제어 관련 문항에서 오답이 있었습니다. "
            + " ".join(_ensure_period(point) for point in points[:2])
        )

    # 5) ModelOps 요약
    if subtopic == "ModelOps":
        points: list[str] = []

        if _contains_any(combined_text, ["latency", "지연", "timeout", "타임아웃"]):
            points.append("Latency는 요청 후 응답을 받기까지 걸리는 시간이므로 처리량이나 정확도와 구분해야 합니다")
        if _contains_any(combined_text, ["monitoring", "모니터링", "drift", "로그", "장애"]):
            points.append("운영 환경에서는 로그, 모니터링, 드리프트 감지를 통해 모델 상태를 점검해야 합니다")
        if _contains_any(combined_text, ["serving", "서빙", "endpoint", "엔드포인트", "배포", "inference", "추론"]):
            points.append("모델 서빙은 학습된 모델을 실제 요청에 응답할 수 있도록 운영하는 과정입니다")

        if not points:
            points.append("모델 배포, 서빙, 모니터링 흐름을 다시 정리할 필요가 있습니다")

        return (
            "- ModelOps: 모델 운영과 서빙 관련 문항에서 오답이 있었습니다. "
            + " ".join(_ensure_period(point) for point in points[:2])
        )

    # 6) AI 기본 요약
    if subtopic == "AI 기본":
        points: list[str] = []

        if _contains_any(combined_text, ["지도학습", "비지도학습", "분류", "예측"]):
            points.append("지도학습, 비지도학습, 분류, 예측의 차이를 구분할 필요가 있습니다")
        if _contains_any(combined_text, ["학습", "추론", "모델"]):
            points.append("모델 학습과 추론의 역할을 다시 정리할 필요가 있습니다")
        if _contains_any(combined_text, ["정의", "개념", "목적", "특징"]):
            points.append("AI 기본 용어의 정의와 목적을 정확히 구분할 필요가 있습니다")

        if not points:
            points.append("AI 기본 개념과 용어를 다시 정리할 필요가 있습니다")

        return (
            "- AI 기본: AI 기본 개념 관련 문항에서 오답이 있었습니다. "
            + " ".join(_ensure_period(point) for point in points[:2])
        )

    # 7) 기타 fallback
    first_explanation = explanations[0] if explanations else ""
    if first_explanation:
        return (
            f"- {subtopic}: {subtopic} 관련 문항에서 오답이 있었습니다. "
            f"{first_explanation}"
        )

    return (
        f"- {subtopic}: {subtopic} 관련 문항에서 오답이 있었습니다. "
        "해당 영역의 핵심 개념을 다시 정리할 필요가 있습니다."
    )


def _build_safe_weak_area_section(current_evidence: dict[str, Any]) -> str:
    grouped = current_evidence.get("wrong_answers_by_subtopic", {}) or {}
    subtopic_stats = current_evidence.get("subtopic_stats", []) or []

    lines: list[str] = ["[부족한 세부 영역]"]

    if not grouped:
        lines.append("- 현재 결과에서 별도로 정리할 오답 영역이 없습니다.")
        return "\n".join(lines)

    # subtopic_stats 정렬 순서를 유지한다.
    # 현재 build_subtopic_stats는 정확도 낮은 영역부터 정렬되어 있으므로,
    # 리포트에서도 약한 영역이 먼저 나오게 된다.
    ordered_subtopics = [
        stat.get("key")
        for stat in subtopic_stats
        if stat.get("key") in grouped and int(stat.get("wrong_count", 0) or 0) > 0
    ]

    # 혹시 stats에 없지만 grouped에 있는 영역이 있으면 뒤에 추가
    for subtopic in grouped.keys():
        if subtopic not in ordered_subtopics:
            ordered_subtopics.append(subtopic)

    for subtopic in ordered_subtopics:
        items = grouped.get(subtopic) or []
        if not items:
            continue

        lines.append(_summarize_subtopic_wrong_answers(subtopic, items))

    if len(lines) == 1:
        lines.append("- 현재 결과에서 별도로 정리할 오답 영역이 없습니다.")

    return "\n".join(lines)


def _replace_report_section(report_text: str, section_title: str, replacement: str) -> str:
    if not report_text:
        return replacement

    start = report_text.find(section_title)

    if start < 0:
        # 섹션이 없으면 추천 학습 순서 앞에 삽입
        next_title = "[추천 학습 순서]"
        next_start = report_text.find(next_title)
        if next_start >= 0:
            return (
                report_text[:next_start].rstrip()
                + "\n\n"
                + replacement.strip()
                + "\n\n"
                + report_text[next_start:].lstrip()
            )
        return report_text.rstrip() + "\n\n" + replacement.strip()

    next_positions = [
        report_text.find(title, start + len(section_title))
        for title in REPORT_SECTION_TITLES
        if title != section_title and report_text.find(title, start + len(section_title)) >= 0
    ]

    end = min(next_positions) if next_positions else len(report_text)

    return (
        report_text[:start].rstrip()
        + "\n\n"
        + replacement.strip()
        + "\n\n"
        + report_text[end:].lstrip()
    ).strip()

def _remove_report_section(report_text: str, section_title: str) -> str:
    if not report_text:
        return report_text

    start = report_text.find(section_title)

    if start < 0:
        return report_text

    next_positions = [
        report_text.find(title, start + len(section_title))
        for title in REPORT_SECTION_TITLES
        if title != section_title and report_text.find(title, start + len(section_title)) >= 0
    ]

    end = min(next_positions) if next_positions else len(report_text)

    return (
        report_text[:start].rstrip()
        + "\n\n"
        + report_text[end:].lstrip()
    ).strip()
    
def normalize_report_text(text: str) -> str:
    replacements = {
        "개념입니다.를": "개념을",
        "방식입니다.를": "방식을",
        "합니다.라는 점": "한다는 점",
        "입니다.라는 점": "이라는 점",
        "정답 보기를 선택하지 못했습니다": "해당 설명이 적절하지 않다는 점을 구분하지 못했습니다",
        "정답 보기": "해당 보기",
        "하회": "낮음",
        "처리하였습니다": "나타났습니다",
        "간과했습니다": "놓쳤습니다",
        "잘못 이해했습니다": "혼동이 있었습니다",
        "이해가 부족합니다": "다시 정리할 필요가 있습니다",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text

def _load_current_record_bundle(db: Session, record_id: int) -> tuple[Record, Diagnosis, list[Question]]:
    record = db.query(Record).filter(Record.record_id == record_id).first()
    if not record:
        raise ValueError("응시 기록을 찾을 수 없습니다.")

    if record.status != "graded":
        raise ValueError("채점 완료된 기록만 AI 리포트를 생성할 수 있습니다.")

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.diagnosis_id == record.diagnosis_id
    ).first()

    if not diagnosis:
        raise ValueError("시험 정보를 찾을 수 없습니다.")

    snapshot_questions = _load_questions_from_record_snapshot(record)
    if snapshot_questions:
        return record, diagnosis, snapshot_questions

    # fallback: 스냅샷이 없는 예전 record만 DB 기준 사용
    if not diagnosis.question_idxs:
        raise ValueError("시험 문항 정보가 없습니다.")

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
        db=db,
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

    safe_weak_area_section = _build_safe_weak_area_section(current_evidence)

    report_text = _replace_report_section(
        report_text=report_text,
        section_title="[부족한 세부 영역]",
        replacement=safe_weak_area_section,
    )

    study_evidence_section = _build_study_evidence_section(current_evidence)

    report_text = _replace_report_section(
        report_text=report_text,
        section_title="[복습 참고 방향]",
        replacement=study_evidence_section,
    )

    report_text = _remove_report_section(
        report_text=report_text,
        section_title="[추천 학습 순서]",
    )

    report_text = normalize_report_text(report_text)

    report_quality_checks = _validate_report_text(
        report_text=report_text,
        current_evidence=current_evidence,
        history_comparison=history_comparison,
    )

    history_comparison["report_quality_checks"] = report_quality_checks

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
        "report_quality_checks": report_quality_checks,
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

    history_comparison = loads_or_default(report.history_comparison_json, {})

    return {
        "record_id": report.record_id,
        "report_id": report.report_id,
        "summary_comment": report.report_text,
        "subtopic_stats": loads_or_default(report.subtopic_stats_json, []),
        "history_comparison": history_comparison,
        "report_quality_checks": history_comparison.get("report_quality_checks"),
    }

def _validate_report_text(
    report_text: str,
    current_evidence: dict[str, Any],
    history_comparison: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, message: str) -> None:
        checks.append({
            "name": name,
            "passed": passed,
            "message": message,
        })

    text = report_text or ""
    comparison_mode = history_comparison.get("comparison_mode")
    is_direct_cbt = comparison_mode == "direct_cbt_current_only"

    if is_direct_cbt:
        add_check(
            name="direct_cbt_section_check",
            passed="[이전 대비 변화]" not in text and "[체험형 분석 기준]" in text,
            message="direct-cbt는 [이전 대비 변화] 없이 [체험형 분석 기준]을 사용해야 합니다.",
        )
    else:
        add_check(
            name="normal_exam_section_check",
            passed="[이전 대비 변화]" in text,
            message="일반 관리자 시험은 [이전 대비 변화] 섹션을 사용할 수 있습니다.",
        )

    forbidden_rag_patterns = [
        "RAG는 SQL 명령으로 데이터베이스 트랜잭션을 관리하는 기술입니다",
        "RAG는 SQL 트랜잭션 관리 기술입니다",
        "RAG는 데이터베이스 트랜잭션을 관리하는 기술입니다",
        "RAG는 SQL을 통해 트랜잭션을 관리합니다",
    ]

    rag_forbidden_found = any(pattern in text for pattern in forbidden_rag_patterns)

    add_check(
        name="rag_hallucination_check",
        passed=not rag_forbidden_found,
        message="RAG를 SQL 트랜잭션 관리 기술처럼 설명하면 안 됩니다.",
    )

    required_sections = [
        "[종합 진단]",
        "[부족한 세부 영역]",
        "[복습 참고 방향]",
    ]

    if is_direct_cbt:
        required_sections.append("[체험형 분석 기준]")
    else:
        required_sections.append("[이전 대비 변화]")

    missing_sections = [
        section for section in required_sections
        if section not in text
    ]

    add_check(
        name="required_section_check",
        passed=len(missing_sections) == 0,
        message=(
            "필수 섹션이 모두 포함되어 있습니다."
            if not missing_sections
            else f"누락된 섹션: {', '.join(missing_sections)}"
        ),
    )

    wrong_subtopics = {
        item.get("subtopic")
        for item in current_evidence.get("wrong_answer_summary", []) or []
        if item.get("subtopic")
    }

    known_subtopics = ["RAG", "LLM", "ModelOps", "ML", "DL", "AI 기본"]

    mentioned_weak_subtopics = {
        subtopic
        for subtopic in known_subtopics
        if f"- {subtopic}:" in text or f"{subtopic}:" in text
    }

    invalid_weak_subtopics = mentioned_weak_subtopics - wrong_subtopics

    add_check(
        name="weak_area_alignment_check",
        passed=len(invalid_weak_subtopics) == 0,
        message=(
            "부족한 세부 영역이 실제 오답 영역과 일치합니다."
            if not invalid_weak_subtopics
            else f"실제 오답이 없는데 포함된 영역: {', '.join(sorted(invalid_weak_subtopics))}"
        ),
    )

    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }