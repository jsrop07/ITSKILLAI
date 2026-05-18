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
    planner_node,
    template_node,
    generate_stem_and_explanation_node,
    generate_options_node,
    rag_generation_node,
    validation_node,
    route_after_validation,
    save_node,
    retrieval_node,
)

logger = logging.getLogger("uvicorn.info")


def build_question_generation_graph():
    """
    멀티 스테이지 문제 생성 LangGraph.

    흐름:
    START
    → normalize
    → topic_validation
    → route
    → [planner / template / retrieval] 분기
    → generate_stem_and_explanation  (planner 경로: Stage-1, template은 바이패스)
    → generate_options               (planner/template 경로: Stage-2)
    → rag_generation                 (rag 경로)
    → validation
        ↓ 충분 or retry>=3           ↓ 부족(retry<3)
       save                    generate_stem_and_explanation (planner)
                               generate_options              (template)
                               rag_generation                (rag)
    → END

    정책:
    - 일반 초급/중급 및 Python/Java 고급: planner → Stage-1 → Stage-2
    - AI/SQL 고급: template → Stage-2(choice_generator 사용)
    - 문서 기반 생성: retrieval → rag_generation
    - retry_count >= 3: validation에서 강제 repair 후 save 진입
    """
    graph = StateGraph(QuestionGenerationState)

    # ── 노드 등록 ──────────────────────────────────────────────────────────────
    graph.add_node("normalize", normalize_node)
    graph.add_node("topic_validation", topic_validation_node)
    graph.add_node("route", route_node)

    graph.add_node("planner", planner_node)
    graph.add_node("template", template_node)
    graph.add_node("retrieval", retrieval_node)

    # 멀티 스테이지 생성 노드
    graph.add_node("generate_stem_and_explanation", generate_stem_and_explanation_node)
    graph.add_node("generate_options", generate_options_node)
    graph.add_node("rag_generation", rag_generation_node)

    graph.add_node("validation", validation_node)
    graph.add_node("save", save_node)

    # ── 엣지 연결 ─────────────────────────────────────────────────────────────
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "topic_validation")
    graph.add_edge("topic_validation", "route")

    # route → 각 경로 분기
    graph.add_conditional_edges(
        "route",
        route_by_generation_mode,
        {
            "planner": "planner",
            "template": "template",
            "rag": "retrieval",
        },
    )

    # planner 경로: planner → Stage-1 → Stage-2
    graph.add_edge("planner", "generate_stem_and_explanation")
    graph.add_edge("generate_stem_and_explanation", "generate_options")

    # template 경로: template → Stage-1(바이패스) → Stage-2
    graph.add_edge("template", "generate_stem_and_explanation")

    # generate_options → validation (planner + template 경로 공통)
    graph.add_edge("generate_options", "validation")

    # rag 경로
    graph.add_edge("retrieval", "rag_generation")
    graph.add_edge("rag_generation", "validation")

    # validation → 조건부 라우팅 (충분/강제 save or 루프백)
    graph.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "save": "save",
            "generate_stem_and_explanation": "generate_stem_and_explanation",
            "generate_options": "generate_options",
            "rag_generation": "rag_generation",
        },
    )

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