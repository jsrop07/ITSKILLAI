from __future__ import annotations

from typing import Any


COMPETENCY_LABEL_MAP = {
    "ai": "AI",
    "sql": "SQL",
    "python": "Python",
    "java": "Java",
    "c": "C",
    "network": "네트워크",
    "database": "데이터베이스",
    "software_engineering": "소프트웨어공학",
    "기타": "기타",
}

DIFFICULTY_LABEL_MAP = {
    "초급": "초급",
    "중급": "중급",
    "고급": "고급",
    "beginner": "초급",
    "intermediate": "중급",
    "advanced": "고급",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_answer(value: Any) -> str:
    """
    answer_json / answer_data 비교용 문자열 정규화.
    현재 프로젝트는 객관식 정답을 1~5 숫자 또는 문자열로 저장하므로
    문자열 비교 기준으로 통일한다.
    """
    if value is None:
        return ""

    return str(value).strip()


def _parse_question_ids(diagnosis) -> list[int]:
    if not diagnosis or not getattr(diagnosis, "question_idxs", None):
        return []

    result: list[int] = []
    for raw in str(diagnosis.question_idxs).split(","):
        raw = raw.strip()
        if raw.isdigit():
            result.append(int(raw))

    return result


def _parse_answer_data(record) -> list[str]:
    if not record or not getattr(record, "answer_data", None):
        return []

    return [answer.strip() for answer in str(record.answer_data).split(",")]


def _get_label(mapping: dict[str, str], key: Any, default: str = "기타") -> str:
    if key is None:
        return default

    key_str = str(key).strip()
    if not key_str:
        return default

    return mapping.get(key_str, key_str)


def _readable_choice_answer(value: Any, choices: Any) -> Any:
    """
    오답 목록에서 사용자가 고른 답/정답을 사람이 읽을 수 있게 변환한다.
    예: "3" + choices_json -> "3번. LLM은 ..."
    """
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


def _empty_stat(key: str, label: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "total_count": 0,
        "correct_count": 0,
        "wrong_count": 0,
        "accuracy_rate": 0.0,
        "earned_score": 0.0,
        "total_score": 0.0,
    }


def _finalize_stat(stat: dict[str, Any]) -> dict[str, Any]:
    total_count = stat["total_count"]
    correct_count = stat["correct_count"]

    stat["wrong_count"] = max(total_count - correct_count, 0)
    stat["accuracy_rate"] = (
        round((correct_count / total_count) * 100, 1)
        if total_count > 0
        else 0.0
    )
    stat["earned_score"] = round(_safe_float(stat["earned_score"]), 1)
    stat["total_score"] = round(_safe_float(stat["total_score"]), 1)

    return stat


def _build_recommendations(
    weak_competencies: list[dict[str, Any]],
    competency_stats: list[dict[str, Any]],
    difficulty_stats: list[dict[str, Any]],
    wrong_count: int,
    accuracy_rate: float,
) -> list[str]:
    recommendations: list[str] = []

    if accuracy_rate >= 80:
        recommendations.append(
            "전체 정답률이 높습니다. 고급 난이도 문제와 실무형 시나리오 문제를 중심으로 학습을 확장해도 좋습니다."
        )
    elif accuracy_rate >= 60:
        recommendations.append(
            "기본 개념은 어느 정도 이해하고 있으나, 오답이 발생한 역량의 개념 비교와 적용 조건을 다시 정리하는 것이 좋습니다."
        )
    else:
        recommendations.append(
            "전체 정답률이 낮은 편입니다. 먼저 초급 개념과 핵심 용어를 정리한 뒤 중급 문제로 넘어가는 것을 추천합니다."
        )

    has_multiple_competencies = len([
        item for item in competency_stats
        if item.get("total_count", 0) > 0
    ]) >= 2

    if has_multiple_competencies and weak_competencies:
        weak_labels = ", ".join(item["label"] for item in weak_competencies[:3])
        recommendations.append(
            f"상대적으로 낮은 역량은 {weak_labels}입니다. 해당 역량의 오답 문제를 먼저 복습하고, 관련 개념을 짧게 정리해보세요."
        )

    low_difficulty_items = [
        item for item in difficulty_stats
        if item["total_count"] > 0 and item["accuracy_rate"] < 60
    ]
    if low_difficulty_items:
        labels = ", ".join(item["label"] for item in low_difficulty_items)
        recommendations.append(
            f"{labels} 난이도에서 정답률이 낮습니다. 해당 난이도의 문제 풀이 기준과 자주 틀리는 선택지 유형을 다시 확인하세요."
        )

    if wrong_count > 0:
        recommendations.append(
            "오답 문제는 정답만 확인하지 말고, 내가 고른 선택지가 왜 부족했는지와 정답 선택지가 어떤 조건에서 가장 적절한지 함께 비교하세요."
        )

    return recommendations


def build_result_analysis_report(record, diagnosis, questions) -> dict[str, Any]:
    """
    시험 결과 분석 리포트 생성.

    입력:
    - record: Record SQLAlchemy 객체
    - diagnosis: Diagnosis SQLAlchemy 객체
    - questions: 해당 시험에 포함된 Question SQLAlchemy 객체 리스트

    반환:
    - schemas.py의 ResultAnalysisReport와 매칭되는 dict
    """

    question_ids = _parse_question_ids(diagnosis)
    submitted_answers = _parse_answer_data(record)

    question_map = {
        int(q.question_id): q
        for q in questions
        if getattr(q, "question_id", None) is not None
    }

    total_questions = 0
    correct_count = 0
    wrong_count = 0
    earned_score_sum = 0.0
    total_score_sum = 0.0

    competency_stats_map: dict[str, dict[str, Any]] = {}
    difficulty_stats_map: dict[str, dict[str, Any]] = {}
    wrong_answers: list[dict[str, Any]] = []

    for index, question_id in enumerate(question_ids):
        question = question_map.get(question_id)
        if not question:
            continue

        total_questions += 1

        submitted_answer = submitted_answers[index] if index < len(submitted_answers) else ""
        correct_answer = _normalize_answer(getattr(question, "answer_json", None))

        is_correct = bool(submitted_answer) and submitted_answer == correct_answer

        question_score = _safe_float(getattr(question, "score", 0))
        earned_score = question_score if is_correct else 0.0

        total_score_sum += question_score
        earned_score_sum += earned_score

        if is_correct:
            correct_count += 1
        else:
            wrong_count += 1

        competency_key = str(getattr(question, "competency_type", None) or "기타")
        competency_label = _get_label(COMPETENCY_LABEL_MAP, competency_key)

        difficulty_key = str(getattr(question, "difficulty", None) or "기타")
        difficulty_label = _get_label(DIFFICULTY_LABEL_MAP, difficulty_key, default=difficulty_key)

        if competency_key not in competency_stats_map:
            competency_stats_map[competency_key] = _empty_stat(
                key=competency_key,
                label=competency_label,
            )

        if difficulty_key not in difficulty_stats_map:
            difficulty_stats_map[difficulty_key] = _empty_stat(
                key=difficulty_key,
                label=difficulty_label,
            )

        competency_stat = competency_stats_map[competency_key]
        competency_stat["total_count"] += 1
        competency_stat["total_score"] += question_score
        competency_stat["earned_score"] += earned_score
        if is_correct:
            competency_stat["correct_count"] += 1

        difficulty_stat = difficulty_stats_map[difficulty_key]
        difficulty_stat["total_count"] += 1
        difficulty_stat["total_score"] += question_score
        difficulty_stat["earned_score"] += earned_score
        if is_correct:
            difficulty_stat["correct_count"] += 1

        if not is_correct:
            choices = getattr(question, "choices_json", None)

            wrong_answers.append({
                "question_id": question.question_id,
                "question_title": getattr(question, "title", "") or "",
                "competency_type": competency_key,
                "competency_label": competency_label,
                "difficulty": difficulty_label,
                "submitted_answer": _readable_choice_answer(submitted_answer, choices),
                "correct_answer": _readable_choice_answer(correct_answer, choices),
                "explanation": getattr(question, "explanation", None),
            })

    accuracy_rate = (
        round((correct_count / total_questions) * 100, 1)
        if total_questions > 0
        else 0.0
    )

    total_score = (
        round((earned_score_sum / total_score_sum) * 100, 1)
        if total_score_sum > 0
        else _safe_float(getattr(record, "total_score", 0))
    )

    pass_score = int(getattr(diagnosis, "pass_score", 70) or 70)
    pass_yn = bool(getattr(record, "pass_yn", False))

    competency_stats = [
        _finalize_stat(stat)
        for stat in competency_stats_map.values()
    ]

    difficulty_stats = [
        _finalize_stat(stat)
        for stat in difficulty_stats_map.values()
    ]

    valid_competency_stats = [
        item for item in competency_stats
        if item["total_count"] > 0
    ]

    if len(valid_competency_stats) >= 2:
        weak_competencies = sorted(
            valid_competency_stats,
            key=lambda item: (item["accuracy_rate"], -item["total_count"]),
        )[:3]
    else:
        weak_competencies = []

    recommendations = _build_recommendations(
        weak_competencies=weak_competencies,
        competency_stats=competency_stats,
        difficulty_stats=difficulty_stats,
        wrong_count=wrong_count,
        accuracy_rate=accuracy_rate,
    )
    return {
        "summary": {
            "total_questions": total_questions,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "accuracy_rate": accuracy_rate,
            "total_score": total_score,
            "pass_score": pass_score,
            "pass_yn": pass_yn,
        },
        "competency_stats": competency_stats,
        "difficulty_stats": difficulty_stats,
        "weak_competencies": weak_competencies,
        "wrong_answers": wrong_answers,
        "recommendations": recommendations,
    }