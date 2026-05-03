# backend/ai/services/question_choice_generator.py

import re
import json
import logging
from copy import deepcopy

from ai.client import client

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


def _sync_answer_number_in_explanation(explanation: str, answer_int: int) -> str:
    """
    LLM이 answer 번호를 잘못 주거나 시스템이 answer를 보정했을 때
    explanation의 '정답은 N번입니다.' 문구를 최종 answer와 맞춘다.
    """
    text = str(explanation or "").strip()

    if not text:
        return f"정답은 {answer_int}번입니다."

    patterns = [
        r"정답은\s*\d+\s*번입니다\.?",
        r"정답은\s*\d+\s*번",
        r"정답\s*:\s*\d+\s*번",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return re.sub(pattern, f"정답은 {answer_int}번입니다.", text, count=1)

    return f"정답은 {answer_int}번입니다. {text}"

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
    
    correct_choice_text = str(choices[answer_int - 1]).lower()

    required_keywords_by_intent = {
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

    required_keyword_groups = required_keywords_by_intent.get(answer_intent)

    if required_keyword_groups:
        # 1차: LLM이 지정한 answer 선택지가 intent를 만족하는지 확인
        if not _matches_required_keyword_groups(correct_choice_text, required_keyword_groups):
            matched_indices = []

            # 2차: choices 전체에서 intent를 만족하는 선택지가 정확히 하나 있는지 확인
            for idx, choice in enumerate(choices):
                if _matches_required_keyword_groups(str(choice), required_keyword_groups):
                    matched_indices.append(idx)

            if len(matched_indices) == 1:
                corrected_answer = matched_indices[0] + 1
                logger.info(
                    "LLM answer 번호 자동 보정: "
                    f"answer_intent={answer_intent}, old_answer={answer_int}, new_answer={corrected_answer}"
                )
                answer_int = corrected_answer
                correct_choice_text = str(choices[answer_int - 1]).lower()
                explanation = _sync_answer_number_in_explanation(explanation, answer_int)
            else:
                missing_groups = []

                for group in required_keyword_groups:
                    if not any(str(keyword).lower() in correct_choice_text for keyword in group):
                        missing_groups.append(group)

                raise ValueError(
                    f"정답 선택지가 answer_intent={answer_intent}의 핵심 조건을 충분히 포함하지 않습니다. "
                    f"missing={missing_groups}, correct_choice={choices[int(result.get('answer', 1)) - 1]}"
                )
    weak_choice_patterns = [
        "무시",
        "삭제",
        "무조건",
        "항상",
        "오직",
        "단순히",
        "만 고려",
        "확인 없이",
    ]

    cleaned_choices = [
        " ".join(str(choice).strip().split())
        for choice in choices
    ]

    for choice_text in cleaned_choices:
        if len(choice_text) < 35:
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

    if revealing_count >= 3:
        raise ValueError(
            f"오답 한계가 너무 노골적으로 드러나는 선택지가 많습니다: revealing_count={revealing_count}"
        )

    cleaned_explanation = _sync_answer_number_in_explanation(explanation, answer_int)

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
- covering_index_tradeoff_with_update_cost 정답은 "커버링 인덱스", "UPDATE 또는 쓰기 비용", "비교 또는 성능 차이 또는 균형 또는 고려"를 선택지 문장에 포함해야 한다.
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
- "무시한다", "삭제한다", "무조건", "항상", "오직", "단순히", "완전히 제거한다", "성능을 개선한다", "결과를 개선한다" 같은 쉽게 제거되는 표현을 쓰지 마라.
- 각 선택지는 최소 35자 이상으로 작성한다.
- 선택지 5개는 비슷한 길이와 비슷한 구체성을 가져야 한다.
- 정답 선택지만 길고 오답이 짧으면 안 된다.
- explanation은 반드시 "정답은 N번입니다."로 시작한다.
- N은 answer 값과 반드시 같아야 한다.
- explanation은 body에 제시된 evidence와 연결해서 설명한다. AI/RAG 문제라면 query, top_k, chunk, similarity, metadata_filter, reranker, latency를 근거로 삼고, SQL 문제라면 테이블 구조, SQL 쿼리, 데이터 규모, 실행 계획, rows, filtered, Extra, 인덱스, 정렬, 락, 쓰기 부하를 근거로 삼는다.
- 오답 설명은 번호 기준으로 쓰지 말고, 선택지의 핵심 조치 내용 기준으로 설명한다.
- 정답 선택지는 [정답 의도]의 핵심 조치를 모두 포함해야 한다.
- 정답 의도가 combine_vector_keyword_and_metadata_filter이면 정답 선택지에는 vector search, keyword search, metadata_filter가 모두 포함되어야 한다.
- 정답 의도가 metadata_filter_and_reranker이면 정답 선택지에는 metadata_filter와 reranker가 모두 포함되어야 한다.
- 정답 의도가 tune_reranker_scope_with_latency_measurement이면 정답 선택지에는 reranker 적용 범위 조정과 latency 측정이 모두 포함되어야 한다.
- 정답 의도가 composite_index_with_execution_plan_and_write_cost이면 정답 선택지에는 복합 인덱스, 실행 계획 확인, rows 또는 filtered 감소 확인, 쓰기 비용 측정이 포함되어야 한다.
- 정답 의도가 join_composite_index_with_filesort_and_write_cost이면 정답 선택지에는 JOIN 조건을 고려한 복합 인덱스, filesort 또는 정렬 병목 확인, 쓰기 비용 측정이 포함되어야 한다.
- 정답 의도가 unique_composite_index_to_reduce_lock_range이면 정답 선택지에는 유니크 복합 인덱스, coupon_id와 user_id 조합, 락 범위 축소 또는 락 경합 완화가 포함되어야 한다.
- 정답 의도가 group_by_composite_index_with_temp_filesort_and_write_cost이면 정답 선택지에는 GROUP BY 또는 집계, 복합 인덱스, temporary/filesort 또는 정렬 비용이 포함되어야 한다. 가능하면 INSERT 부하, 쓰기 비용, 운영 조건, 동시 조회 부하 중 하나도 함께 포함한다.
- 정답 의도가 cursor_pagination_with_index_scan_reduction이면 정답 선택지 한 문장 안에 커서 기반 페이지네이션, OFFSET 또는 깊은 페이지 스캔 문제, rows 또는 스캔 감소가 포함되어야 한다.
- 정답 의도가 covering_index_tradeoff_with_update_cost이면 정답 선택지에는 커버링 인덱스, UPDATE 또는 쓰기 비용이 포함되어야 한다. 가능하면 기본 복합 인덱스와의 비교, 성능 차이 분석, 평가, 균형, 고려 중 하나를 함께 포함한다.
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