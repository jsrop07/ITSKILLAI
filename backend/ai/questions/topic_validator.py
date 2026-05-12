# backend/ai/questions/topic_validator.py

from fastapi import HTTPException
from ai.core.config import (
    SUPPORTED_COMPETENCIES,
    COMPETENCY_KEYWORDS,
    normalize_competency_type,
)

# competency_config 기반으로 COMPETENCY_TOPIC_RULES 동적 생성 (신규 8개 기준)
COMPETENCY_TOPIC_RULES = {
    key: {
        "label": label,
        "keywords": COMPETENCY_KEYWORDS.get(key, []),
    }
    for key, label in SUPPORTED_COMPETENCIES.items()
}


BLOCKED_NON_IT_KEYWORDS = [
    "음식", "맛집", "요리", "레시피", "추천해줘",
    "연애", "소개팅", "여행", "호텔", "운세", "사주",
    "영화", "드라마", "노래", "가수", "쇼핑",
    "다이어트", "헬스", "운동 루틴", "화장품 추천"
]


def normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def validate_topic_for_competency(competency_type: str | None, topic: str | None):
    normalized_topic = normalize_text(topic)

    if not normalized_topic:
        raise HTTPException(
            status_code=400,
            detail="세부 주제를 입력해주세요."
        )

    if len(normalized_topic) < 2:
        raise HTTPException(
            status_code=400,
            detail="세부 주제는 2글자 이상 입력해주세요."
        )

    if not competency_type:
        raise HTTPException(
            status_code=400,
            detail="역량 유형을 선택해주세요."
        )

    # legacy value → 신규 value normalize
    competency_type = normalize_competency_type(competency_type)

    if competency_type not in COMPETENCY_TOPIC_RULES:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 역량 유형입니다."
        )

    # 1차: 명백한 비IT 주제 차단
    for blocked in BLOCKED_NON_IT_KEYWORDS:
        if blocked.lower() in normalized_topic:
            raise HTTPException(
                status_code=400,
                detail="세부 주제는 IT 역량진단과 관련된 주제만 입력할 수 있습니다."
            )

    selected_rule = COMPETENCY_TOPIC_RULES[competency_type]
    selected_keywords = selected_rule["keywords"]

    # 2차: 선택한 역량 유형과 세부 주제 매칭 확인
    is_matched = any(keyword.lower() in normalized_topic for keyword in selected_keywords)

    if is_matched:
        return

    # 3차: 다른 역량 유형에 더 잘 맞는 주제인지 확인
    matched_other_competencies = []

    for key, rule in COMPETENCY_TOPIC_RULES.items():
        if key == competency_type:
            continue

        other_keywords = rule["keywords"]
        if any(keyword.lower() in normalized_topic for keyword in other_keywords):
            matched_other_competencies.append(rule["label"])

    if matched_other_competencies:
        raise HTTPException(
            status_code=400,
            detail=(
                f"세부 주제가 선택한 역량 유형({selected_rule['label']})과 맞지 않습니다. "
                f"'{topic}' 주제는 {', '.join(matched_other_competencies)} 역량 유형에 더 적합합니다."
            )
        )

    # 4차: IT 키워드가 아예 없는 애매한 주제 차단
    raise HTTPException(
        status_code=400,
        detail=(
            f"세부 주제가 선택한 역량 유형({selected_rule['label']})과 관련 있는지 확인하기 어렵습니다. "
            f"예: {', '.join(selected_keywords[:6])} 같은 주제로 입력해주세요."
        )
    )