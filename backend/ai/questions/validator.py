import re

from ai.questions.models import GeneratedQuestion

ANSWER_LEAK_PATTERNS = [
    "부적절합니다",
    "잘못된 접근입니다",
    "오답입니다",
    "틀렸습니다",
    "정답입니다",
    "항상 해결",
    "무조건",
    "필요 없습니다",
    "무시합니다",
    "삭제합니다",
    "제거합니다",
    "원인을 구분하지",
    "평가하지 않고",
    "검토하지 않고",
    "확인하지 않고",
    "만 판단합니다",
    "만 확인합니다",
    "만 조정합니다",
    "만 사용합니다",
    "인식할 수 없습니다",
    "적절하지 않습니다",
    "효과적이지 않습니다",
    "직접적인 해결책이 아닙니다",
    "관련이 부족합니다",
    "우선순위가 낮습니다",
    "정답입니다",
    "오답입니다",
    "출처 확인 없이",
    "그대로 제공합니다",
    "생략합니다",
    "자신 있게 답하라는",
    "친절하라는",
    "역할만",
    "문장만 추가",
    "검증을 생략",
    "확인 단계를 생략",
    "만으로 해결",
    "만 기준으로",
    "만 점검",
    "만 비교",
]

META_CHOICE_PATTERNS = [
    "오해할 수 있다",
    "혼동할 수 있다",
    "착각할 수 있다",
    "잘못 이해할 수 있다",
]

INFORMAL_ENDING_PATTERNS = [
    r"한다\.$",
    r"된다\.$",
    r"이다\.$",
    r"없다\.$",
    r"있다\.$",
]


def _has_informal_ending(text: str) -> bool:
    stripped = text.strip()
    return any(re.search(pattern, stripped) for pattern in INFORMAL_ENDING_PATTERNS)


def validate_generated_question(question: GeneratedQuestion) -> None:
    if not question.title.strip():
        raise ValueError("title이 비어 있습니다.")

    if not question.body.strip():
        raise ValueError("body가 비어 있습니다.")

    if not isinstance(question.choices, list) or len(question.choices) != 5:
        raise ValueError("choices는 반드시 5개여야 합니다.")

    if not isinstance(question.answer, int) or not (1 <= question.answer <= 5):
        raise ValueError("answer는 1~5 정수여야 합니다.")

    if not question.explanation.strip():
        raise ValueError("explanation이 비어 있습니다.")

    expected_prefix = f"정답은 {question.answer}번입니다."
    if not question.explanation.strip().startswith(expected_prefix):
        raise ValueError(f"explanation은 '{expected_prefix}'로 시작해야 합니다.")

    if _has_informal_ending(question.explanation):
        raise ValueError("explanation에 반말 종결 표현이 포함되어 있습니다.")

    for choice in question.choices:
        if not choice.strip():
            raise ValueError("빈 선택지가 있습니다.")

        for pattern in META_CHOICE_PATTERNS:
            if pattern in choice:
                raise ValueError(f"선택지에 메타 표현이 포함되어 있습니다: {pattern}")
    
    # 추가 검증
    if question.difficulty == "초급":
        _validate_beginner_choice_basic_quality(question)
        _validate_beginner_explanation_style(question)
    else:
        _validate_intermediate_body_has_context(question)
        _validate_choice_length_balance(
            question.choices,
            difficulty=question.difficulty,
        )
        _validate_answer_length_not_obvious(question)
        _validate_no_answer_leak_patterns(question.choices, difficulty=question.difficulty)
        _validate_ai_intermediate_terms(question)
    
        _validate_explanation_not_choice_copy(question)
        _validate_explanation_has_reasoning_depth(question)
        _validate_explanation_answer_consistency(question)
    body = question.body

    _validate_body_polite_question(question.body)

    if question.difficulty == "초급":
        _validate_beginner_body_by_format(question)
    else:
        if question.answer_style == "find_correct":
            if not any(keyword in body for keyword in ["옳은 것은", "적절한 것은"]):
                raise ValueError("find_correct 문제는 body에 '옳은 것은' 또는 '적절한 것은'이 포함되어야 합니다.")

        if question.answer_style == "find_incorrect":
            find_incorrect_body_keywords = [
                "옳지 않은 것은",
                "옳지 않은 설명",
                "옳지 않은 조치",
                "옳지 않은 대응",
                "부적절한 것은",
                "부적절한 설명",
                "부적절한 조치",
                "부적절한 대응",
                "잘못된 것은",
                "잘못된 설명",
                "잘못된 조치",
                "잘못된 대응",
                "부적절합니까",
                "옳지 않습니까",
                "잘못되었습니까",
            ]

            if not any(keyword in body for keyword in find_incorrect_body_keywords):
                raise ValueError(
                    "find_incorrect 문제는 body에 옳지 않은/부적절한/잘못된 설명·조치·대응을 묻는 표현이 포함되어야 합니다."
                )

        if question.answer_style == "best_action":
            best_action_body_keywords = [
                "가장 적절한 조치",
                "가장 적절한 방법",
                "가장 적절한 것은",
                "적절한 조치",
                "적절한 방법",
                "어떤 조치",
                "어떤 방법",
                "개선 방향",
                "대응",
            ]

            if not any(keyword in body for keyword in best_action_body_keywords):
                raise ValueError("best_action 문제는 body에 적절한 조치/방법/대응을 묻는 표현이 포함되어야 합니다.")

        if question.answer_style == "diagnosis":
            if not any(keyword in body for keyword in ["원인으로 가장 적절한 것은", "원인으로 적절한 것은"]):
                raise ValueError("diagnosis 문제는 원인 판단 표현이 포함되어야 합니다.")

    if question.question_format == "ai_log_or_metric_interpretation":
        required_log_keywords = ["query","top_k","similarity","accuracy","loss","latency","검색 로그","검색 결과","평가 지표","학습 지표","운영 로그","응답 설정 로그","로그","지표",]
        if not any(keyword in body for keyword in required_log_keywords):
            raise ValueError("log_or_metric_interpretation 문제는 로그/지표 정보가 body에 포함되어야 합니다.")

def _validate_beginner_choice_basic_quality(question: GeneratedQuestion) -> None:
    """
    초급 문제는 개념 이해 확인이 목적이므로
    중급처럼 선택지 힌트성 표현을 강하게 제한하지 않는다.
    """
    for choice in question.choices:
        text = choice.strip()

        if len(text) < 6:
            raise ValueError("초급 선택지 중 지나치게 짧은 문장이 있습니다.")

        hard_forbidden_patterns = [
            "정답입니다",
            "오답입니다",
            "부적절합니다",
            "잘못된 접근입니다",
        ]

        for pattern in hard_forbidden_patterns:
            if pattern in text:
                raise ValueError(f"초급 선택지에 직접적인 정답/오답 표현이 포함되어 있습니다: {pattern}")

def _validate_beginner_body_by_format(question: GeneratedQuestion) -> None:
    body = question.body.strip()
    question_format = question.question_format

    if question_format == "ai_basic_concept_find_correct":
        if not any(keyword in body for keyword in ["옳은 것은", "옳은 설명", "어떤 설명"]):
            raise ValueError("초급 개념 문제는 옳은 설명을 묻는 표현이 포함되어야 합니다.")

    elif question_format == "ai_basic_concept_find_incorrect":
        if not any(keyword in body for keyword in ["옳지 않은 것은", "옳지 않은 설명", "잘못된 것은", "부적절한 것은"]):
            raise ValueError("초급 오답 고르기 문제는 옳지 않은 설명을 묻는 표현이 포함되어야 합니다.")

    elif question_format == "ai_purpose_find_correct":
        if not any(keyword in body for keyword in ["목적", "사용", "활용"]):
            raise ValueError("초급 목적 문제는 사용 목적이나 활용 목적을 묻는 표현이 포함되어야 합니다.")

    elif question_format == "ai_concept_compare_basic":
        if not any(keyword in body for keyword in ["차이", "비교", "구분"]):
            raise ValueError("초급 비교 문제는 개념 간 차이나 구분을 묻는 표현이 포함되어야 합니다.")

    elif question_format == "ai_term_role_match":
        if not any(keyword in body for keyword in ["역할", "연결"]):
            raise ValueError("초급 용어-역할 문제는 역할 또는 연결을 묻는 표현이 포함되어야 합니다.")

        answer_choice = question.choices[question.answer - 1].strip()
        if answer_choice and answer_choice in body:
            raise ValueError("초급 용어-역할 문제의 body에 정답 선택지가 그대로 포함되어 있습니다.")
            
def validate_generated_questions(questions: list[GeneratedQuestion]) -> None:
    for question in questions:
        validate_generated_question(question)

def _validate_choice_length_balance(
    choices: list[str],
    *,
    difficulty: str,
) -> None:
    lengths = [len(choice.strip()) for choice in choices]

    if not lengths:
        return

    min_len = min(lengths)
    max_len = max(lengths)

    if difficulty == "초급":
        min_allowed_len = 10
        max_ratio = 2.8
        max_gap = 45
    else:
        min_allowed_len = 16
        max_ratio = 3.0
        max_gap = 45

    if min_len < min_allowed_len:
        raise ValueError("선택지 중 지나치게 짧은 문장이 있습니다.")

    # 비율만 보면 19자 vs 47자 같은 정상 범위도 과하게 실패할 수 있으므로
    # 비율과 절대 길이 차이를 함께 본다.
    if max_len >= min_len * max_ratio and (max_len - min_len) >= max_gap:
        raise ValueError("선택지 간 길이 차이가 지나치게 큽니다.")

def _validate_answer_length_not_obvious(question: GeneratedQuestion) -> None:
    answer_index = question.answer - 1
    choices = question.choices

    if not (0 <= answer_index < len(choices)):
        return

    answer_len = len(choices[answer_index].strip())
    other_lengths = [
        len(choice.strip())
        for index, choice in enumerate(choices)
        if index != answer_index
    ]

    if not other_lengths:
        return

    avg_other_len = sum(other_lengths) / len(other_lengths)

    if question.difficulty == "초급":
        upper_ratio = 1.7
        lower_ratio = 0.5
        min_gap = 35
    else:
        upper_ratio = 1.8
        lower_ratio = 0.55
        min_gap = 35

    # 정답이 조금 긴 정도는 허용하고,
    # 평균 대비 비율도 크고 절대 차이도 큰 경우만 실패 처리한다.
    if answer_len > avg_other_len * upper_ratio and (answer_len - avg_other_len) >= min_gap:
        raise ValueError("정답 선택지가 다른 선택지보다 지나치게 깁니다.")

    if answer_len < avg_other_len * lower_ratio and (avg_other_len - answer_len) >= min_gap:
        raise ValueError("정답 선택지가 다른 선택지보다 지나치게 짧습니다.")

def _validate_no_answer_leak_patterns(
    choices: list[str],
    *,
    difficulty: str,
) -> None:
    if difficulty == "초급":
        return

    for choice in choices:
        for pattern in ANSWER_LEAK_PATTERNS:
            if pattern in choice:
                raise ValueError(f"선택지에 정답 힌트성 표현이 포함되어 있습니다: {pattern}")

def _validate_explanation_answer_consistency(question: GeneratedQuestion) -> None:
    answer = int(question.answer)
    explanation = question.explanation.strip()

    required_prefix = f"정답은 {answer}번입니다."
    if not explanation.startswith(required_prefix):
        raise ValueError("해설의 정답 번호가 answer와 일치하지 않습니다.")

    for n in range(1, 6):
        if n == answer:
            continue

        forbidden_markers = [
            f"정답은 {n}번",
            f"정답인 {n}번",
            f"{n}번 선택지",
            f"{n}번은",
        ]

        for marker in forbidden_markers:
            if marker in explanation:
                raise ValueError("해설에 answer와 다른 선택지 번호가 포함되어 있습니다.")

def _validate_body_polite_question(body: str) -> None:
    stripped = body.strip()

    informal_question_endings = [
        "무엇인가?",
        "어떤 것인가?",
        "무엇인가요?",
    ]

    for ending in informal_question_endings:
        if stripped.endswith(ending):
            raise ValueError("문제 본문이 존댓말 질문형으로 끝나야 합니다.")

    # 존댓말 질문형이면 통과
    if stripped.endswith("습니까?"):
        return

    # 혹시 LLM이 다른 존댓말 질문형을 쓴 경우 최소 허용
    if stripped.endswith("?") and any(
        marker in stripped
        for marker in [
            "무엇입니까",
            "어떤",
            "옳은",
            "옳지 않은",
            "적절한",
            "목적",
            "역할",
            "설명",
            "조치",
            "방법",
            "원인",
            "판단",
        ]
    ):
        return

    raise ValueError("문제 본문 마지막 문장이 허용된 존댓말 질문형이 아닙니다.")

def _validate_beginner_explanation_style(question: GeneratedQuestion) -> None:
    if question.difficulty != "초급":
        return

    forbidden_words = [
        "적절한 대응",
        "대응입니다",
        "조치입니다",
        "개선 방향",
        "현재 상황",
        "핵심 원인",
    ]

    for word in forbidden_words:
        if word in question.explanation:
            raise ValueError(f"초급 해설에 중급/실무형 표현이 포함되어 있습니다: {word}")

def _validate_ai_intermediate_terms(question: GeneratedQuestion) -> None:
    if question.difficulty != "중급":
        return

    if question.competency_type != "ai":
        return

    text = " ".join([
        question.title,
        question.body,
        *question.choices,
        question.explanation,
    ])

    if "온도" in text:
        raise ValueError("AI 중급 문제에서는 temperature를 '온도'로 번역하지 말고 temperature로 표기해야 합니다.")

def _validate_intermediate_body_has_context(question: GeneratedQuestion) -> None:
    if question.difficulty != "중급":
        return

    body = question.body.strip()

    # "위 상황에서 ..."만 있고 실제 상황 설명이 없는 문제 방지
    weak_body_prefixes = [
        "위 상황에서",
        "위 현상에서",
        "위 로그를",
        "이 상황에서",
        "이 현상에서",
    ]

    if any(body.startswith(prefix) for prefix in weak_body_prefixes) and len(body) < 80:
        raise ValueError("중급 문제 body에 실제 상황 설명 없이 질문 문장만 포함되어 있습니다.")

    # 중급 문제는 최소한 상황 설명 + 질문으로 구성되어야 함
    if any(body.startswith(prefix) for prefix in weak_body_prefixes) and len(body) < 80:
        raise ValueError("중급 문제 body에 실제 상황 설명 없이 질문 문장만 포함되어 있습니다.")

    # 문장이 1문장뿐이면 대부분 상황 없이 질문만 있는 문제
    sentence_count = body.count(".") + body.count("?")
    if sentence_count < 2 and question.question_format != "ai_log_or_metric_interpretation":
        raise ValueError("중급 문제 body는 최소 2문장 이상의 상황 설명과 질문을 포함해야 합니다.")

def _normalize_for_overlap_check(text: str) -> str:
    if not text:
        return ""

    text = str(text).lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^\w가-힣]", "", text)
    return text


def _validate_explanation_not_choice_copy(question) -> None:
    choices = getattr(question, "choices", None) or []
    answer = getattr(question, "answer", None)
    explanation = getattr(question, "explanation", "") or ""

    if not choices or not explanation:
        return

    try:
        answer_index = int(answer) - 1
    except Exception:
        return

    if answer_index < 0 or answer_index >= len(choices):
        return

    answer_choice = str(choices[answer_index])

    normalized_choice = _normalize_for_overlap_check(answer_choice)
    normalized_explanation = _normalize_for_overlap_check(explanation)

    if not normalized_choice or not normalized_explanation:
        return

    # 정답 선택지 문장이 해설에 거의 그대로 포함된 경우 reject
    if len(normalized_choice) >= 20 and normalized_choice in normalized_explanation:
        raise ValueError("해설이 정답 선택지 문장을 거의 그대로 반복하고 있습니다.")

    # 선택지 앞부분만 살짝 바꿔서 복붙한 경우도 일부 reject
    choice_prefix = normalized_choice[:25]
    if len(choice_prefix) >= 20 and choice_prefix in normalized_explanation:
        raise ValueError("해설이 정답 선택지 표현을 과도하게 반복하고 있습니다.")

def _normalize_for_similarity(text: str) -> str:
    if not text:
        return ""

    text = str(text).lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^\w가-힣]", "", text)
    return text


def _similarity_ratio(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    a_norm = _normalize_for_similarity(a)
    b_norm = _normalize_for_similarity(b)

    if not a_norm or not b_norm:
        return 0.0

    return SequenceMatcher(None, a_norm, b_norm).ratio()


def _validate_explanation_not_choice_copy(question: GeneratedQuestion) -> None:
    choices = question.choices or []
    answer = question.answer
    explanation = question.explanation or ""

    if not choices or not explanation:
        return

    answer_index = int(answer) - 1

    if answer_index < 0 or answer_index >= len(choices):
        return

    answer_choice = str(choices[answer_index])
    expected_prefix = f"정답은 {question.answer}번입니다."
    reason_text = explanation.replace(expected_prefix, "", 1).strip()

    # 정답 선택지 전체 문장이 해설에 그대로 포함되는 경우
    normalized_choice = _normalize_for_similarity(answer_choice)
    normalized_reason = _normalize_for_similarity(reason_text)

    if len(normalized_choice) >= 20 and normalized_choice in normalized_reason:
        raise ValueError("해설이 정답 선택지 문장을 거의 그대로 반복하고 있습니다.")

    # 문장을 조금 바꿨지만 의미상 거의 같은 경우
    if _similarity_ratio(answer_choice, reason_text[: len(answer_choice) + 30]) >= 0.86:
        raise ValueError("해설이 정답 선택지를 문장만 조금 바꿔 반복하고 있습니다.")

def _validate_explanation_has_reasoning_depth(question: GeneratedQuestion) -> None:
    explanation = (question.explanation or "").strip()
    expected_prefix = f"정답은 {question.answer}번입니다."

    if not explanation.startswith(expected_prefix):
        return

    reason_text = explanation.replace(expected_prefix, "", 1).strip()

    # 너무 짧은 해설만 막는다.
    # 180 이상은 현재 LLM이 자주 실패하므로 110~120 정도가 현실적이다.
    if len(reason_text) < 110:
        raise ValueError("해설이 너무 짧습니다. 정답 판단 근거와 오답 한계를 더 설명해야 합니다.")

    # 정답 판단 근거가 아예 없는 경우만 막는다.
    reasoning_keywords = [
        "검증",
        "범위",
        "schema",
        "스키마",
        "비즈니스 규칙",
        "저장",
        "채점",
        "검수",
        "결과",
        "오류",
        "정합성",
        "매핑",
        "선택지",
        "값",
    ]

    if not any(keyword in reason_text for keyword in reasoning_keywords):
        raise ValueError("해설에 정답 판단 근거가 부족합니다.")

    # 오답 한계 설명은 다양한 표현을 허용한다.
    wrong_limit_keywords = [
        "나머지 선택지",
        "다른 선택지",
        "JSON 형태",
        "형식",
        "schema 검증",
        "스키마 검증",
        "낮은 우선순위",
        "무시",
        "허용",
        "choices 개수",
        "일부 조건",
        "검증 기준",
        "비즈니스 규칙",
        "빠뜨",
        "부족",
        "한계",
        "직접",
    ]

    if not any(keyword in reason_text for keyword in wrong_limit_keywords):
        raise ValueError("해설에 오답 선택지의 한계 설명이 부족합니다.")

    # 정말 뭉뚱그린 해설만 막는다.
    weak_phrases = [
        "나머지 선택지들은 부적절합니다.",
        "나머지 선택지들은 적절하지 않습니다.",
        "문제를 해결하지 못합니다.",
        "잘못된 접근입니다.",
    ]

    if any(phrase in reason_text for phrase in weak_phrases):
        raise ValueError("해설이 정답/오답을 뭉뚱그려 설명하고 있습니다.")