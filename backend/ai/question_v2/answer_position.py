import re

from ai.question_v2.models import GeneratedQuestion


ANSWER_POSITION_PATTERN = [3, 5, 2, 4, 1]


def rebalance_answer_positions(
    questions: list[GeneratedQuestion],
) -> list[GeneratedQuestion]:
    rebalanced: list[GeneratedQuestion] = []

    for index, question in enumerate(questions):
        target_position = ANSWER_POSITION_PATTERN[index % len(ANSWER_POSITION_PATTERN)]
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
        return re.sub(pattern, new_prefix, text, count=1)

    return f"{new_prefix} {text}"