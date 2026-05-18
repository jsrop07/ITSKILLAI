# backend/ai/questions/graph_state.py

from typing import Any, Literal
from typing_extensions import TypedDict


GenerationMode = Literal["planner", "template", "rag"]


class QuestionGenerationState(TypedDict, total=False):
    # 입력값
    topic: str
    difficulty: Literal["초급", "중급", "고급"]
    count: int
    score: int
    question_type: str
    competency_type: str | None
    db: Any

    # 생성 소스
    generation_source: Literal["general", "rag"]

    # rag 입력값
    search_query: str | None
    search_mode: Literal["vector", "keyword", "hybrid"]
    top_k: int
    rag_context: str | None

    # 정규화/라우팅 결과
    normalized_competency_type: str
    generation_mode: GenerationMode

    # ─────────────────────────────────────────────────────────────────
    # 멀티 스테이지 파이프라인 중간 결과
    # ─────────────────────────────────────────────────────────────────

    # 1단계 생성 결과: 본문·코드·해설·correct_statement만 있고 choices가 없는 임시 문제 배열
    stem_and_explanation_questions: list[dict[str, Any]]

    # 2단계 이후 choices까지 완성된 문제 배열 (기존 raw_questions와 동일 역할)
    raw_questions: list[dict[str, Any]]

    # 수리/검증 결과
    repaired_questions: list[dict[str, Any]]
    validated_questions: list[dict[str, Any]]

    # 저장 결과
    saved_questions: list[dict[str, Any]]

    # 설계서 (planner 경로)
    plans: list[dict[str, Any]]

    # 제어/에러
    error: str | None
    retry_count: int
    max_retries: int