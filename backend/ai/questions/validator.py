# backend/ai/questions/validator.py

import re
import logging
from typing import Any
from ai.questions.competency_config import normalize_competency_type

logger = logging.getLogger("uvicorn.info")


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
    - 품질 이슈는 가능한 한 quality_warnings로 남긴다.
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


def _replace_answer_number_in_explanation(explanation: str, new_answer: int) -> str:
    """
    explanation 안의 '정답은 N번입니다' 형태를 새 정답 번호로 교체한다.

    주의:
    원래는 postprocessor 역할이지만, 현재 1단계에서는 validator가
    explanation_answer_mismatch를 자동 보정하므로 임시로 validator 안에 둔다.
    """
    if not explanation:
        return explanation

    patterns = [
        r"정답은\s*\d\s*번",
        r"정답\s*:\s*\d\s*번",
        r"답은\s*\d\s*번",
        r"\d\s*번이\s*정답",
    ]

    new_text = f"정답은 {new_answer}번"
    updated = explanation

    for pattern in patterns:
        if re.search(pattern, updated):
            updated = re.sub(pattern, new_text, updated, count=1)
            return updated

    return f"정답은 {new_answer}번입니다. {updated}"


def _remove_answer_number_from_explanation(explanation: str) -> str:
    """
    서술형/코드작성형 explanation에 잘못 들어간 객관식 정답 번호 표현을 제거한다.

    주의:
    원래는 postprocessor 역할이지만, 현재 1단계에서는 서술형 검증에서 바로 사용하므로
    임시로 validator 안에 둔다.
    """
    if not explanation:
        return explanation

    cleaned = str(explanation)

    patterns = [
        r"\d+\)\s*정답\s*번호\s*:\s*\d+\s*",
        r"정답\s*번호\s*:\s*\d+\s*",
        r"정답은\s*\d+\s*번입니다\.?\s*",
        r"정답은\s*\d+\s*번\s*",
        r"\d+\s*번이\s*정답입니다\.?\s*",
        r"\d+\s*번이\s*정답\s*",
    ]

    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


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
        if not any(signal in body for signal in signals):
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
    if competency_type == "c_language":
        c_signals = [
            "#include",
            "int main",
            "printf",
            "scanf",
            "int ",
            "char ",
            "void ",
            "return",
            "*",
            "&",
            "->",
            "malloc",
            "free",
            "sizeof",
            "struct",
            "arr[",
            "str[",
        ]

        if not any(signal in body for signal in c_signals):
            return False, (
                "c_language 중급/고급 문제에는 C 코드 조각, 포인터/배열/문자열/구조체/동적 할당 예시 중 하나가 필요합니다."
            )

        if difficulty == "중급":
            semicolon_count = body.count(";")

            if semicolon_count < 4:
                return False, (
                    "C 중급 문제에는 최소 4개 이상의 실행 문장이 포함된 코드 조각이 필요합니다."
                )

            normalized_body = body.replace("\n", " ")

            too_simple_pointer_patterns = [
                r"int\s+arr\s*\[\s*\]\s*=\s*\{[^}]+\}\s*;\s*int\s*\*\s*\w+\s*=\s*arr\s*\+\s*1\s*;\s*\*\s*\w+\s*=",
            ]

            if any(re.search(pattern, normalized_body) for pattern in too_simple_pointer_patterns):
                if not any(keyword in body for keyword in [
                    "함수",
                    "void ",
                    "return",
                    "인자",
                    "매개변수",
                    "문자열",
                    "구조체",
                    "동적 할당",
                    "malloc",
                    "free",
                ]):
                    return False, (
                        "C 중급 포인터 문제가 단순 arr + 1 위치 확인에 머물러 있습니다. "
                        "함수 인자 전달, 배열 원소 변경 흐름, 문자열 처리, 구조체, 동적 할당 등 추가 조건이 필요합니다."
                    )

            compact_body = body.replace(" ", "").replace("\n", "")

            if 'char*str="Hello"' in compact_body or 'char*str="hello"' in compact_body:
                if not any(keyword in body for keyword in [
                    "문자열 리터럴",
                    "정의되지 않은 동작",
                    "undefined behavior",
                    "수정할 수 없는 영역",
                    "읽기 전용",
                ]):
                    return False, (
                        "문자열 리터럴 수정 문제는 정의되지 않은 동작 또는 문자열 리터럴 수정 불가를 명확히 다뤄야 합니다."
                    )
            # C 중급 코드 문제는 질문 문장과 선택지 유형이 맞아야 한다.
            # "가장 적절한 판단"처럼 추상적인 질문은 C 코드 실행 결과 문제와 맞지 않는 경우가 많다.
            if "가장 적절한 판단" in body:
                if any(keyword in body for keyword in [
                    "printf",
                    "출력",
                    "배열의 첫 번째 원소",
                    "arr[0]",
                    "array[0]",
                    "scores[",
                    "*(ptr",
                ]):
                    return False, (
                        "C 중급 코드 실행 문제에서 질문이 '가장 적절한 판단'처럼 추상적으로 작성되었습니다. "
                        "출력 결과, 변경된 배열 원소, 오류 원인 중 하나를 직접 묻도록 작성해야 합니다."
                    )

            choices = q.get("choices", [])

            if isinstance(choices, list) and len(choices) == 5:
                choice_text = " ".join(str(choice) for choice in choices)

                # 값/출력 결과를 묻는 문제인데 선택지가 조언형이면 탈락
                if any(keyword in body for keyword in [
                    "어떻게 될 것인가",
                    "출력 결과",
                    "무엇이 출력",
                    "값은 무엇",
                    "원소는 어떻게",
                    "arr[0]",
                    "array[0]",
                ]):
                    advice_patterns = [
                        "사용해야",
                        "수정해야",
                        "다른 방법",
                        "올바르게 접근",
                        "필요가 없다",
                        "문제가 없다",
                        "항상 안전",
                    ]

                    if any(pattern in choice_text for pattern in advice_patterns):
                        return False, (
                            "C 실행 결과 문제의 선택지에 일반 조언형 문장이 포함되어 있습니다. "
                            "값 변화 또는 출력 결과 중심의 선택지로 작성해야 합니다."
                        )

                # undefined behavior 문제는 body나 choices에 원인 단서가 있어야 함
                if any(keyword in body for keyword in [
                    "문자열 리터럴",
                    "char *",
                    "strcpy",
                    "str[",
                ]):
                    if "정의되지 않은 동작" in choice_text or "undefined behavior" in choice_text:
                        if not any(keyword in body for keyword in [
                            "문자열 리터럴",
                            "수정할 수 없는",
                            "읽기 전용",
                            "정의되지 않은 동작",
                            "undefined behavior",
                        ]):
                            return False, (
                                "C 문자열 문제에서 undefined behavior를 정답으로 쓰려면 "
                                "본문에 문자열 리터럴 수정 불가 또는 읽기 전용 메모리 단서를 명확히 포함해야 합니다."
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

def _ensure_question_body_ends_with_question(
    body: str,
    question_type: str,
    difficulty: str,
) -> str:
    """
    문제 본문이 상황 설명으로만 끝나는 경우,
    마지막에 명확한 질문 문장을 붙인다.

    LLM이 고급 문제에서 상황 설명만 작성하고 마침표로 끝내는 문제를 방지한다.
    """
    if not body:
        return body

    text = str(body).strip()

    # 이미 질문형이면 그대로 둔다.
    question_endings = (
        "?",
        "？",
        "무엇인가?",
        "무엇인가요?",
        "어느 것인가?",
        "어느 것인가요?",
        "무엇입니까?",
        "무엇인가.",
        "어느 것인가.",
    )

    if text.endswith(question_endings):
        return text

    # 마지막 문장이 이미 질문 의도를 갖고 있으면 물음표만 보정
    interrogative_keywords = [
        "무엇인가",
        "어느 것인가",
        "어떤 것인가",
        "가장 적절한 것은",
        "가장 타당한 것은",
        "가장 우선적으로",
        "어떻게 해야 하는가",
        "어떤 조치를 취해야 하는가",
        "무엇을 선택해야 하는가",
    ]

    if any(keyword in text for keyword in interrogative_keywords):
        if text.endswith("."):
            return text[:-1].rstrip() + "?"
        return text + "?"

    if question_type == "multiple_choice":
        if difficulty == "고급":
            return (
                f"{text} "
                "이 상황에서 문제의 원인과 제약 조건을 종합적으로 고려했을 때 가장 적절한 판단은 무엇인가?"
            )

        if difficulty == "중급":
            return (
                f"{text} "
                "이 상황에서 가장 적절한 선택지는 무엇인가?"
            )

        return (
            f"{text} "
            "다음 중 가장 적절한 것은 무엇인가?"
        )

    if question_type == "essay":
        return (
            f"{text} "
            "이 상황을 어떻게 설명할 수 있는지 핵심 근거를 포함하여 서술하시오."
        )

    return (
        f"{text} "
        "요구사항을 만족하는 해결 방법을 작성하시오."
    )

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
            q["body"] = _ensure_question_body_ends_with_question(
                body=str(body),
                question_type=question_type,
                difficulty=difficulty,
            )
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

            explanation_answer = _extract_answer_number_from_explanation(str(explanation))

            if explanation_answer is not None and explanation_answer != answer_int:
                logger.warning(
                    f"문제 품질 경고: index={idx}, reason=explanation_answer_mismatch, "
                    f"answer={answer_int}, explanation_answer={explanation_answer}"
                )
                quality_warnings.append(
                    f"해설의 정답 번호({explanation_answer})와 answer({answer_int})가 달라 자동 수정했습니다."
                )
                q["explanation"] = _replace_answer_number_in_explanation(
                    str(explanation),
                    answer_int,
                )

            if _has_explanation_contradiction(str(q.get("explanation", explanation)), answer_int):
                logger.warning(f"문제 품질 경고: index={idx}, reason=explanation_contradiction")
                quality_warnings.append(
                    "해설에서 정답이 아닌 선택지를 긍정적으로 설명했을 가능성이 있습니다."
                )

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

            if _has_numbered_distractor_explanation(str(q.get("explanation", explanation))):
                logger.warning(
                    f"문제 품질 경고: index={idx}, reason=numbered_distractor_explanation"
                )
                quality_warnings.append(
                    "해설에서 오답을 번호 기준으로 설명하고 있어 선택지 재배치 후 불일치 가능성이 있습니다."
                )

            # ─────────────────────────────────────────────
            # find_incorrect 유형 전용 검증
            # ─────────────────────────────────────────────
            answer_style = str(q.get("answer_style", "")).strip()
            if answer_style == "find_incorrect":
                body_str = str(body or "").strip()
                explanation_str = str(q.get("explanation", explanation) or "").strip()

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
                    "틀", "잘못", "부적절", "옳지 않", "incorrect", "false", "아니다", "아닙니다",
                    "오해", "혼동", "오류",
                ]
                if not any(m in explanation_str for m in explanation_correct_markers):
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

            q["answer"] = str(answer)
            q["explanation"] = _remove_answer_number_from_explanation(str(explanation))

        q["difficulty"] = difficulty
        q["score"] = score

        if not isinstance(q.get("competency_tags"), list):
            q["competency_tags"] = []

        validated.append(q)

    logger.info(f"문제 검증 결과: input={len(questions)}, validated={len(validated)}")

    return validated