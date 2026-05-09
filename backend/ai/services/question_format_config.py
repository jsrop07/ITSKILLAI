# backend/ai/services/question_format_config.py

from ai.services.competency_config import normalize_competency_type


QUESTION_FORMAT_RULES = {
    "java": {
        "중급": ["code_output", "override_behavior", "compile_error"],
        "고급": ["refactoring_choice", "exception_design", "collection_tradeoff"],
    },
    "python": {
        "중급": ["runtime_error", "code_output", "data_structure_fix"],
        "고급": ["exception_handling", "refactoring_choice", "performance_tradeoff"],
    },
    "sql": {
        "중급": ["query_result", "join_where_bug", "group_by_result"],
        "고급": ["index_plan_choice", "transaction_lock_case", "query_optimization"],
    },
    "ai": {
        "중급": [
            "retrieval_result_analysis",
            "metric_interpretation",
            "chunking_issue",
            "prompt_output_validation",
        ],
        "고급": [
            "rag_pipeline_diagnosis",
            "reranker_tradeoff",
            "hybrid_search_choice",
            "context_filtering_failure",
            "query_rewrite_failure",
            "llm_output_schema_validation",
        ],
    },
    "c_language": {
        "중급": [
            "c_pointer_array_result",
            "c_string_literal_error",
            "c_memory_allocation_result",
        ],
        "고급": [
            "c_malloc_free_bug",
            "c_dangling_pointer",
            "c_buffer_overflow",
            "c_struct_pointer",
        ],
    },
    "data_structure_algorithm": {
        "중급": ["complexity_analysis", "operation_trace", "data_structure_choice"],
        "고급": ["algorithm_selection", "pseudocode_bug", "tradeoff_analysis"],
    },
    "security": {
        "중급": ["vulnerable_code", "http_request_analysis", "authz_bug"],
        "고급": ["log_analysis", "token_risk", "access_policy_tradeoff"],
    },
    "software_engineering": {
        "중급": ["requirement_review", "test_failure", "change_request"],
        "고급": ["change_impact", "quality_attribute", "traceability_gap"],
    },
}


FORMAT_EVIDENCE_TYPE_MAP = {
    "code_output": "code_snippet",
    "override_behavior": "code_snippet",
    "compile_error": "code_snippet",
    "refactoring_choice": "code_snippet",
    "exception_design": "code_snippet",
    "collection_tradeoff": "code_snippet",

    "runtime_error": "code_snippet",
    "data_structure_fix": "code_snippet",
    "exception_handling": "code_snippet",
    "performance_tradeoff": "code_snippet",

    "pointer_trace": "code_snippet",
    "array_string_bug": "code_snippet",
    "function_parameter": "code_snippet",
    "memory_error": "code_snippet",
    "malloc_free_bug": "code_snippet",
    "struct_pointer": "code_snippet",

    "query_result": "sql_query",
    "join_where_bug": "sql_query",
    "group_by_result": "sql_query",
    "index_plan_choice": "execution_plan",
    "transaction_lock_case": "execution_plan",
    "query_optimization": "execution_plan",

    "retrieval_result_analysis": "retrieval_result",
    "metric_interpretation": "metric_report",
    "chunking_issue": "pipeline_condition",
    "rag_pipeline_diagnosis": "retrieval_result",
    "reranker_tradeoff": "retrieval_result",
    "hybrid_search_choice": "pipeline_condition",

    "complexity_analysis": "input_constraints",
    "operation_trace": "operation_pattern",
    "data_structure_choice": "operation_pattern",
    "algorithm_selection": "input_constraints",
    "pseudocode_bug": "pseudocode",
    "tradeoff_analysis": "operation_pattern",

    "vulnerable_code": "vulnerable_code",
    "http_request_analysis": "request_response",
    "authz_bug": "access_policy",
    "log_analysis": "log",
    "token_risk": "request_response",
    "access_policy_tradeoff": "access_policy",

    "requirement_review": "requirement_list",
    "test_failure": "test_failure",
    "change_request": "change_request",
    "change_impact": "change_request",
    "quality_attribute": "requirement_list",
    "traceability_gap": "requirement_list",

    "c_pointer_array_result": "code_snippet",
    "c_string_literal_error": "code_snippet",
    "c_memory_allocation_result": "code_snippet",
    "c_malloc_free_bug": "code_snippet",
    "c_dangling_pointer": "code_snippet",
    "c_buffer_overflow": "code_snippet",
    "c_struct_pointer": "code_snippet",
}


def get_allowed_question_formats(
    competency_type: str | None,
    difficulty: str,
) -> list[str]:
    competency_type = normalize_competency_type(competency_type)
    rules = QUESTION_FORMAT_RULES.get(competency_type or "")

    if not rules:
        return []

    if difficulty == "초급":
        return ["concept"]

    return rules.get(difficulty, rules.get("중급", []))


def get_expected_evidence_type(question_format: str | None) -> str | None:
    if not question_format:
        return None

    return FORMAT_EVIDENCE_TYPE_MAP.get(question_format)


def build_question_format_instruction(
    competency_type: str | None,
    difficulty: str,
) -> str:
    allowed_formats = get_allowed_question_formats(competency_type, difficulty)

    if not allowed_formats:
        return """
[문제 형식 규칙]
- 주어진 역량과 난이도에 맞는 문제 형식을 선택한다.
"""

    return f"""
[문제 형식 규칙]
- question_format은 반드시 다음 중 하나여야 한다: {", ".join(allowed_formats)}
- 중급/고급 문제에서는 question_format에 맞는 evidence_type과 evidence_detail을 반드시 작성한다.
- Java/Python/C언어 문제는 코드 없는 설명형 문제로 설계하지 않는다.
- SQL 문제는 쿼리/테이블/실행 계획 없는 설명형 문제로 설계하지 않는다.
- AI/RAG 문제는 검색 로그, 평가 지표, chunk, top_k, similarity, metadata, reranker 같은 구체 자료 없이 일반론으로 설계하지 않는다.
"""