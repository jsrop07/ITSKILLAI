# backend/ai/services/question_format_config.py

from ai.services.competency_config import normalize_competency_type


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
            "query_result",
        ],
        "중급": [
            "query_result",
            "join_where_bug",
            "group_by_result",
            "having_condition",
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
            "metric_interpretation",
            "embedding_similarity_case",
        ],
        "중급": [
            "retrieval_result_analysis",
            "embedding_similarity_case",
            "hybrid_search_choice",
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
            "langgraph_workflow_repair",
            "modelops_vllm_serving_tradeoff",
        ],
    },

    # 나머지 역량은 지금 우선순위는 아니지만 기존 구조 유지용
    "c_language": {
        "초급": [
            "c_pointer_array_result",
        ],
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
    "security": {
        "초급": [
            "http_request_analysis",
        ],
        "중급": [
            "vulnerable_code",
            "http_request_analysis",
            "authz_bug",
        ],
        "고급": [
            "log_analysis",
            "token_risk",
            "access_policy_tradeoff",
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
    # C
    # ─────────────────────────────────────────────
    "c_pointer_array_result": "code_snippet",
    "c_string_literal_error": "code_snippet",
    "c_memory_allocation_result": "code_snippet",
    "c_malloc_free_bug": "code_snippet",
    "c_dangling_pointer": "code_snippet",
    "c_buffer_overflow": "code_snippet",
    "c_struct_pointer": "code_snippet",

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
    # Security
    # ─────────────────────────────────────────────
    "vulnerable_code": "vulnerable_code",
    "http_request_analysis": "request_response",
    "authz_bug": "access_policy",
    "log_analysis": "log",
    "token_risk": "request_response",
    "access_policy_tradeoff": "access_policy",

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


def build_question_format_instruction(
    competency_type: str | None,
    difficulty: str,
) -> str:
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
- 중급/고급 문제에서는 question_format, evidence_type, evidence_detail을 반드시 작성한다.
- evidence_detail은 한 줄 설명이 아니라 실제 문제 본문에 들어갈 구체 단서여야 한다.
- evidence_detail에 "코드를 제시한다", "컬렉션 예시를 사용한다", "Python 코드를 포함한다" 같은 추상 설명을 쓰지 않는다.
evidence_detail에는 실제 코드 조각이 직접 들어가야 한다. 이 코드는 Generator가 body에 그대로 삽입할 수 있어야 한다.
[역량별 evidence 강제 규칙]
- Java/Python 중급·고급 문제는 코드 없는 설명형 문제로 설계하지 않는다.
- Java 중급/고급 evidence_detail에는 class, interface, extends, implements, new, Override, try/catch, HashSet, ArrayList, HashMap 중 하나 이상이 포함된 실제 Java 코드 조각이 들어가야 한다.
- Python 중급/고급 evidence_detail에는 def, print, list, dict, copy, yield, next, try, except, nonlocal, decorator, return 중 하나 이상이 포함된 실제 Python 코드 조각이 들어가야 한다.
- SQL 문제는 쿼리/테이블/실행 계획 없는 설명형 문제로 설계하지 않는다.
- SQL 중급/고급 evidence_detail에는 SELECT, FROM, WHERE, JOIN, GROUP BY, HAVING, INDEX, EXPLAIN, TRANSACTION 중 하나 이상이 들어가야 한다.
- AI/RAG 문제는 검색 로그, 평가 지표, chunk, top_k, similarity, metadata, reranker 같은 구체 자료 없이 일반론으로 설계하지 않는다.
- AI 중급/고급 evidence_detail에는 query, top_k, chunk, similarity, embedding, vector, keyword, metadata, reranker, latency, context 중 하나 이상이 들어가야 한다.

[금지 규칙]
- question_format을 허용 목록 밖의 값으로 만들지 않는다.
- evidence_type을 question_format과 맞지 않게 만들지 않는다.
- evidence_detail에 "코드를 제시한다", "SQL을 제시한다", "검색 결과를 제시한다", "Java 코드를 포함한다", "Python 예제를 사용한다"처럼 추상적으로 쓰지 않는다.
- evidence_detail에는 실제 코드 조각, 쿼리 조각, 로그 수치, 테이블 구조, 검색 결과 예시 중 하나를 직접 포함한다.
"""