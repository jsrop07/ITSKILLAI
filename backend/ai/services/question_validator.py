# backend/ai/services/question_validator.py

import re
import logging
from typing import Any

logger = logging.getLogger("uvicorn.info")


def validate_questions(
    questions: list,
    question_type: str,
    difficulty: str,
    score: int,
) -> list[dict[str, Any]]:
    """
    LLM이 생성한 문제 목록을 검증하고, 통과한 문제만 반환한다.

    - JSON 배열 구조 검증
    - 객관식 choices / answer / explanation 검증
    - 서술형/코드작성형 answer 검증
    - 품질 이슈는 가능한 한 quality_warnings로 남긴다.
    """
    return _validate_questions(
        questions=questions,
        question_type=question_type,
        difficulty=difficulty,
        score=score,
    )


def _extract_answer_number_from_explanation(explanation: str):
    if not explanation:
        return None

    patterns = [
        r"정답은\s*(\d)\s*번",
        r"정답\s*:\s*(\d)\s*번",
        r"답은\s*(\d)\s*번",
        r"(\d)\s*번이\s*정답",
    ]

    for pattern in patterns:
        match = re.search(pattern, explanation)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None

    return None


def _replace_answer_number_in_explanation(explanation: str, new_answer: int) -> str:
    """
    explanation 안의 '정답은 N번입니다' 형태를 새 정답 번호로 교체한다.

    주의:
    원래는 postprocessor 역할이지만, 현재 1단계에서는 validator가
    explanation_answer_mismatch를 자동 보정하므로 임시로 validator 안에 둔다.
    """
    if not explanation:
        return explanation

    patterns = [
        r"정답은\s*\d\s*번",
        r"정답\s*:\s*\d\s*번",
        r"답은\s*\d\s*번",
        r"\d\s*번이\s*정답",
    ]

    new_text = f"정답은 {new_answer}번"
    updated = explanation

    for pattern in patterns:
        if re.search(pattern, updated):
            updated = re.sub(pattern, new_text, updated, count=1)
            return updated

    return f"정답은 {new_answer}번입니다. {updated}"


def _remove_answer_number_from_explanation(explanation: str) -> str:
    """
    서술형/코드작성형 explanation에 잘못 들어간 객관식 정답 번호 표현을 제거한다.

    주의:
    원래는 postprocessor 역할이지만, 현재 1단계에서는 서술형 검증에서 바로 사용하므로
    임시로 validator 안에 둔다.
    """
    if not explanation:
        return explanation

    cleaned = str(explanation)

    patterns = [
        r"\d+\)\s*정답\s*번호\s*:\s*\d+\s*",
        r"정답\s*번호\s*:\s*\d+\s*",
        r"정답은\s*\d+\s*번입니다\.?\s*",
        r"정답은\s*\d+\s*번\s*",
        r"\d+\s*번이\s*정답입니다\.?\s*",
        r"\d+\s*번이\s*정답\s*",
    ]

    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def _has_explanation_contradiction(explanation: str, answer: int) -> bool:
    """
    객관식 해설에서 정답이 아닌 선택지를 '정확하다', '올바르다', '맞다'처럼
    설명하는 경우 복수정답 가능성이 있으므로 품질 경고로 남긴다.
    """
    if not explanation:
        return False

    text = str(explanation)

    positive_patterns = [
        r"(\d)\s*번\s*선택지는\s*.*(정확|올바르|맞는|타당|적절)",
        r"(\d)\s*번은\s*.*(정확|올바르|맞는|타당|적절)",
    ]

    for pattern in positive_patterns:
        for match in re.finditer(pattern, text):
            try:
                mentioned_no = int(match.group(1))
            except Exception:
                continue

            if mentioned_no != answer:
                return True

    return False


def _find_weak_multiple_choice_options(q: dict, difficulty: str) -> list[str]:
    """
    고급 객관식에서 너무 쉽게 제거되는 선택지 표현을 찾는다.
    단, 여기서는 문제를 폐기하지 않고 quality_warnings 용도로만 사용한다.
    """
    if difficulty != "고급":
        return []

    choices = q.get("choices", [])

    if not isinstance(choices, list):
        return []

    weak_patterns = [
        "무시한다",
        "완전히 제거",
        "무조건",
        "항상",
        "오직",
        "성능만",
        "보안만",
        "아무 조치",
        "고려하지 않는다",
        "방치한다",
    ]

    found: list[str] = []

    for choice in choices:
        choice_text = str(choice)

        for pattern in weak_patterns:
            if pattern in choice_text:
                found.append(f"'{pattern}' 포함 선택지: {choice_text}")

    return found

def _should_reject_for_choice_quality(q: dict, difficulty: str) -> bool:
    """
    고급 객관식에서 정말 심각한 선택지 품질 문제만 실제 폐기한다.

    주의:
    - '무시', '고려하지 않는다'는 LLM이 오답 한계를 설명할 때 자주 쓰므로
      지금 단계에서는 reject하지 않고 warning으로만 처리한다.
    - 너무 강하게 reject하면 validated=0으로 400이 다시 발생한다.
    """
    if difficulty != "고급":
        return False

    choices = q.get("choices", [])

    if not isinstance(choices, list) or len(choices) != 5:
        return True

    extreme_reject_patterns = [
        "모든 컬럼",
        "모든 테이블",
        "모든 데이터",
        "모든 조건",
        "모든 조인",
        "모든 접근",
        "데이터를 삭제",
        "접근을 차단",
        "완전히 제거",
    ]

    bad_choice_count = 0

    for choice in choices:
        choice_text = str(choice)

        if any(pattern in choice_text for pattern in extreme_reject_patterns):
            bad_choice_count += 1

    # 정말 심각한 선택지가 2개 이상일 때만 폐기
    return bad_choice_count >= 2

def _find_hard_choice_quality_errors(q: dict, difficulty: str) -> list[str]:
    """
    객관식 선택지 품질이 낮은 경우를 감지한다.
    현재 단계에서는 hard reject하지 않고 quality_warnings에만 남긴다.
    """
    if difficulty != "고급":
        return []

    choices = q.get("choices", [])
    answer = q.get("answer")

    if not isinstance(choices, list) or len(choices) != 5:
        return ["선택지가 5개가 아닙니다."]

    try:
        answer_int = int(answer)
    except Exception:
        return ["answer가 숫자가 아닙니다."]

    if answer_int < 1 or answer_int > 5:
        return ["answer가 1~5 범위를 벗어났습니다."]

    errors: list[str] = []

    correct_choice = str(choices[answer_int - 1]).strip()
    wrong_choices = [
        str(choice).strip()
        for idx, choice in enumerate(choices)
        if idx != answer_int - 1
    ]

    choice_lengths = [len(str(choice).strip()) for choice in choices]
    wrong_lengths = [len(choice) for choice in wrong_choices]

    avg_wrong_len = sum(wrong_lengths) / max(len(wrong_lengths), 1)
    min_len = min(choice_lengths)
    max_len = max(choice_lengths)

    if len(correct_choice) > avg_wrong_len * 1.35:
        errors.append("정답 선택지만 다른 오답보다 과도하게 길어 정답이 노출됩니다.")

    if min_len > 0 and max_len / min_len >= 2.0:
        errors.append("선택지 간 길이 편차가 너무 커서 정답 추측 가능성이 높습니다.")

    too_short_choices = [
        choice for choice in choices
        if len(str(choice).strip()) < 22
    ]

    if too_short_choices:
        errors.append(
            f"고급 문제에 너무 짧은 선택지가 포함되어 있습니다: {too_short_choices}"
        )

    hard_reject_patterns = [
        "모든 컬럼",
        "모든 테이블",
        "모든 데이터",
        "모든 조건",
        "모든 조인",
        "모든 접근",
        "데이터를 삭제",
        "접근을 차단",
        "완전히 제거",
    ]

    warning_patterns = [
        "고려하지 않는다",
        "무시",
        "무조건",
        "항상",
        "오직",
        "쿼리를 단순화",
        "조인 순서를 수동으로 고정",
        "조인 순서를 무조건",
        "인덱스를 추가하여 모든",
        "성능을 높인다",
        "성능을 개선한다",
        "쓰기 작업의 성능을 높인다",
    ]

    for choice in choices:
        choice_text = str(choice)

        for pattern in hard_reject_patterns:
            if pattern in choice_text:
                errors.append(
                    f"강한 품질 저하 선택지 표현이 포함되어 있습니다: '{pattern}' / {choice_text}"
                )

        for pattern in warning_patterns:
            if pattern in choice_text:
                errors.append(
                    f"품질 저하 선택지 표현이 포함되어 있습니다: '{pattern}' / {choice_text}"
                )

    correct_judgment_words = [
        "고려",
        "평가",
        "종합",
        "분석",
        "판단",
        "리스크",
        "트레이드오프",
    ]

    simple_action_patterns = [
        "추가한다",
        "제거한다",
        "단순화한다",
        "변경한다",
        "고정한다",
        "높인다",
    ]

    correct_has_judgment = any(word in correct_choice for word in correct_judgment_words)
    simple_wrong_count = 0

    for wrong_choice in wrong_choices:
        if any(pattern in wrong_choice for pattern in simple_action_patterns):
            if not any(word in wrong_choice for word in correct_judgment_words):
                simple_wrong_count += 1

    if correct_has_judgment and simple_wrong_count >= 2:
        errors.append(
            "정답만 종합 판단형이고 오답은 단순 조치형이라 정답이 쉽게 드러납니다."
        )

    return errors


def _has_numbered_distractor_explanation(explanation: str) -> bool:
    """
    해설에서 오답을 '1번은', '2번은'처럼 번호 기준으로 설명하는지 감지한다.
    정답 첫 문장 '정답은 N번입니다.'는 허용한다.
    """
    if not explanation:
        return False

    text = str(explanation).strip()

    text = re.sub(r"^정답은\s*\d\s*번입니다\.?\s*", "", text)

    numbered_patterns = [
        r"\b[1-5]\s*번은",
        r"\b[1-5]\s*번의",
        r"\b[1-5]\s*번 선택지",
        r"\b[1-5]\s*번 보기",
        r"\b[1-5]\s*번과\s*[1-5]\s*번",
        r"\b[1-5]\s*번,\s*[1-5]\s*번",
    ]

    return any(re.search(pattern, text) for pattern in numbered_patterns)

def _has_required_evidence_for_competency(
    q: dict,
    difficulty: str,
) -> tuple[bool, str | None]:
    """
    중급/고급 문제에서 역량별 실전 자료가 포함되어 있는지 확인한다.
    비문학형 문제를 저장하지 않기 위한 검증이다.
    """
    if difficulty not in {"중급", "고급"}:
        return True, None

    competency_type = str(q.get("competency_type") or "").strip()
    body = str(q.get("body", "") or "")

    if competency_type == "java":
        signals = [
            "class ",
            "extends",
            "@Override",
            "new ",
            "public ",
            "private ",
            "void ",
            "System.out.println",
            "interface ",
            "implements",
            "List<",
            "Map<",
        ]
        if not any(signal in body for signal in signals):
            return False, "java 중급/고급 문제에는 Java 코드 조각, 상속/인터페이스 구조, 컬렉션 사용 예시 중 하나가 필요합니다."

    if competency_type == "python":
        signals = [
            "def ",
            "for ",
            "while ",
            "if ",
            "try:",
            "except",
            "print(",
            ".get(",
            "KeyError",
            "TypeError",
            "users =",
            "items =",
            "data =",
            "[",
            "{",
        ]
        if not any(signal in body for signal in signals):
            return False, "python 중급/고급 문제에는 Python 코드 조각 또는 실제 리스트/딕셔너리 예시가 필요합니다."

    if competency_type == "sql":
        upper_body = body.upper()
        signals = [
            "SELECT",
            "FROM",
            "JOIN",
            "WHERE",
            "GROUP BY",
            "ORDER BY",
            "HAVING",
            "EXPLAIN",
            "CREATE TABLE",
            "테이블",
            "실행 계획",
        ]
        if not any(signal in upper_body for signal in signals):
            return False, "sql 중급/고급 문제에는 SQL 쿼리, 테이블 구조, 실행 계획 설명 중 하나가 필요합니다."

    if competency_type == "ai":
        lower_body = body.lower()

        retrieval_signals = [
            "query",
            "질의",
            "top_k",
            "top-k",
            "chunk",
            "청크",
            "similarity",
            "유사도",
            "score",
            "점수",
            "metadata",
            "메타데이터",
            "filter",
            "필터",
            "검색 결과",
            "검색된 문서",
        ]

        pipeline_signals = [
            "reranker",
            "리랭커",
            "reranking",
            "재정렬",
            "embedding",
            "임베딩",
            "vector search",
            "벡터 검색",
            "keyword search",
            "키워드 검색",
            "hybrid search",
            "하이브리드 검색",
            "context filtering",
            "context filter",
            "컨텍스트 필터링",
        ]

        metric_signals = [
            "precision",
            "recall",
            "f1",
            "accuracy",
            "정확도",
            "정밀도",
            "재현율",
            "latency",
            "지연 시간",
            "p95",
            "응답 시간",
            "hallucination",
            "환각",
        ]

        retrieval_count = sum(1 for signal in retrieval_signals if signal in lower_body)
        pipeline_count = sum(1 for signal in pipeline_signals if signal in lower_body)
        metric_count = sum(1 for signal in metric_signals if signal in lower_body)

        total_signal_count = retrieval_count + pipeline_count + metric_count

        if difficulty == "중급":
            if total_signal_count < 2:
                return False, (
                    "ai 중급 문제에는 query/top_k/chunk/similarity/metadata/embedding/reranker/"
                    "precision/recall/latency 중 최소 2개 이상의 구체 단서가 필요합니다."
                )

        if difficulty == "고급":
            if total_signal_count < 3:
                return False, (
                    "ai 고급 문제에는 검색 로그, 파이프라인 조건, 평가 지표 중 최소 3개 이상의 "
                    "구체 단서가 필요합니다."
                )

            if retrieval_count < 1:
                return False, (
                    "ai 고급 RAG 문제에는 query, top_k, chunk, similarity, metadata, 검색 결과 중 "
                    "최소 1개 이상의 검색 결과 단서가 필요합니다."
                )

            if pipeline_count < 1:
                return False, (
                    "ai 고급 RAG 문제에는 embedding, vector search, hybrid search, reranker, "
                    "context filtering 중 최소 1개 이상의 파이프라인 단서가 필요합니다."
                )

    return True, None

def _ensure_question_body_ends_with_question(
    body: str,
    question_type: str,
    difficulty: str,
) -> str:
    """
    문제 본문이 상황 설명으로만 끝나는 경우,
    마지막에 명확한 질문 문장을 붙인다.

    LLM이 고급 문제에서 상황 설명만 작성하고 마침표로 끝내는 문제를 방지한다.
    """
    if not body:
        return body

    text = str(body).strip()

    # 이미 질문형이면 그대로 둔다.
    question_endings = (
        "?",
        "？",
        "무엇인가?",
        "무엇인가요?",
        "어느 것인가?",
        "어느 것인가요?",
        "무엇입니까?",
        "무엇인가.",
        "어느 것인가.",
    )

    if text.endswith(question_endings):
        return text

    # 마지막 문장이 이미 질문 의도를 갖고 있으면 물음표만 보정
    interrogative_keywords = [
        "무엇인가",
        "어느 것인가",
        "어떤 것인가",
        "가장 적절한 것은",
        "가장 타당한 것은",
        "가장 우선적으로",
        "어떻게 해야 하는가",
        "어떤 조치를 취해야 하는가",
        "무엇을 선택해야 하는가",
    ]

    if any(keyword in text for keyword in interrogative_keywords):
        if text.endswith("."):
            return text[:-1].rstrip() + "?"
        return text + "?"

    if question_type == "multiple_choice":
        if difficulty == "고급":
            return (
                f"{text} "
                "이 상황에서 문제의 원인과 제약 조건을 종합적으로 고려했을 때 가장 적절한 판단은 무엇인가?"
            )

        if difficulty == "중급":
            return (
                f"{text} "
                "이 상황에서 가장 적절한 선택지는 무엇인가?"
            )

        return (
            f"{text} "
            "다음 중 가장 적절한 것은 무엇인가?"
        )

    if question_type == "essay":
        return (
            f"{text} "
            "이 상황을 어떻게 설명할 수 있는지 핵심 근거를 포함하여 서술하시오."
        )

    return (
        f"{text} "
        "요구사항을 만족하는 해결 방법을 작성하시오."
    )

def _validate_questions(
    questions: list,
    question_type: str,
    difficulty: str,
    score: int,
) -> list[dict[str, Any]]:
    if not isinstance(questions, list):
        raise ValueError("AI 응답이 JSON 배열이 아닙니다.")

    validated: list[dict[str, Any]] = []

    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            logger.warning(f"문제 검증 제외: index={idx}, reason=not_dict")
            continue

        title = q.get("title")
        body = q.get("body")
        choices = q.get("choices")
        answer = q.get("answer")
        explanation = q.get("explanation")

        if body:
            q["body"] = _ensure_question_body_ends_with_question(
                body=str(body),
                question_type=question_type,
                difficulty=difficulty,
            )
            body = q["body"]

        if not title or not body or explanation is None:
            logger.warning(f"문제 검증 제외: index={idx}, reason=missing_required_fields")
            continue

        has_evidence, evidence_reason = _has_required_evidence_for_competency(
            q=q,
            difficulty=difficulty,
        )

        if not has_evidence:
            logger.warning(
                f"문제 검증 제외: index={idx}, reason=missing_required_evidence, details={evidence_reason}"
            )
            continue

        if question_type == "multiple_choice":
            if not isinstance(choices, list) or len(choices) != 5:
                logger.warning(f"문제 검증 제외: index={idx}, reason=invalid_choices")
                continue

            try:
                answer_int = int(answer)
            except Exception:
                logger.warning(f"문제 검증 제외: index={idx}, reason=invalid_answer_type")
                continue

            if answer_int < 1 or answer_int > 5:
                logger.warning(f"문제 검증 제외: index={idx}, reason=answer_out_of_range")
                continue

            quality_warnings: list[str] = []

            explanation_answer = _extract_answer_number_from_explanation(str(explanation))

            if explanation_answer is not None and explanation_answer != answer_int:
                logger.warning(
                    f"문제 품질 경고: index={idx}, reason=explanation_answer_mismatch, "
                    f"answer={answer_int}, explanation_answer={explanation_answer}"
                )
                quality_warnings.append(
                    f"해설의 정답 번호({explanation_answer})와 answer({answer_int})가 달라 자동 수정했습니다."
                )
                q["explanation"] = _replace_answer_number_in_explanation(
                    str(explanation),
                    answer_int,
                )

            if _has_explanation_contradiction(str(q.get("explanation", explanation)), answer_int):
                logger.warning(f"문제 품질 경고: index={idx}, reason=explanation_contradiction")
                quality_warnings.append(
                    "해설에서 정답이 아닌 선택지를 긍정적으로 설명했을 가능성이 있습니다."
                )

            weak_option_reasons = _find_weak_multiple_choice_options(q, difficulty)
            if weak_option_reasons:
                logger.warning(
                    f"문제 품질 경고: index={idx}, reason=weak_multiple_choice_options, "
                    f"details={weak_option_reasons}"
                )
                quality_warnings.extend(weak_option_reasons)

            hard_choice_errors = _find_hard_choice_quality_errors(q, difficulty)

            if hard_choice_errors:
                logger.warning(
                    f"문제 품질 경고: index={idx}, reason=hard_choice_quality_error, "
                    f"details={hard_choice_errors}"
                )

                if _should_reject_for_choice_quality(q, difficulty):
                    logger.warning(
                        f"문제 검증 제외: index={idx}, reason=hard_choice_quality_reject"
                    )
                    continue

                quality_warnings.extend(hard_choice_errors)

            if _has_numbered_distractor_explanation(str(q.get("explanation", explanation))):
                logger.warning(
                    f"문제 품질 경고: index={idx}, reason=numbered_distractor_explanation"
                )
                quality_warnings.append(
                    "해설에서 오답을 번호 기준으로 설명하고 있어 선택지 재배치 후 불일치 가능성이 있습니다."
                )

            if quality_warnings:
                q["quality_warnings"] = quality_warnings

            q["answer"] = answer_int

        else:
            q["choices"] = []

            if answer is None or str(answer).strip() == "":
                logger.warning(f"문제 검증 제외: index={idx}, reason=empty_subjective_answer")
                continue

            q["answer"] = str(answer)
            q["explanation"] = _remove_answer_number_from_explanation(str(explanation))

        q["difficulty"] = difficulty
        q["score"] = score

        if not isinstance(q.get("competency_tags"), list):
            q["competency_tags"] = []

        validated.append(q)

    logger.info(f"문제 검증 결과: input={len(questions)}, validated={len(validated)}")

    return validated