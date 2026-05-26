from ai.questions.models import QuestionFormatPlan


AI_BEGINNER_FORMATS = [
    {
        "question_format": "ai_basic_concept_find_correct",
        "answer_style": "find_correct",
        "focus": "핵심 개념에 대한 옳은 설명 판단",
    },
    {
        "question_format": "ai_basic_concept_find_incorrect",
        "answer_style": "find_incorrect",
        "focus": "핵심 개념에 대한 옳지 않은 설명 판단",
    },
    {
        "question_format": "ai_purpose_find_correct",
        "answer_style": "find_correct",
        "focus": "기술의 사용 목적 판단",
    },
    {
        "question_format": "ai_concept_compare_basic",
        "answer_style": "find_correct",
        "focus": "비슷한 개념 간 기본 차이 판단",
    },
    {
        "question_format": "ai_term_role_match",
        "answer_style": "find_correct",
        "focus": "용어와 역할의 올바른 연결 판단",
    },
]


AI_INTERMEDIATE_FORMATS = [
    {
        "question_format": "ai_scenario_best_action",
        "answer_style": "best_action",
        "focus": "상황에서 가장 적절한 대응 선택",
    },
    {
        "question_format": "ai_scenario_find_incorrect_action",
        "answer_style": "find_incorrect",
        "focus": "상황에서 부적절한 대응 선택",
    },
    {
        "question_format": "ai_quality_issue_diagnosis",
        "answer_style": "diagnosis",
        "focus": "품질 저하 원인 판단",
    },
    {
        "question_format": "ai_method_compare_decision",
        "answer_style": "best_action",
        "focus": "여러 개선 방법 중 적절한 방식 선택",
    },
    {
        "question_format": "ai_log_or_metric_interpretation",
        "answer_style": "best_action",
        "focus": "로그 또는 지표를 보고 개선 방향 판단",
    },
]


def _infer_preferred_intermediate_format_from_topic(topic: str) -> str | None:
    text = topic.strip().lower()

    if any(
        keyword in text
        for keyword in [
            "옳지 않은",
            "부적절",
            "잘못된",
            "틀린",
            "오답",
            "잘못된 대응",
            "부적절한 대응",
        ]
    ):
        return "ai_scenario_find_incorrect_action"

    if any(
        keyword in text
        for keyword in [
            "원인",
            "이유",
            "진단",
            "왜",
            "문제 원인",
            "품질 저하",
        ]
    ):
        return "ai_quality_issue_diagnosis"

    if any(
        keyword in text
        for keyword in [
            "로그",
            "지표",
            "metric",
            "loss",
            "accuracy",
            "precision",
            "recall",
            "latency",
            "timeout",
            "drift",
            "learning rate",
            "validation loss",
        ]
    ):
        return "ai_log_or_metric_interpretation"

    if any(
        keyword in text
        for keyword in [
            "비교",
            "선택",
            "방법",
            "어떤 방법",
            "어느 방식",
        ]
    ):
        return "ai_method_compare_decision"

    if any(
        keyword in text
        for keyword in [
            "개선",
            "조치",
            "대응",
            "해결",
            "가장 적절",
        ]
    ):
        return "ai_scenario_best_action"

    return None


def _infer_preferred_beginner_format_from_topic(topic: str) -> str | None:
    text = topic.strip().lower()

    if any(
        keyword in text
        for keyword in [
            "옳지 않은",
            "부적절",
            "잘못된",
            "틀린",
            "오답",
        ]
    ):
        return "ai_basic_concept_find_incorrect"

    if any(
        keyword in text
        for keyword in [
            "목적",
            "사용 목적",
            "왜 사용",
            "쓰는 이유",
        ]
    ):
        return "ai_purpose_find_correct"

    if any(
        keyword in text
        for keyword in [
            "차이",
            "비교",
            "구분",
        ]
    ):
        return "ai_concept_compare_basic"

    if any(
        keyword in text
        for keyword in [
            "역할",
            "용어",
            "매칭",
        ]
    ):
        return "ai_term_role_match"

    if any(
        keyword in text
        for keyword in [
            "개념",
            "정의",
            "무엇",
            "옳은",
        ]
    ):
        return "ai_basic_concept_find_correct"

    return None


def _build_plan(
    *,
    index: int,
    item: dict,
) -> QuestionFormatPlan:
    return QuestionFormatPlan(
        index=index,
        question_format=item["question_format"],
        answer_style=item["answer_style"],
        focus=item["focus"],
    )


def _reorder_formats_by_preferred(
    *,
    source: list[dict],
    preferred_format: str | None,
) -> list[dict]:
    if not preferred_format:
        return source

    preferred_items = [
        item for item in source if item["question_format"] == preferred_format
    ]

    if not preferred_items:
        return source

    remaining_items = [
        item for item in source if item["question_format"] != preferred_format
    ]

    return preferred_items + remaining_items

def _find_format_item(
    *,
    source: list[dict],
    question_format: str,
) -> dict:
    for item in source:
        if item["question_format"] == question_format:
            return item

    raise ValueError(f"지원하지 않는 question_format입니다: {question_format}")

def select_question_formats(
    *,
    difficulty: str,
    count: int,
    topic: str = "",
    beginner_slots: list[dict[str, str | None]] | None = None,
) -> list[QuestionFormatPlan]:
    if difficulty == "초급":
        if difficulty == "초급" and beginner_slots:
            plans: list[QuestionFormatPlan] = []

            fallback_formats = AI_BEGINNER_FORMATS

            for index, slot in enumerate(beginner_slots[:count], start=1):
                forced_format = slot.get("question_format")

                if forced_format:
                    item = _find_format_item(
                        source=AI_BEGINNER_FORMATS,
                        question_format=forced_format,
                    )
                else:
                    item = fallback_formats[(index - 1) % len(fallback_formats)]

                plans.append(
                    _build_plan(
                        index=index,
                        item=item,
                    )
                )

            return plans
            source = AI_BEGINNER_FORMATS
            preferred_format = _infer_preferred_beginner_format_from_topic(topic)
    elif difficulty == "중급":
        source = AI_INTERMEDIATE_FORMATS
        preferred_format = _infer_preferred_intermediate_format_from_topic(topic)
    else:
        raise ValueError(f"지원하지 않는 난이도입니다: {difficulty}")

    ordered_source = _reorder_formats_by_preferred(
        source=source,
        preferred_format=preferred_format,
    )

    selected = [
        ordered_source[i % len(ordered_source)]
        for i in range(count)
    ]

    return [
        _build_plan(
            index=i + 1,
            item=item,
        )
        for i, item in enumerate(selected)
    ]