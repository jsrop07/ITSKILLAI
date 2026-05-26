def normalize_question_body_choice_style(text: str) -> str:
    """
    문제 본문과 선택지를 시험 문항체로 정리한다.
    - body/choices는 존댓말을 쓰지 않는다.
    - explanation은 별도 함수에서 존댓말로 정리한다.
    """
    if not text:
        return ""

    normalized = str(text).strip()

    replacements = {
        "어떤 접근 방식을 선택해야 할까요?": "가장 적절한 접근 방식은 무엇인가?",
        "어떤 방안을 선택해야 할까요?": "가장 적절한 방안은 무엇인가?",
        "어떤 판단을 해야 할까요?": "가장 적절한 판단은 무엇인가?",
        "무엇을 선택해야 할까요?": "무엇을 선택해야 하는가?",
        "무엇을 검토해야 할까요?": "무엇을 검토해야 하는가?",
        "어떻게 해야 할까요?": "어떻게 해야 하는가?",
        "해야 할까요?": "해야 하는가?",
        "할까요?": "하는가?",
        "무엇일까요?": "무엇인가?",
        "예측하라": "예측하십시오",
        "고려하라": "고려하십시오",
        "해야 합니다.": "해야 한다.",
        "해야 합니다": "해야 한다",
        "할 수 있습니다.": "할 수 있다.",
        "할 수 있습니다": "할 수 있다",
        "수 있습니다.": "수 있다.",
        "수 있습니다": "수 있다",
        "입니다.": "이다.",
        "입니다": "이다",
        "합니다.": "한다.",
        "합니다": "한다",
        "됩니다.": "된다.",
        "됩니다": "된다",
        "높입니다.": "높인다.",
        "높입니다": "높인다",
        "개선합니다.": "개선한다.",
        "개선합니다": "개선한다",
        "적용합니다.": "적용한다.",
        "적용합니다": "적용한다",
        "검토합니다.": "검토한다.",
        "검토합니다": "검토한다",
        "판단합니다.": "판단한다.",
        "판단합니다": "판단한다",
        "구성합니다.": "구성한다.",
        "구성합니다": "구성한다",
        "제거합니다.": "제거한다.",
        "제거합니다": "제거한다",
    }

    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    return normalized


def normalize_question_body_choice_styles(questions: list[dict]) -> list[dict]:
    """
    최종 검증 통과 문제의 body/choices 문체를 시험 문항체로 정리한다.
    """
    if not questions:
        return questions

    for q in questions:
        if not isinstance(q, dict):
            continue

        q["body"] = normalize_question_body_choice_style(q.get("body", ""))

        choices = q.get("choices", [])
        if isinstance(choices, list):
            q["choices"] = [
                normalize_question_body_choice_style(choice)
                for choice in choices
            ]

    return questions


def normalize_question_text(q: dict) -> None:
    """
    저장 가능한 문제에 대해 최종적으로 텍스트 포맷을 정규화한다.
    - body/choices의 존댓말→시험체 변환
    - explanation의 반말 어미→존댓말 변환
    주의: Java/Python 코드 블록 내부 재포맷은 하지 않는다.
          LLM이 생성한 코드 구조를 정규표현식으로 건드리면 깨질 수 있다.
    """
    # 1. body 정규화 (존댓말→시험체만, 코드블록 내부는 건드리지 않음)
    body = q.get("body", "")
    if body:
        q["body"] = normalize_question_body_choice_style(body).strip()

    # 2. choices 정규화
    choices = q.get("choices", [])
    if isinstance(choices, list):
        q["choices"] = [
            normalize_question_body_choice_style(str(c))
            for c in choices
        ]

    # 3. explanation 존댓말 정규화 (반말 어미만 교체, 과도한 치환 금지)
    explanation = q.get("explanation", "")
    if explanation:
        # 반말 종결 어미만 안전하게 교체 (단어 경계 고려)
        safe_replacements = [
            ("하지 않는다.", "하지 않습니다."),
            ("아니다.", "아닙니다."),
            ("출력된다.", "출력됩니다."),
            ("영향을 미친다.", "영향을 미칩니다."),
            ("잘못된 것이다.", "잘못된 설명입니다."),
        ]
        for src, tgt in safe_replacements:
            explanation = explanation.replace(src, tgt)
        q["explanation"] = explanation.strip()