# backend/ai/questions/validator.py

import re
import logging
from typing import Any
from ai.core.config import normalize_competency_type
from ai.questions.text_normalizer import normalize_question_text

logger = logging.getLogger("uvicorn.info")


def _has_answer_length_bias(q: dict) -> bool:
    """
    정답 선택지가 오답들보다 과도하게 길어서 정답이 노출되는 문제를 감지한다.
    단, 출력 결과 예측(output_prediction) 유형은 선택지가 원래 짧으므로 제외한다.
    """
    choices = q.get("choices", [])
    answer = q.get("answer")
    answer_style = str(q.get("answer_style", "")).strip()

    # output_prediction 유형은 선택지가 짧을 수 있으므로 제외
    if answer_style == "output_prediction":
        return False

    if not isinstance(choices, list) or len(choices) != 5:
        return False
    try:
        ans_idx = int(answer) - 1
        if ans_idx < 0 or ans_idx > 4:
            return False
    except Exception:
        return False

    correct_len = len(str(choices[ans_idx]).strip())
    wrong_lens = [len(str(c).strip()) for i, c in enumerate(choices) if i != ans_idx]
    if not wrong_lens:
        return False

    avg_wrong_len = sum(wrong_lens) / len(wrong_lens)
    max_wrong_len = max(wrong_lens)

    # 1.5배 이상이고 최장 오답보다 20자 이상 긴 경우에만 탈락
    if correct_len >= avg_wrong_len * 1.5 and correct_len >= max_wrong_len + 20:
        return True
    return False

def _is_explanation_too_similar_to_answer_choice(q: dict) -> bool:
    choices = q.get("choices", [])
    answer = q.get("answer")
    explanation = q.get("explanation", "")

    if not isinstance(choices, list) or len(choices) != 5 or not explanation:
        return False
    try:
        ans_idx = int(answer) - 1
        if ans_idx < 0 or ans_idx > 4:
            return False
    except Exception:
        return False

    ans_text = str(choices[ans_idx]).strip()
    exp_text = str(explanation).strip()

    exp_text_clean = re.sub(r"^정답은\s*\d\s*번입니다\.?\s*", "", exp_text).strip()

    # 선택지 텍스트가 해설 전체에 그대로 있고, 해설이 선택지보다 40자 이하로만 더 긴 경우
    if ans_text in exp_text_clean and len(exp_text_clean) < len(ans_text) + 40:
        return True
    return False

def _has_too_obvious_distractors(q: dict) -> bool:
    """
    오답이 너무 뻔해서 쉽게 제거되는 패턴을 가진 문제를 감지한다.
    lock_choices=True인 템플릿 문제는 선택지 품질을 별도 검증했으므로 제외한다.
    """
    # 템플릿 문제는 이미 수작업으로 선택지를 검증했으므로 제외
    if q.get("lock_choices") is True:
        return False

    choices = q.get("choices", [])
    if not isinstance(choices, list) or len(choices) != 5:
        return False

    extreme_patterns = [
        "항상", "무조건", "절대", "전혀", "모든 ", "유일한",
        "보장한다", "보장합니다",
        "필요하지 않다", "필요하지 않습니다",
        "사용하지 않는다", "사용하지 않습니다",
        "삭제한다", "삭제합니다",
        "생략한다", "생략합니다",
        "무시한다", "무시합니다",
        "아무 조치", "관련 없는",
        "잘못된 설명:",
        "오답 후보:",
        "관련 없는 설명:",
        "혼동하기 쉬운 설명:",
    ]

    count = 0
    for choice in choices:
        c_text = str(choice)
        if any(p in c_text for p in extreme_patterns):
            count += 1

    # 2개 이상의 선택지가 극단 표현을 가질 때만 탈락 (기존 3 → 2 )
    return count >= 2

def validate_questions(
    questions: list,
    question_type: str,
    difficulty: str,
    score: int,
) -> list[dict[str, Any]]:
    """
    LLM이 생성한 문제 목록을 검증하고, 통과한 문제만 반환한다.

    - JSON 배열 구조 검증
    - 객관식 choices / answer / explanation 검증
    - 서술형/코드작성형 answer 검증
    - validator는 항상 동일한 기준으로 통과/탈락만 판단한다.
    """
    return _validate_questions(
        questions=questions,
        question_type=question_type,
        difficulty=difficulty,
        score=score,
    )


def _extract_answer_number_from_explanation(explanation: str):
    if not explanation:
        return None

    patterns = [
        r"정답은\s*(\d)\s*번",
        r"정답\s*:\s*(\d)\s*번",
        r"답은\s*(\d)\s*번",
        r"(\d)\s*번이\s*정답",
    ]

    for pattern in patterns:
        match = re.search(pattern, explanation)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None

    return None


def _has_explanation_contradiction(explanation: str, answer: int) -> bool:
    """
    객관식 해설에서 정답이 아닌 선택지를 '정확하다', '올바르다', '맞다'처럼
    설명하는 경우 복수정답 가능성이 있으므로 품질 경고로 남긴다.
    """
    if not explanation:
        return False

    text = str(explanation)

    positive_patterns = [
        r"(\d)\s*번\s*선택지는\s*.*(정확|올바르|맞는|타당|적절)",
        r"(\d)\s*번은\s*.*(정확|올바르|맞는|타당|적절)",
    ]

    for pattern in positive_patterns:
        for match in re.finditer(pattern, text):
            try:
                mentioned_no = int(match.group(1))
            except Exception:
                continue

            if mentioned_no != answer:
                return True

    return False


def _find_weak_multiple_choice_options(q: dict, difficulty: str) -> list[str]:
    """
    고급 객관식에서 너무 쉽게 제거되는 선택지 표현을 찾는다.
    단, 여기서는 문제를 폐기하지 않고 quality_warnings 용도로만 사용한다.
    """
    if difficulty != "고급":
        return []

    choices = q.get("choices", [])

    if not isinstance(choices, list):
        return []

    weak_patterns = [
        "무시한다",
        "완전히 제거",
        "무조건",
        "항상",
        "오직",
        "성능만",
        "보안만",
        "아무 조치",
        "고려하지 않는다",
        "방치한다",
    ]

    found: list[str] = []

    for choice in choices:
        choice_text = str(choice)

        for pattern in weak_patterns:
            if pattern in choice_text:
                found.append(f"'{pattern}' 포함 선택지: {choice_text}")

    return found

def _find_meta_choice_expressions(q: dict) -> list[str]:
    """
    choices에 '오해할 수 있다', '혼동할 수 있다'처럼
    학습자의 상태를 설명하는 메타 문장이 들어간 경우를 감지한다.
    선택지는 개념/코드/쿼리에 대한 직접 설명이어야 한다.
    """
    choices = q.get("choices", [])

    if not isinstance(choices, list):
        return []

    meta_patterns = [
        "오해할 수 있다",
        "오해할 수",
        "오해한다",
        "오해",
        "혼동할 수 있다",
        "혼동할 수",
        "혼동한다",
        "혼동",
        "착각할 수 있다",
        "착각할 수",
        "착각한다",
        "착각",
        "잘못 이해할 수 있다",
        "잘못 이해",
    ]

    found: list[str] = []

    for choice in choices:
        choice_text = str(choice)

        for pattern in meta_patterns:
            if pattern in choice_text:
                found.append(f"메타 표현 선택지: '{pattern}' / {choice_text}")

    return found

def _should_reject_for_choice_quality(q: dict, difficulty: str) -> bool:
    """
    고급 객관식에서 정말 심각한 선택지 품질 문제만 실제 폐기한다.

    주의:
    - '무시', '고려하지 않는다'는 LLM이 오답 한계를 설명할 때 자주 쓰므로
      지금 단계에서는 reject하지 않고 warning으로만 처리한다.
    - 너무 강하게 reject하면 validated=0으로 400이 다시 발생한다.
    """
    if difficulty != "고급":
        return False

    choices = q.get("choices", [])

    if not isinstance(choices, list) or len(choices) != 5:
        return True

    extreme_reject_patterns = [
        "모든 컬럼",
        "모든 테이블",
        "모든 데이터",
        "모든 조건",
        "모든 조인",
        "모든 접근",
        "데이터를 삭제",
        "접근을 차단",
        "완전히 제거",
    ]

    bad_choice_count = 0

    for choice in choices:
        choice_text = str(choice)

        if any(pattern in choice_text for pattern in extreme_reject_patterns):
            bad_choice_count += 1

    # 정말 심각한 선택지가 2개 이상일 때만 폐기
    return bad_choice_count >= 2

def _find_hard_choice_quality_errors(q: dict, difficulty: str) -> list[str]:
    """
    객관식 선택지 품질이 낮은 경우를 감지한다.
    현재 단계에서는 hard reject하지 않고 quality_warnings에만 남긴다.
    """
    if difficulty != "고급":
        return []

    choices = q.get("choices", [])
    answer = q.get("answer")

    if not isinstance(choices, list) or len(choices) != 5:
        return ["선택지가 5개가 아닙니다."]

    try:
        answer_int = int(answer)
    except Exception:
        return ["answer가 숫자가 아닙니다."]

    if answer_int < 1 or answer_int > 5:
        return ["answer가 1~5 범위를 벗어났습니다."]

    errors: list[str] = []

    correct_choice = str(choices[answer_int - 1]).strip()
    wrong_choices = [
        str(choice).strip()
        for idx, choice in enumerate(choices)
        if idx != answer_int - 1
    ]

    choice_lengths = [len(str(choice).strip()) for choice in choices]
    wrong_lengths = [len(choice) for choice in wrong_choices]

    avg_wrong_len = sum(wrong_lengths) / max(len(wrong_lengths), 1)
    min_len = min(choice_lengths)
    max_len = max(choice_lengths)

    if len(correct_choice) > avg_wrong_len * 1.35:
        errors.append("정답 선택지만 다른 오답보다 과도하게 길어 정답이 노출됩니다.")

    if min_len > 0 and max_len / min_len >= 2.0:
        errors.append("선택지 간 길이 편차가 너무 커서 정답 추측 가능성이 높습니다.")

    too_short_choices = [
        choice for choice in choices
        if len(str(choice).strip()) < 22
    ]

    if too_short_choices:
        errors.append(
            f"고급 문제에 너무 짧은 선택지가 포함되어 있습니다: {too_short_choices}"
        )

    hard_reject_patterns = [
        "모든 컬럼",
        "모든 테이블",
        "모든 데이터",
        "모든 조건",
        "모든 조인",
        "모든 접근",
        "데이터를 삭제",
        "접근을 차단",
        "완전히 제거",
    ]

    warning_patterns = [
        "고려하지 않는다",
        "무시",
        "무조건",
        "항상",
        "오직",
        "쿼리를 단순화",
        "조인 순서를 수동으로 고정",
        "조인 순서를 무조건",
        "인덱스를 추가하여 모든",
        "쓰기 작업의 성능을 높인다",
    ]

    for choice in choices:
        choice_text = str(choice)

        for pattern in hard_reject_patterns:
            if pattern in choice_text:
                errors.append(
                    f"강한 품질 저하 선택지 표현이 포함되어 있습니다: '{pattern}' / {choice_text}"
                )

        for pattern in warning_patterns:
            if pattern in choice_text:
                errors.append(
                    f"품질 저하 선택지 표현이 포함되어 있습니다: '{pattern}' / {choice_text}"
                )

    correct_judgment_words = [
        "고려",
        "평가",
        "종합",
        "분석",
        "판단",
        "리스크",
        "트레이드오프",
    ]

    simple_action_patterns = [
        "추가한다",
        "제거한다",
        "단순화한다",
        "변경한다",
        "고정한다",
        "높인다",
    ]

    correct_has_judgment = any(word in correct_choice for word in correct_judgment_words)
    simple_wrong_count = 0

    for wrong_choice in wrong_choices:
        if any(pattern in wrong_choice for pattern in simple_action_patterns):
            if not any(word in wrong_choice for word in correct_judgment_words):
                simple_wrong_count += 1

    if correct_has_judgment and simple_wrong_count >= 2:
        errors.append(
            "정답만 종합 판단형이고 오답은 단순 조치형이라 정답이 쉽게 드러납니다."
        )

    return errors


def _has_numbered_distractor_explanation(explanation: str) -> bool:
    """
    해설에서 오답을 '1번은', '2번은'처럼 번호 기준으로 설명하는지 감지한다.
    정답 첫 문장 '정답은 N번입니다.'는 허용한다.
    """
    if not explanation:
        return False

    text = str(explanation).strip()

    text = re.sub(r"^정답은\s*\d\s*번입니다\.?\s*", "", text)

    numbered_patterns = [
        r"\b[1-5]\s*번은",
        r"\b[1-5]\s*번의",
        r"\b[1-5]\s*번 선택지",
        r"\b[1-5]\s*번 보기",
        r"\b[1-5]\s*번과\s*[1-5]\s*번",
        r"\b[1-5]\s*번,\s*[1-5]\s*번",
    ]

    return any(re.search(pattern, text) for pattern in numbered_patterns)

def _has_informal_explanation_ending(explanation: str) -> bool:
    """
    해설이 존댓말 설명체가 아니라 '~다', '~한다', '~된다' 같은 반말/평서체로 끝나는지 감지한다.
    단, 첫 문장 '정답은 N번입니다.'는 허용한다.
    """
    if not explanation:
        return False

    text = str(explanation).strip()

    # 첫 문장 정답 안내 제거
    text = re.sub(r"^정답은\s*\d\s*번입니다\.?\s*", "", text).strip()

    if not text:
        return False

    # 문장 단위로 나눠서 마지막 표현 확인
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。])\s+", text) if s.strip()]

    informal_endings = [
        "다.",
        "한다.",
        "된다.",
        "이다.",
        "아니다.",
        "있다.",
        "없다.",
        "높아진다.",
        "낮아진다.",
        "발생한다.",
        "증가한다.",
        "감소한다.",
        "필요하다.",
        "적절하다.",
        "타당하다.",
    ]

    polite_endings = [
        "입니다.",
        "합니다.",
        "됩니다.",
        "아닙니다.",
        "있습니다.",
        "없습니다.",
        "높아집니다.",
        "낮아집니다.",
        "발생합니다.",
        "증가합니다.",
        "감소합니다.",
        "필요합니다.",
        "적절합니다.",
        "타당합니다.",
    ]

    for sentence in sentences:
        if any(sentence.endswith(polite) for polite in polite_endings):
            continue

        if any(sentence.endswith(informal) for informal in informal_endings):
            return True

    return False
    
def _has_required_evidence_for_competency(
    q: dict,
    difficulty: str,
) -> tuple[bool, str | None]:
    """
    중급/고급 문제에서 역량별 실전 자료가 포함되어 있는지 확인한다.
    비문학형 문제를 저장하지 않기 위한 검증이다.
    """
    if difficulty not in {"중급", "고급"}:
        return True, None

    competency_type = normalize_competency_type(q.get("competency_type")) or str(q.get("competency_type") or "").strip()
    body = str(q.get("body", "") or "")
    
    question_format = str(q.get("question_format") or q.get("template_format") or "").strip()
    code_formats = [
        "code_output", "runtime_error", "exception_flow", "generator_behavior",
        "override_behavior", "equals_hashcode", "polymorphism_dispatch",
        "collection_behavior", "data_structure_fix", "list_dict_mutation",
        "shallow_deep_copy", "decorator_behavior", "scope_closure", "compile_error",
        "interface_abstract"
    ]
    sql_query_formats = [
        "query_result", "join_where_bug", "index_plan_choice"
    ]
    
    if competency_type in {"python", "java"} and question_format in code_formats:
        if "```" not in body and "def " not in body and "class " not in body and "print(" not in body and "System.out" not in body:
            return False, f"{competency_type} 코드 기반 문제({question_format})에는 반드시 코드블럭 또는 코드가 포함되어야 합니다."
            
    if competency_type == "sql" and question_format in sql_query_formats:
        if "```sql" not in body and not any(k in body.upper() for k in ["SELECT", "WHERE", "JOIN", "GROUP BY", "HAVING"]):
            return False, f"SQL 쿼리 기반 문제({question_format})에는 반드시 SQL 코드블럭이나 핵심 쿼리 키워드가 포함되어야 합니다."

    if competency_type == "java":
        signals = [
            "class ",
            "extends",
            "@Override",
            "new ",
            "public ",
            "private ",
            "void ",
            "System.out.println",
            "interface ",
            "implements",
            "List<",
            "Map<",
        ]
        if not any(signal in body for signal in signals) and "```java" not in body:
            return False, "java 중급/고급 문제에는 Java 코드 조각, 상속/인터페이스 구조, 컬렉션 사용 예시 중 하나가 필요합니다."

    if competency_type == "python":
        signals = [
            "def ",
            "for ",
            "while ",
            "if ",
            "try:",
            "except",
            "print(",
            ".get(",
            "KeyError",
            "TypeError",
            "users =",
            "items =",
            "data =",
            "[",
            "{",
        ]
        if not any(signal in body for signal in signals):
            return False, "python 중급/고급 문제에는 Python 코드 조각 또는 실제 리스트/딕셔너리 예시가 필요합니다."
        if any(keyword in body for keyword in ["얕은 복사", "shallow copy", "리스트 복사"]):
            shallow_copy_signals = [
                ".copy()",
                "[:]",
                "copy.copy",
            ]

            reference_assignment_patterns = [
                r"\w+\s*=\s*\w+\s*\n",
                r"copied_list\s*=\s*original_list",
                r"list_b\s*=\s*list_a",
                r"copied\s*=\s*original",
            ]

            has_shallow_copy_signal = any(signal in body for signal in shallow_copy_signals)
            has_reference_assignment_only = any(
                re.search(pattern, body)
                for pattern in reference_assignment_patterns
            )

            if has_reference_assignment_only and not has_shallow_copy_signal:
                return False, (
                    "얕은 복사 문제에서 copied = original 형태의 참조 할당만 제시하고 있습니다. "
                    "list.copy(), slicing [:], copy.copy() 중 하나를 포함해야 합니다."
                )
    if competency_type == "sql":
        upper_body = body.upper()
        signals = [
            "SELECT",
            "FROM",
            "JOIN",
            "WHERE",
            "GROUP BY",
            "ORDER BY",
            "HAVING",
            "EXPLAIN",
            "CREATE TABLE",
            "테이블",
            "실행 계획",
        ]
        if not any(signal in upper_body for signal in signals):
            return False, "sql 중급/고급 문제에는 SQL 쿼리, 테이블 구조, 실행 계획 설명 중 하나가 필요합니다."

    if competency_type == "ai":
        lower_body = body.lower()
        template_format = str(q.get("template_format") or "").strip().lower()

        def count_signals(signals: list[str]) -> int:
            return sum(1 for signal in signals if signal.lower() in lower_body)

        def has_any(signals: list[str]) -> bool:
            return any(signal.lower() in lower_body for signal in signals)

        rag_signals = [
            "rag",
            "query",
            "질의",
            "top_k",
            "top-k",
            "chunk",
            "청크",
            "similarity",
            "유사도",
            "metadata",
            "메타데이터",
            "metadata_filter",
            "검색 결과",
            "검색된 문서",
            "embedding",
            "임베딩",
            "vector search",
            "벡터 검색",
            "keyword search",
            "키워드 검색",
            "hybrid search",
            "하이브리드 검색",
            "reranker",
            "리랭커",
            "context filtering",
            "컨텍스트 필터링",
            "hallucination",
            "환각",
        ]

        llm_signals = [
            "llm",
            "prompt",
            "프롬프트",
            "json",
            "schema",
            "스키마",
            "structured output",
            "구조화 출력",
            "response_format",
            "parsing",
            "파싱",
            "choices",
            "answer",
            "explanation",
            "tool calling",
            "function calling",
            "도구 호출",
            "함수 호출",
            "tool schema",
            "인자",
            "argument",
            "타입 검증",
            "validation",
            "검증",
            "fallback",
            "재시도",
        ]

        agent_signals = [
            "agent",
            "에이전트",
            "langgraph",
            "graph",
            "그래프",
            "node",
            "노드",
            "state",
            "상태",
            "plan",
            "planning",
            "tool call",
            "tool",
            "도구",
            "observation",
            "관찰",
            "retry",
            "재시도",
            "repair_node",
            "validation_node",
            "human review",
            "human-in-the-loop",
            "human_review_node",
            "검수",
            "분기",
        ]

        modelops_signals = [
            "fine-tuning",
            "파인튜닝",
            "qlora",
            "lora",
            "vllm",
            "serving",
            "서빙",
            "inference",
            "추론",
            "latency",
            "지연",
            "p95",
            "cost",
            "비용",
            "gpu",
            "canary",
            "배포",
            "monitoring",
            "모니터링",
            "quality_score",
            "jsonl",
            "approved",
            "pending",
            "rejected",
        ]

        ml_signals = [
            "machine learning",
            "머신러닝",
            "deep learning",
            "딥러닝",
            "train",
            "validation",
            "test",
            "accuracy",
            "정확도",
            "precision",
            "정밀도",
            "recall",
            "재현율",
            "f1",
            "threshold",
            "임계값",
            "overfitting",
            "과적합",
            "regularization",
            "early stopping",
            "일반화",
            "불균형",
            "소수 클래스",
            "false positive",
            "false negative",
        ]

        # template_format이 남아 있으면 가장 정확하게 하위 유형을 판단한다.
        if template_format.startswith(("retrieval_", "reranker_", "hybrid_", "chunking_", "context_", "hallucination_", "evaluation_", "query_rewrite")):
            ai_subtype = "rag"
        elif template_format.startswith("llm_"):
            ai_subtype = "llm"
        elif template_format.startswith("agent_"):
            ai_subtype = "agent"
        elif template_format.startswith("modelops_"):
            ai_subtype = "modelops"
        elif template_format.startswith("ml_"):
            ai_subtype = "ml"
        else:
            # template_format이 이미 pop된 경우 body 기반으로 추론한다.
            subtype_scores = {
                "rag": count_signals(rag_signals),
                "llm": count_signals(llm_signals),
                "agent": count_signals(agent_signals),
                "modelops": count_signals(modelops_signals),
                "ml": count_signals(ml_signals),
            }
            ai_subtype = max(subtype_scores, key=subtype_scores.get)

        if ai_subtype == "rag":
            total_count = count_signals(rag_signals)

            if difficulty == "중급" and total_count < 2:
                return False, (
                    "ai 중급 RAG 문제에는 query/top_k/chunk/similarity/metadata/embedding/"
                    "reranker/context filtering 중 최소 2개 이상의 구체 단서가 필요합니다."
                )

            if difficulty == "고급":
                retrieval_ok = has_any([
                    "query",
                    "질의",
                    "top_k",
                    "top-k",
                    "chunk",
                    "청크",
                    "similarity",
                    "유사도",
                    "검색 결과",
                    "검색된 문서",
                ])
                pipeline_ok = has_any([
                    "embedding",
                    "임베딩",
                    "vector search",
                    "벡터 검색",
                    "keyword search",
                    "키워드 검색",
                    "hybrid search",
                    "하이브리드 검색",
                    "reranker",
                    "리랭커",
                    "metadata_filter",
                    "metadata",
                    "메타데이터",
                    "context filtering",
                    "컨텍스트 필터링",
                ])

                if total_count < 3 or not retrieval_ok or not pipeline_ok:
                    return False, (
                        "ai 고급 RAG 문제에는 검색 결과 단서(query/top_k/chunk/similarity 등)와 "
                        "파이프라인 단서(embedding/vector search/keyword search/metadata_filter/"
                        "reranker/context filtering 등)가 함께 필요합니다."
                    )

        elif ai_subtype == "llm":
            total_count = count_signals(llm_signals)

            if difficulty == "중급" and total_count < 2:
                return False, (
                    "ai 중급 LLM 문제에는 prompt/JSON/schema/structured output/tool calling/"
                    "validation 중 최소 2개 이상의 구체 단서가 필요합니다."
                )

            if difficulty == "고급":
                output_or_tool_ok = has_any([
                    "json",
                    "schema",
                    "structured output",
                    "구조화 출력",
                    "response_format",
                    "tool calling",
                    "function calling",
                    "도구 호출",
                    "함수 호출",
                    "tool schema",
                ])
                validation_ok = has_any([
                    "validation",
                    "검증",
                    "필수 필드",
                    "answer",
                    "choices",
                    "parsing",
                    "파싱",
                    "fallback",
                    "재시도",
                ])

                if total_count < 3 or not output_or_tool_ok or not validation_ok:
                    return False, (
                        "ai 고급 LLM 문제에는 JSON/schema/structured output/tool calling 같은 출력·도구 조건과 "
                        "validation/fallback/retry 같은 검증 단서가 함께 필요합니다."
                    )

        elif ai_subtype == "agent":
            total_count = count_signals(agent_signals)

            if difficulty == "중급" and total_count < 2:
                return False, (
                    "ai 중급 Agent 문제에는 agent/tool/observation/state/retry/graph 중 "
                    "최소 2개 이상의 구체 단서가 필요합니다."
                )

            if difficulty == "고급":
                workflow_ok = has_any([
                    "agent",
                    "에이전트",
                    "langgraph",
                    "graph",
                    "node",
                    "노드",
                    "state",
                    "상태",
                ])
                control_ok = has_any([
                    "observation",
                    "관찰",
                    "retry",
                    "재시도",
                    "repair",
                    "repair_node",
                    "validation_node",
                    "human review",
                    "human_review_node",
                    "human-in-the-loop",
                    "검수",
                    "분기",
                ])

                if total_count < 3 or not workflow_ok or not control_ok:
                    return False, (
                        "ai 고급 Agent 문제에는 Agent/LangGraph/state/node 같은 워크플로우 단서와 "
                        "observation/retry/repair/human review 같은 제어 단서가 함께 필요합니다."
                    )

        elif ai_subtype == "modelops":
            total_count = count_signals(modelops_signals)

            if difficulty == "중급" and total_count < 2:
                return False, (
                    "ai 중급 ModelOps 문제에는 fine-tuning/QLoRA/vLLM/serving/latency/cost/"
                    "quality_score/JSONL 중 최소 2개 이상의 구체 단서가 필요합니다."
                )

            if difficulty == "고급":
                model_or_data_ok = has_any([
                    "fine-tuning",
                    "파인튜닝",
                    "qlora",
                    "lora",
                    "quality_score",
                    "jsonl",
                    "approved",
                    "pending",
                    "rejected",
                    "vllm",
                    "serving",
                    "서빙",
                ])
                ops_metric_ok = has_any([
                    "latency",
                    "지연",
                    "p95",
                    "cost",
                    "비용",
                    "gpu",
                    "canary",
                    "monitoring",
                    "모니터링",
                    "통과율",
                    "운영",
                ])

                if total_count < 3 or not model_or_data_ok or not ops_metric_ok:
                    return False, (
                        "ai 고급 ModelOps 문제에는 fine-tuning/QLoRA/vLLM/serving/JSONL/quality_score 같은 "
                        "모델·데이터 단서와 latency/cost/p95/canary/monitoring 같은 운영 단서가 함께 필요합니다."
                    )

        elif ai_subtype == "ml":
            total_count = count_signals(ml_signals)

            if difficulty == "중급" and total_count < 2:
                return False, (
                    "ai 중급 ML 문제에는 train/validation/test/accuracy/precision/recall/F1/"
                    "overfitting 중 최소 2개 이상의 구체 단서가 필요합니다."
                )

            if difficulty == "고급":
                metric_or_split_ok = has_any([
                    "train",
                    "validation",
                    "test",
                    "accuracy",
                    "정확도",
                    "precision",
                    "정밀도",
                    "recall",
                    "재현율",
                    "f1",
                ])
                risk_or_action_ok = has_any([
                    "불균형",
                    "소수 클래스",
                    "threshold",
                    "임계값",
                    "비용",
                    "overfitting",
                    "과적합",
                    "regularization",
                    "early stopping",
                    "일반화",
                ])

                if total_count < 3 or not metric_or_split_ok or not risk_or_action_ok:
                    return False, (
                        "ai 고급 ML 문제에는 평가 지표 또는 데이터 분리 단서와 "
                        "불균형/threshold/비용/과적합/regularization/early stopping 같은 판단 단서가 함께 필요합니다."
                    )
    return True, None


def _validate_questions(
    questions: list,
    question_type: str,
    difficulty: str,
    score: int,
) -> list[dict[str, Any]]:
    if not isinstance(questions, list):
        raise ValueError("AI 응답이 JSON 배열이 아닙니다.")

    validated: list[dict[str, Any]] = []

    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            logger.warning(f"문제 검증 제외: index={idx}, reason=not_dict")
            continue

        title = q.get("title")
        body = q.get("body")
        choices = q.get("choices")
        answer = q.get("answer")
        explanation = q.get("explanation")

        if body:
            q["body"] = str(body).strip()
            body = q["body"]

        if not title or not body or explanation is None:
            logger.warning(f"문제 검증 제외: index={idx}, reason=missing_required_fields")
            continue

        has_evidence, evidence_reason = _has_required_evidence_for_competency(
            q=q,
            difficulty=difficulty,
        )

        if not has_evidence:
            logger.warning(
                f"문제 검증 제외: index={idx}, reason=missing_required_evidence, details={evidence_reason}"
            )
            continue

        if question_type == "multiple_choice":
            if not isinstance(choices, list) or len(choices) != 5:
                logger.warning(f"문제 검증 제외: index={idx}, reason=invalid_choices")
                continue

            try:
                answer_int = int(answer)
            except Exception:
                logger.warning(f"문제 검증 제외: index={idx}, reason=invalid_answer_type")
                continue

            if answer_int < 1 or answer_int > 5:
                logger.warning(f"문제 검증 제외: index={idx}, reason=answer_out_of_range")
                continue

            quality_warnings: list[str] = []
            meta_choice_errors = _find_meta_choice_expressions(q)

            if meta_choice_errors:
                logger.warning(
                    f"문제 검증 제외: index={idx}, reason=meta_choice_expression, "
                    f"details={meta_choice_errors}"
                )
                continue
            explanation_answer = _extract_answer_number_from_explanation(str(explanation))

            if explanation_answer is not None and explanation_answer != answer_int:
                logger.warning(
                    f"문제 검증 제외: index={idx}, reason=explanation_answer_mismatch, "
                    f"answer={answer_int}, explanation_answer={explanation_answer}"
                )
                continue
            
            if _has_answer_choice_mismatch(q):
                logger.warning(
                    f"문제 검증 제외: index={idx}, reason=answer_choice_mismatch, "
                    f"answer={answer_int}, answer_choice={str(choices[answer_int - 1])[:120]}, "
                    f"explanation={str(explanation)[:200]}"
                )
                continue

            if _has_output_explanation_mismatch(q):
                logger.warning(
                    f"문제 검증 제외: index={idx}, reason=output_explanation_mismatch, "
                    f"answer={answer_int}, answer_choice={str(choices[answer_int - 1])[:120]}, "
                    f"explanation={str(explanation)[:200]}"
                )
                continue
            if _has_explanation_contradiction(str(q.get("explanation", explanation)), answer_int):
                logger.warning(
                    f"문제 검증 제외: index={idx}, reason=explanation_contradiction, "
                    f"answer={answer_int}, answer_choice={str(choices[answer_int - 1])[:120]}, "
                    f"explanation={str(q.get('explanation', explanation))[:200]}"
                )
                continue
            if _has_informal_explanation_ending(str(q.get("explanation", explanation))):
                logger.warning(
                    f"문제 검증 제외: index={idx}, reason=informal_explanation_ending, "
                    f"explanation={str(q.get('explanation', explanation))[:200]}"
                )
                continue
            weak_option_reasons = _find_weak_multiple_choice_options(q, difficulty)
            if weak_option_reasons:
                logger.warning(
                    f"문제 품질 경고: index={idx}, reason=weak_multiple_choice_options, "
                    f"details={weak_option_reasons}"
                )
                quality_warnings.extend(weak_option_reasons)

            hard_choice_errors = _find_hard_choice_quality_errors(q, difficulty)

            if hard_choice_errors:
                logger.warning(
                    f"문제 품질 경고: index={idx}, reason=hard_choice_quality_error, "
                    f"details={hard_choice_errors}"
                )

                if _should_reject_for_choice_quality(q, difficulty):
                    logger.warning(
                        f"문제 검증 제외: index={idx}, reason=hard_choice_quality_reject"
                    )
                    continue

                quality_warnings.extend(hard_choice_errors)

            if _has_answer_length_bias(q):
                if difficulty == "고급":
                    logger.warning(f"문제 검증 제외: index={idx}, reason=answer_length_bias")
                    continue

                quality_warnings.append(
                    "정답 선택지가 오답보다 길어 정답 노출 가능성이 있습니다."
                )

            if _is_explanation_too_similar_to_answer_choice(q):
                logger.warning(f"문제 검증 제외: index={idx}, reason=explanation_too_similar_to_answer_choice")
                continue
            if _has_too_shallow_explanation(q):
                logger.warning(
                    f"문제 검증 제외: index={idx}, reason=too_shallow_explanation, "
                    f"answer={answer_int}, explanation={str(explanation)[:200]}"
                )
                continue
            if _has_too_obvious_distractors(q):
                logger.warning(f"문제 검증 제외: index={idx}, reason=too_obvious_distractors")
                continue
            if _has_java_static_instance_multiple_truth(q):
                logger.warning(
                    f"문제 검증 제외: index={idx}, reason=java_static_instance_multiple_truth, "
                    f"answer={answer_int}, choices={choices}"
                )
                continue
            if _has_numbered_distractor_explanation(str(q.get("explanation", explanation))):
                logger.warning(
                    f"문제 검증 제외: index={idx}, reason=numbered_distractor_explanation, "
                    f"answer={answer_int}, answer_choice={str(choices[answer_int - 1])[:120]}, "
                    f"explanation={str(q.get('explanation', explanation))[:200]}"
                )
                continue

            # ─────────────────────────────────────────────
            # find_incorrect 유형 전용 검증
            # ─────────────────────────────────────────────
            answer_style = str(q.get("answer_style", "")).strip()
            body_str = str(body or "").strip()

            find_incorrect_body_markers = [
                "옳지 않",
                "틀린",
                "부적절한",
                "잘못된",
                "옳은 것이 아닌",
                "incorrect",
                "false",
                "아닌 것",
            ]

            is_find_incorrect_question = (
                answer_style == "find_incorrect"
                or any(marker in body_str for marker in find_incorrect_body_markers)
            )

            if is_find_incorrect_question:
                body_str = str(body or "").strip()
                explanation_str = str(q.get("explanation", explanation) or "").strip()
                answer_choice = ""
                try:
                    answer_choice = str(choices[answer_int - 1])
                except Exception:
                    answer_choice = ""

                answer_choice_meta_patterns = [
                    "오해할 수",
                    "오해",
                    "혼동할 수",
                    "혼동",
                    "착각할 수",
                    "착각",
                    "잘못 이해",
                ]

                if any(pattern in answer_choice for pattern in answer_choice_meta_patterns):
                    logger.warning(
                        f"문제 검증 제외: index={idx}, reason=find_incorrect_meta_answer_choice, "
                        f"answer_choice={answer_choice}"
                    )
                    continue
                # body 질문 형태 검증: "옳지 않은", "틀린", "부적절한" 등이 포함되어야 함
                find_incorrect_body_markers = [
                    "옳지 않", "틀린", "부적절한", "잘못된", "옳은 것이 아닌",
                    "incorrect", "false", "아닌 것",
                ]
                if not any(m in body_str for m in find_incorrect_body_markers):
                    logger.warning(
                        f"find_incorrect 검증 경고: index={idx}, "
                        f"reason=body_not_find_incorrect_form. body가 '옳지 않은 것'을 묻지 않음."
                    )
                    quality_warnings.append(
                        "find_incorrect 유형인데 body 질문이 '옳지 않은 것'을 묻는 형태가 아닙니다."
                    )

                # explanation 방향 검증: 정답 선택지가 "틀렸다"는 내용을 설명해야 함
                explanation_correct_markers = [
                    "틀",
                    "잘못",
                    "부적절",
                    "옳지 않",
                    "incorrect",
                    "false",
                    "아니다",
                    "아닙니다",
                    "사용되지 않는다",
                    "사용되지 않습니다",
                    "해당하지 않는다",
                    "해당하지 않습니다",
                    "역할이 아니다",
                    "역할이 아닙니다",
                    "정렬하기 위해 사용되지",
                    "그룹화하는 역할",
                    "올바른 역할",
                    "나머지 선택지",
                ]
                answer_choice = ""
                try:
                    answer_choice = str(choices[answer_int - 1])
                except Exception:
                    answer_choice = ""

                answer_choice_keywords = [
                    word
                    for word in re.split(r"\s+|,|\.|\(|\)", answer_choice)
                    if len(word.strip()) >= 2
                ]

                has_answer_choice_reference = any(
                    keyword in explanation_str
                    for keyword in answer_choice_keywords
                )

                if not any(m in explanation_str for m in explanation_correct_markers) and not has_answer_choice_reference:
                    logger.warning(
                        f"find_incorrect 검증 경고: index={idx}, "
                        f"reason=explanation_not_pointing_to_incorrect. "
                        f"explanation이 틀린 이유를 설명하지 않음."
                    )
                    quality_warnings.append(
                        "find_incorrect 유형인데 explanation이 정답(틀린 것)의 오류 이유를 설명하지 않습니다."
                    )
            if quality_warnings:
                q["quality_warnings"] = quality_warnings

            q["answer"] = answer_int

        else:
            q["choices"] = []

            if answer is None or str(answer).strip() == "":
                logger.warning(f"문제 검증 제외: index={idx}, reason=empty_subjective_answer")
                continue

            explanation_text = str(explanation)
            
            if _extract_answer_number_from_explanation(explanation_text) is not None:
                logger.warning(f"문제 검증 제외 : index={idx}, reason=subjective_question_answer_number_in_explanation")
                continue
            q["answer"]=str(answer)
            q["explanation"]=explanation_text
                

        q["difficulty"] = difficulty
        q["score"] = score

        if not isinstance(q.get("competency_tags"), list):
            q["competency_tags"] = []

        normalize_question_text(q)

        validated.append(q)

    logger.info(f"문제 검증 결과: input={len(questions)}, validated={len(validated)}")

    return validated

def _has_answer_choice_mismatch(q: dict) -> bool:
    """
    해설에서 설명하는 핵심 결과/개념이 실제 정답 선택지와 충돌하는지 감지한다.
    특히 코드 출력 결과형 문제에서 answer와 explanation이 서로 다른 값을 말하는 경우를 잡는다.
    """
    choices = q.get("choices", [])
    answer = q.get("answer")
    explanation = str(q.get("explanation", "") or "")

    if not isinstance(choices, list) or len(choices) != 5 or not explanation:
        return False

    try:
        answer_int = int(answer)
    except Exception:
        return False

    if answer_int < 1 or answer_int > 5:
        return False

    answer_choice = str(choices[answer_int - 1])

    bracket_patterns = [
        r"\[[^\]]+\]",
    ]

    explanation_values = []
    answer_values = []

    for pattern in bracket_patterns:
        explanation_values.extend(re.findall(pattern, explanation))
        answer_values.extend(re.findall(pattern, answer_choice))

    if explanation_values and answer_values:
        return explanation_values[0] != answer_values[0]

    number_result_pattern = r"출력\s*결과는\s*([A-Za-z0-9_\[\],\s]+)"
    exp_match = re.search(number_result_pattern, explanation)
    ans_match = re.search(number_result_pattern, answer_choice)

    if exp_match and ans_match:
        exp_value = exp_match.group(1).strip().rstrip(".입니다")
        ans_value = ans_match.group(1).strip().rstrip(".입니다")
        return exp_value != ans_value

    return False

def _extract_output_values(text: str) -> list[str]:
    """
    선택지/해설에서 출력값 후보를 추출한다.
    예:
    - 출력 결과는 0이다. -> ["0"]
    - 출력 결과는 0과 1이다. -> ["0", "1"]
    - 출력 결과는 [4, 6, 8]이다. -> ["[4, 6, 8]"]
    """
    text = str(text or "").strip()

    list_values = re.findall(r"\[[^\]]+\]", text)
    if list_values:
        return [list_values[0].replace(" ", "")]

    patterns = [
        r"출력\s*결과는\s*(.+?)(?:이다|입니다|가\s*된다|된다|\.|$)",
        r"실행\s*결과는\s*(.+?)(?:이다|입니다|가\s*된다|된다|\.|$)",
        r"결과는\s*(.+?)(?:이다|입니다|가\s*된다|된다|\.|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        value_text = match.group(1).strip().strip("'\"")
        value_text = value_text.replace(" ", "")

        if "과" in value_text:
            return [v for v in value_text.split("과") if v]

        if "," in value_text:
            return [v for v in value_text.split(",") if v]

        return [value_text]

    # 해설에서 "첫 번째 ... 0", "두 번째 ... 1" 형태 추출
    ordered_values = []
    ordered_patterns = [
        r"첫\s*번째[^0-9\[]*([0-9]+|\[[^\]]+\])",
        r"두\s*번째[^0-9\[]*([0-9]+|\[[^\]]+\])",
        r"세\s*번째[^0-9\[]*([0-9]+|\[[^\]]+\])",
    ]

    for pattern in ordered_patterns:
        match = re.search(pattern, text)
        if match:
            ordered_values.append(match.group(1).replace(" ", ""))

    return ordered_values

def _has_output_explanation_mismatch(q: dict) -> bool:
    """
    출력 결과 예측 문제에서 정답 선택지와 해설 또는 코드 출력 개수가 맞지 않으면 True.
    """
    body = str(q.get("body", "") or "")
    explanation = str(
        q.get("_llm_explanation_before_rebalance")
        or q.get("_explanation_after_rebalance_before_repair")
        or q.get("explanation", "")
        or ""
    )

    choices = q.get("choices", [])
    answer = q.get("answer")

    if "출력 결과" not in body and "실행 결과" not in body and "print(" not in body:
        return False

    if not isinstance(choices, list) or len(choices) != 5:
        return False

    try:
        answer_int = int(answer)
    except Exception:
        return False

    if answer_int < 1 or answer_int > 5:
        return False

    answer_choice = str(choices[answer_int - 1])

    answer_values = _extract_output_values(answer_choice)
    explanation_values = _extract_output_values(explanation)

    # print가 2개 이상이면 단일 출력값 선택지는 위험하므로 제외
    # 단, body가 "두 번째 호출 결과"처럼 특정 출력 하나만 묻는 경우는 예외
    asks_single_result = any(
        marker in body
        for marker in [
            "두 번째 호출",
            "첫 번째 호출",
            "마지막 출력",
            "최종 출력",
            "마지막 결과",
        ]
    )

    if body.count("print(") >= 2 and not asks_single_result:
        if len(answer_values) < 2:
            return True

    if answer_values and explanation_values:
        return answer_values != explanation_values

    return False

def _has_java_static_instance_multiple_truth(q: dict) -> bool:
    """
    Java static/instance 비교 문제에서 정답 외 선택지에
    일반적으로 참인 설명만 단독으로 들어가 복수정답처럼 보이는 경우를 감지한다.
    단, 참인 설명과 틀린 설명이 함께 들어간 오답은 허용한다.
    """
    competency_type = normalize_competency_type(q.get("competency_type"))
    if competency_type != "java":
        return False

    body = str(q.get("body", "") or "").lower()
    choices = q.get("choices", [])
    answer = q.get("answer")

    if "static" not in body or "인스턴스" not in body:
        return False

    if not isinstance(choices, list) or len(choices) != 5:
        return False

    try:
        answer_int = int(answer)
    except Exception:
        return False

    if answer_int < 1 or answer_int > 5:
        return False

    true_like_patterns = [
        "인스턴스 메서드는 객체를 통해 호출",
        "인스턴스 메서드는 객체의 상태",
        "인스턴스 메서드는 인스턴스 변수에 접근",
        "static 메서드는 클래스 레벨에서 호출",
        "static 메서드는 클래스에 속",
        "static 메서드는 인스턴스 변수에 접근할 수 없다",
        "static 메서드는 this 키워드를 사용할 수 없다",
    ]

    false_markers = [
        "static 메서드는 this 키워드를 사용할 수 있다",
        "static 메서드는 인스턴스 변수에 접근할 수 있다",
        "static 메서드는 인스턴스 메서드와 동일한 방식으로 호출",
        "인스턴스 메서드는 클래스 이름으로 호출",
        "인스턴스 메서드는 객체 생성 없이 호출",
        "인스턴스 메서드는 static",
        "더 많은 메모리",
        "더 빠르게 실행",
    ]

    for idx, choice in enumerate(choices, start=1):
        if idx == answer_int:
            continue

        choice_text = str(choice)

        has_true_like = any(pattern in choice_text for pattern in true_like_patterns)
        has_false_marker = any(marker in choice_text for marker in false_markers)

        # 일반적으로 참인 설명만 단독으로 들어간 오답만 reject
        if has_true_like and not has_false_marker:
            return True

    return False

def _has_too_shallow_explanation(q: dict) -> bool:
    """
    해설이 정답 선택지를 반복하는 수준이거나,
    개념 설명/오답 판단 근거가 너무 부족한 경우를 감지한다.
    """
    explanation = str(q.get("explanation", "") or "").strip()
    body = str(q.get("body", "") or "")
    competency_type = normalize_competency_type(q.get("competency_type"))

    if not explanation:
        return True

    explanation_body = re.sub(
        r"^정답은\s*\d\s*번입니다\.?\s*",
        "",
        explanation,
    ).strip()

    # Java static/instance 문제는 최소 설명량을 요구한다.
    if (
        competency_type == "java"
        and "static" in body.lower()
        and ("인스턴스" in body or "instance" in body.lower())
    ):
        required_terms = [
            "this",
            "인스턴스 필드",
            "객체",
            "클래스",
        ]

        if len(explanation_body) < 120:
            return True

        if sum(1 for term in required_terms if term in explanation_body) < 2:
            return True

        if "다른 선택지" not in explanation_body and "반면" not in explanation_body:
            return True

    return False