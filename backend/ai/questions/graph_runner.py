# backend/ai/questions/graph_runner.py

import time
import logging
from langgraph.graph import StateGraph, START, END
from ai.questions.graph_state import QuestionGenerationState
from ai.questions.graph_nodes import (
    normalize_node,
    topic_validation_node,
    route_node,
    route_by_generation_mode,
    retrieval_node,
    question_generation_node,
    validation_node,
    save_node,
)

logger = logging.getLogger("uvicorn.info")


def build_question_generation_graph():
    """
    V2 중심 문제 생성 LangGraph.

    흐름:
    START
    → normalize
    → topic_validation
    → route
    → 조건 분기:
        question_v2     → question_generation
        question_v2_rag → retrieval → question_generation
    → question_generation → validation → save → END

    정책:
    - competency_type != "ai" → route_node에서 ValueError
    - difficulty == "고급" → route_node에서 ValueError
    - generation_source == "rag" → retrieval_node에서 RAG 검색 후 question_generation_node로
    - 초급/중급 일반 생성 → question_generation_node로 직행
    - V2 service 내부에서 자체 retry/validate를 수행하므로 LangGraph retry 루프 없음
    """
    graph = StateGraph(QuestionGenerationState)

    # ── 노드 등록 ──────────────────────────────────────────────────────────────
    graph.add_node("normalize", normalize_node)
    graph.add_node("topic_validation", topic_validation_node)
    graph.add_node("route", route_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("question_generation", question_generation_node)
    graph.add_node("validation", validation_node)
    graph.add_node("save", save_node)

    # ── 엣지 연결 ─────────────────────────────────────────────────────────────
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "topic_validation")
    graph.add_edge("topic_validation", "route")

    # route → 조건 분기
    graph.add_conditional_edges(
        "route",
        route_by_generation_mode,
        {
            "question_v2": "question_generation",
            "question_v2_rag": "retrieval",
        },
    )

    # RAG 경로: retrieval → question_generation
    graph.add_edge("retrieval", "question_generation")

    # 공통: question_generation → validation → save → END
    graph.add_edge("question_generation", "validation")
    graph.add_edge("validation", "save")
    graph.add_edge("save", END)

    compiled_graph = graph.compile()

    return compiled_graph


question_generation_graph = build_question_generation_graph()


def run_question_generation_graph(initial_state: QuestionGenerationState) -> QuestionGenerationState:
    """
    외부에서 호출할 LangGraph 실행 함수.
    초기 state에 retry_count=0이 없으면 자동 세팅한다.
    """
    if "retry_count" not in initial_state or initial_state.get("retry_count") is None:
        initial_state = {**initial_state, "retry_count": 0}

    start_time = time.perf_counter()
    logger.info("LangGraph [Run]: question generation graph start")

    try:
        result = question_generation_graph.invoke(initial_state)
        return result
    finally:
        elapsed = time.perf_counter() - start_time
        generation_mode = locals().get("result", {}).get("generation_mode", "unknown")
        retry_count = locals().get("result", {}).get("retry_count", 0)
        logger.info(
            f"LangGraph [Run]: question generation graph end "
            f"(generation_mode={generation_mode}, retry_count={retry_count}, elapsed={elapsed:.3f}s)"
        )