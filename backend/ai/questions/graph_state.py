# backend/ai/questions/graph_state.py

from typing import Any, Literal
from typing_extensions import TypedDict


GenerationMode = Literal["planner", "template"]


class QuestionGenerationState(TypedDict, total=False):
    # 입력값
    topic: str
    difficulty: Literal["초급", "중급", "고급"]
    count: int
    score: int
    question_type: str
    competency_type: str | None
    db: Any
    
    # 정규화/라우팅 결과
    normalized_competency_type: str
    generation_mode: GenerationMode

    # 생성 중간 결과
    plans: list[dict[str, Any]]
    raw_questions: list[dict[str, Any]]
    repaired_questions: list[dict[str, Any]]
    validated_questions: list[dict[str, Any]]

    # 저장 결과
    saved_questions: list[dict[str, Any]]

    # 제어/에러
    error: str | None
    retry_count: int
    max_retries: int