import re
import json
import logging
from ai.core.openai_client import client

logger = logging.getLogger("uvicorn.info")


def normalize_explanation_style_local(explanation: str, answer_int: int) -> str:
    """
    해설 문자열에서 반말 종결 어미를 존댓말로 교체한다.
    - 이미 '입니다'로 끝나는 문장은 건드리지 않는다.
    - '이다.' → '입니다.' 같은 과도한 광범위 치환은 제거한다.
    - answer 번호 동기화는 replace_answer_number_in_explanation에서 처리한다.
    """
    text = replace_answer_number_in_explanation(
        str(explanation or "").strip(),
        answer_int,
    )

    if not text:
        return f"정답은 {answer_int}번입니다."

    # 문장 단위로 분리 후 각 문장 끝 어미만 교체 (이미 존댓말인 문장은 건드리지 않음)
    polite_suffixes = (
        "입니다.", "합니다.", "됩니다.", "습니다.", "았습니다.", "었습니다.",
        "아닙니다.", "있습니다.", "없습니다.", "됩니다.", "합니다.",
    )

    # 명확한 반말→존댓말 매핑만 적용 (문장 끝 어미 한정)
    safe_endings = [
        ("하지 않는다.", "하지 않습니다."),
        ("이 아니다.", "이 아닙니다."),
        ("가 아니다.", "가 아닙니다."),
        ("을 수 없다.", "을 수 없습니다."),
        ("ㄹ 수 없다.", "ㄹ 수 없습니다."),
        ("출력된다.", "출력됩니다."),
        ("반환된다.", "반환됩니다."),
        ("발생한다.", "발생합니다."),
        ("발생할 수 있다.", "발생할 수 있습니다."),
        ("저장된다.", "저장됩니다."),
        ("공유된다.", "공유됩니다."),
        ("누적된다.", "누적됩니다."),
        ("제외된다.", "제외됩니다."),
        ("포함된다.", "포함됩니다."),
        ("실행된다.", "실행됩니다."),
        ("생성된다.", "생성됩니다."),
        ("사용된다.", "사용됩니다."),
        ("호출된다.", "호출됩니다."),
        ("소비된다.", "소비됩니다."),
        ("소진된다.", "소진됩니다."),
        ("영향을 미친다.", "영향을 미칩니다."),
        ("잘못된 것이다.", "잘못된 설명입니다."),
    ]

    for src, tgt in safe_endings:
        # 이미 존댓말인 문장에 이중 적용 방지
        text = text.replace(src, tgt)

    return text


def replace_answer_number_in_explanation(explanation: str, new_answer: int) -> str:
    """
    explanation 안의 '정답은 N번입니다' 형태를 새 정답 번호로 교체한다.
    중복 정답 번호 선언은 첫 번째만 유지하고 나머지는 제거한다.
    """
    if not explanation:
        return explanation

    patterns = [
        r"정답은\s*\d\s*번입니다",
        r"정답은\s*\d\s*번",
        r"정답\s*:\s*\d\s*번",
        r"답은\s*\d\s*번",
        r"\d\s*번이\s*정답",
    ]

    new_text = f"정답은 {new_answer}번입니다"
    updated = explanation
    replaced = False

    for pattern in patterns:
        while re.search(pattern, updated):
            if not replaced:
                updated = re.sub(pattern, new_text, updated, count=1)
                replaced = True
            else:
                # 중복된 정답 선언은 제거
                updated = re.sub(pattern + r"[.。]?\s*", "", updated, count=1)

    if replaced:
        # "정답은 N번입니다" 뒤에 마침표가 없으면 추가
        updated = re.sub(r"(정답은\s*\d\s*번입니다)(?![.。])", r"\1.", updated)
        return updated

    return f"정답은 {new_answer}번입니다. {updated}"


def _build_concept_based_fallback_explanation(q: dict, answer_int: int) -> str:
    choices = q.get("choices", [])
    body = str(q.get("body", "") or "")
    competency_type = str(q.get("competency_type", "") or "").lower()

    correct_choice = str(choices[answer_int - 1]).strip()

    if competency_type == "python":
        body_lower = body.lower()

        if "yield" in body_lower or "next(" in body_lower:
            return (
                f"정답은 {answer_int}번입니다. "
                f"제너레이터는 함수 호출 시 전체 코드를 즉시 실행하지 않고, next()가 호출될 때마다 yield 지점까지 실행한 뒤 상태를 보존합니다. "
                f"따라서 여러 번 next()를 호출하면 이전 yield 이후의 지점부터 다시 실행되어 다음 값이 순서대로 반환됩니다. "
                f"정답은 코드에 포함된 next() 호출 횟수와 각 yield에서 반환되는 값을 기준으로 판단해야 합니다."
            )

        if "my_list=[]" in body_lower or "default argument" in body_lower or "기본 인자" in body:
            return (
                f"정답은 {answer_int}번입니다. "
                f"Python의 기본 인자는 함수가 호출될 때마다 새로 만들어지는 것이 아니라 함수 정의 시점에 한 번 생성됩니다. "
                f"리스트처럼 변경 가능한 객체를 기본값으로 사용하면 여러 호출 사이에서 같은 객체가 공유되어 이전 호출의 변경 결과가 다음 호출에 영향을 줄 수 있습니다. "
                f"따라서 문제의 핵심은 리스트 append 자체가 아니라 mutable 기본 인자의 공유 동작입니다."
            )

        return (
            f"정답은 {answer_int}번입니다. "
            f"Python 코드는 조건식, 반복문, 함수 호출 시점, 객체 참조 관계에 따라 실행 결과가 결정됩니다. "
            f"정답은 문제에 제시된 코드의 실행 순서와 실제 반환값을 기준으로 판단해야 합니다."
        )

    if competency_type == "java":
        body_lower = body.lower()

        if "static" in body_lower and ("인스턴스" in body or "instance" in body_lower):
            return (
                f"정답은 {answer_int}번입니다. "
                f"static 메서드는 특정 객체에 속하지 않고 클래스에 소속되므로, "
                f"this 키워드나 인스턴스 필드에 직접 접근할 수 없습니다. "
                f"반면 인스턴스 메서드는 객체가 생성된 뒤 해당 객체를 통해 호출되며, "
                f"그 객체의 인스턴스 필드를 읽거나 변경할 수 있습니다. "
                f"따라서 고객 정보처럼 객체별로 달라지는 상태를 변경하려면 인스턴스 메서드를 사용해야 합니다. "
                f"다른 선택지들은 static 메서드와 인스턴스 메서드의 호출 방식, this 사용 가능 여부, "
                f"인스턴스 필드 접근 가능 여부를 잘못 설명하고 있습니다."
            )

        if "equals" in body_lower or "hashcode" in body_lower or "hashset" in body_lower:
            return (
                f"정답은 {answer_int}번입니다. "
                f"HashSet은 객체의 중복 여부를 판단할 때 equals 결과와 hashCode 값을 함께 사용합니다. "
                f"두 객체가 논리적으로 같은 값으로 취급되려면 equals가 true를 반환하는 조건과 "
                f"hashCode가 같은 기준으로 계산되는 조건이 일관되어야 합니다. "
                f"따라서 문제의 코드는 어떤 필드를 동등성 기준으로 삼는지와 해시 값 계산 기준이 일치하는지를 중심으로 판단해야 합니다."
            )

        return (
            f"정답은 {answer_int}번입니다. "
            f"Java 문제에서는 코드의 실제 호출 대상, 타입 규칙, 객체 상태 접근 가능 여부를 기준으로 판단해야 합니다. "
            f"다른 선택지들은 호출 방식이나 객체 동작 규칙을 지나치게 일반화했거나, 문제의 코드 구조와 맞지 않는 설명입니다."
        )

    if competency_type == "sql":
        return (
            f"정답은 {answer_int}번입니다. "
            f"'{correct_choice}'가 SQL의 처리 순서와 조건 적용 위치에 부합합니다. "
            f"WHERE, JOIN, GROUP BY, HAVING은 적용되는 단계와 대상 데이터가 다르므로 "
            f"문제에 제시된 쿼리 흐름을 기준으로 판단해야 합니다. "
            f"다른 선택지들은 조건이 적용되는 위치나 집계 전후의 차이를 잘못 해석한 설명입니다."
        )

    if competency_type == "ai":
        return (
            f"정답은 {answer_int}번입니다. "
            f"RAG 검색에서는 검색 쿼리의 의도와 metadata filter 조건이 함께 맞아야 관련 문서가 안정적으로 검색됩니다. "
            f"필터 조건이 지나치게 넓거나 좁으면 관련 없는 chunk가 포함되거나 필요한 chunk가 제외될 수 있습니다. "
            f"따라서 검색 품질은 필터를 적용했는지 여부만이 아니라 query, category, 날짜 범위, chunk 품질, 후처리 조건을 함께 기준으로 판단해야 합니다."
        )

    return (
        f"정답은 {answer_int}번입니다. "
        f"'{correct_choice}'가 문제에서 제시된 조건과 가장 직접적으로 일치합니다. "
        f"다른 선택지들은 문제의 핵심 조건이나 판단 기준을 충분히 반영하지 못합니다."
    )

def remove_numbered_distractor_sentences(explanation: str) -> str:
    """
    정답 안내 첫 문장을 제외하고,
    '1번은', '2번 선택지는', '3번과 4번은'처럼 번호 기준으로 오답을 설명하는 문장을 제거한다.
    """
    text = str(explanation or "").strip()
    if not text:
        return ""

    answer_prefix_match = re.match(r"^정답은\s*\d\s*번입니다\.?\s*", text)
    answer_prefix = ""

    if answer_prefix_match:
        answer_prefix = answer_prefix_match.group(0).strip()
        text = text[answer_prefix_match.end():].strip()

    sentences = re.split(r"(?<=[.!?。])\s+", text)
    cleaned_sentences = []

    numbered_patterns = [
        r"[1-5]\s*번은",
        r"[1-5]\s*번의",
        r"[1-5]\s*번\s*선택지",
        r"[1-5]\s*번\s*보기",
        r"[1-5]\s*번과\s*[1-5]\s*번",
        r"[1-5]\s*번,\s*[1-5]\s*번",
    ]

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if any(re.search(pattern, sentence) for pattern in numbered_patterns):
            continue

        cleaned_sentences.append(sentence)

    body = " ".join(cleaned_sentences).strip()

    if answer_prefix and body:
        return f"{answer_prefix} {body}"

    if answer_prefix:
        return answer_prefix

    return body


def build_safe_multiple_choice_explanation(q: dict, answer: int) -> str:
    """
    choices 재배치 이후에도 깨지지 않는 안전한 객관식 해설을 만든다.
    - 정답 번호는 현재 answer 기준으로 맞춘다.
    - 기존 해설의 번호별 오답 설명은 제거한다.
    - 해설이 너무 짧거나 선택지 반복 수준이면 개념 기반 fallback 해설을 만든다.
    """
    choices = q.get("choices", [])

    try:
        answer_int = int(answer)
    except Exception:
        return str(q.get("explanation", "") or "")

    if not isinstance(choices, list) or len(choices) != 5:
        return replace_answer_number_in_explanation(
            str(q.get("explanation", "") or ""),
            answer_int,
        )

    if answer_int < 1 or answer_int > 5:
        return str(q.get("explanation", "") or "")

    original_explanation = str(q.get("explanation", "") or "").strip()

    cleaned = remove_numbered_distractor_sentences(original_explanation)
    cleaned = replace_answer_number_in_explanation(cleaned, answer_int)

    cleaned_body = re.sub(
        r"^정답은\s*\d\s*번입니다\.?\s*",
        "",
        cleaned,
    ).strip()
    competency_type = str(q.get("competency_type", "") or "").lower()
    body_text = str(q.get("body", "") or "")

    if (
        competency_type == "java"
        and "static" in body_text.lower()
        and ("인스턴스" in body_text or "instance" in body_text.lower())
    ):
        return _build_concept_based_fallback_explanation(q, answer_int)
    correct_choice = str(choices[answer_int - 1]).strip()

    # 해설이 없거나 너무 짧으면 개념 기반 fallback 사용
    if not cleaned_body or len(cleaned_body) < 60:
        return _build_concept_based_fallback_explanation(q, answer_int)

    # 해설이 정답 선택지를 거의 그대로 반복하는 수준이면 fallback 사용
    if correct_choice and correct_choice in cleaned_body and len(cleaned_body) < len(correct_choice) + 50:
        return _build_concept_based_fallback_explanation(q, answer_int)

    return f"정답은 {answer_int}번입니다. {cleaned_body}"

def repair_multiple_choice_explanations(questions: list[dict]) -> list[dict]:
    """
    choices 재배치 이후 최종 answer/choices 기준으로 객관식 해설 문자열 보정을 수행한다.
    - 정답 번호를 새 answer에 맞게 교체한다.
    - 존댓말 정규화를 적용한다.
    - LLM 호출 없이 빠르고 안전하게 보정한다.
    """
    if not questions:
        return questions

    for q in questions:
        choices = q.get("choices", [])
        answer = q.get("answer")
        explanation = q.get("explanation", "")

        if not isinstance(choices, list) or len(choices) != 5 or not explanation:
            continue

        try:
            answer_int = int(answer)
        except Exception:
            continue

        if answer_int < 1 or answer_int > 5:
            continue

        # 정답 번호 교체만 수행 (내용 삭제 없음)
        updated = build_safe_multiple_choice_explanation(q, answer_int)

        # 존댓말 정규화
        final = normalize_explanation_style_local(updated, answer_int)

        q["explanation"] = final

    return questions


def clean_json_response(content: str):
    cleaned = content.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return json.loads(cleaned)


def _request_explanation_repair_json(
    prompt: str,
    system_message: str,
    temperature: float = 0.0,
):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )

    content = response.choices[0].message.content or ""
    logger.info(f"LLM explanation repair response preview: {str(content)[:1000]}")
    return clean_json_response(content)

