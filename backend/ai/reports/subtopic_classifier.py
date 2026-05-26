from __future__ import annotations

from typing import Any


SUBTOPIC_KEYWORDS: dict[str, list[str]] = {
    "RAG": [
        "rag", "retrieval", "검색", "chunk", "청크", "metadata", "메타데이터",
        "reranker", "rerank", "rrf", "vector", "벡터", "keyword", "키워드",
        "hybrid", "하이브리드", "top_k", "top-k", "embedding", "임베딩",
        "문서", "근거", "context", "컨텍스트"
    ],
    "LLM": [
        "llm", "prompt", "프롬프트", "json", "schema", "스키마",
        "structured output", "구조화", "tool calling", "tool", "함수 호출",
        "retry", "repair", "hallucination", "환각", "temperature",
        "system prompt", "few-shot", "few shot"
    ],
    "ModelOps": [
        "serving", "서빙", "vllm", "latency", "지연", "timeout", "타임아웃",
        "monitoring", "모니터링", "drift", "endpoint", "엔드포인트",
        "배포", "운영", "inference", "추론", "장애", "로그", "sla"
    ],
    "ML": [
        "accuracy", "precision", "recall", "f1", "feature", "피처",
        "train/test", "train test", "validation", "검증", "imbalance",
        "불균형", "class", "클래스", "threshold", "임계값",
        "confusion matrix", "교차 검증", "과소적합"
    ],
    "DL": [
        "deep learning", "딥러닝", "overfitting", "과적합", "train loss",
        "validation loss", "epoch", "에폭", "dropout", "드롭아웃",
        "learning rate", "학습률", "cnn", "rnn", "transformer",
        "attention", "backpropagation", "역전파"
    ],
    "AI 기본": [
        "정의", "개념", "목적", "특징", "기본", "모델", "학습", "추론",
        "인공지능", "ai", "분류", "예측", "지도학습", "비지도학습"
    ],
}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).lower()


def classify_question_subtopic(question: Any) -> str:
    text = " ".join([
        _normalize_text(getattr(question, "title", "")),
        _normalize_text(getattr(question, "body", "")),
        _normalize_text(getattr(question, "explanation", "")),
        _normalize_text(getattr(question, "choices_json", "")),
        _normalize_text(getattr(question, "competency_tags_json", "")),
        _normalize_text(getattr(question, "ai_generation_type", "")),
    ])

    scores: dict[str, int] = {}

    for subtopic, keywords in SUBTOPIC_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text:
                score += 1
        scores[subtopic] = score

    best_subtopic = max(scores, key=scores.get)

    if scores[best_subtopic] <= 0:
        return "AI 기본"

    return best_subtopic


def build_subtopic_stats(answer_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stats_map: dict[str, dict[str, Any]] = {}

    for subtopic in SUBTOPIC_KEYWORDS.keys():
        stats_map[subtopic] = {
            "key": subtopic,
            "label": subtopic,
            "total_count": 0,
            "correct_count": 0,
            "wrong_count": 0,
            "accuracy_rate": 0.0,
            "example_titles": [],
            "wrong_titles": [],
        }

    for item in answer_items:
        subtopic = item.get("subtopic") or "AI 기본"
        if subtopic not in stats_map:
            subtopic = "AI 기본"

        stat = stats_map[subtopic]
        stat["total_count"] += 1

        title = item.get("title") or ""
        if title and len(stat["example_titles"]) < 3:
            stat["example_titles"].append(title)

        if item.get("is_correct"):
            stat["correct_count"] += 1
        else:
            stat["wrong_count"] += 1
            if title and len(stat["wrong_titles"]) < 5:
                stat["wrong_titles"].append(title)

    result = []
    for stat in stats_map.values():
        total = stat["total_count"]
        correct = stat["correct_count"]
        stat["accuracy_rate"] = round((correct / total) * 100, 1) if total else 0.0
        if total > 0:
            result.append(stat)

    return sorted(
        result,
        key=lambda x: (x["accuracy_rate"], -x["wrong_count"], -x["total_count"])
    )