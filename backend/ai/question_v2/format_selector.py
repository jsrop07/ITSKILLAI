from ai.question_v2.models import QuestionFormatPlan


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


def select_question_formats(
    *,
    difficulty: str,
    count: int,
) -> list[QuestionFormatPlan]:
    if difficulty == "초급":
        source = AI_BEGINNER_FORMATS
    elif difficulty == "중급":
        source = AI_INTERMEDIATE_FORMATS
    else:
        raise ValueError(f"지원하지 않는 난이도입니다: {difficulty}")

    selected = source[:count]

    return [
        QuestionFormatPlan(
            index=i + 1,
            question_format=item["question_format"],
            answer_style=item["answer_style"],
            focus=item["focus"],
        )
        for i, item in enumerate(selected)
    ]