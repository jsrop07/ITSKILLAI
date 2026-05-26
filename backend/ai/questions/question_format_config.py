# backend/ai/questions/question_format_config.py

from ai.core.config import normalize_competency_type


QUESTION_FORMAT_RULES = {
    # ─────────────────────────────────────────────
    # Java
    # 초급/중급은 Planner 기반
    # 고급은 Template 기반이지만, planner fallback 상황도 대비해 format을 맞춰둔다.
    # ─────────────────────────────────────────────
    "java": {
        "초급": [
            "code_output",
        ],
        "중급": [
            "code_output",
            "override_behavior",
            "compile_error",
            "collection_behavior",
            "equals_hashcode",
            "exception_flow",
        ],
        "고급": [
            "polymorphism_dispatch",
            "equals_hashcode",
            "interface_abstract",
            "exception_flow",
            "collection_behavior",
            "compile_error",
        ],
    },

    # ─────────────────────────────────────────────
    # Python
    # ─────────────────────────────────────────────
    "python": {
        "초급": [
            "code_output",
        ],
        "중급": [
            "code_output",
            "runtime_error",
            "list_dict_mutation",
            "shallow_deep_copy",
            "generator_behavior",
            "exception_flow",
        ],
        "고급": [
            "generator_behavior",
            "decorator_behavior",
            "scope_closure",
            "exception_flow",
            "shallow_deep_copy",
            "runtime_error",
        ],
    },

    # ─────────────────────────────────────────────
    # SQL
    # ─────────────────────────────────────────────
    "sql": {
        "초급": [
            "basic_concept",
            "concept_difference",
        ],
        "중급": [
            "query_result",
            "join_where_bug",
            "group_by_result",
            "having_condition",
            "concept_compare_find_incorrect",
        ],
        "고급": [
            "index_plan_choice",
            "transaction_lock_case",
            "transaction_isolation",
            "normalization_case",
            "group_by_result",
        ],
    },
    
    # ─────────────────────────────────────────────
    # AI
    # ─────────────────────────────────────────────

    "ai": {
        "초급": [
            "basic_concept",
            "concept_difference",
        ],
        "중급": [
            "retrieval_result_analysis",
            "embedding_similarity_case",
            "hybrid_search_choice",
            "metric_interpretation",
            "chunking_issue",
            "prompt_output_validation",
            "structured_output_validation",
        ],
        "고급": [
            "structured_output_validation",
            "rag_pipeline_diagnosis",
            "reranker_tradeoff",
            "hybrid_search_choice",
            "context_filtering_failure",
            "query_rewrite_failure",
            "llm_output_schema_validation",
            "langgraph_workflow_repair",
            "modelops_vllm_serving_tradeoff",
        ],
    },

    "data_structure_algorithm": {
        "초급": [
            "operation_trace",
        ],
        "중급": [
            "complexity_analysis",
            "operation_trace",
            "data_structure_choice",
        ],
        "고급": [
            "algorithm_selection",
            "pseudocode_bug",
            "tradeoff_analysis",
        ],
    },
    
    "software_engineering": {
        "초급": [
            "requirement_review",
        ],
        "중급": [
            "requirement_review",
            "test_failure",
            "change_request",
        ],
        "고급": [
            "change_impact",
            "quality_attribute",
            "traceability_gap",
        ],
    },
}


FORMAT_EVIDENCE_TYPE_MAP = {
    "basic_concept": "concept",
    "concept_difference": "concept",
    "structured_output_validation": "llm_output",
    # ─────────────────────────────────────────────
    # Java
    # ─────────────────────────────────────────────
    "code_output": "code_snippet",
    "override_behavior": "code_snippet",
    "compile_error": "code_snippet",
    "polymorphism_dispatch": "code_snippet",
    "collection_behavior": "code_snippet",
    "equals_hashcode": "code_snippet",
    "interface_abstract": "code_snippet",
    "exception_flow": "code_snippet",

    # ─────────────────────────────────────────────
    # Python
    # ─────────────────────────────────────────────
    "runtime_error": "code_snippet",
    "list_dict_mutation": "code_snippet",
    "shallow_deep_copy": "code_snippet",
    "generator_behavior": "code_snippet",
    "decorator_behavior": "code_snippet",
    "scope_closure": "code_snippet",

    # ─────────────────────────────────────────────
    # SQL
    # ─────────────────────────────────────────────
    "query_result": "sql_query",
    "join_where_bug": "sql_query",
    "group_by_result": "sql_query",
    "having_condition": "sql_query",
    "index_plan_choice": "execution_plan",
    "concept_compare_find_incorrect": "sql_query",
    "transaction_lock_case": "execution_plan",
    "transaction_isolation": "execution_plan",
    "normalization_case": "table_schema",

    # ─────────────────────────────────────────────
    # AI / RAG / LLM / Agent / ModelOps
    # ─────────────────────────────────────────────
    "retrieval_result_analysis": "retrieval_result",
    "embedding_similarity_case": "retrieval_result",
    "metric_interpretation": "metric_report",
    "chunking_issue": "pipeline_condition",
    "prompt_output_validation": "llm_output",

    "rag_pipeline_diagnosis": "retrieval_result",
    "reranker_tradeoff": "retrieval_result",
    "hybrid_search_choice": "pipeline_condition",
    "context_filtering_failure": "retrieval_result",
    "query_rewrite_failure": "retrieval_result",
    "llm_output_schema_validation": "llm_output",
    "langgraph_workflow_repair": "workflow_state",
    "modelops_vllm_serving_tradeoff": "serving_metric",

    # ─────────────────────────────────────────────
    # Data Structure / Algorithm
    # ─────────────────────────────────────────────
    "complexity_analysis": "input_constraints",
    "operation_trace": "operation_pattern",
    "data_structure_choice": "operation_pattern",
    "algorithm_selection": "input_constraints",
    "pseudocode_bug": "pseudocode",
    "tradeoff_analysis": "operation_pattern",


    # ─────────────────────────────────────────────
    # Software Engineering
    # ─────────────────────────────────────────────
    "requirement_review": "requirement_list",
    "test_failure": "test_failure",
    "change_request": "change_request",
    "change_impact": "change_request",
    "quality_attribute": "requirement_list",
    "traceability_gap": "requirement_list",
}


def get_allowed_question_formats(
    competency_type: str | None,
    difficulty: str,
) -> list[str]:
    normalized_type = normalize_competency_type(competency_type)
    rules = QUESTION_FORMAT_RULES.get(normalized_type or "")

    if not rules:
        return []

    if difficulty == "초급":
        return rules.get("초급", ["concept"])

    return rules.get(difficulty, rules.get("중급", []))


def get_expected_evidence_type(question_format: str | None) -> str | None:
    if not question_format:
        return None

    return FORMAT_EVIDENCE_TYPE_MAP.get(question_format)


def build_question_format_instruction( competency_type: str | None, difficulty: str,) -> str:
    normalized_type = normalize_competency_type(competency_type)
    allowed_formats = get_allowed_question_formats(normalized_type, difficulty)

    if not allowed_formats:
        return """
            [문제 형식 규칙]
            - 주어진 역량과 난이도에 맞는 문제 형식을 선택한다.
            - question_format, evidence_type, evidence_detail을 가능한 한 구체적으로 작성한다.
        """

    expected_pairs = [
        f"{fmt} → {get_expected_evidence_type(fmt) or 'evidence_detail'}"
        for fmt in allowed_formats
    ]

    return f"""
        [문제 형식 규칙]
        - question_format은 반드시 다음 중 하나여야 한다: {", ".join(allowed_formats)}
        - 각 question_format에 맞는 evidence_type은 다음 기준을 따른다:
        {chr(10).join("- " + pair for pair in expected_pairs)}
        - question_format은 허용 목록 밖의 값을 사용하지 않는다.
        - evidence_type은 question_format과 맞는 값을 사용한다.
        - evidence_detail은 실제 문제 본문에 반영할 수 있는 구체 단서로 작성한다.
        """