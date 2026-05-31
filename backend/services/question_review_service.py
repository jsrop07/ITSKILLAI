import json
import re
from difflib import SequenceMatcher
from typing import Any


def parse_choices(raw_choices: Any) -> list[str]:
    if raw_choices is None:
        return []

    if isinstance(raw_choices, list):
        return [str(choice).strip() for choice in raw_choices]

    if isinstance(raw_choices, str):
        try:
            parsed = json.loads(raw_choices)
            if isinstance(parsed, list):
                return [str(choice).strip() for choice in parsed]
        except Exception:
            pass

    return []


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w가-힣\s]", "", text)
    return text.lower().strip()


def extract_explanation_answer(explanation: str | None) -> int | None:
    if not explanation:
        return None

    match = re.match(r"^\s*정답은\s*([1-5])번입니다\.", explanation.strip())
    if not match:
        return None

    return int(match.group(1))


def has_raw_context_leak(text: str | None) -> bool:
    if not text:
        return False

    leak_patterns = [
        "RAG Context",
        "rag context",
        "vector_rank",
        "keyword_rank",
        "hybrid_score",
        "rrf_score",
        "search_source",
        "chunk_index",
        "content_preview",
        "metadata",
        "출처:",
        "문서명:",
        "파일명:",
    ]

    lowered = text.lower()

    for pattern in leak_patterns:
        if pattern.lower() in lowered:
            return True

    return False


def is_too_similar(a: str, b: str, threshold: float = 0.88) -> bool:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)

    if not a_norm or not b_norm:
        return False

    if a_norm == b_norm:
        return True

    ratio = SequenceMatcher(None, a_norm, b_norm).ratio()
    return ratio >= threshold


def validate_single_question(question: Any) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    question_id = get_question_id(question)
    title = getattr(question, "title", "") or ""
    body = getattr(question, "body", "") or ""
    choices = get_question_choices(question)
    answer = get_question_answer(question)
    explanation = getattr(question, "explanation", "") or ""

    if not body.strip():
        errors.append("body_empty")

    if len(choices) != 5:
        errors.append(f"choices_count_invalid:{len(choices)}")

    if len(choices) == 5:
        empty_choice_indexes = [
            index + 1 for index, choice in enumerate(choices) if not choice.strip()
        ]
        if empty_choice_indexes:
            errors.append(f"empty_choices:{empty_choice_indexes}")

        normalized_choices = [normalize_text(choice) for choice in choices]
        if len(set(normalized_choices)) != len(normalized_choices):
            errors.append("duplicate_choices_exact")

    if not isinstance(answer, int):
        try:
            answer = int(answer)
        except Exception:
            errors.append("answer_not_int")
            answer = None

    if answer is not None and not (1 <= answer <= 5):
        errors.append(f"answer_out_of_range:{answer}")

    if not explanation.strip():
        errors.append("explanation_empty")
    else:
        explanation_answer = extract_explanation_answer(explanation)

        if explanation_answer is None:
            errors.append("explanation_prefix_missing")
        elif answer is not None and explanation_answer != answer:
            errors.append(
                f"explanation_answer_mismatch:answer={answer},prefix={explanation_answer}"
            )

    if body and len(body.strip()) < 20:
        warnings.append("body_too_short")

    if explanation and len(explanation.strip()) < 30:
        warnings.append("explanation_too_short")

    if has_raw_context_leak(body):
        warnings.append("body_raw_context_leak_suspected")

    if has_raw_context_leak(explanation):
        warnings.append("explanation_raw_context_leak_suspected")

    if len(choices) == 5:
        choice_lengths = [len(choice) for choice in choices if choice]
        if choice_lengths:
            min_len = min(choice_lengths)
            max_len = max(choice_lengths)

            if min_len > 0 and max_len / min_len >= 2.8:
                warnings.append(
                    f"choice_length_imbalance:min={min_len},max={max_len}"
                )

        # 선택지끼리 거의 같은 문장인지 확인
        similar_pairs = []
        for i in range(len(choices)):
            for j in range(i + 1, len(choices)):
                if is_too_similar(choices[i], choices[j], threshold=0.9):
                    similar_pairs.append((i + 1, j + 1))

        if similar_pairs:
            errors.append(f"duplicate_choices_similar:{similar_pairs}")
    if answer is not None and 1 <= answer <= 5 and len(choices) == 5:
        correct_choice = choices[answer - 1]
        same_as_correct = []

        for index, choice in enumerate(choices):
            if index == answer - 1:
                continue

            if normalize_text(choice) == normalize_text(correct_choice):
                same_as_correct.append(index + 1)

        if same_as_correct:
            errors.append(f"duplicate_correct_choice_with:{same_as_correct}")
    return {
        "id": question_id,
        "title": title,
        "body": body,
        "choices": choices,
        "answer": answer,
        "explanation": explanation,
        "errors": errors,
        "warnings": warnings,
        "review_status": get_question_status(question),
        "review_result": "ERROR" if errors else "WARN" if warnings else "OK",
    }


def detect_duplicate_questions(review_items: list[dict[str, Any]]) -> None:
    for i in range(len(review_items)):
        for j in range(i + 1, len(review_items)):
            item_a = review_items[i]
            item_b = review_items[j]

            body_a = item_a.get("body", "")
            body_b = item_b.get("body", "")

            title_a = item_a.get("title", "")
            title_b = item_b.get("title", "")

            if is_too_similar(body_a, body_b, threshold=0.88):
                item_a["warnings"].append(
                    f"duplicate_body_suspected_with:{item_b.get('id')}"
                )
                item_b["warnings"].append(
                    f"duplicate_body_suspected_with:{item_a.get('id')}"
                )

            elif title_a and title_b and is_too_similar(title_a, title_b, threshold=0.95):
                item_a["warnings"].append(
                    f"duplicate_title_suspected_with:{item_b.get('id')}"
                )
                item_b["warnings"].append(
                    f"duplicate_title_suspected_with:{item_a.get('id')}"
                )

    for item in review_items:
        if item["errors"]:
            item["status"] = "ERROR"
        elif item["warnings"]:
            item["status"] = "WARN"
        else:
            item["status"] = "OK"


def build_question_review_result(questions: list[Any]) -> dict[str, Any]:
    items = [validate_single_question(question) for question in questions]

    detect_duplicate_questions(items)

    total = len(items)
    error_count = sum(1 for item in items if item["status"] == "ERROR")
    warn_count = sum(1 for item in items if item["status"] == "WARN")
    ok_count = sum(1 for item in items if item["status"] == "OK")

    return {
        "total": total,
        "ok_count": ok_count,
        "warn_count": warn_count,
        "error_count": error_count,
        "items": items,
    }

def get_question_id(question: Any) -> Any:
    return (
        getattr(question, "question_id", None)
        or getattr(question, "id", None)
    )


def get_question_choices(question: Any) -> list[str]:
    # 실제 Question 모델 기준
    parsed = parse_choices(getattr(question, "choices_json", None))
    if parsed:
        return parsed

    # fallback
    parsed = parse_choices(getattr(question, "choices", None))
    if parsed:
        return parsed

    return []


def get_question_answer(question: Any) -> int | None:
    # 실제 Question 모델 기준
    raw_answer = getattr(question, "answer_json", None)

    if raw_answer is not None:
        try:
            parsed = json.loads(raw_answer) if isinstance(raw_answer, str) else raw_answer

            # answer_json이 "3" 또는 3 형태인 경우
            if isinstance(parsed, (int, str)):
                return int(parsed)

            # answer_json이 {"answer": 3} 같은 형태인 경우
            if isinstance(parsed, dict):
                for key in ["answer", "correct_answer", "value"]:
                    if key in parsed:
                        return int(parsed[key])
        except Exception:
            try:
                return int(raw_answer)
            except Exception:
                pass

    # fallback
    raw_answer = getattr(question, "answer", None)
    if raw_answer is not None:
        try:
            return int(raw_answer)
        except Exception:
            pass

    return None


def get_question_status(question: Any) -> str | None:
    return (
        getattr(question, "review_status", None)
        or getattr(question, "status", None)
    )