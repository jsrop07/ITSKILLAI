import re
import json
import time
import random
import logging
from ai.client import client
from collections import Counter
from ai.services.question_planner import generate_question_plans

logger = logging.getLogger("uvicorn.info")

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
    설명하는 경우 복수정답 가능성이 있으므로 폐기한다.
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
    단, 여기서는 문제를 폐기하지 않고 quality warning 용도로만 사용한다.
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

    # "단순히", "삭제한다"는 너무 자주 걸리므로 일단 hard warning에서 제외
    # 나중에 question_reviewer.py에서 quality_score 감점 항목으로 처리하는 것이 좋다.

    found: list[str] = []

    for choice in choices:
        choice_text = str(choice)

        for pattern in weak_patterns:
            if pattern in choice_text:
                found.append(f"'{pattern}' 포함 선택지: {choice_text}")

    return found

def _find_hard_choice_quality_errors(q: dict, difficulty: str) -> list[str]:
    """
    객관식 선택지 품질이 너무 낮은 경우 문제를 폐기하기 위한 hard error 검사.
    특히 고급 문제에서 정답만 길고 오답이 짧거나,
    오답이 누가 봐도 틀린 일반론이면 폐기한다.
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

    # 1) 정답만 과도하게 긴 경우
    if len(correct_choice) > avg_wrong_len * 1.35:
        errors.append(
            "정답 선택지만 다른 오답보다 과도하게 길어 정답이 노출됩니다."
        )

    # 2) 선택지 길이 편차가 너무 큰 경우
    if min_len > 0 and max_len / min_len >= 2.0:
        errors.append(
            "선택지 간 길이 편차가 너무 커서 정답 추측 가능성이 높습니다."
        )

    # 3) 고급 문제인데 너무 짧은 일반론 선택지가 있는 경우
    too_short_choices = [
        choice for choice in choices
        if len(str(choice).strip()) < 22
    ]

    if too_short_choices:
        errors.append(
            f"고급 문제에 너무 짧은 선택지가 포함되어 있습니다: {too_short_choices}"
        )

    # 4) 너무 쉽게 제거되는 DB/성능 튜닝 오답 패턴
    hard_weak_patterns = [
        "무조건",
        "항상",
        "오직",
        "모든 컬럼",
        "모든 조건",
        "모든 조인",
        "모든 테이블",
        "인덱스를 제거",
        "인덱스를 삭제",
        "쿼리를 단순화",
        "조인 순서를 무조건",
        "조인 순서를 수동으로 고정",
        "인덱스를 추가하여 모든",
        "성능을 높인다",
        "성능을 개선한다",
        "쓰기 작업의 성능을 높인다",
    ]

    for choice in choices:
        choice_text = str(choice)

        for pattern in hard_weak_patterns:
            if pattern in choice_text:
                errors.append(
                    f"너무 쉽게 제거되는 선택지 표현이 포함되어 있습니다: '{pattern}' / {choice_text}"
                )

    # 5) 정답만 '고려/평가/종합' 구조이고 오답은 단순 조치인 경우
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

    # 첫 문장의 정답 번호 표현은 제거하고 검사
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

def _get_target_answer_positions(count: int) -> list[int]:
    """
    객관식 정답 위치를 랜덤으로 배치하되,
    1,2번에만 몰리거나 특정 번호에 과도하게 몰리는 것을 방지한다.

    예:
    - count=3: [1, 4, 2], [3, 3, 5], [2, 5, 4] 가능
    - count=5: [1, 2, 5, 3, 4], [3, 3, 4, 5, 2] 가능
    """
    if count <= 0:
        return []

    if count == 1:
        return [random.randint(1, 5)]

    def is_valid_positions(positions: list[int]) -> bool:
        counter = Counter(positions)
        unique_count = len(counter)
        max_repeat = max(counter.values())

        # 1,2번에만 몰리는 패턴 방지
        if set(positions).issubset({1, 2}):
            return False

        # 전부 같은 번호 방지
        if unique_count == 1:
            return False

        if count == 2:
            return unique_count == 2

        if count == 3:
            # 예: [3,3,4] 허용, [1,1,1] 금지, [1,2,1] 금지
            return unique_count >= 2 and max_repeat <= 2

        if count == 4:
            # 최소 3개 번호는 섞이게 함
            return unique_count >= 3 and max_repeat <= 2

        if count == 5:
            # 예: [3,3,4,5,2] 허용, [1,1,1,2,2] 방지
            return unique_count >= 4 and max_repeat <= 2

        # 6개 이상 생성 시에도 특정 번호 과반 쏠림 방지
        return unique_count >= 4 and max_repeat <= max(2, (count // 2))

    for _ in range(100):
        positions = [random.randint(1, 5) for _ in range(count)]
        if is_valid_positions(positions):
            return positions

    # 혹시 100번 안에 적절한 패턴을 못 찾으면 안전하게 셔플 기반으로 생성
    fallback = []
    while len(fallback) < count:
        bag = [1, 2, 3, 4, 5]
        random.shuffle(bag)
        fallback.extend(bag)

    return fallback[:count]

def _rebalance_answer_positions(questions: list[dict], question_type: str) -> list[dict]:
    """
    객관식 문제의 정답 위치가 1,2번에 몰리지 않도록 choices 순서를 코드에서 재배치한다.
    - 정답 텍스트는 유지한다.
    - choices 배열 순서만 바꾼다.
    - answer 번호와 explanation의 정답 번호를 함께 수정한다.
    """
    if question_type != "multiple_choice":
        return questions

    if not questions:
        return questions

    target_positions = _get_target_answer_positions(len(questions))

    rebalanced = []

    for idx, q in enumerate(questions):
        choices = q.get("choices", [])
        answer = q.get("answer")

        if not isinstance(choices, list) or len(choices) != 5:
            rebalanced.append(q)
            continue

        try:
            current_answer = int(answer)
        except Exception:
            rebalanced.append(q)
            continue

        if current_answer < 1 or current_answer > 5:
            rebalanced.append(q)
            continue

        correct_choice = choices[current_answer - 1]
        wrong_choices = [
            choice for i, choice in enumerate(choices)
            if i != current_answer - 1
        ]

        target_answer = target_positions[idx % len(target_positions)]

        # 오답 순서는 매번 조금씩 섞어서 보기 패턴이 고정되지 않게 한다.
        random.shuffle(wrong_choices)

        new_choices = []
        wrong_index = 0

        for position in range(1, 6):
            if position == target_answer:
                new_choices.append(correct_choice)
            else:
                new_choices.append(wrong_choices[wrong_index])
                wrong_index += 1

        q["choices"] = new_choices
        q["answer"] = target_answer
        q["explanation"] = _replace_answer_number_in_explanation(
            str(q.get("explanation", "")),
            target_answer,
        )

        rebalanced.append(q)

    return rebalanced

def _repair_multiple_choice_explanations(questions: list[dict]) -> list[dict]:
    """
    choices 재배치 이후 최종 answer/choices 기준으로 객관식 해설만 다시 생성한다.
    """
    if not questions:
        return questions

    repair_targets = []

    for idx, q in enumerate(questions):
        choices = q.get("choices", [])
        answer = q.get("answer")

        if not isinstance(choices, list) or len(choices) != 5:
            continue

        try:
            answer_int = int(answer)
        except Exception:
            continue

        if answer_int < 1 or answer_int > 5:
            continue

        repair_targets.append({
            "index": idx,
            "title": q.get("title", ""),
            "body": q.get("body", ""),
            "choices": choices,
            "answer": answer_int,
            "correct_choice": choices[answer_int - 1],
        })

    if not repair_targets:
        return questions

    prompt = f"""
    너는 IT 역량진단 문제은행의 객관식 해설 검수자다.

    아래 문제들의 title, body, choices, answer는 이미 확정되어 있다.
    choices 순서와 answer 번호를 절대 바꾸지 마라.
    explanation만 다시 작성해라.

    반드시 JSON 배열만 출력해라.
    각 객체는 index, explanation 필드만 가진다.

    [해설 작성 규칙]
    - explanation은 반드시 "정답은 N번입니다."로 시작한다.
    - N은 주어진 answer 값과 반드시 같아야 한다.
    - 정답 선택지가 왜 맞는지 구체적으로 설명한다.
    - 오답 선택지들도 왜 부적절한지 설명하되, 번호가 아니라 선택지의 핵심 조치 내용 기준으로 설명한다.
    - 단순히 "다른 선택지는 관련이 없습니다"처럼 뭉뚱그려 쓰지 마라.
    - 오답 설명은 선택지의 핵심 내용 기준으로 설명한다.
    - 정답 번호는 첫 문장 "정답은 N번입니다."에서만 사용한다.
    - 그 이후 문장에서는 "1번은", "2번은", "3번은", "4번은", "5번은" 같은 표현을 절대 사용하지 마라.
    - "1번 선택지", "2번 보기", "3번의 방식" 같은 번호 기준 표현도 사용하지 마라.
    - 오답은 반드시 선택지의 핵심 개념이나 조치 내용 기준으로 설명한다.
    - 예: "인덱스를 삭제하는 방식은 쓰기 부하는 줄일 수 있지만 조회 성능 저하 원인을 악화시킬 수 있다."
    - 예: "단일 인덱스 추가는 일부 조회에는 도움이 될 수 있으나 조인 조건, 정렬 조건, 쓰기 부하를 함께 고려하지 못한다."
    - 문제 본문 상황과 직접 연결해서 설명한다.
    - 문서에 없는 새로운 기술명, 수치, 도구명, 절차를 추가하지 마라.
    - 해설은 3~6문장 정도로 작성한다.
    - 정답이 아닌 선택지를 "정확하다", "올바르다", "맞다", "타당하다", "적절하다"라고 설명하지 마라.
    - 오답 설명은 반드시 왜 정답 기준에 미치지 못하는지 설명해야 한다.
    - 만약 선택지 중 정답으로도 해석될 수 있는 보기가 있으면 explanation을 작성하지 말고 해당 index의 explanation에 "검증 실패: 복수정답 가능성"이라고 작성한다.

    [출력 예시]
    [
      {{
        "index": 0,
        "explanation": "정답은 3번입니다. ..."
      }}
    ]

    [문제 목록]
    {json.dumps(repair_targets, ensure_ascii=False)}
    """

    try:
        repaired = _request_llm_json(
            prompt=prompt,
            system_message="너는 IT 역량진단 문제은행의 객관식 해설 검수자다. 반드시 유효한 JSON 배열만 출력한다.",
            temperature=0.0,
        )

        if not isinstance(repaired, list):
            return questions

        for item in repaired:
            if not isinstance(item, dict):
                continue

            idx = item.get("index")
            explanation = item.get("explanation")

            if idx is None or explanation is None:
                continue

            try:
                idx = int(idx)
            except Exception:
                continue

            if idx < 0 or idx >= len(questions):
                continue

            questions[idx]["explanation"] = str(explanation)

        return questions

    except Exception as e:
        logger.warning(f"객관식 해설 재생성 실패: {str(e)}")
        return questions

def _validate_questions(questions: list, question_type: str, difficulty: str, score: int):
    if not isinstance(questions, list):
        raise ValueError("AI 응답이 JSON 배열이 아닙니다.")

    validated = []

    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            logger.warning(f"문제 검증 제외: index={idx}, reason=not_dict")
            continue

        title = q.get("title")
        body = q.get("body")
        choices = q.get("choices")
        answer = q.get("answer")
        explanation = q.get("explanation")

        if not title or not body or explanation is None:
            logger.warning(f"문제 검증 제외: index={idx}, reason=missing_required_fields")
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

            quality_warnings = []

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
                quality_warnings.extend(hard_choice_errors)

            if _has_numbered_distractor_explanation(str(q.get("explanation", explanation))):
                logger.warning(
                    f"문제 품질 경고: index={idx}, reason=numbered_distractor_explanation"
                )
                quality_warnings.append(
                    "해설에서 오답을 번호 기준으로 설명하고 있어 선택지 재배치 후 불일치 가능성이 있습니다."
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



def _clean_json_response(content: str):
    cleaned = content.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return json.loads(cleaned)

def _request_llm_json(prompt: str, system_message: str, temperature: float = 0.1):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
    )

    content = response.choices[0].message.content
    logger.info(f"LLM raw response preview: {str(content)[:1000]}")
    return _clean_json_response(content)

def _generate_with_retry(
    prompt: str,
    system_message: str,
    question_type: str,
    difficulty: str,
    score: int,
    temperature: float = 0.1,
    max_retries: int = 0,
):
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            questions = _request_llm_json(
                prompt=prompt,
                system_message=system_message,
                temperature=temperature,
            )

            validated_questions = _validate_questions(
                questions,
                question_type,
                difficulty,
                score,
            )
            logger.info(
                f"LLM 원본 문제 생성 수: {len(questions) if isinstance(questions, list) else 'not_list'}"
            )

            if len(validated_questions) == 0:
                raise ValueError("검증을 통과한 문제가 없습니다.")

            validated_questions = _rebalance_answer_positions(
                validated_questions,
                question_type,
            )

            if _has_answer_position_bias(validated_questions, question_type):
                logger.warning("정답 번호 편향 경고: 정답 번호가 한쪽으로 몰릴 가능성이 있습니다.")

            # 임시 안정화:
            # choices 재배치 후 해설 재생성은 추가 LLM 호출을 발생시키고,
            # 다시 검증 실패를 유발할 수 있으므로 리팩토링 전까지 비활성화한다.
            #
            # if question_type == "multiple_choice":
            #     validated_questions = _repair_multiple_choice_explanations(validated_questions)
            #     validated_questions = _validate_questions(
            #         validated_questions,
            #         question_type,
            #         difficulty,
            #         score,
            #     )
            #
            #     if len(validated_questions) == 0:
            #         raise ValueError("해설 재생성 후 검증을 통과한 문제가 없습니다.")

            return validated_questions
            
        except Exception as e:
            last_error = e
            logger.warning(
                f"LLM 문제 생성 재시도 필요: attempt={attempt + 1}/{max_retries + 1}, error={str(e)}"
            )

    raise ValueError(f"AI 문제 생성 검증 실패: {str(last_error)}")


def _difficulty_rule(difficulty: str) -> str:
    if difficulty == "초급":
        return """
        [초급 난이도 출제 기준]
        - 개념 정의, 기본 용어, 기본 구분, 단순 동작 원리를 평가한다.
        - 문제 본문은 짧고 명확하게 작성한다.
        - 복잡한 실무 상황, 장애 분석, 우선순위 판단, 리스크 분석 문제는 출제하지 않는다.
        - 정답은 학습자가 기본 개념을 알고 있으면 명확히 고를 수 있어야 한다.
        - 단, 너무 뻔한 상식 문제나 말장난 문제는 금지한다.
        """

    if difficulty == "중급":
        return """
        [중급 난이도 출제 기준]
        - 단순 정의 암기 문제를 금지한다.
        - "무엇인가?", "어떤 요소인가?", "올바른 설명은?"처럼 개념만 묻는 문제를 반복하지 않는다.
        - 반드시 짧은 실무 상황을 제시한다.
        - 세부 주제의 개념을 실제 상황에 적용하거나 비교, 분류, 원인 판단, 검토 기준 선택을 요구한다.
        - 보기들은 모두 선택된 역량 유형과 같은 업무 맥락 안에서 그럴듯하게 작성한다.
        - 정답은 하나만 명확해야 하지만, 오답도 실무자가 헷갈릴 수 있는 수준으로 작성한다.
        - 초급 수준의 용어 정의 문제는 생성하지 않는다.
        """

    return """
        [고급 난이도 출제 기준]
        - 단순 정의형, 용어 암기형, 항목 나열형 문제를 금지한다.
        - "무엇인가?", "어떤 요소가 포함되어야 하는가?", "올바른 설명은?" 형태의 문제를 금지한다.
        - 반드시 실무 상황을 포함한다.
        - 문제 본문은 최소 3문장 이상으로 작성한다.
        - 문제 본문에는 반드시 다음 중 3개 이상을 포함한다:
        1) 현재 시스템/업무 상황
        2) 발생한 문제 또는 증상
        3) 제약 조건
        4) 잘못된 판단으로 인한 리스크
        5) 선택해야 할 대응 방향
        - 세부 주제와 관련된 원인, 영향, 리스크, 우선순위, 대응 방안, 트레이드오프를 판단하게 한다.
        - 보기들은 모두 그럴듯해야 하며, 정답은 문제 상황에서 가장 우선적으로 선택해야 하는 판단 또는 대응이어야 한다.
        - 오답은 완전히 엉뚱한 내용이 아니라, 관련은 있지만 우선순위가 낮거나 문제 상황의 핵심 원인을 해결하지 못하는 선택지로 작성한다.
        - 정답은 선택된 역량 유형과 세부 주제에 직접 연결되어야 한다.
        - 해설에는 정답이 가장 적절한 이유와 주요 오답이 왜 우선순위가 낮거나 문제 상황과 직접 맞지 않는지 포함한다.

        [고급 문제 금지 패턴]
        - "가장 중요한 요소는 무엇인가요?"
        - "가장 적절한 자료구조는 무엇인가요?"
        - "어떤 조치를 취해야 하나요?"
        - "무엇을 고려해야 하나요?"
        - "어떤 컬럼에 인덱스를 추가해야 하나요?"
        위와 같은 질문은 구체적인 조건, 제약, 증상 없이 단독으로 사용하지 않는다.

        [고급 선택지 작성 규칙]
        - 선택지는 단어 하나 또는 짧은 명사구로 작성하지 않는다.
        - 선택지는 모두 구체적인 판단 또는 대응 문장으로 작성한다.
        - 예: "인덱스를 추가한다"처럼 짧게 쓰지 말고, "WHERE 동등 조건과 ORDER BY 조건을 함께 만족하도록 복합 인덱스를 설계한다"처럼 작성한다.
        - 예: "해시 테이블"처럼 단어만 쓰지 말고, "중복 여부 조회가 반복되므로 평균 O(1) 조회가 가능한 해시 기반 구조를 사용한다"처럼 작성한다.
        """

def _competency_rule(competency_type: str | None, topic: str) -> str:
    """
    역량 유형별 출제 방향을 정의한다.
    일반 생성과 RAG 생성에서 모두 사용한다.
    """
    if not competency_type:
        return """
        [역량 유형별 출제 규칙]
        - 선택된 역량 유형이 없으므로 세부 주제에 맞는 IT 문제를 생성한다.
        - 세부 주제와 무관한 기술 영역으로 확장하지 않는다.
        """

    rules = {
        "programming": """
        [프로그래밍 역량 출제 규칙]
        - 변수, 자료형, 조건문, 반복문, 함수, 예외 처리, 객체지향, 코드 실행 흐름을 중심으로 출제한다.
        - 중급 이상은 단순 문법 정의가 아니라 코드 실행 결과, 버그 원인, 예외 상황, 리팩토링 판단을 묻는다.
        - 고급은 메모리 사용, 예외 처리 전략, 모듈화, 유지보수성, 성능 영향, 테스트 용이성을 판단하게 한다.
        - 특정 언어가 topic에 명시되지 않으면 특정 언어의 세부 API를 임의로 만들지 않는다.
        - 고급 문제는 반드시 짧은 코드 조각, 오류 상황, 유지보수 문제, 성능 병목 중 하나를 포함한다.
        - "가장 좋은 코드"처럼 기준이 모호한 문제는 만들지 말고, 조건과 제약을 명확히 제시한다.
        """,

        "data_structure_algorithm": """
        [자료구조/알고리즘 역량 출제 규칙]
        - 배열, 리스트, 스택, 큐, 해시, 트리, 그래프, 정렬, 탐색, 재귀, BFS/DFS, 시간복잡도, 공간복잡도를 중심으로 출제한다.
        - 중급 이상은 단순 정의가 아니라 주어진 상황에 적절한 자료구조 선택, 시간복잡도 판단, 알고리즘 흐름 추론을 묻는다.
        - 고급은 입력 크기, 성능 제약, 최악/평균 시간복잡도, 공간복잡도, 자료구조 선택의 트레이드오프를 판단하게 한다.
        - 인공지능, RAG, LLM 같은 주제로 벗어나지 않는다.

        [자료구조/알고리즘 고급 문제 강제 규칙]
        - 고급 문제는 반드시 입력 크기 N, 연산 빈도, 조회/삽입/삭제/정렬/탐색 패턴 중 2개 이상을 제시한다.
        - "O(N^2)을 개선하려면 어떤 자료구조?"처럼 원인이 불명확한 문제를 만들지 않는다.
        - "삽입과 삭제가 빈번하면 연결 리스트"처럼 일반론을 정답으로 만들지 않는다.
        - 자료구조 선택 문제는 반드시 어떤 연산이 자주 발생하는지 명시한다.
        - 해시 테이블, 트리, 배열, 연결 리스트 중 무엇이 정답인지는 문제의 연산 패턴과 제약 조건으로 판단 가능해야 한다.
        - 선택지는 "해시 테이블", "트리"처럼 단어만 쓰지 말고, 선택 이유가 포함된 문장으로 작성한다.
        - 평균 시간복잡도와 최악 시간복잡도가 다른 자료구조는 그 차이를 해설에 반영한다.

        [자료구조 선택 정답 조건]
        - 해시 테이블은 특정 키 기반의 동등 조회가 많고 정렬/범위 검색이 핵심이 아닐 때만 정답으로 사용한다.
        - 균형 트리는 정렬 상태 유지, 범위 검색, 삽입/삭제/조회 균형이 필요할 때 정답으로 사용한다.
        - 배열은 인덱스 기반 접근이 중요하고 중간 삽입/삭제가 적을 때만 정답으로 사용한다.
        - 연결 리스트는 위치를 이미 알고 있는 삽입/삭제가 많고 임의 조회가 중요하지 않을 때만 정답으로 사용한다.
        - B-트리는 디스크 기반 대용량 인덱싱, 범위 검색, 정렬된 탐색이 필요한 상황에서 사용한다.
        - 스택/큐는 LIFO/FIFO 처리 순서가 문제의 핵심일 때만 정답으로 사용한다.
        - “삽입과 삭제가 빈번하다”는 조건만으로 연결 리스트를 정답으로 만들지 않는다.
        - “O(N²)을 개선한다”는 조건만으로 해시 테이블이나 트리를 정답으로 만들지 않는다.
        """,

        "web_development": """
        [웹 개발 역량 출제 규칙]
        - HTTP, REST API, 상태 코드, 쿠키/세션, 인증 흐름, CORS, 프론트엔드 상태 관리, 라우팅, 비동기 통신, 웹 보안을 중심으로 출제한다.
        - 중급 이상은 단순 용어 정의가 아니라 요청/응답 흐름, 장애 원인, 프론트-백엔드 연동 문제, 보안상 주의점을 묻는다.
        - 고급은 인증/인가 설계, API 오류 처리, 성능 최적화, 캐싱, 배포 환경에서의 문제 해결을 판단하게 한다.
        - 고급 문제는 반드시 실제 증상, 예를 들어 401/403 혼동, CORS 오류, 세션 만료, 캐시 불일치, API 응답 지연 같은 상황을 포함한다.
        - HTTP 상태 코드 문제는 하나의 정답만 가능하도록 요청 결과와 실패 원인을 명확히 제시한다.
        """,

        "database": """
        [데이터베이스 역량 출제 규칙]
        - SQL, 정규화, 트랜잭션, 인덱스, 조인, 무결성, ERD, 격리 수준, 락, 성능 튜닝을 중심으로 출제한다.
        - 중급 이상은 단순 SQL 문법이 아니라 쿼리 결과 해석, 인덱스 적용 판단, 트랜잭션 문제 상황을 묻는다.
        - 고급은 동시성 문제, 정규화/반정규화 판단, 인덱스 설계, 장애 복구, 성능 병목 원인 분석을 포함한다.

        [데이터베이스 고급 문제 강제 규칙]
        - 고급 문제는 반드시 SQL 조건, 데이터 규모, 실행 빈도, 동시성, 락 대기, 실행 계획, 쓰기 부하 중 2개 이상을 포함한다.
        - 인덱스 문제는 "자주 검색되는 컬럼에 인덱스를 추가한다" 같은 일반론을 정답으로 만들지 않는다.
        - 복합 인덱스 문제는 WHERE, JOIN, ORDER BY, GROUP BY 조건 중 2개 이상을 제시한다.
        - 인덱스 선택지는 "인덱스를 추가한다"처럼 짧게 쓰지 말고, 어떤 컬럼 조합을 왜 선택하는지 드러나게 작성한다.
        - 복합 인덱스 순서는 항상 고정 규칙으로 단정하지 말고, 쿼리 패턴과 조건을 기준으로 판단하게 한다.
        - 쓰기 작업이 빈번한 테이블에서는 인덱스 추가의 조회 성능 이점과 쓰기 비용 증가를 함께 판단하게 한다.
        """,

        "os_network": """
        [운영체제/네트워크 역량 출제 규칙]
        - 프로세스, 스레드, 메모리, 스케줄링, 교착 상태, TCP/IP, DNS, HTTP, 라우팅, 포트, 패킷 흐름을 중심으로 출제한다.
        - 중급 이상은 단순 정의가 아니라 장애 상황, 통신 흐름, 병목 원인, 자원 관리 문제를 묻는다.
        - 고급은 동시성, 데드락, 네트워크 지연, 패킷 손실, 연결 문제, 시스템 자원 한계 상황을 판단하게 한다.
        - 고급 문제는 반드시 CPU 사용률, 메모리 부족, 스레드 경합, 연결 지연, DNS 실패, 타임아웃, 패킷 손실 중 하나의 증상을 포함한다.
        - TCP/UDP, 프로세스/스레드, 캐시/메모리처럼 비교 문제는 사용 상황을 제시하여 복수정답이 되지 않게 한다.
        """,

        "security": """
        [정보보안 역량 출제 규칙]
        - 인증, 인가, 암호화, 해시, 접근 제어, SQL Injection, XSS, CSRF, 취약점 대응, 로그/감사를 중심으로 출제한다.
        - 중급 이상은 공격 원리와 대응 방안, 보안 설정 누락, 권한 검증 문제를 상황 기반으로 묻는다.
        - 고급은 위협 모델링, 보안 설계 트레이드오프, 권한 분리, 데이터 보호, 사고 대응 우선순위를 판단하게 한다.
        - 고급 문제는 반드시 공격 시나리오, 취약한 코드/설정, 권한 우회, 로그 이상 징후, 개인정보 노출 위험 중 하나를 포함한다.
        - 인증과 인가 문제는 로그인 성공 여부와 자원 접근 권한 검증을 명확히 구분한다.
        - DAC, MAC, RBAC 같은 접근 제어 모델 문제는 선택지 중 두 개 이상이 올바른 정의가 되지 않도록 질문 기준을 좁힌다.
        """,

        "cloud_devops": """
        [클라우드/DevOps 역량 출제 규칙]
        - CI/CD, 컨테이너, Docker, 배포 전략, 모니터링, 로깅, 오토스케일링, 인프라 구성, 장애 대응을 중심으로 출제한다.
        - 중급 이상은 단순 도구 설명이 아니라 배포 실패 원인, 환경 변수 관리, 롤백, 모니터링 지표 해석을 묻는다.
        - 고급은 무중단 배포, 장애 격리, 확장성, 비용/성능 트레이드오프, 운영 자동화 전략을 판단하게 한다.
        - 고급 문제는 반드시 배포 실패 로그, 컨테이너 재시작, 헬스체크 실패, 트래픽 증가, 비용 증가, 롤백 필요 상황 중 하나를 포함한다.
        - 특정 클라우드 서비스명을 임의로 만들지 말고, topic에 명시된 경우에만 사용한다.
        - "무조건 스케일 아웃"처럼 비용과 운영 제약을 무시한 정답은 만들지 않는다.
        """,

        "ai_data": """
        [인공지능/데이터 역량 출제 규칙]
        - 데이터 전처리, 모델 평가, 과적합, 학습/검증 데이터 분리, 임베딩, RAG, LLM, 벡터 검색, 지표 해석을 중심으로 출제한다.
        - 중급 이상은 단순 개념 정의가 아니라 모델 성능 저하 원인, 데이터 품질 문제, 평가 지표 선택, 검색 품질 개선을 묻는다.
        - 고급은 hallucination 방지, RAG 검색 실패 원인, 임베딩/청킹 전략, precision/recall trade-off, 운영 환경의 모델 개선 전략을 판단하게 한다.

        [AI/Data 고급 문제 강제 규칙]
        - 고급 문제는 반드시 데이터 또는 검색 품질 문제가 발생한 상황을 포함한다.
        - RAG 문제는 chunk 크기, top_k, metadata filter, vector search, keyword search, reranking, context filtering 중 최소 2개 이상을 함께 다룬다.
        - "RAG에서 가장 중요한 요소는?"처럼 일반론 문제를 만들지 않는다.
        - "chunk 크기 조정 시 고려할 요소는?"처럼 단일 개념만 묻지 않는다.
        - 검색 정확도를 높이면 응답 시간이 증가하거나, chunk를 줄이면 문맥이 부족해지는 등 트레이드오프를 포함한다.
        - reranking은 사용자 피드백 반영으로 단정하지 말고, 검색 후보와 질의의 관련도를 재평가하는 과정으로 다룬다.
        - hallucination 문제는 문서 근거 부족, 잘못된 chunk 검색, context filtering 실패와 연결해 출제한다.
        - 선택지는 모두 운영상 선택 가능한 개선 전략으로 작성한다.

        [RAG 개선 전략별 정답 조건]
        - reranking은 후보 문서가 검색되었지만 순서나 관련도 평가가 부정확한 상황에서만 정답으로 사용한다.
        - metadata filter는 역량 유형, 문서 유형, 날짜, 출처 등 metadata가 존재하고 검색 범위를 줄여야 하는 상황에서만 정답으로 사용한다.
        - keyword search 또는 hybrid search는 벡터 검색이 정확한 용어, 코드, 약어, 고유명사를 놓치는 상황에서만 정답으로 사용한다.
        - chunk 크기 조정은 문맥이 너무 잘리거나 여러 주제가 한 chunk에 섞이는 상황에서만 정답으로 사용한다.
        - context filtering은 검색된 후보 중 답변 근거로 부적절한 chunk를 제거해야 하는 상황에서만 정답으로 사용한다.
        - top_k 증가는 후보 문서가 너무 적어 정답 근거가 누락되는 상황에서만 정답으로 사용한다.
        - 같은 생성 묶음 안에서 reranking을 정답으로 2회 이상 반복하지 않는다.
        """,

        "software_engineering": """
        [소프트웨어공학 역량 출제 규칙]
        - 요구사항 분석, 요구사항 확인, 설계, 테스트, 품질 속성, 형상관리, 변경관리, 유지보수, 검증/검토를 중심으로 출제한다.
        - 중급 이상은 단순 용어 정의가 아니라 요구사항 누락, 변경 영향, 검증 가능성, 품질 속성 판단을 묻는다.
        - 고급은 요구사항 충돌, 추적성 부족, 검증 실패, 품질 리스크, 변경 요청 증가 가능성을 분석하게 한다.
        - 고급 문제는 반드시 요구사항 누락, 이해관계자 충돌, 변경 요청 증가, 테스트 실패, 품질 속성 미정의, 추적성 부족 중 하나의 상황을 포함한다.
        - 요구사항 문제는 "명확성", "완전성", "일관성", "검증 가능성" 중 어떤 기준을 묻는지 상황에서 분명히 드러나야 한다.
        - 선택지들이 모두 검토 활동으로 맞는 말이 되지 않도록, 문제 상황에서 가장 우선되는 검토 기준을 명확히 제시한다.
        """,
    }

    base_rule = rules.get(competency_type, "")
    topic_rule = _topic_specific_rule(competency_type, topic)

    return f"""
    {base_rule}

    {topic_rule}
    """

def _topic_specific_rule(competency_type: str | None, topic: str) -> str:
    """
    특정 topic일 때만 적용하는 세부 출제 패턴.
    자주 쓰는 주제부터 점진적으로 추가한다.
    """
    topic_text = topic or ""

    if competency_type == "software_engineering" and "요구사항" in topic_text:
        return """
        [요구사항 관련 세부 출제 패턴]
        - 요구사항 목록의 완전성, 명확성, 일관성, 검증 가능성을 판단하게 한다.
        - 기능 요구사항과 비기능 요구사항의 구분 또는 누락 여부를 다룰 수 있다.
        - 요구사항 검토, 요구사항 명세서, 요구사항 검증 계획, 인수 테스트와 연결해 출제한다.
        - 중급/고급은 단순히 요구사항의 정의를 묻지 말고, 누락/변경/검증 실패 리스크를 판단하게 한다.
        """

    if competency_type == "database" and any(keyword in topic_text for keyword in ["인덱스", "index", "Index"]):
        return """
        [인덱스 세부 출제 패턴]
        - 인덱스가 조회 성능에 미치는 영향과 쓰기 성능, 저장 공간, 유지 비용을 함께 판단하게 한다.
        - 중급은 WHERE, JOIN, ORDER BY, GROUP BY에 사용되는 컬럼을 보고 적절한 인덱스 후보를 고르게 한다.
        - 고급은 실행 계획, 선택도, 복합 인덱스의 선행 컬럼, 범위 조건, 정렬 조건, 커버링 인덱스, 쓰기 부하를 함께 고려하게 한다.
        - 복합 인덱스 순서는 "항상 정렬 컬럼이 먼저" 또는 "항상 필터링 컬럼이 먼저"처럼 단정하지 않는다.
        - 복합 인덱스 문제는 반드시 짧은 SQL 예시 또는 쿼리 조건을 제시하고, 그 조건에서 가장 적절한 인덱스를 판단하게 한다.
        - 정답은 실제 쿼리의 WHERE 조건, 동등 조건, 범위 조건, ORDER BY 조건을 기준으로 판단 가능해야 한다.
        - 고급 문제에서 "자주 검색되는 컬럼에 인덱스를 추가한다"처럼 일반론만 묻는 문제는 만들지 않는다.
        """

    if competency_type == "database" and any(keyword in topic_text for keyword in ["트랜잭션", "격리", "락", "동시성"]):
        return """
        [트랜잭션 세부 출제 패턴]
        - 원자성, 일관성, 격리성, 지속성을 실제 상황에 적용하게 한다.
        - 중급/고급은 동시성 문제, 락 경합, 격리 수준 선택, 롤백 필요 상황을 판단하게 한다.
        """

    if competency_type == "security" and any(keyword in topic_text for keyword in ["인증", "인가", "권한"]):
        return """
        [인증/인가 세부 출제 패턴]
        - 인증과 인가를 구분하게 한다.
        - 중급/고급은 로그인 여부만 확인하는 문제와 권한 검증 누락 문제를 구분하게 한다.
        - 접근 제어 실패로 인한 보안 리스크를 판단하게 한다.
        """

    if competency_type == "web_development" and any(keyword in topic_text for keyword in ["HTTP", "API", "REST", "상태 코드"]):
        return """
        [HTTP/API 세부 출제 패턴]
        - HTTP 메서드, 상태 코드, 요청/응답 구조, REST API 설계 원칙을 다룬다.
        - 중급/고급은 잘못된 상태 코드 사용, 인증 실패 처리, CORS, API 오류 응답 설계를 상황 기반으로 묻는다.
        """

    if competency_type == "ai_data" and any(keyword in topic_text for keyword in ["RAG", "임베딩", "벡터", "검색"]):
        return """
        [RAG/임베딩 세부 출제 패턴]
        - 청킹, 임베딩, 벡터 검색, 검색 품질, 문서 근거, hallucination 방지를 중심으로 출제한다.
        - 중급은 검색 결과가 부정확한 원인, chunk 품질, query 보강, metadata filter 적용 여부를 상황 기반으로 판단하게 한다.
        - 고급은 vector search만으로 부족한 상황에서 keyword search, metadata filter, reranker, context filtering을 어떻게 조합할지 판단하게 한다.
        - reranking 문제는 단순히 "사용자 피드백"을 정답으로 단정하지 않는다.
        - reranking은 검색된 후보 문서와 사용자 질의의 관련도를 다시 평가해 순서를 조정하는 과정으로 다룬다.
        - 고급 문제는 latency와 검색 정확도, top_k 크기, chunk 크기, 문서 근거 부족, hallucination 위험 간의 트레이드오프를 포함한다.
        - "가장 중요한 요소는?"처럼 추상적인 질문만 만들지 말고, 검색 실패 상황이나 운영 제약을 제시한다.
        """

    if competency_type == "cloud_devops" and any(keyword in topic_text for keyword in ["Docker", "컨테이너", "CI", "CD", "배포"]):
        return """
        [컨테이너/배포 세부 출제 패턴]
        - 이미지 빌드, 컨테이너 실행, 환경 변수, 배포 실패, 롤백, 무중단 배포를 중심으로 출제한다.
        - 중급/고급은 배포 실패 원인, 모니터링 지표, 장애 범위 축소, 롤백 판단을 상황 기반으로 묻는다.
        """

    return ""

def _answer_distribution_rule(count: int, question_type: str) -> str:
    if question_type != "multiple_choice":
        return ""

    return f"""
    [이번 생성 정답 배치 규칙]
    - 객관식 문제의 answer는 1~5 중 하나여야 한다.
    - answer가 1번이나 2번에만 몰리지 않게 한다.
    - 여러 문제를 생성할 경우 정답 번호는 매번 랜덤하게 분산한다.
    - 단, 모든 문제의 answer가 같은 번호이면 안 된다.
    - answer가 [1, 1, 1], [2, 2, 2], [1, 2, 1], [2, 1, 2]처럼 낮은 번호에만 몰리면 안 된다.
    - 3번, 4번, 5번도 자연스럽게 정답 위치로 사용한다.
    - {count}개의 문제는 정답 위치 패턴이 항상 동일하면 안 된다.
    - 예시는 참고용일 뿐이며, 매번 같은 순서를 반복하지 않는다.
    """

def _question_type_rule(question_type: str) -> str:
    if question_type == "multiple_choice":
        return """
        [객관식 문제 생성 규칙]
        - choices는 반드시 문자열 5개 배열이어야 한다.
        - answer는 반드시 1~5 사이의 정답 번호로 작성한다.
        - answer는 0부터 시작하는 index가 아니다.
        - 첫 번째 보기가 정답이면 answer는 1이다.
        - 두 번째 보기가 정답이면 answer는 2이다.
        - 정답은 반드시 1개만 존재해야 한다.
        - JSON 예시의 answer 번호를 그대로 반복하지 말고 문제마다 정답 위치를 다르게 배치한다.
        - explanation에 적힌 정답 번호는 반드시 answer 값과 일치해야 한다.
        - explanation에서 "정답은 N번입니다"라고 쓸 경우 N은 반드시 answer와 같아야 한다.
        - "모두 정답", "정답 없음", "위 내용 모두" 같은 선택지는 금지한다.
        - 오답은 그럴듯해야 하지만 정답으로 해석될 수 있으면 안 된다.
        - explanation에는 정답인 이유와 주요 오답이 틀린 이유를 포함한다.
        - 선택지 중 정답으로 볼 수 있는 문장이 2개 이상이면 해당 문제를 생성하지 않는다.
        - 정답 선택지와 오답 선택지는 같은 개념 영역에 있어도 판단 기준이 명확히 달라야 한다.
        - 해설에서 오답 선택지를 맞는 설명처럼 인정하지 않는다.
        - 오답 선택지가 일반론으로는 맞더라도, 문제 상황의 질문 기준에서는 가장 적절하지 않아야 한다.

        [객관식 JSON 형식]
        {
            "title": "문제 제목",
            "body": "문제 본문",
            "choices": ["보기1", "보기2", "보기3", "보기4", "보기5"],
            "answer": 3,
            "explanation": "정답은 3번입니다. ...",
            "difficulty": "초급",
            "competency_type": "programming",
            "competency_tags": ["Python"],
            "score": 1
        }
        
        [고급 객관식 선택지 품질 규칙]
        - 난이도가 고급인 경우 choices는 단어 하나로 작성하지 않는다.
        - 난이도가 고급인 경우 각 선택지는 판단 기준이나 대응 이유가 포함된 문장으로 작성한다.
        - 예: "해시 테이블" 금지
        - 예: "반복 조회가 많고 순서 보장이 필요 없으므로 해시 테이블을 사용한다" 허용
        - 예: "인덱스를 추가한다" 금지
        - 예: "WHERE 조건과 정렬 조건을 함께 고려해 복합 인덱스를 설계한다" 허용
        - 선택지 5개는 모두 같은 깊이와 비슷한 길이로 작성한다.
        """

    if question_type == "essay":
        return """
        [서술형 문제 생성 규칙]
        - choices는 반드시 빈 배열 [] 이어야 한다.
        - answer는 모범답안 문자열이어야 한다.
        - body는 단순히 '설명하시오'가 아니라 평가 기준이 드러나도록 구체적으로 작성한다.
        - answer에는 핵심 키워드와 논리 흐름을 포함한다.
        - explanation에는 채점 기준을 포함한다.
        - 모범답안은 너무 짧지 않게 작성하되, 불필요한 장문은 피한다.

        [서술형 JSON 형식]
        {
          "title": "문제 제목",
          "body": "문제 본문",
          "choices": [],
          "answer": "모범답안",
          "explanation": "채점 기준 및 핵심 포인트",
          "difficulty": "중급",
          "competency_type": "database",
          "competency_tags": ["SQL"],
          "score": 3
        }
        """

    return """
    [코드작성형 문제 생성 규칙]
    - choices는 반드시 빈 배열 [] 이어야 한다.
    - body에는 반드시 다음 항목을 포함한다:
      1) 구현 요구사항
      2) 입력 조건
      3) 출력 조건
      4) 제한 조건 또는 예외 조건
    - answer에는 예시 코드 또는 핵심 풀이 방향을 작성한다.
    - explanation에는 풀이 전략, 시간복잡도 또는 주의할 점을 포함한다.
    - 단순 문법 확인 문제가 아니라 실제 구현 능력을 평가해야 한다.
    - 고급 난이도에서는 성능, 예외 처리, 자료구조 선택 이유 중 하나 이상을 포함한다.

    [코드작성형 JSON 형식]
    {
      "title": "문제 제목",
      "body": "문제 본문\\n\\n구현 요구사항:\\n- ...\\n\\n입력 조건:\\n- ...\\n\\n출력 조건:\\n- ...\\n\\n제한 조건:\\n- ...",
      "choices": [],
      "answer": "예시 코드 또는 핵심 풀이 방향",
      "explanation": "풀이 전략 및 채점 기준",
      "difficulty": "고급",
      "competency_type": "programming_language",
      "competency_tags": ["Python", "Algorithm"],
      "score": 5
    }
    """
def _build_plan_based_generation_prompt(
    topic: str,
    difficulty: str,
    count: int,
    score: int,
    question_type: str,
    competency_type: str,
    plans: list[dict],
) -> str:
    """
    문제 설계서를 기반으로 실제 문제 JSON을 생성하는 프롬프트.

    기존 generate_questions()에 있던 긴 프롬프트 규칙을 버리는 것이 아니라,
    설계서 기반 생성 단계에서 다시 적용한다.
    """
    plans_json = json.dumps(plans, ensure_ascii=False, indent=2)

    return f"""
너는 IT 역량진단 문제은행의 전문 출제자다.
목표는 실제 채용/역량진단에 사용할 수 있는 품질의 문제를 생성하는 것이다.

중요:
너는 문제를 처음부터 자유롭게 만드는 것이 아니라,
아래 [문제 설계서]를 기반으로 실제 문제 JSON만 생성해야 한다.

반드시 JSON 배열만 출력해라.
마크다운 코드블록, 설명 문장, 추가 텍스트는 절대 출력하지 마라.

[출제 조건]
- 역량 유형: {competency_type or "미지정"}
- 세부 주제: {topic}
- 난이도: {difficulty}
- 배점: {score}
- 생성 개수: {count}
- 문제 유형: {question_type}

[문제 설계서]
{plans_json}

[중요 검증 규칙]
- 문제는 반드시 IT 역량진단과 관련된 내용이어야 한다.
- 세부 주제가 음식, 여행, 연애, 취미, 쇼핑 등 IT와 무관하면 문제를 생성하지 않는다.
- 선택된 역량 유형과 세부 주제가 맞지 않으면 문제를 생성하지 않는다.
- 역량 유형이 자료구조/알고리즘이면 LLM, RAG, 딥러닝 같은 인공지능 문제를 만들지 않는다.
- 역량 유형이 데이터베이스이면 SQL, 트랜잭션, 인덱스, 정규화 등 데이터베이스 중심 문제만 만든다.
- 역량 유형이 인공지능/데이터이면 LLM, RAG, 임베딩, 모델 평가, 머신러닝, 데이터 분석 중심 문제만 만든다.

[출제 기준]
- 사용자가 선택한 역량 유형을 최우선 기준으로 문제를 생성한다.
- 세부 주제는 역량 유형 안에서 더 좁은 출제 범위로만 사용한다.
- 세부 주제가 역량 유형보다 우선하면 안 된다.
- 문제 설계서의 target_concept를 문제의 평가 대상으로 삼는다.
- 문제 설계서의 scenario와 constraints를 문제 본문에 반영한다.
- 문제 설계서의 correct_reason과 answer_decision_rule을 정답 판단 기준으로 사용한다.
- 문제 설계서의 distractor_strategy를 기준으로 오답을 만든다.

[환각 방지 규칙]
- 확실하지 않은 기술명, 버전, 수치, 공식 문서 내용은 임의로 만들지 마라.
- 특정 프레임워크/라이브러리의 세부 API 이름을 확신할 수 없으면 일반 개념 중심으로 출제해라.
- 존재하지 않는 함수명, 옵션명, 명령어, 설정값을 만들어내지 마라.
- 정답 근거가 불명확한 문제는 생성하지 마라.
- 문제 본문과 보기 사이에 모순이 있으면 안 된다.
- answer는 choices 배열 기준으로 정확히 하나의 정답만 가리켜야 한다.
- 약어가 포함된 주제는 임의로 풀어쓰지 마라.
- SLLM은 일반적으로 Small LLM 또는 Small Language Model 문맥으로 해석한다.
- vLLM은 언어 모델 자체가 아니라 LLM 추론/서빙 엔진이다.
- VLM은 Vision Language Model을 의미하며 vLLM과 혼동하지 마라.
- 약어의 의미가 불명확하면 문제를 생성하지 말거나, 약어의 의미를 명시한 문제로 생성해라.

[품질 기준]
- 문제는 실제 IT 역량진단에 사용할 수 있어야 한다.
- 너무 쉬운 상식 문제, 말장난 문제, 암기만 요구하는 문제는 피한다.
- 문제 본문은 평가하려는 개념이 명확해야 한다.
- 오답은 그럴듯해야 하지만, 정답과 명확히 구분되어야 한다.
- 해설은 정답 이유만 쓰지 말고 핵심 개념과 오답 판단 근거를 포함해야 한다.
- 같은 개념을 문장만 바꿔 반복 출제하지 마라.
- {count}개의 문제는 서로 평가 포인트가 달라야 한다.

[설계서 반영 규칙]
- 각 문제는 문제 설계서 1개를 기반으로 생성한다.
- 설계서 개수보다 문제 개수가 적으면 설계서 개수만큼만 생성한다.
- 설계서에 있는 scenario를 문제 본문에 자연스럽게 반영한다.
- 설계서에 있는 constraints를 문제 본문에 반드시 반영한다.
- 설계서에 있는 target_concept를 벗어난 문제를 만들지 않는다.
- 설계서에 있는 correct_reason과 answer_decision_rule에 따라 정답을 결정한다.
- 설계서에 있는 distractor_strategy에 따라 오답을 구성한다.
- plan_review.is_valid가 false인 설계서는 가능한 한 보완하되, 보완이 어렵다면 해당 설계서 문제는 생성하지 않는다.

[고급 문제 강제 품질 규칙]
- 난이도가 "고급"이면 문제 본문은 최소 3문장 이상이어야 한다.
- 난이도가 "고급"이면 선택지를 단어 또는 짧은 명사구로 작성하지 않는다.
- 난이도가 "고급"이면 문제 본문에 구체적인 조건, 제약, 증상, 리스크 중 3개 이상을 포함한다.
- 난이도가 "고급"이면 정답이 일반론으로 결정되면 안 된다.
- 난이도가 "고급"이면 선택지 5개 모두 실무적으로 가능한 판단이어야 한다.
- 단, 정답 외 선택지는 문제 상황의 핵심 원인을 해결하지 못하거나 우선순위가 낮아야 한다.
- 고급 문제에서 단순히 "무엇이 가장 효과적인가요?", "무엇이 가장 중요한가요?"처럼 조건 없는 질문을 금지한다.

[중급/고급 상황형 출제 강화 규칙]
- 난이도가 "중급" 또는 "고급"이면 문제 본문에 반드시 짧은 실무 상황을 포함한다.
- 중급은 개념 적용, 비교, 원인 판단, 검토 기준 선택을 묻는다.
- 고급은 원인 분석, 장애 대응, 성능 병목, 보안 리스크, 운영 트레이드오프, 우선순위 판단 중 하나를 포함한다.

[오답 품질 규칙]
- 오답은 장난스럽거나 비현실적인 문장으로 만들지 않는다.
- "자동으로 해결된다", "삭제한다", "무시한다", "생략한다", "항상", "무조건", "오직" 같은 극단적 표현을 반복하지 않는다.
- 오답도 실무자가 헷갈릴 수 있는 그럴듯한 선택지로 작성한다.
- 오답은 정답과 같은 주제 영역 안에서 만들어야 한다.
- 오답은 선택된 역량 유형과 같은 업무 맥락 안에서 구성한다.
- 예를 들어 데이터베이스 문제라면 오답도 SQL, 인덱스, 트랜잭션, 정규화 등 관련 개념 안에서 구성한다.
- 예를 들어 보안 문제라면 오답도 인증, 인가, 암호화, 접근 제어, 취약점 대응 등 관련 개념 안에서 구성한다.
- 난이도가 "고급"이면 "삭제한다", "무시한다", "무조건", "항상", "오직", "단순히", "완전히 제거한다"가 포함된 선택지를 만들지 마라.
- 난이도가 "고급"이면 오답도 실무자가 실제로 선택할 수 있는 대안이어야 한다.
- 오답은 일부 조건에서는 타당하지만, 현재 문제의 핵심 조건 또는 제약을 만족하지 못해야 한다.
- 선택지는 "인덱스를 추가한다", "쿼리를 단순화한다", "정규화한다"처럼 짧은 일반론으로 작성하지 마라.
- 선택지에는 판단 기준을 포함해라.
- 예: "주문 날짜 단일 인덱스를 추가해 기간 조건을 먼저 처리한다"는 일부 상황에서는 가능하지만, 고객 조인 조건과 쓰기 부하를 함께 고려하지 못하는 오답이 될 수 있다.
- 예: "조인 순서를 수동으로 고정한다"는 일부 상황에서는 도움이 될 수 있지만, 통계 정보와 실제 행 수 차이를 먼저 확인해야 하는 상황에서는 우선순위가 낮은 오답이 될 수 있다.

{_difficulty_rule(difficulty)}

{_competency_rule(competency_type, topic)}

{_question_type_rule(question_type)}

{_explanation_rule(question_type)}

{_answer_distribution_rule(count, question_type)}

[선택지 재배치 대응 규칙]
- 시스템은 생성 후 선택지 순서를 재배치할 수 있다.
- 따라서 explanation에서 오답을 설명할 때 "1번은", "2번은", "4번과 5번은"처럼 선택지 번호를 기준으로 설명하지 마라.
- 정답 번호는 "정답은 N번입니다." 첫 문장에만 사용한다.
- 오답 설명은 번호가 아니라 선택지 내용 또는 개념 기준으로 작성한다.

[출력 검증 규칙]
출력하기 전에 스스로 다음을 검증해라:
1. JSON 배열만 출력했는가?
2. 문제 개수가 최대 {count}개인가?
3. 각 문제에 title, body, choices, answer, explanation, difficulty, competency_type, competency_tags, score가 있는가?
4. 객관식이면 choices가 정확히 5개인가?
5. 객관식 answer가 1~5 숫자인가?
6. answer는 0부터 시작하는 index가 아닌가?
7. 정답이 실제로 choices 중 하나와 일치하는가?
8. explanation에 적힌 정답 번호와 answer 값이 같은가?
9. 난이도가 "{difficulty}"에 맞는가?
10. score가 {score}인가?
11. 존재하지 않는 기술/함수/API/명령어를 만들지 않았는가?
12. 문제 설계서의 constraints가 문제 본문에 반영되었는가?
13. 정답이 answer_decision_rule에 의해 결정되는가?
14. 오답이 distractor_strategy에 맞게 구성되었는가?

[공통 출력 규칙]
- 반드시 JSON 배열로만 반환한다.
- 배열 안에는 최대 {count}개의 문제 객체만 넣는다.
- difficulty는 반드시 "{difficulty}"로 작성한다.
- score는 반드시 {score}로 작성한다.
- competency_type은 "{competency_type or topic}" 값으로 작성한다.
- competency_tags는 세부 주제와 관련된 문자열 배열로 작성한다.
"""

def _explanation_rule(question_type: str) -> str:
    if question_type == "multiple_choice":
        return """
        [객관식 해설 작성 규칙]
        - explanation은 반드시 "정답은 N번입니다."로 시작한다.
        - N은 answer 값과 반드시 같아야 한다.
        - 정답 선택지가 왜 맞는지 설명한다.
        - 정답 선택지의 핵심 문구를 직접 언급해도 된다.
        - 오답 설명은 선택지 번호 기준으로 쓰지 않는다.
        - "1번은", "2번은", "3번은", "4번은", "5번은" 같은 표현을 사용하지 않는다.
        - "4번과 5번은", "1번, 2번은"처럼 번호를 묶어서 오답을 설명하지 않는다.
        - "다른 선택지는 관련이 없습니다"처럼 모든 오답을 한 문장으로 뭉뚱그려 설명하지 않는다.
        - 각 오답 선택지의 핵심 내용이 왜 문제 상황의 정답 기준과 맞지 않는지 구체적으로 설명한다.
        - 문서에 없는 새로운 기술명, 수치, 도구명, 절차를 추가하지 않는다.
        - 예: "명명 규칙 검토나 중복 여부 확인은 관련 활동일 수 있으나, 누락된 기능으로 인한 오류 방지의 핵심 검토 포인트와는 직접성이 낮다."
        - explanation에 적힌 정답 번호는 answer 값과 반드시 같아야 한다.
        """

    if question_type == "essay":
        return """
        [서술형 해설 작성 규칙]
        - 서술형에는 정답 번호가 없으므로 explanation에 "정답 번호", "정답은 N번입니다", "N번이 정답" 같은 표현을 절대 쓰지 않는다.
        - explanation에는 채점 기준, 핵심 키워드, 문서 근거를 포함한다.
        - 모범답안에서 반드시 포함해야 할 개념을 설명한다.
        - 부족한 답안이 되는 경우도 간단히 설명한다.
        """

    return """
    [코드작성형 해설 작성 규칙]
    - 코드작성형에는 정답 번호가 없으므로 explanation에 "정답 번호", "정답은 N번입니다", "N번이 정답" 같은 표현을 절대 쓰지 않는다.
    - explanation에는 풀이 전략, 핵심 구현 포인트, 예외 처리 기준, 시간복잡도 또는 자료구조 선택 이유를 포함한다.
    - 채점 시 확인해야 할 기준을 설명한다.
    """

def generate_questions_from_plans(
    topic: str,
    difficulty: str,
    plans: list[dict],
    count: int = 1,
    score: int = 1,
    question_type: str = "multiple_choice",
    competency_type: str | None = None,
):
    """
    문제 설계서 기반으로 실제 문제 JSON을 생성한다.
    기존 _generate_with_retry()를 그대로 사용해서
    JSON 검증, 정답 번호 검증, 정답 위치 재배치, 해설 재생성을 모두 유지한다.
    """
    prompt = _build_plan_based_generation_prompt(
        topic=topic,
        difficulty=difficulty,
        count=count,
        score=score,
        question_type=question_type,
        competency_type=competency_type or "미지정",
        plans=plans,
    )

    return _generate_with_retry(
        prompt=prompt,
        system_message="너는 IT 역량진단 문제은행의 문제 출제 전문가다. 반드시 유효한 JSON 배열만 출력한다.",
        question_type=question_type,
        difficulty=difficulty,
        score=score,
        temperature=0.2,
        max_retries=0,
    )

def generate_questions(
    topic: str,
    difficulty: str,
    count: int = 1,
    score: int = 1,
    question_type: str = "multiple_choice",
    competency_type: str | None = None,
):
    """
    일반 AI 문제 생성.

    변경된 흐름:
    1. question_planner.py에서 문제 설계서 생성
    2. 설계서를 기반으로 실제 문제 생성
    3. 기존 검증/정답 재배치/해설 재생성 로직 유지
    """
    start_time = time.time()

    logger.info(
        f"LLM Pipeline [Generate]: 설계서 기반 AI 문제 생성 시작 "
        f"(주제: '{topic}', 유형: {question_type}, 난이도: {difficulty}, 개수: {count}, 역량: {competency_type})"
    )

    try:
        candidate_count = max(count + 2, 5)

        plans = generate_question_plans(
            topic=topic,
            difficulty=difficulty,
            count=candidate_count,
            question_type=question_type,
            competency_type=competency_type or "programming",
        )

        logger.info(
            f"LLM Pipeline [Planner]: 문제 설계서 생성 완료 "
            f"(생성된 설계서 수: {len(plans)}/{candidate_count})"
        )

        validated_questions = generate_questions_from_plans(
            topic=topic,
            difficulty=difficulty,
            plans=plans,
            count=candidate_count,
            score=score,
            question_type=question_type,
            competency_type=competency_type,
        )

        elapsed_time = time.time() - start_time

        logger.info(
            f"LLM Pipeline [Generate]: 설계서 기반 AI 문제 생성 완료 "
            f"(생성된 문제 수: {len(validated_questions[:count])}/{count}, 후보 통과 수: {len(validated_questions)}, 소요 시간: {elapsed_time:.3f}초)"
        )

        return validated_questions[:count]

    except Exception as e:
        elapsed_time = time.time() - start_time

        logger.error(
            f"LLM Pipeline [Generate]: 설계서 기반 AI 문제 생성 실패 "
            f"(소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}"
        )

        raise


def generate_questions_from_context(
    topic: str,
    context: str,
    difficulty: str,
    count: int = 1,
    score: int = 1,
    question_type: str = "multiple_choice",
    competency_type: str | None = None,
):
    start_time = time.time()
    logger.info(f"LLM Pipeline [RAG Generate]: RAG 기반 AI 문제 생성 시작 (주제: '{topic}', 유형: {question_type}, 난이도: {difficulty}, 개수: {count})")
    
    prompt = f"""
        너는 IT 역량진단 문제은행의 문서 기반 문제 출제 전문가다.
        목표는 제공된 문서 내용에 근거한 검증 가능한 문제만 생성하는 것이다.

        반드시 JSON 배열만 출력해라.
        마크다운 코드블록, 설명 문장, 추가 텍스트는 절대 출력하지 마라.

        [가장 중요한 규칙]
        아래 [문서 내용]에 명시되어 있거나 직접적으로 추론 가능한 내용만 사용해라.
        문서에 없는 개념, 정의, 예시, 기술명, API, 명령어, 수치, 장단점은 절대 추가하지 마라.
        문서 내용만으로 문제와 정답을 만들 수 없으면 억지로 만들지 말고 빈 JSON 배열 [] 을 반환해라.

        [출제 조건]
        - 역량 유형: {competency_type or "미지정"}
        - 세부 주제: {topic}
        - 난이도: {difficulty}
        - 배점: {score}
        - 생성 개수: {count}
        - 문제 유형: {question_type}
        
        [역량 유형 제한 규칙]
        - 문제는 반드시 선택된 역량 유형에 맞아야 한다.
        - 세부 주제가 선택된 역량 유형과 충돌하면 문제를 생성하지 말고 빈 JSON 배열 [] 을 반환한다.
        - 역량 유형이 자료구조/알고리즘이면 LLM, RAG, 딥러닝 같은 인공지능 문제를 만들지 않는다.
        - 역량 유형이 데이터베이스이면 SQL, 트랜잭션, 인덱스, 정규화 등 데이터베이스 중심 문제만 만든다.
        - 역량 유형이 인공지능/데이터이면 LLM, RAG, 임베딩, 모델 평가, 머신러닝, 데이터 분석 중심 문제만 만든다.

        [문서 기반 환각 방지 규칙]
        - 문서에 없는 용어를 새로 추가하지 마라.
        - 문서에 없는 새로운 기술, 도구, API, 수치, 절차를 추가하지 마라.
        - 단, 중급/고급 문제에서는 문서에 나온 개념을 벗어나지 않는 범위에서 짧은 검토/판단 상황으로 재구성할 수 있다.
        - 상황은 문서의 개념을 적용하기 위한 최소한의 배경으로만 사용하고, 정답 판단 근거는 반드시 문서 내용에 있어야 한다.
        - 문서에 없는 도구명, 함수명, 라이브러리명, 명령어를 만들지 마라.
        - 문서의 표현을 그대로 복사하지 말고, 의미를 유지한 상태에서 문제로 재구성해라.
        - 단, 문서의 의미를 벗어난 해석은 금지한다.
        - 문서에 근거가 부족한 고급 문제는 생성하지 말고 더 낮은 수준의 문제로 만들거나 []를 반환해라.
        - 정답은 반드시 문서 내용에서 판단 가능해야 한다.
        - explanation에는 가능한 한 문서의 어떤 내용에 근거했는지 요약해서 포함한다.
        - 문서 내용과 무관한 일반 지식으로 정답을 만들지 마라.
        - 문서에서 약어의 의미가 정의되어 있지 않으면 약어를 임의로 확장하지 마라.
        - SLLM, vLLM, VLM처럼 비슷한 약어는 반드시 구분해라.
        - vLLM을 VLM 또는 다국어 모델로 설명하지 마라.
        
        [품질 기준]
        - 단순히 문장 일부를 빈칸처럼 바꾸는 문제는 피한다.
        - 같은 문장을 거의 그대로 반복하는 문제는 피한다.
        - 문제는 역량진단에 적합해야 한다.
        - 오답은 문서의 유사 개념을 활용해 그럴듯하게 만들되, 문서 기준으로 명확히 틀려야 한다.
        - 생성되는 {count}개의 문제는 서로 다른 평가 포인트를 가져야 한다.
        - 문서 내용이 부족하면 {count}개보다 적게 생성해도 된다.
        - 단, 이 경우에도 JSON 배열만 출력한다.

        [문서 기반 중급/고급 문제 강화 규칙]
        - 중급/고급 문제는 문서의 문장을 그대로 확인하는 문제로 만들지 않는다.
        - 중급 문제는 문서 내용을 실제 상황에 적용하게 만든다.
        - 고급 문제는 문서 내용을 바탕으로 원인, 영향, 리스크, 우선순위, 대응 방안을 판단하게 만든다.
        - 단, 문서에 근거가 없는 상황은 만들지 않는다.

        [문서 기반 고급 문제 강제 규칙]
        - 난이도가 "고급"이면 문제 본문은 최소 3문장 이상으로 작성한다.
        - 문서에 나온 개념을 단순히 고르는 문제를 만들지 않는다.
        - 문서에 나온 개념 2개 이상을 연결해 판단하게 한다.
        - 예: 요구사항 완전성 + 변경 요청 증가
        - 예: 비기능 요구사항 + 검증 가능성
        - 예: 추적성 부족 + 변경 영향 분석 실패
        - 예: 기술적 타당성 + 성능/용량 제약
        - 선택지는 단어 또는 짧은 명사구로 쓰지 않는다.
        - 선택지는 모두 실무자가 실제로 선택할 수 있는 검토 기준 또는 대응 방안 문장으로 작성한다.
        - 문제 본문에 이미 정답 키워드를 직접 노출하지 않는다.
        - 예: 정답이 "완전성"이면 본문에 "누락", "모든 기능" 같은 단서를 과도하게 반복하지 않는다.

        [중급/고급 문제 본문 작성 방식]
        - 난이도가 "중급" 또는 "고급"이면 문제 본문은 반드시 상황 설명 + 판단 질문 구조로 작성한다.
        - 중급 문제 본문 구조:
            "프로젝트/검토/명세 상황 설명 → 이때 가장 적절한 검토 기준은?"
        - 고급 문제 본문 구조:
            "문제 상황 + 제약 조건 + 발생 가능한 리스크 → 가장 우선적으로 판단하거나 대응해야 할 것은?"
        - 고급 문제는 최소 2문장 이상으로 작성한다.

        [중급/고급 금지 문제 유형]
        - 난이도가 "중급" 또는 "고급"이면 다음 유형의 문제를 만들지 않는다.
        - 단순히 문서에 있는 항목을 고르는 문제
        - "어떤 요소가 포함되어야 하는가?"처럼 목록 암기만 요구하는 문제
        - "올바른 설명은 무엇인가?"처럼 상황이 없는 문제
        - "다음 중 정의로 맞는 것은?" 형태의 문제
        - 정답만 명확하고 오답이 너무 쉽게 배제되는 문제
        - 선택지 중 3개 이상이 명백히 엉뚱한 문제
        
        [난이도별 문제 특성 규칙]
        - 문제는 반드시 요청된 난이도 "{difficulty}"에 맞게 생성한다.
        - 초급은 기본 개념, 용어 이해, 단순 구분을 평가한다.
        - 중급은 단순 정의 암기가 아니라 문서 내용을 바탕으로 한 비교, 적용, 검토 기준 선택, 상황 판단을 평가한다.
        - 고급은 문서 내용을 바탕으로 원인, 영향, 리스크, 우선순위, 대응 방안을 판단하게 한다.
        - "{difficulty}"가 중급 또는 고급이면 문제 본문에 짧은 실무 상황을 포함한다.

        [선택지 재배치 대응 규칙]
        - 시스템은 생성 후 선택지 순서를 재배치할 수 있다.
        - 따라서 explanation에서 오답을 설명할 때 "1번은", "2번은", "4번과 5번은"처럼 선택지 번호를 기준으로 설명하지 마라.
        - 정답 번호는 "정답은 N번입니다." 첫 문장에만 사용한다.
        - 오답 설명은 번호가 아니라 선택지 내용 또는 개념 기준으로 작성한다.
        - 예: "명명 규칙 검토는 요구사항 완전성 확인과 직접 관련이 낮다."

        [문서 기반 우선순위 판단 제한 규칙]
        - 문서에 여러 검토 기준이 나열되어 있을 뿐 우선순위가 명시되어 있지 않다면, 특정 기준을 "가장 우선"이라고 단정하지 않는다.
        - "가장 우선적으로 고려해야 할 사항"을 묻는 문제는 본문에 우선순위를 결정할 수 있는 구체적 상황을 반드시 포함한다.
        - 시장 성숙도, 상호 운용성, 기술 의존성, 성능/용량, 검증 여부처럼 모두 타당한 선택지가 있을 경우, 문서 근거 없이 하나만 정답으로 만들지 않는다.
        - 선택지들이 모두 문서상 타당한 검토 항목이면 문제를 생성하지 않는다.
        - 정답은 문서 내용과 문제 상황을 함께 보았을 때 다른 보기보다 명확히 우선되어야 한다.

        {_difficulty_rule(difficulty)}

        {_competency_rule(competency_type, topic)}

        {_question_type_rule(question_type)}

        {_explanation_rule(question_type)}

        {_answer_distribution_rule(count, question_type)}

        [문서 내용]
        {context}

        [출력 검증 규칙]
        출력하기 전에 스스로 다음을 검증해라:
        1. JSON 배열만 출력했는가?
        2. 각 문제는 문서 내용에 근거하는가?
        3. 문서에 없는 개념/기술/API/명령어/수치를 추가하지 않았는가?
        4. 객관식이면 choices가 정확히 5개인가?
        5. 객관식 answer가 1~5 숫자인가?
        6. 정답이 문서 내용으로 판단 가능한가?
        7. 오답이 정답으로도 해석될 여지가 없는가?
        8. explanation에 문서 근거 요약이 포함되어 있는가?
        9. 난이도가 "{difficulty}"에 맞는가?
        10. 근거가 부족한 문제는 제거했는가?

        [공통 출력 규칙]
        - 반드시 JSON 배열로만 반환한다.
        - 모든 문제 객체는 title, body, choices, answer, explanation, difficulty, competency_type, competency_tags, score 필드를 가진다.
        - difficulty는 반드시 "{difficulty}"로 작성한다.
        - score는 반드시 {score}로 작성한다.
        - competency_type은 "{competency_type or topic}" 값으로 작성한다.
        - competency_tags는 문서 내용과 주제에 관련된 문자열 배열로 작성한다.
        - 문서 근거가 부족하면 빈 배열 [] 을 반환한다.
        """
        

    try:
        validated_questions = _generate_with_retry(
            prompt=prompt,
            system_message="너는 문서 기반 IT 역량진단 문제 출제자다. 반드시 제공된 문서 내용에 근거한 유효한 JSON 배열만 출력한다.",
            question_type=question_type,
            difficulty=difficulty,
            score=score,
            temperature=0.1,
            max_retries=0,
        )

        elapsed_time = time.time() - start_time
        logger.info(f"LLM Pipeline [RAG Generate]: RAG 기반 AI 문제 생성 완료 (생성된 문제 수: {len(validated_questions)}/{count}, 소요 시간: {elapsed_time:.3f}초)")
        
        return validated_questions[:count]
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"LLM Pipeline [RAG Generate]: RAG 기반 AI 문제 생성 실패 (소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}")
        raise

def _has_answer_position_bias(questions: list, question_type: str) -> bool:
    if question_type != "multiple_choice":
        return False

    if len(questions) < 3:
        return False

    try:
        answers = [int(q.get("answer")) for q in questions]
    except Exception:
        return False

    counter = Counter(answers)
    unique_count = len(counter)
    max_repeat = max(counter.values())

    # 전부 같은 번호면 편향
    if unique_count == 1:
        return True

    # 정답이 1,2번에만 몰리면 편향
    if set(answers).issubset({1, 2}):
        return True

    # 3문제는 [3,3,4] 같은 중복은 허용하되, 전부 같거나 1/2에만 몰리는 것은 위에서 차단
    if len(answers) == 3:
        return False

    # 4문제는 최소 3개 이상의 번호가 섞이게 함
    if len(answers) == 4:
        return unique_count < 3 or max_repeat > 2

    # 5문제는 최소 4개 이상의 번호가 섞이게 함
    if len(answers) == 5:
        return unique_count < 4 or max_repeat > 2

    # 6문제 이상은 특정 번호가 60% 이상이면 편향
    if max_repeat / len(answers) >= 0.6:
        return True

    return False