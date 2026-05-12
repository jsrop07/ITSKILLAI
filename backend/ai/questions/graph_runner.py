# backend/ai/questions/graph_runner.py

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
    generation_node,
    validation_node,
    save_node,
)

logger = logging.getLogger("uvicorn.info")


def build_question_generation_graph():
    """
    일반 문제 생성 LangGraph MVP.

    1차 목표:
    START
    → normalize_node
    → topic_validation_node
    → route_node
    → END

    이후 단계에서 planner/template/generation/validation/save 노드를 붙인다.
    """
    graph = StateGraph(QuestionGenerationState)

    graph.add_node("normalize", normalize_node)
    graph.add_node("topic_validation", topic_validation_node)
    graph.add_node("route", route_node)
    graph.add_node("planner", planner_node)
    graph.add_node("template", template_node)
    graph.add_node("generation", generation_node)
    graph.add_node("validation", validation_node)
    graph.add_node("save", save_node)

    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "topic_validation")
    graph.add_edge("topic_validation", "route")

    graph.add_conditional_edges(
        "route",
        route_by_generation_mode,
        {
            "planner": "planner",
            "template": "template",
        },
    )

    graph.add_edge("planner", "generation")
    graph.add_edge("template", "generation")
    graph.add_edge("generation", "validation")
    graph.add_edge("validation", "save")
    graph.add_edge("save", END)

    compiled_graph = graph.compile()

    return compiled_graph


question_generation_graph = build_question_generation_graph()


def run_question_generation_graph(initial_state: QuestionGenerationState) -> QuestionGenerationState:
    """
    외부에서 호출할 LangGraph 실행 함수.
    """
    logger.info("LangGraph [Run]: question generation graph start")

    result = question_generation_graph.invoke(initial_state)

    logger.info(
        f"LangGraph [Run]: question generation graph end "
        f"(generation_mode={result.get('generation_mode')})"
    )

    return result