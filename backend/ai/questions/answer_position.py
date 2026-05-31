import re
import random
from ai.questions.models import GeneratedQuestion


ANSWER_POSITION_PATTERN = [3, 5, 2, 4, 1]


def rebalance_answer_positions(
    questions: list[GeneratedQuestion],
) -> list[GeneratedQuestion]:
    rebalanced: list[GeneratedQuestion] = []

    if not questions:
        return rebalanced

    question_count = len(questions)

    # 1~3문제 생성 시에는 정답 위치를 랜덤 배치
    # 단, 같은 요청 안에서는 중복되지 않도록 sample 사용
    if question_count <= 3:
        target_positions = random.sample([1, 2, 3, 4, 5], k=question_count)
    else:
        target_positions = [
            ANSWER_POSITION_PATTERN[index % len(ANSWER_POSITION_PATTERN)]
            for index in range(question_count)
        ]

    for question, target_position in zip(questions, target_positions):
        rebalanced.append(
            move_answer_to_position(
                question=question,
                target_position=target_position,
            )
        )

    return rebalanced


def move_answer_to_position(
    *,
    question: GeneratedQuestion,
    target_position: int,
) -> GeneratedQuestion:
    if not (1 <= target_position <= 5):
        return question

    if not isinstance(question.answer, int) or not (1 <= question.answer <= 5):
        return question

    current_position = question.answer

    if current_position == target_position:
        return question

    choices = question.choices[:]

    correct_choice = choices.pop(current_position - 1)
    choices.insert(target_position - 1, correct_choice)

    question.choices = choices
    question.answer = target_position
    question.explanation = _replace_explanation_answer_prefix(
        explanation=question.explanation,
        answer=target_position,
    )

    return question


def _replace_explanation_answer_prefix(
    *,
    explanation: str,
    answer: int,
) -> str:
    text = explanation.strip()
    new_prefix = f"정답은 {answer}번입니다."

    pattern = r"^정답은\s+\d+번입니다\."

    if re.match(pattern, text):
        text = re.sub(pattern, new_prefix, text, count=1)
    else:
        text = f"{new_prefix} {text}"

    return _remove_choice_number_references_after_rebalance(text, answer)

def _remove_choice_number_references_after_rebalance(text: str, answer: int) -> str:
    if not text:
        return ""

    prefix = f"정답은 {answer}번입니다."

    if text.startswith(prefix):
        reason_text = text.replace(prefix, "", 1).strip()
    else:
        reason_text = text.strip()

    number_ref_pattern = re.compile(
        r"([1-5]\s*번\s*(선택지|은|는|이|가|의|을|를)|[1-5]\s*번째\s*선택지)"
    )

    matches = number_ref_pattern.findall(reason_text)

    # 번호별 선택지 설명이 없으면 원문 유지
    if not matches:
        return text

    sentence_parts = re.split(r"(?<=[.!?])\s+", reason_text)
    cleaned_parts = []

    for sentence in sentence_parts:
        if number_ref_pattern.search(sentence):
            continue
        cleaned_parts.append(sentence.strip())

    cleaned_reason = " ".join(part for part in cleaned_parts if part)

    if cleaned_reason:
        return f"{prefix} {cleaned_reason}"

    return prefix