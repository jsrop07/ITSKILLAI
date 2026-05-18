# backend/ai/questions/choice_generator.py

import re
import json
import logging
from copy import deepcopy

from ai.core.openai_client import client

logger = logging.getLogger("uvicorn.info")

ABSTRACT_SQL_CHOICE_PATTERNS = [
    "성능을 개선한다",
    "최적화를 진행한다",
    "주기적으로 검토한다",
    "상황에 맞게 적용한다",
    "적절히 조정한다",
    "효율적으로 처리한다",
    "문제를 해결한다",
    "쿼리 성능을 개선한다",
]

SQL_ANSWER_INTENTS = {
    "composite_index_with_execution_plan_and_write_cost",
    "join_composite_index_with_filesort_and_write_cost",
    "group_by_composite_index_with_temp_filesort_and_write_cost",
    "cursor_pagination_with_index_scan_reduction",
    "covering_index_tradeoff_with_update_cost",
    "unique_composite_index_to_reduce_lock_range",
}

REQUIRED_KEYWORDS_BY_INTENT = {
    # AI/RAG 고급 템플릿
    "combine_vector_keyword_and_metadata_filter": [
        ["vector", "벡터"],
        ["keyword", "키워드"],
        ["metadata", "메타데이터"],
    ],
    "metadata_filter_and_reranker": [
        ["metadata", "메타데이터"],
        ["reranker", "리랭커", "재정렬"],
    ],
    "tune_reranker_scope_with_latency_measurement": [
        ["reranker", "리랭커", "재정렬"],
        ["latency", "지연", "응답 시간", "p95"],
    ],
    "adjust_chunking_by_semantic_units": [
        ["chunk", "청크"],
        ["chunk_size", "overlap", "분할", "재분할"],
        ["문단", "제목", "수행준거", "semantic", "의미"],
    ],
    "filter_context_by_relevance_evidence_metadata": [
        ["context", "컨텍스트", "chunk", "청크", "검색된 chunk", "검색된 문서"],
        ["filtering", "필터링", "거르는", "선별", "전달"],
        ["evidence", "근거", "metadata", "메타데이터", "relevance", "관련성"],
    ],
    "reject_or_retry_when_context_evidence_insufficient": [
        ["context", "문서", "검색"],
        ["근거", "evidence"],
        ["부족", "불충분", "재검색", "보류", "reject", "retry"],
    ],
    "evaluate_retrieval_with_recall_mrr_latency": [
        ["recall", "Recall"],
        ["mrr", "MRR", "순위"],
        ["latency", "지연", "p95", "응답 시간"],
    ],
    "rewrite_query_with_domain_terms_and_compare_results": [
        ["query", "질의"],
        ["rewrite", "재작성", "확장"],
        ["도메인", "복합 인덱스", "실행 계획", "filesort", "rows", "filtered"],
        ["비교", "compare", "keyword", "키워드"],
    ],

    # LLM 고급 템플릿
    "llm_structured_output_validation": [
        ["structured output", "structured", "schema", "json", "JSON", "response_format", "구조화"],
        ["검증", "validation", "필수 필드", "answer", "choices", "범위", "서버"],
    ],
    "llm_tool_calling_argument_validation": [
        ["tool calling", "tool", "도구", "function calling", "function", "함수"],
        ["schema", "인자", "argument", "타입", "category", "top_k", "허용값"],
        ["검증", "validation", "재시도", "retry", "observation", "오류 원인"],
    ],
    "llm_prompt_injection_guard": [
        ["prompt", "프롬프트", "injection", "인젝션"],
        ["system", "instruction", "사용자 입력", "지시"],
        ["validation", "검증", "fallback", "정책"],
    ],
    "llm_response_format_fallback": [
        ["response_format", "schema", "JSON", "필수 필드"],
        ["validation", "검증", "파싱", "타입", "서버"],
        ["fallback", "재시도", "보류", "실패 사유", "실패 원인"],
    ],
    "llm_multi_turn_context_state_tracking": [
        ["multi-turn", "대화", "이전", "최근"],
        ["state", "current_competency", "previous_question_id", "요약"],
        ["확인", "분기", "context", "맥락", "추적", "지시 대상", "요청"],
    ],

    # AI Agent 고급 템플릿
    "agent_tool_retry_observation_loop": [
        ["observation", "관찰", "도구 결과"],
        ["tool call", "도구 호출"],
        ["재시도", "retry", "재검색", "query 재작성"],
    ],
    "agent_langgraph_state_human_review": [
        ["validation_node", "검증 오류", "validation error"],
        ["retry_count", "반복 실패", "repair_node", "repair 한도"],
        ["human review", "human_review_node", "검수 분기"],
    ],
    "agent_conditional_edge_by_validation_error": [
        ["validation_node", "검증 오류", "validation error"],
        ["conditional edge", "조건부 edge", "조건부 분기"],
        ["repair_node", "retrieval_node", "human_review_node", "human review"],
    ],
    "agent_state_schema_validation": [
        ["state", "상태"],
        ["schema", "스키마", "타입 검증"],
        ["validation_errors", "retry_count", "노드 입출력"],
    ],
    "agent_checkpoint_resume_with_retry_count": [
        ["checkpoint", "체크포인트"],
        ["resume", "재개", "실패 노드", "실패 지점"],
        ["retry_count", "human review", "human_review_node", "반복 실패"],
    ],
    "agent_memory_filter_by_current_context": [
        ["memory", "메모리"],
        ["current_competency", "current_topic", "현재 요청 기준"],
        ["filter", "필터링", "context leak", "컨텍스트 누출"],
    ],
    # AI ModelOps 고급 템플릿
    "modelops_finetuning_dataset_quality": [
        ["fine-tuning", "파인튜닝", "JSONL"],
        ["approved", "quality_score"],
        ["answer/explanation", "answer", "explanation", "competency_type", "불일치"],
    ],
    "modelops_vllm_serving_latency_cost_tradeoff": [
        ["vLLM", "vllm", "자체 서빙", "serving"],
        ["latency", "p95", "cost", "비용"],
        ["품질 통과율", "canary", "일부 트래픽 검증", "단계적 검증"],
    ],
    "modelops_dataset_leakage_prevention": [
        ["fine-tuning", "파인튜닝", "JSONL"],
        ["leakage", "데이터 누수", "유사 문제", "중복 문제"],
        ["train/validation/test", "train", "validation", "test", "split"],
    ],
    "modelops_evaluation_gate_before_deployment": [
        ["evaluation gate", "평가 게이트"],
        ["quality_score", "검증 통과율", "answer 불일치율", "hallucination rate", "관리자 반려율"],
        ["배포 보류", "기준 미달", "배포 기준"],
    ],
    "modelops_monitoring_and_rollback": [
        ["monitoring", "모니터링", "운영 대시보드"],
        ["rollback", "롤백"],
        ["관리자 반려율", "검증 실패율", "answer 불일치율", "p95 latency", "cost"],
    ],

    # ML/DL 고급 템플릿
    "ml_imbalanced_metric_precision_recall_f1": [
        ["accuracy", "정확도", "불균형", "소수", "소수 클래스", "이탈 위험 고객", "이탈 고객", "모델", "성능"],
        ["precision", "정밀도", "recall", "재현율", "f1"],
    ],
    "ml_overfitting_split_regularization": [
        ["train", "validation", "test"],
        ["과적합", "overfitting", "일반화"],
        ["분리", "split", "regularization", "early stopping"],
    ],
    "ml_threshold_tuning_with_cost_tradeoff": [
        ["threshold", "임계값"],
        ["precision", "정밀도", "recall", "재현율", "f1", "F1"],
        ["false positive", "false negative", "비용", "쿠폰", "매출 손실"],
    ],
    "ml_precision_recall_tradeoff_with_cost": [
        ["precision", "정밀도"],
        ["recall", "재현율"],
        ["trade-off", "트레이드오프", "균형", "비용"],
    ],
    "ml_data_drift_monitoring_and_retraining": [
        ["drift", "드리프트", "분포"],
        ["feature", "prediction", "운영 데이터", "학습 데이터"],
        ["monitoring", "모니터링", "재학습", "데이터 보강"],
    ],
    "dl_learning_rate_scheduler_stability": [
        ["learning rate", "학습률"],
        ["scheduler", "스케줄러", "early stopping"],
        ["loss", "validation", "수렴", "안정성"],
    ],
    "dl_transfer_learning_gradual_unfreeze": [
        ["transfer learning", "전이학습", "사전학습", "backbone"],
        ["freeze", "unfreeze", "동결"],
        ["fine-tuning", "파인튜닝", "learning rate"],
    ],
    "dl_batch_size_gpu_memory_tradeoff": [
        ["batch size", "배치 크기"],
        ["GPU memory", "GPU 메모리", "OOM"],
        ["gradient accumulation", "mixed precision", "sequence length"],
    ],
    # SQL 고급 템플릿
    "composite_index_with_execution_plan_and_write_cost": [
        ["복합", "composite"],
        ["인덱스", "index"],
        ["실행 계획", "execution plan", "rows", "filtered"],
        ["쓰기", "insert", "지연", "비용", "부하"],
    ],
    "join_composite_index_with_filesort_and_write_cost": [
        ["join", "조인"],
        ["복합", "composite"],
        ["인덱스", "index"],
        ["filesort", "정렬"],
        ["쓰기", "insert", "비용", "지연", "부하"],
    ],
    "group_by_composite_index_with_temp_filesort_and_write_cost": [
        ["group by", "GROUP BY", "집계"],
        ["복합", "composite"],
        ["인덱스", "index"],
        ["temporary", "임시", "filesort", "정렬"],
        ["쓰기", "insert", "INSERT", "지연", "비용", "부하", "운영 조건", "동시 조회"]
    ],
    "cursor_pagination_with_index_scan_reduction": [
        ["커서", "cursor"],
        ["페이징", "pagination", "페이지네이션"],
        ["offset", "OFFSET", "깊은 페이지", "스캔"],
        ["rows", "스캔", "감소"],
    ],
    "covering_index_tradeoff_with_update_cost": [
        ["커버링", "covering"],
        ["인덱스", "index"],
        ["update", "UPDATE", "쓰기", "비용", "부하"],
        ["비교", "trade-off", "트레이드오프", "성능 차이", "차이를 분석", "평가", "균형", "분석", "고려"]
    ],
    "unique_composite_index_to_reduce_lock_range": [
        ["unique", "유니크"],
        ["coupon_id", "쿠폰"],
        ["user_id", "사용자"],
        ["락", "lock"],
        ["범위", "경합", "충돌"],
    ],
}


def _is_too_abstract_sql_choice(choice: str) -> bool:
    normalized = " ".join(choice.strip().split())

    # 너무 짧은 선택지는 고급 SQL 문제에서 근거 부족 가능성이 큼
    if len(normalized) < 28:
        return True

    # 추상 표현으로 끝나는 선택지 감지
    for pattern in ABSTRACT_SQL_CHOICE_PATTERNS:
        if pattern in normalized:
            # 단, 구체 키워드가 충분하면 허용
            concrete_keywords = [
                "복합 인덱스",
                "커버링 인덱스",
                "실행 계획",
                "rows",
                "filtered",
                "temporary",
                "filesort",
                "OFFSET",
                "LIMIT",
                "커서",
                "SELECT FOR UPDATE",
                "유니크",
                "락",
                "쓰기 비용",
                "쓰기 부하",
                "INSERT",
                "UPDATE",
                "버퍼풀",
                "JOIN",
                "GROUP BY",
                "인덱스 후보",
                "성능 차이",
                "비교",
                "평가",
                "균형",
            ]
            if not any(keyword in normalized for keyword in concrete_keywords):
                return True

    return False

def _has_extreme_choice_length_gap(choices: list[str]) -> bool:
    lengths = [len(choice.strip()) for choice in choices if choice and choice.strip()]

    if len(lengths) < 5:
        return True

    min_len = min(lengths)
    max_len = max(lengths)

    # 제일 긴 선택지가 제일 짧은 선택지의 2.6배 이상이면 티가 남
    if min_len > 0 and max_len / min_len >= 2.6:
        return True

    return False

def _clean_json_response(content: str):
    cleaned = content.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return json.loads(cleaned)


def _request_choice_json(prompt: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 IT 역량진단 문제은행의 객관식 선택지/해설 작성자다. "
                    "반드시 유효한 JSON 객체만 출력한다."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content or ""
    logger.info(f"LLM choice response preview: {str(content)[:800]}")
    return _clean_json_response(content)

def _matches_required_keyword_groups(choice_text: str, required_keyword_groups: list[list[str]]) -> bool:
    """
    선택지 하나가 answer_intent의 필수 키워드 그룹을 모두 만족하는지 확인한다.
    각 그룹 안에서는 하나의 키워드만 포함되어도 통과한다.
    """
    lowered = str(choice_text).lower()

    for group in required_keyword_groups:
        if not any(str(keyword).lower() in lowered for keyword in group):
            return False

    return True

def _extract_answer_number_from_explanation(explanation: str) -> int | None:
    if not explanation:
        return None

    patterns = [
        r"정답은\s*(\d+)\s*번",
        r"정답\s*:\s*(\d+)\s*번",
        r"답은\s*(\d+)\s*번",
        r"(\d+)\s*번이\s*정답",
    ]

    for pattern in patterns:
        match = re.search(pattern, explanation)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None

    return None

def _normalize_explanation_style(explanation: str, answer_int: int) -> str:
    """
    객관식 해설의 종결 어미를 존댓말 스타일로 통일한다.
    - '~다.' / '~한다.' / '~높아진다.' 같은 문어체 반말 종결을 줄인다.
    - 정답 번호 문구는 최종 answer와 맞춘다.
    """
    text = str(explanation or "").strip()

    if not text:
        return f"정답은 {answer_int}번입니다."

    replacements = {
        "가능성이 높아진다.": "가능성이 높아집니다.",
        "가능성이 낮아진다.": "가능성이 낮아집니다.",
        "개선될 수 있다.": "개선될 수 있습니다.",
        "판단할 수 있다.": "판단할 수 있습니다.",
        "확인할 수 있다.": "확인할 수 있습니다.",
        "줄일 수 있다.": "줄일 수 있습니다.",
        "높일 수 있다.": "높일 수 있습니다.",
        "도움이 된다.": "도움이 됩니다.",
        "필요하다.": "필요합니다.",
        "중요하다.": "중요합니다.",
        "적절하다.": "적절합니다.",
        "타당하다.": "타당합니다.",
        "부족하다.": "부족합니다.",
        "제한된다.": "제한됩니다.",
        "발생한다.": "발생합니다.",
        "증가한다.": "증가합니다.",
        "감소한다.": "감소합니다.",
        "해결한다.": "해결합니다.",
        "반영한다.": "반영합니다.",
        "고려한다.": "고려합니다.",
        "검토한다.": "검토합니다.",
        "비교한다.": "비교합니다.",
        "평가한다.": "평가합니다.",
        "분석한다.": "분석합니다.",
        "측정한다.": "측정합니다.",
        "역할을 한다.": "역할을 합니다.",
        "설명하고 있다.": "설명하고 있습니다.",
        "잘못 설명하고 있다.": "잘못 설명하고 있습니다.",
        "잘못 이해한 것이다.": "잘못 이해한 것입니다.",
        "잘못 이해한 설명이다.": "잘못 이해한 설명입니다.",
        "잘못된 설명이다.": "잘못된 설명입니다.",
        "구분된다.": "구분됩니다.",
        "사용된다.": "사용됩니다.",
        "포함한다.": "포함합니다.",
        "의미한다.": "의미합니다.",
        "생성한다.": "생성합니다.",
        "반환한다.": "반환합니다.",
        "유지한다.": "유지합니다.",
        "결정한다.": "결정합니다.",
        "정의한다.": "정의합니다.",
        "재정의한다.": "재정의합니다.",
        "동작한다.": "동작합니다.",
        "실패한다.": "실패합니다.",
        "통과한다.": "통과합니다.",
        "누락된다.": "누락됩니다.",
        "발생할 수 있다.": "발생할 수 있습니다.",
        "볼 수 있다.": "볼 수 있습니다.",
        "해야 한다.": "해야 합니다.",
        "아니다.": "아닙니다.",
        "않는다.": "않습니다.",
        "설명한다.": "설명합니다.",
        "다르다.": "다릅니다.",
        "같다.": "같습니다.",
        "이다.": "입니다.",
        "한다.": "합니다.",
        "안 된다.": "안 됩니다.",
        "안 된 다.": "안 됩니다.",
        "혼동해서는 안 된다.": "혼동해서는 안 됩니다.",
        "가진다.": "가집니다.",
        "포함된다.": "포함됩니다.",
        "어렵다.": "어렵습니다.",
        "쉽다.": "쉽습니다.",
        "나타낸다.": "나타냅니다.",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    return text

def _validate_generated_choices(
    result: dict,
    answer_intent: str | None = None,
) -> tuple[list[str], int, str]:
    """
    LLM이 생성한 choices/answer/explanation을 검사한다.
    문제가 있으면 ValueError를 발생시킨다.
    """
    if not isinstance(result, dict):
        raise ValueError("choices 생성 결과가 JSON 객체가 아닙니다.")

    choices = result.get("choices", [])

    answer = result.get("answer")
    explanation = result.get("explanation")

    if not isinstance(choices, list) or len(choices) != 5:
        raise ValueError("choices가 5개 배열이 아닙니다.")
    answer_intent = answer_intent or ""

    if answer_intent in SQL_ANSWER_INTENTS:
        for choice in choices:
            if _is_too_abstract_sql_choice(str(choice)):
                raise ValueError(f"SQL 선택지가 너무 추상적입니다: {choice}")

        if _has_extreme_choice_length_gap(choices):
            raise ValueError("SQL 선택지 간 길이 차이가 너무 큽니다.")
    try:
        answer_int = int(answer)
    except Exception as e:
        raise ValueError("answer가 숫자가 아닙니다.") from e

    if answer_int < 1 or answer_int > 5:
        raise ValueError("answer가 1~5 범위를 벗어났습니다.")

    if not explanation or not str(explanation).strip():
        raise ValueError("explanation이 비어 있습니다.")

    explanation_text = str(explanation).strip()
    explanation_answer = _extract_answer_number_from_explanation(explanation_text)

    if explanation_answer is None:
        raise ValueError("explanation에 '정답은 N번입니다.' 형식의 정답 번호가 없습니다.")

    if explanation_answer != answer_int:
        raise ValueError(
            f"explanation의 정답 번호가 answer와 다릅니다. "
            f"answer={answer_int}, explanation_answer={explanation_answer}"
        )
    if len(explanation_text) < 100:
        raise ValueError(
            "explanation이 너무 짧습니다. 정답 이유와 주요 오답이 부족한 이유를 함께 설명해야 합니다."
        )

    # 정답 문장만 반복하고 끝나는 해설 방지
    weak_explanation_patterns = [
        "효과적으로 반영할 수 있습니다.",
        "품질을 개선할 수 있습니다.",
        "안정성을 높일 수 있습니다.",
        "가장 적절한 접근입니다.",
        "가장 효과적입니다.",
    ]

    if len(explanation_text.split(".")) <= 2 and any(
        pattern in explanation_text for pattern in weak_explanation_patterns
    ):
        raise ValueError(
            "explanation이 정답 선택지를 반복하는 수준입니다. 오답이 왜 부족한지도 설명해야 합니다."
        )
    correct_choice_text = str(choices[answer_int - 1]).lower()

    required_keyword_groups = REQUIRED_KEYWORDS_BY_INTENT.get(answer_intent)

    def _count_matched_required_groups(choice_text: str, required_keyword_groups: list[list[str]]) -> int:
        lowered = str(choice_text).lower()
        count = 0

        for group in required_keyword_groups:
            if any(str(keyword).lower() in lowered for keyword in group):
                count += 1

        return count

    if required_keyword_groups:
        if not _matches_required_keyword_groups(correct_choice_text, required_keyword_groups):
            missing_groups = []

            for group in required_keyword_groups:
                if not any(str(keyword).lower() in correct_choice_text for keyword in group):
                    missing_groups.append(group)

            raise ValueError(
                f"정답 선택지가 answer_intent={answer_intent}의 핵심 조건을 충분히 포함하지 않습니다. "
                f"missing={missing_groups}, correct_choice={choices[answer_int - 1]}"
            )
        # 정답과 오답의 조건 충족 차이가 너무 작으면 복수정답처럼 보일 수 있다.
        correct_match_count = _count_matched_required_groups(
            choices[answer_int - 1],
            required_keyword_groups,
        )

        confusing_wrong_choices = []

        for idx, choice in enumerate(choices):
            if idx == answer_int - 1:
                continue

            wrong_match_count = _count_matched_required_groups(
                str(choice),
                required_keyword_groups,
            )

            # 오답이 정답 조건을 모두 만족하는 경우만 복수정답 후보로 본다.
            # 단, 정답 조건 그룹이 4개 이상이면 1개 부족까지는 경고 대상으로 본다.
            if wrong_match_count >= correct_match_count:
                confusing_wrong_choices.append(choice)
            elif len(required_keyword_groups) >= 4 and wrong_match_count >= correct_match_count - 1:
                confusing_wrong_choices.append(choice)

        if confusing_wrong_choices:
            raise ValueError(
                "오답이 정답 조건을 너무 많이 만족해 복수정답처럼 보입니다. "
                f"answer_intent={answer_intent}, confusing_wrong_choices={confusing_wrong_choices}"
            )
    weak_choice_patterns = [
        "무조건",
        "항상",
        "오직",
        "확인 없이",
        "완전히 제거",
        "데이터를 삭제",
        "모든 요청",
        "모든 데이터를",
        "전혀",
        "절대",
        "유일한",
        "무관하게",
        "관계없이",
    ]

    cleaned_choices = [
        " ".join(str(choice).strip().split())
        for choice in choices
    ]

    normalized_for_duplicate_check = [
        re.sub(r"\s+", "", choice.lower())
        for choice in cleaned_choices
    ]

    if len(set(normalized_for_duplicate_check)) != len(normalized_for_duplicate_check):
        raise ValueError("중복되거나 거의 동일한 선택지가 포함되어 있습니다.")

    for choice_text in cleaned_choices:
        min_choice_length = 28 if answer_intent and answer_intent not in SQL_ANSWER_INTENTS else 35

        if len(choice_text) < min_choice_length:
            raise ValueError(f"선택지가 너무 짧습니다: {choice_text}")

        if any(pattern in choice_text for pattern in weak_choice_patterns):
            raise ValueError(f"약한 선택지 표현이 포함되어 있습니다: {choice_text}")

    revealing_patterns = [
        "하지만",
        "그러나",
        "다만",
        "못한다",
        "않는다",
        "제한적",
        "보장하지",
        "해결하지",
    ]

    revealing_count = 0

    for choice_text in cleaned_choices:
        if any(pattern in choice_text for pattern in revealing_patterns):
            revealing_count += 1

    if answer_intent in SQL_ANSWER_INTENTS and revealing_count >= 3:
        raise ValueError(
            f"오답 한계가 너무 노골적으로 드러나는 선택지가 많습니다: revealing_count={revealing_count}"
        )

    if answer_intent not in SQL_ANSWER_INTENTS and revealing_count >= 4:
        raise ValueError(
            f"오답 한계가 너무 노골적으로 드러나는 선택지가 많습니다: revealing_count={revealing_count}"
        )

    cleaned_explanation = _normalize_explanation_style(explanation, answer_int)

    return cleaned_choices, answer_int, str(cleaned_explanation).strip()

def _build_choice_prompt(
    title: str,
    body: str,
    answer_intent: str,
    distractor_intents: list,
    retry: bool = False,
) -> str:
    retry_rule = ""

    if retry:
        retry_rule = """
[이전 생성 실패 사유]
- 오답 선택지들이 "~하지만", "~못한다", "~제한적이다" 구조로 반복되어 정답이 쉽게 드러났다.
- 이번에는 오답의 한계를 문장 안에 노골적으로 쓰지 말고, 모두 그럴듯한 대안처럼 작성한다.
- 선택지 5개 모두 실제 실무자가 고려할 수 있는 조치처럼 작성한다.
- 정답만 "종합적 조치"로 보이고 오답은 "단일 조치 + 한계"로 보이면 안 된다.
- SQL 정답 선택지는 explanation이 아니라 선택지 문장 자체에 필수 키워드를 포함해야 한다.
- composite_index_with_execution_plan_and_write_cost 정답은 "복합 인덱스", "실행 계획", "rows 또는 filtered", "쓰기 비용 또는 INSERT 지연"을 한 문장 안에 모두 포함해야 한다.
- join_composite_index_with_filesort_and_write_cost 정답은 "JOIN", "복합 인덱스", "filesort 또는 정렬", "쓰기 비용 또는 INSERT 부하"를 한 문장 안에 모두 포함해야 한다.
- unique_composite_index_to_reduce_lock_range 정답은 "유니크 복합 인덱스", "coupon_id", "user_id", "락 범위 또는 락 경합"을 한 문장 안에 모두 포함해야 한다.
- group_by_composite_index_with_temp_filesort_and_write_cost 정답은 "GROUP BY 또는 집계", "복합 인덱스", "temporary/filesort 또는 정렬", "쓰기 비용 또는 INSERT 부하 또는 운영 조건"을 선택지 문장에 포함해야 한다.
- llm_structured_output_validation 정답은 "JSON/schema/structured output/response_format" 중 하나와 "서버 검증/필수 필드/answer 범위/choices 개수" 중 하나를 함께 포함해야 한다.
- llm_tool_calling_argument_validation 정답은 "tool calling/tool schema/도구 호출" 중 하나와 "인자 타입/category/top_k/허용값 검증" 중 하나를 함께 포함해야 한다.
- agent_tool_retry_observation_loop 정답은 "observation/도구 결과" 확인과 "재시도/retry/재검색/query 재작성" 중 하나를 함께 포함해야 한다.
- agent_langgraph_state_human_review 정답은 "validation_node/검증 오류"와 "retry_count/repair_node/반복 실패"와 "human review/검수 분기" 중 둘 이상을 포함해야 한다.
- modelops_finetuning_dataset_quality 정답은 "approved/quality_score/JSONL" 중 하나와 "answer/explanation/competency_type 검증 또는 정제" 중 하나를 함께 포함해야 한다.
- modelops_vllm_serving_latency_cost_tradeoff 정답은 "vLLM/서빙", "latency/cost", "품질 통과율/canary/일부 트래픽 검증" 흐름이 드러나게 작성한다.
- ml_imbalanced_metric_precision_recall_f1 정답은 "accuracy만 보지 않는다"는 취지와 "precision/recall/F1" 중 하나를 반드시 포함해야 한다. threshold/비용/소수 클래스/불균형은 가능하면 포함하되 필수는 아니다.
- ml_overfitting_split_regularization 정답은 "train/validation/test 분리"와 "과적합/일반화/regularization/early stopping" 중 하나를 함께 포함해야 한다.
- covering_index_tradeoff_with_update_cost 정답은 "커버링 인덱스", "UPDATE 또는 쓰기 비용", "비교 또는 성능 차이 또는 균형 또는 고려"를 선택지 문장에 포함해야 한다.
- 이전 생성에서 정답 선택지만 길어 정답이 노출되었다.
- 이번에는 정답 선택지를 줄이기보다 오답 선택지도 정답과 비슷한 길이와 구체성으로 작성한다.
- 모든 선택지는 70~110자 사이로 맞추고, 선택지 간 길이 차이는 최대 25자 이내로 유지한다.
"""

    return f"""
아래 문제의 title과 body는 이미 확정되어 있다.
title과 body는 절대 수정하지 마라.

너의 역할은 choices 5개와 explanation만 작성하는 것이다.

{retry_rule}

[확정 title]
{title}

[확정 body]
{body}

[정답 의도]
{answer_intent}

[오답 의도 목록]
{json.dumps(distractor_intents, ensure_ascii=False)}

[작성 규칙]
- 반드시 JSON 객체 하나만 출력한다.
- JSON 객체는 choices, answer, explanation 필드만 가진다.
- choices는 반드시 문자열 5개 배열이다.
- answer는 반드시 1~5 사이 숫자다.
- 정답 선택지는 [정답 의도]에 해당해야 한다.
- 오답 선택지는 [오답 의도 목록]을 각각 반영해야 한다.
- 오답도 틀린 행동처럼 쓰지 말고, 실제 실무자가 고려할 수 있는 대안처럼 작성한다.
- 오답의 부족한 점을 "하지만", "그러나", "다만", "못한다", "않는다", "제한적"으로 직접 드러내지 마라.
- 선택지 5개 중 "하지만", "그러나", "다만", "못한다", "않는다", "제한적" 표현은 최대 2개 선택지에서만 사용한다.
- "무시한다", "삭제한다", "무조건", "항상", "오직", "단순히", "완전히 제거한다", "전혀", "절대", "유일한", "무관하게", "관계없이" 같은 쉽게 제거되는 표현을 절대 쓰지 마라.
- 각 선택지는 최소 35자 이상으로 작성한다.
- 선택지 5개는 비슷한 길이와 비슷한 구체성을 가져야 한다.
- 정답 선택지만 길고 오답이 짧으면 안 된다. 오답 선택지도 정답과 비슷한 길이로 작성하거나, 때로는 오답을 더 길게 작성하여 길이로 정답을 유추할 수 없도록 만든다.
- explanation은 반드시 "정답은 N번입니다."로 시작한다.
- N은 answer 값과 반드시 같아야 한다.
- explanation은 반드시 처음부터 끝까지 존댓말(경어체) 문체로 작성한다.
- "~이다", "~한다", "~높아진다", "~적절하다", "~필요하다", "~않는다" 같은 반말형 종결을 쓰지 않는다.
- 모든 문장은 "~입니다", "~합니다", "~수 있습니다", "~해야 합니다", "~않습니다"처럼 존댓말(경어체)로 끝낸다. 반말과 존댓말이 섞이면 절대 안 된다.
- explanation은 최소 4문장 이상으로 작성한다.
- explanation은 body에 제시된 evidence와 연결해서 설명한다.
- 첫 문장에서는 정답 선택지가 문제의 어떤 조건을 만족하는지 설명한다.
- 두 번째 문장에서는 정답 선택지가 다른 선택지보다 우선되는 이유를 설명한다.
- 세 번째 문장부터는 주요 오답 2개 이상이 왜 부족한지 설명한다.
- 오답 설명은 번호 기준으로 쓰지 말고 선택지의 핵심 조치 기준으로 설명한다.
- 예: "top_k만 늘리는 방식은 후보 수는 늘릴 수 있으나 metadata 불일치나 정확 키워드 누락을 직접 해결하지 못합니다."
- 예: "embedding 모델 교체는 장기적으로 검토할 수 있지만, 현재 로그에서 드러난 metadata_filter 미적용 문제를 즉시 해결하지 못합니다."
- "정답 선택지를 다시 말하는 수준"의 해설은 금지한다.
- "가장 적절합니다", "효과적입니다", "품질을 높일 수 있습니다" 한 문장으로 끝내지 않는다.
- RAG 문제라면 query, top_k, chunk, similarity, metadata_filter, reranker, latency를 근거로 삼는다.
- LLM 문제라면 prompt, JSON, schema, structured output, tool calling, 인자 검증, fallback, retry를 근거로 삼는다.
- Agent 문제라면 plan, tool call, observation, state, validation_node, repair_node, retry_count, human review 분기를 근거로 삼는다.
- ModelOps 문제라면 approved 데이터, quality_score, JSONL, fine-tuning, QLoRA, vLLM, latency, cost, canary, 운영 부담을 근거로 삼는다.
- ML 문제라면 train/validation/test, accuracy, precision, recall, F1, threshold, overfitting, regularization, early stopping을 근거로 삼는다.
- SQL 문제라면 테이블 구조, SQL 쿼리, 데이터 규모, 실행 계획, rows, filtered, Extra, 인덱스, 정렬, 락, 쓰기 부하를 근거로 삼는다.
- 오답 설명은 번호 기준으로 쓰지 말고, 선택지의 핵심 조치 내용 기준으로 설명한다.
- 정답 선택지는 [정답 의도]의 핵심 조치를 모두 포함해야 한다.
- 정답 의도가 combine_vector_keyword_and_metadata_filter이면 정답 선택지에는 vector search, keyword search, metadata_filter가 모두 포함되어야 한다.
- 정답 의도가 metadata_filter_and_reranker이면 정답 선택지에는 metadata_filter와 reranker가 모두 포함되어야 한다.
- 정답 의도가 tune_reranker_scope_with_latency_measurement이면 정답 선택지에는 reranker 적용 범위 조정과 latency 측정이 모두 포함되어야 한다.
- 정답 의도가 adjust_chunking_by_semantic_units이면 정답 선택지에는 chunk 또는 청크, chunk_size/overlap/분할 중 하나, 문단/제목/수행준거/의미 단위 중 하나가 포함되어야 한다.
- 정답 의도가 filter_context_by_relevance_evidence_metadata이면 정답 선택지에는 context 또는 컨텍스트, filtering 또는 선별, evidence/근거/metadata/relevance 중 하나가 포함되어야 한다.
- 정답 의도가 reject_or_retry_when_context_evidence_insufficient이면 정답 선택지에는 검색 context 또는 문서 근거, 근거 부족 판단, 재검색/보류/retry/reject 중 하나가 포함되어야 한다.
- 정답 의도가 evaluate_retrieval_with_recall_mrr_latency이면 정답 선택지에는 Recall, MRR, latency 또는 p95가 포함되어야 한다.
- 정답 의도가 rewrite_query_with_domain_terms_and_compare_results이면 정답 선택지에는 query rewrite 또는 질의 확장, 도메인 용어, keyword search 또는 검색 결과 비교가 포함되어야 한다.
- 정답 의도가 composite_index_with_execution_plan_and_write_cost이면 정답 선택지에는 복합 인덱스, 실행 계획 확인, rows 또는 filtered 감소 확인, 쓰기 비용 측정이 포함되어야 한다.
- 정답 의도가 join_composite_index_with_filesort_and_write_cost이면 정답 선택지에는 JOIN 조건을 고려한 복합 인덱스, filesort 또는 정렬 병목 확인, 쓰기 비용 측정이 포함되어야 한다.
- 정답 의도가 unique_composite_index_to_reduce_lock_range이면 정답 선택지에는 유니크 복합 인덱스, coupon_id와 user_id 조합, 락 범위 축소 또는 락 경합 완화가 포함되어야 한다.
- 정답 의도가 group_by_composite_index_with_temp_filesort_and_write_cost이면 정답 선택지에는 GROUP BY 또는 집계, 복합 인덱스, temporary/filesort 또는 정렬 비용이 포함되어야 한다. 가능하면 INSERT 부하, 쓰기 비용, 운영 조건, 동시 조회 부하 중 하나도 함께 포함한다.
- 정답 의도가 cursor_pagination_with_index_scan_reduction이면 정답 선택지 한 문장 안에 커서 기반 페이지네이션, OFFSET 또는 깊은 페이지 스캔 문제, rows 또는 스캔 감소가 포함되어야 한다.
- 정답 의도가 covering_index_tradeoff_with_update_cost이면 정답 선택지에는 커버링 인덱스, UPDATE 또는 쓰기 비용이 포함되어야 한다. 가능하면 기본 복합 인덱스와의 비교, 성능 차이 분석, 평가, 균형, 고려 중 하나를 함께 포함한다.
- 정답 의도가 modelops_vllm_serving_latency_cost_tradeoff이면 정답 선택지에는 vLLM 또는 자체 서빙, latency 또는 cost, 품질 통과율 또는 canary 또는 일부 트래픽 검증이 포함되어야 한다.
- 정답 의도가 modelops_finetuning_dataset_quality이면 정답 선택지에는 approved 또는 quality_score와 함께 answer/explanation 일치성, competency_type 정규화, JSONL 학습 데이터 정제 중 하나가 포함되어야 한다.
- ModelOps 자체 서빙 문제에서는 "즉시 전환한다", "전체 트래픽에 바로 적용한다", "모든 요청을 처리한다"처럼 단계적 검증 없는 전환을 정답으로 만들지 마라.
- 위 핵심 표현은 explanation에만 쓰면 안 되고, 반드시 정답 선택지 자체에 포함해야 한다.
- 정답 의도의 핵심 조치를 여러 선택지로 나눠 쓰지 마라.
- 정답 선택지만 "A를 적용한 후 B를 수행한다"처럼 2단계 조치로 쓰고, 오답은 단일 조치로만 쓰지 마라.
- 오답 선택지 중 최소 2개는 두 단계 이상의 실무 조치처럼 작성한다.
- 예: "top_k를 늘린 뒤 candidate 수별 p95 latency와 정답 후보 포함률을 비교한다."
- 예: "query rewrite를 적용한 뒤 기존 vector search 결과와 metadata_filter 적용 결과를 비교한다."
- 예: "embedding 모델 교체 전 chunk 분할 기준과 category 분포를 샘플링해 검색 실패 원인을 분리한다."
- SQL 문제에서는 문제 body에 실제로 등장하지 않는 테이블명, 컬럼명, 조건을 선택지에 새로 추가하지 마라.
- SQL 문제의 선택지는 반드시 body에 제시된 테이블, 컬럼, 실행 계획, 인덱스 후보, 운영 조건만 사용해야 한다.
- SQL 선택지는 body에 제시된 테이블, 컬럼, 실행 계획, 인덱스 후보, 운영 조건만 사용한다.
- 좋은 선택지 예시를 그대로 복사하지 말고 현재 body의 테이블명과 컬럼명에 맞게 작성한다.
- 정답 선택지는 explanation이 아니라 choices 문장 자체에 answer_intent의 필수 판단 근거를 포함해야 한다.
- body에 users 테이블이나 JOIN 조건이 없으면 users, JOIN, grade, VIP 같은 표현을 선택지나 explanation에 쓰지 마라.
- body에 orders 단일 테이블 쿼리만 있으면 JOIN 최적화 선택지를 만들지 마라.
- body에 coupon_issue 트랜잭션 문제가 아니면 coupon_id, user_id 유니크 인덱스, SELECT FOR UPDATE, 락 경합 선택지를 만들지 마라.
- 좋은 선택지 예시는 참고용일 뿐이며, 현재 body에 없는 테이블명/컬럼명/조건을 그대로 가져오면 안 된다.

[좋은 선택지 작성 예시]
- "metadata_filter로 category 범위를 제한한 뒤 reranker를 적용해 후보 chunk의 순서를 재평가한다."
- "top_k를 5에서 20으로 늘리고 reranker를 상위 후보에만 적용해 정답 후보 포함률을 비교한다."
- "query rewrite로 요구사항 변경, 영향 분석, 추적성 키워드를 확장하고 기존 vector search 결과와 비교한다."
- "embedding 모델 교체 전 현재 chunk 분할 기준과 문서 category 분포를 샘플링해 검색 실패 원인을 분리한다."
- "keyword search를 추가해 정확 용어 매칭을 보강하고 vector score와 keyword score의 병합 기준을 조정한다."
- "문제 본문에 제시된 WHERE 조건과 ORDER BY 조건을 기준으로 복합 인덱스 후보를 검토하고, 실행 계획의 rows와 filtered 변화를 측정한다."
- "문제 본문에 제시된 JOIN 조건과 정렬 조건을 함께 고려해 복합 인덱스 후보를 비교하고, filesort 제거 여부와 쓰기 부하 변화를 확인한다."
- "문제 본문에 제시된 중복 검증 조건을 기준으로 유니크 복합 인덱스를 검토하고, SELECT FOR UPDATE의 탐색 범위와 락 경합 변화를 측정한다."
- "created_at 단일 인덱스 사용 계획과 복합 인덱스 사용 계획을 비교해 rows, filtered, Extra 항목의 변화를 확인한다."
- "인덱스 추가 전후의 p95 응답 시간, rows 스캔 수, INSERT 지연 시간을 함께 비교해 읽기 성능과 쓰기 비용의 균형을 판단한다."
- "chunk_size와 overlap을 조정하고 문단·제목·수행준거 단위로 재분할해 검색 context 적합도를 비교한다."
- "검색된 context를 relevance, evidence 포함 여부, metadata 일치 여부로 선별한 뒤 LLM에 전달한다."
- "문서 근거가 부족하면 문제 생성을 보류하거나 재검색하고, 해설은 검색 context 안의 내용으로만 작성한다."
- "Recall@5와 MRR@5로 정답 근거 포함률과 순위를 평가하고, p95 latency 증가를 함께 비교한다."
- "query rewrite에 도메인 용어를 추가한 뒤 vector search와 keyword search 결과를 비교해 검색 실패 원인을 분리한다."

[나쁜 선택지 작성 예시]
- "지연 시간만 고려하여 Reranker를 제거한다."
- "지연 시간 확인 없이 top_k를 증가시킨다."
- "임베딩 모델만 교체하여 성능을 개선한다."
- "키워드 검색 가중치를 증가시켜 결과를 개선한다."
- "top_k를 증가시켜 더 많은 후보를 확보할 수 있지만, reranker의 성능과 비용을 함께 고려하지 않으면 효과가 제한적일 수 있다."
- "reranker만을 적용하여 상위 후보의 순위를 조정할 수 있지만, metadata_filter의 부재로 인해 여전히 부적합한 결과가 포함될 수 있다."
- "인덱스를 추가하여 성능을 개선한다."
- "실행 계획을 확인하지 않고 복합 인덱스를 바로 추가한다."
- "쓰기 부하는 고려하지 않고 SELECT 성능만 기준으로 인덱스를 추가한다."
- "created_at 인덱스가 있으므로 다른 조건은 모두 where 필터링에 맡긴다."
- "락 대기를 줄이기 위해 트랜잭션을 제거한다."

[출력 형식]
{{
  "choices": [
    "선택지1",
    "선택지2",
    "선택지3",
    "선택지4",
    "선택지5"
  ],
  "answer": 1,
  "explanation": "정답은 1번입니다. ..."
}}
"""

def generate_choices_for_template_question(base_question: dict) -> dict:
    """
    템플릿이 만든 body는 그대로 유지하고,
    choices/explanation만 LLM으로 생성한다.

    1차 생성 실패 시 더 강한 조건으로 1번 재시도한다.
    2차도 실패하면 base_question의 기존 choices/explanation을 fallback으로 사용한다.
    """
    question = deepcopy(base_question)

    body = str(question.get("body", "")).strip()
    title = str(question.get("title", "")).strip()
    answer_intent = str(question.get("answer_intent", "")).strip()
    distractor_intents = question.get("distractor_intents", [])

    fallback_choices = question.get("choices", [])
    fallback_answer = question.get("answer", 1)
    fallback_explanation = question.get("explanation", "")
    
    # SQL 고급처럼 선택지 품질을 코드 템플릿으로 고정해야 하는 문제는
    # LLM choices 생성을 건너뛰고 템플릿 choices/explanation을 그대로 사용한다.
    if question.get("lock_choices") is True:
        question["choices"] = [
            " ".join(str(choice).strip().split())
            for choice in fallback_choices
        ]

        try:
            question["answer"] = int(fallback_answer)
        except Exception:
            question["answer"] = 1

        question["explanation"] = " ".join(str(fallback_explanation).strip().split())

        logger.info("템플릿 문제 choices/explanation 고정 사용: lock_choices=True")
        return question

    last_error = None

    for retry in [False, True]:
        try:
            prompt = _build_choice_prompt(
                title=title,
                body=body,
                answer_intent=answer_intent,
                distractor_intents=distractor_intents,
                retry=retry,
            )

            result = _request_choice_json(prompt)

            choices, answer_int, explanation = _validate_generated_choices(
                result=result,
                answer_intent=answer_intent,
            )

            question["choices"] = choices
            question["answer"] = answer_int
            question["explanation"] = explanation

            if retry:
                logger.info("템플릿 문제 choices/explanation LLM 재생성 성공")

            return question

        except Exception as e:
            last_error = e
            logger.warning(
                f"템플릿 문제 choices/explanation LLM 생성 실패 "
                f"(retry={retry}): {str(e)}"
            )

    logger.warning(
        f"템플릿 문제 choices/explanation LLM 생성 최종 실패. fallback 사용: {str(last_error)}"
    )

    question["choices"] = fallback_choices
    question["answer"] = fallback_answer
    question["explanation"] = fallback_explanation

    return question

def _request_choice_json_array(prompt: str):
    """
    여러 템플릿 문제의 choices/answer/explanation을 한 번의 LLM 호출로 생성한다.
    반드시 JSON 배열을 기대한다.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 IT 역량진단 문제은행의 객관식 선택지/해설 작성자다. "
                    "반드시 유효한 JSON 배열만 출력한다."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content or ""
    logger.info(f"LLM batch choice response preview: {str(content)[:1200]}")

    parsed = _clean_json_response(content)

    # 혹시 LLM이 {"questions": [...]} 형태로 감싸서 주는 경우까지 방어
    if isinstance(parsed, dict):
        if isinstance(parsed.get("questions"), list):
            return parsed["questions"]
        if isinstance(parsed.get("results"), list):
            return parsed["results"]
        if isinstance(parsed.get("items"), list):
            return parsed["items"]

    if not isinstance(parsed, list):
        raise ValueError("batch choices 생성 결과가 JSON 배열이 아닙니다.")

    return parsed


def _build_batch_choice_prompt(
    base_questions: list[dict],
    retry: bool = False,
) -> str:
    """
    여러 템플릿 문제의 title/body는 고정하고,
    choices/answer/explanation만 한 번에 생성하도록 지시한다.
    """
    prompt_questions = []
    retry_rule = ""
    
    for idx, q in enumerate(base_questions):
        prompt_questions.append(
            {
                "index": idx,
                "title": q.get("title", ""),
                "body": q.get("body", ""),
                "answer_intent": q.get("answer_intent", ""),
                "distractor_intents": q.get("distractor_intents", []),
            }
        )
        

    if retry:
        retry_rule = """
        [이전 batch 생성 실패 사유]
        - 일부 선택지가 너무 짧았다.
        - 정답 선택지에 answer_intent의 핵심 키워드가 부족했다.
        - 오답이 너무 단순하거나 쉽게 제거되는 표현을 포함했다.
        - 이번에는 각 선택지를 55~95자 정도의 구체적인 판단 문장으로 작성한다.
        - 선택지에는 반드시 문제 본문에 나온 핵심 명사를 포함한다.
        - ML 지표 문제라면 accuracy, precision, recall, F1, 불균형, 이탈 위험 고객 중 2개 이상을 정답 선택지에 포함한다.
        - fine-tuning 데이터셋 문제라면 approved, quality_score, answer, explanation, competency_type, 학습 데이터, 데이터셋 중 3개 이상을 정답 선택지에 포함한다.
        - RAG 문제라면 query, chunk, similarity, metadata, reranker, context, latency 중 2개 이상을 정답 선택지에 포함한다.
        - 정답 선택지에는 answer_intent의 핵심 키워드를 반드시 직접 포함한다.
        - 오답도 실제 실무자가 고려할 수 있는 대안처럼 작성한다.
        - 단어 하나 또는 짧은 명사구 선택지는 절대 만들지 않는다.
        - "무시한다", "무시한 채", "검증을 생략한다", "오류를 삭제한다", "자동 저장한다"처럼 바로 오답으로 보이는 표현을 쓰지 않는다.
        - llm_multi_turn_context_state_tracking 정답 choice에는 current_competency, previous_question_id, context 또는 맥락, 사용자 확인 또는 분기 중 3개 이상을 반드시 포함한다.
        - llm_response_format_fallback 정답 choice에는 response_format 또는 JSON/schema, 서버 validation 또는 필수 필드 검증, fallback 또는 재시도 또는 보류를 반드시 포함한다.
        - llm_tool_calling_argument_validation 정답 choice에는 tool calling 또는 도구 호출, category, top_k, 인자 검증, 재시도 중 4개 이상을 반드시 포함한다.
        - prompt injection 문제의 오답에는 "무시", "생략", "검증 없이" 같은 노골적 표현을 쓰지 말고, 일부 기준은 충족하지만 출력 정책 검사가 부족한 대안처럼 작성한다.
        - multi-turn 문제의 오답에는 "무조건", "항상", "검증 없이"를 쓰지 말고, 최근 대화 활용은 하지만 지시 대상 확인이나 state 추적이 부족한 대안처럼 작성한다.
        - response_format 문제의 오답에는 "무시"를 쓰지 말고, response_format 또는 parsing 처리에 의존하지만 서버 validation/fallback이 부족한 대안처럼 작성한다.
        """
    return f"""
아래는 이미 확정된 템플릿 기반 문제 목록이다.
각 문제의 title과 body는 절대 수정하지 마라.

너의 역할은 각 문제마다 choices 5개, answer, explanation만 생성하는 것이다.

{retry_rule}

[출력 형식]
- 반드시 JSON 배열만 출력한다.
- 배열의 각 객체는 index, choices, answer, explanation 필드만 가진다.
- index는 입력 문제의 index와 동일해야 한다.
- choices는 반드시 문자열 5개 배열이다.
- answer는 반드시 1~5 사이 숫자다.

[해설 품질 규칙]
- explanation은 반드시 "정답은 N번입니다."로 시작한다.
- N은 answer 값과 반드시 같아야 한다.
- explanation은 반드시 존댓말 문체로 작성한다.
- "~이다", "~한다", "~높아진다", "~적절하다", "~필요하다" 같은 반말형 종결을 쓰지 않는다.
- 모든 문장은 "~입니다", "~합니다", "~수 있습니다", "~해야 합니다"처럼 끝낸다.
- explanation은 최소 4문장 이상으로 작성한다.
- explanation은 정답 선택지를 그대로 반복하는 수준이면 안 된다.
- 정답이 문제의 어떤 조건을 만족하는지 설명한다.
- 오답 중 최소 2개 이상에 대해 왜 현재 문제 조건에서는 부족한지 설명한다.
- 오답 설명은 번호 기준이 아니라 선택지의 핵심 조치 기준으로 설명한다.
- 예: "top_k 확대는 후보 수를 늘릴 수 있으나 정확 키워드와 metadata 조건을 동시에 반영하지 못합니다."
- 예: "reranker만 적용하는 방식은 후보군에 정답 근거 chunk가 포함되지 않으면 순위 개선 효과가 제한됩니다."
- 예: "embedding 모델 교체는 장기 개선 후보이지만 현재 로그의 category 불일치와 metadata_filter 미적용 문제를 직접 해결하지 못합니다."

[선택지 길이 강제 규칙]
- 각 선택지는 반드시 55자 이상 100자 이하의 한 문장으로 작성한다.
- 선택지는 "무엇을 한다"로 끝나는 짧은 문장이 아니라, "무엇을 한 뒤 어떤 기준으로 판단한다" 구조로 작성한다.
- 좋은 구조: "A를 적용한 뒤 B 지표를 측정하여 C 기준으로 판단한다."
- 나쁜 구조: "reranker를 적용한다.", "정확도 외에 recall을 고려한다."
- 정답뿐 아니라 오답도 2단계 판단 문장으로 작성한다.

[공통 작성 규칙]
- 각 문제의 정답 선택지는 answer_intent를 만족해야 한다.
- 오답 선택지는 distractor_intents를 각각 반영하되, 실무자가 실제로 고려할 수 있는 대안처럼 작성한다.
- 정답 선택지만 과도하게 길거나 구체적이면 안 된다.
- 정답 선택지와 오답 선택지의 글자 수 차이는 최대 25자 이내로 맞춘다.
- 선택지 5개는 비슷한 길이와 비슷한 구체성을 가져야 한다.
- 각 선택지는 반드시 55자 이상 100자 이하로 작성한다.
- 선택지끼리 문장이 중복되거나 거의 같으면 안 된다.
- 오답의 부족한 점을 "하지만", "그러나", "다만", "못한다", "않는다", "제한적"으로 노골적으로 드러내지 마라.
- 선택지 5개 중 "하지만", "그러나", "다만", "못한다", "않는다", "제한적" 표현은 최대 2개 선택지에서만 사용한다.
- "무시한다", "무시한 채", "삭제한다", "무조건", "항상", "오직", "단순히", "완전히 제거한다", "모든 요청을 처리한다" 같은 쉽게 제거되는 표현을 쓰지 마라.
- 오답도 실제 실무자가 고려할 수 있는 대안처럼 작성하되, 노골적으로 틀린 표현을 쓰지 마라.
- "검증을 생략한다", "오류를 무시한다", "자동 저장한다"처럼 고급 문제에서 바로 제거되는 선택지는 만들지 마라.
- explanation은 body에 제시된 evidence와 연결해서 설명한다.
- explanation에서 오답을 설명할 때 "1번은", "2번은", "3번은"처럼 번호 기준으로 설명하지 마라.
- 오답 설명은 선택지의 핵심 조치 내용 기준으로 설명한다.

[정답 의도별 필수 규칙]
- combine_vector_keyword_and_metadata_filter: 정답 선택지에는 vector search, keyword search, metadata_filter가 포함되어야 한다.
- metadata_filter_and_reranker: 정답 선택지에는 metadata_filter와 reranker가 포함되어야 한다.
- tune_reranker_scope_with_latency_measurement: 정답 선택지에는 reranker 적용 범위 조정과 latency 또는 p95 측정이 포함되어야 한다.
- adjust_chunking_by_semantic_units: 정답 선택지에는 chunk/청크, 분할/재분할, 문단/제목/의미 단위 중 하나가 포함되어야 한다.
- filter_context_by_relevance_evidence_metadata: 정답 선택지에는 context/chunk, filtering/선별, evidence/metadata/relevance 중 하나가 포함되어야 한다.
- reject_or_retry_when_context_evidence_insufficient: 정답 선택지에는 검색 context 또는 문서 근거, 근거 부족 판단, 재검색/보류/retry 중 하나가 포함되어야 한다.
- evaluate_retrieval_with_recall_mrr_latency: 정답 선택지에는 Recall, MRR, latency 또는 p95가 포함되어야 한다.
- rewrite_query_with_domain_terms_and_compare_results: 정답 선택지에는 query rewrite 또는 질의 확장, 도메인 용어, keyword search 또는 검색 결과 비교가 포함되어야 한다.

- llm_structured_output_validation: 정답 선택지에는 JSON/schema/structured output/response_format 중 하나와 서버 검증/필수 필드/answer 범위/choices 개수 중 하나가 포함되어야 한다.
- llm_tool_calling_argument_validation: 정답 선택지에는 tool calling/tool schema/도구 호출 중 하나와 인자 타입/category/top_k/허용값 검증 중 하나가 포함되어야 한다.
- llm_prompt_injection_guard: 정답 선택지에는 prompt injection 또는 프롬프트 인젝션, system instruction 또는 사용자 입력 분리, validation 또는 fallback이 포함되어야 한다.
- llm_response_format_fallback: 정답 선택지에는 response_format 또는 JSON/schema, 서버 validation 또는 필수 필드 검증, fallback/재시도/보류 중 하나가 반드시 포함되어야 한다.
- llm_multi_turn_context_state_tracking: 정답 선택지에는 multi-turn 또는 이전 대화, current_competency, previous_question_id, context 또는 맥락, 사용자 확인 또는 분기 중 4개 이상이 포함되어야 한다.

- agent_tool_retry_observation_loop: 정답 선택지에는 observation 또는 도구 결과 확인과 재시도/retry/재검색/query 재작성 중 하나가 포함되어야 한다.
- agent_langgraph_state_human_review: 정답 선택지에는 validation_node/검증 오류, retry_count/repair_node/반복 실패, human review/검수 분기 중 둘 이상이 포함되어야 한다.
- agent_conditional_edge_by_validation_error: 정답 선택지에는 validation_node 또는 오류 유형, conditional edge 또는 분기, repair_node/retrieval_node/human_review_node 중 둘 이상이 포함되어야 한다.
- agent_state_schema_validation: 정답 선택지에는 state 또는 상태, schema 또는 타입 검증, validation_errors 또는 retry_count 중 하나가 포함되어야 한다.
- agent_checkpoint_resume_with_retry_count: 정답 선택지에는 checkpoint, resume 또는 실패 지점 재개, retry_count 또는 human review 분기 중 하나가 포함되어야 한다.
- agent_memory_filter_by_current_context: 정답 선택지에는 memory 또는 메모리, current_competency/current_topic 또는 현재 요청 기준, context 분리 또는 필터링이 포함되어야 한다.

- modelops_finetuning_dataset_quality: 정답 선택지에는 approved 또는 quality_score와 함께 answer/explanation 일치성, competency_type 정규화, JSONL 학습 데이터 정제 중 하나가 포함되어야 한다.
- modelops_vllm_serving_latency_cost_tradeoff: 정답 선택지에는 vLLM 또는 자체 서빙, latency 또는 cost, 품질 통과율 또는 canary 또는 일부 트래픽 검증이 포함되어야 한다.
- modelops_dataset_leakage_prevention: 정답 선택지에는 fine-tuning 또는 JSONL, train/validation/test 분리, 데이터 누수 또는 중복 제거가 포함되어야 한다.
- modelops_evaluation_gate_before_deployment: 정답 선택지에는 evaluation gate 또는 평가 기준, quality_score/검증 통과율/불일치율/hallucination rate/관리자 반려율 중 둘 이상, 배포 보류 또는 기준 미달 판단이 포함되어야 한다.
- modelops_monitoring_and_rollback: 정답 선택지에는 monitoring 또는 모니터링, rollback 또는 롤백, 관리자 반려율/검증 실패율/answer 불일치율/latency/cost 중 둘 이상이 포함되어야 한다.

- ml_imbalanced_metric_precision_recall_f1: 정답 선택지에는 accuracy만 보지 않는다는 취지와 precision/recall/F1 중 하나가 포함되어야 한다.
- ml_overfitting_split_regularization: 정답 선택지에는 train/validation/test 분리와 과적합/일반화/regularization/early stopping 중 하나가 포함되어야 한다.
- ml_threshold_tuning_with_cost_tradeoff: 정답 선택지에는 threshold 또는 임계값, precision/recall/F1 중 둘 이상, false positive/false negative/비용/매출 손실 중 하나가 포함되어야 한다.
- ml_precision_recall_tradeoff_with_cost: 정답 선택지에는 precision과 recall이 모두 포함되어야 하며, trade-off/균형/비용/오탐/탐지 누락 중 하나가 포함되어야 한다.
- ml_data_drift_monitoring_and_retraining: 정답 선택지에는 feature drift 또는 data drift, 운영 데이터와 학습 데이터 비교, monitoring 또는 재학습이 포함되어야 한다.
- dl_learning_rate_scheduler_stability: 정답 선택지에는 learning rate 또는 학습률, scheduler 또는 early stopping, loss/validation/수렴 안정성 중 하나가 포함되어야 한다.
- dl_transfer_learning_gradual_unfreeze: 정답 선택지에는 transfer learning 또는 사전학습, freeze/unfreeze 또는 동결, fine-tuning 또는 낮은 learning rate가 포함되어야 한다.
- dl_batch_size_gpu_memory_tradeoff: 정답 선택지에는 batch size, GPU memory 또는 OOM, gradient accumulation/mixed precision/sequence length 중 하나가 포함되어야 한다.

[문제 목록]
{json.dumps(prompt_questions, ensure_ascii=False, indent=2)}

[출력 예시]
[
  {{
    "index": 0,
    "choices": [
      "선택지1",
      "선택지2",
      "선택지3",
      "선택지4",
      "선택지5"
    ],
    "answer": 1,
    "explanation": "정답은 1번입니다. ..."
  }}
]
"""

def _use_template_fallback_question(base_question: dict) -> dict:
    """
    LLM batch/retry가 실패한 경우 추가 LLM 호출 없이
    템플릿에 이미 들어있는 choices/answer/explanation을 사용한다.
    """
    question = deepcopy(base_question)

    fallback_choices = question.get("choices", [])
    fallback_answer = question.get("answer", 1)
    fallback_explanation = question.get("explanation", "")

    question["choices"] = [
        " ".join(str(choice).strip().split())
        for choice in fallback_choices
    ]

    try:
        question["answer"] = int(fallback_answer)
    except Exception:
        question["answer"] = 1

    question["explanation"] = " ".join(str(fallback_explanation).strip().split())

    logger.info(
        "템플릿 choices/explanation 고정 사용: "
        f"template_format={question.get('template_format')}"
    )

    return question

def generate_choices_for_template_questions_batch(base_questions: list[dict]) -> list[dict]:
    """
    여러 템플릿 문제의 choices/explanation을 한 번의 LLM 호출로 생성한다.

    속도 개선 핵심:
    - 1차 batch 호출
    - 실패한 문제만 모아서 2차 batch retry
    - 그래도 실패하면 추가 LLM 호출 없이 템플릿 fallback 사용
    """
    if not base_questions:
        return []

    # count=1이면 batch 이점이 거의 없으므로 기존 단건 함수를 사용한다.
    if len(base_questions) == 1:
        return [generate_choices_for_template_question(base_questions[0])]

    questions = [deepcopy(q) for q in base_questions]
    final_questions: list[dict | None] = [None] * len(questions)

    batch_questions: list[dict] = []
    batch_index_to_original_index: dict[int, int] = {}

    for original_index, question in enumerate(questions):
        if question.get("lock_choices") is True:
            final_questions[original_index] = _use_template_fallback_question(question)
            continue

        batch_index = len(batch_questions)
        batch_questions.append(question)
        batch_index_to_original_index[batch_index] = original_index

    if not batch_questions:
        return [q for q in final_questions if q is not None]

    def apply_batch_results(
        target_questions: list[dict],
        target_index_to_original_index: dict[int, int],
        retry: bool = False,
    ) -> list[int]:
        """
        batch 결과를 final_questions에 반영한다.
        실패한 batch_index 목록을 반환한다.
        """
        failed_batch_indices: list[int] = []

        prompt = _build_batch_choice_prompt(
            target_questions,
            retry=retry,
        )
        batch_results = _request_choice_json_array(prompt)

        result_by_index: dict[int, dict] = {}

        for item in batch_results:
            if not isinstance(item, dict):
                continue

            try:
                item_index = int(item.get("index"))
            except Exception:
                continue

            result_by_index[item_index] = item

        for batch_index, base_question in enumerate(target_questions):
            original_index = target_index_to_original_index[batch_index]
            result = result_by_index.get(batch_index)

            if result is None:
                logger.warning(
                    f"batch choices 결과 누락: "
                    f"batch_index={batch_index}, "
                    f"template_format={base_question.get('template_format')}"
                )
                failed_batch_indices.append(batch_index)
                continue

            try:
                choices, answer_int, explanation = _validate_generated_choices(
                    result=result,
                    answer_intent=str(base_question.get("answer_intent", "")).strip(),
                )

                generated_question = deepcopy(base_question)
                generated_question["choices"] = choices
                generated_question["answer"] = answer_int
                generated_question["explanation"] = explanation

                final_questions[original_index] = generated_question

            except Exception as e:
                logger.warning(
                    f"batch choices 개별 검증 실패: "
                    f"batch_index={batch_index}, "
                    f"template_format={base_question.get('template_format')}, "
                    f"error={str(e)}"
                )
                failed_batch_indices.append(batch_index)

        return failed_batch_indices

    try:
        # 1차 batch 생성
        failed_batch_indices = apply_batch_results(
            target_questions=batch_questions,
            target_index_to_original_index=batch_index_to_original_index,
            retry=False,
        )

        # 2차 batch retry: 실패한 문제만 다시 묶어서 한 번 더 호출
        if failed_batch_indices:
            retry_questions: list[dict] = []
            retry_index_to_original_index: dict[int, int] = {}

            for failed_batch_index in failed_batch_indices:
                retry_index = len(retry_questions)
                retry_questions.append(batch_questions[failed_batch_index])
                retry_index_to_original_index[retry_index] = batch_index_to_original_index[failed_batch_index]

            logger.warning(
                "batch choices 일부 실패. 실패 문제만 batch retry 수행: "
                f"failed_count={len(retry_questions)}"
            )

            retry_failed_indices = apply_batch_results(
                target_questions=retry_questions,
                target_index_to_original_index=retry_index_to_original_index,
                retry=True,
            )

            # 2차 retry까지 실패한 문제는 추가 LLM 호출 없이 템플릿 fallback 사용
            for retry_failed_index in retry_failed_indices:
                original_index = retry_index_to_original_index[retry_failed_index]
                final_questions[original_index] = _use_template_fallback_question(
                    questions[original_index]
                )

        # 혹시 아직 비어 있는 문제는 템플릿 fallback으로 채운다.
        for original_index, question in enumerate(final_questions):
            if question is None:
                logger.warning(
                    f"batch choices 최종 누락. 템플릿 fallback으로 보완: index={original_index}"
                )
                final_questions[original_index] = _use_template_fallback_question(
                    questions[original_index]
                )

        logger.info(
            "템플릿 문제 choices/explanation batch 생성 완료: "
            f"input={len(base_questions)}, batch_targets={len(batch_questions)}"
        )

        return [q for q in final_questions if q is not None]

    except Exception as e:
        logger.warning(
            f"템플릿 문제 choices/explanation batch 생성 전체 실패. "
            f"전체 템플릿 fallback 사용: error={str(e)}"
        )

        return [
            _use_template_fallback_question(question)
            for question in questions
        ]