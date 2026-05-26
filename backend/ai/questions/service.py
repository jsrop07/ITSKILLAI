import logging

from ai.questions.format_selector import select_question_formats
from ai.questions.models import GeneratedQuestion, QuestionV2Request
from ai.questions.renderer import render_question_from_evidence
from ai.questions.answer_position import rebalance_answer_positions
from ai.questions.advanced_templates import build_ai_advanced_v2_questions
from ai.questions.validator import validate_generated_question, validate_generated_questions
from ai.questions.evidence_builder import (build_evidence_pack,build_rag_evidence_pack,build_beginner_evidence_pack_from_slot,resolve_beginner_generation_slots,)

logger = logging.getLogger(__name__)

def _compact_rag_context(rag_context: str, max_chars: int = 1200) -> str:
    text = rag_context.strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "\n\n[이하 문서 내용 생략]"

def _find_plain_style_ending(text: str) -> tuple[str, str] | None:
    patterns = [
        "본다.",
        "미룬다.",
        "한다.",
        "된다.",
        "있다.",
        "없다.",
        "않는다.",
        "못한다.",
        "되었다.",
        "않았다.",
        "상태다.",
        "상황이다.",
        "원한다.",
        "기대한다.",
        "수행하고 있다.",
        "사용하고 있다.",
        "검토하고 있다.",
        "저장하고 있다.",
        "관리하고 있다.",
        "적용되어 있다.",
        "포함되어 있다.",
        "섞여 있다.",
        "반영되어 있다.",
        "확인하고 있다.",
        "확인하지 않고 있다.",
        "선별하지 않고 있다.",
    ]

    value = str(text or "")

    for pattern in patterns:
        index = value.find(pattern)
        if index >= 0:
            start = max(0, index - 50)
            end = min(len(value), index + len(pattern) + 50)
            return pattern, value[start:end]

    return None

def _validate_advanced_template_questions(
    questions: list[GeneratedQuestion],
    *,
    expected_count: int,
) -> None:
    if not questions:
        raise ValueError("AI 고급 template 문제가 생성되지 않았습니다.")

    if len(questions) < expected_count:
        raise ValueError(
            f"AI 고급 template 문제 수가 부족합니다. "
            f"generated={len(questions)}, expected={expected_count}"
        )

    for question in questions:
        if not question.title or not question.title.strip():
            raise ValueError("AI 고급 template 문제 title이 비어 있습니다.")

        if not question.body or not question.body.strip():
            raise ValueError("AI 고급 template 문제 body가 비어 있습니다.")

        if not isinstance(question.choices, list) or len(question.choices) != 5:
            raise ValueError("AI 고급 template 문제 choices는 5개여야 합니다.")

        try:
            answer = int(question.answer)
        except Exception as exc:
            raise ValueError("AI 고급 template 문제 answer가 숫자가 아닙니다.") from exc

        if answer < 1 or answer > 5:
            raise ValueError("AI 고급 template 문제 answer가 1~5 범위를 벗어났습니다.")

        if not question.explanation or not question.explanation.strip():
            raise ValueError("AI 고급 template 문제 explanation이 비어 있습니다.")

        body_plain = _find_plain_style_ending(question.body)
        if body_plain:
            pattern, context = body_plain
            raise ValueError(
                f"AI 고급 template body에 반말 종결이 남아 있습니다. "
                f"pattern={pattern}, context={context}"
            )

        for choice in question.choices:
            choice_plain = _find_plain_style_ending(choice)
            if choice_plain:
                pattern, context = choice_plain
                raise ValueError(
                    f"AI 고급 template choice에 반말 종결이 남아 있습니다. "
                    f"pattern={pattern}, context={context}"
                )

        explanation_plain = _find_plain_style_ending(question.explanation)
        if explanation_plain:
            pattern, context = explanation_plain
            raise ValueError(
                f"AI 고급 template explanation에 반말 종결이 남아 있습니다. "
                f"pattern={pattern}, context={context}"
            )
        expected_prefix = f"정답은 {answer}번입니다."
        if not question.explanation.strip().startswith(expected_prefix):
            raise ValueError(
                f"AI 고급 template 문제 explanation의 정답 번호가 answer와 다릅니다. "
                f"expected_prefix={expected_prefix}"
            )

def generate_ai_questions_v2(
    request: QuestionV2Request,
    rag_context: str | None = None,
) -> list[GeneratedQuestion]:
    if request.competency_type != "ai":
        raise ValueError("V2 현재 버전은 competency_type='ai'만 지원합니다.")

    if request.question_type != "multiple_choice":
        raise ValueError("V2 현재 버전은 multiple_choice만 지원합니다.")

    if request.difficulty == "고급":
        questions = build_ai_advanced_v2_questions(
            topic=request.topic,
            count=request.count,
        )

        questions = rebalance_answer_positions(questions)

        _validate_advanced_template_questions(
            questions,
            expected_count=request.count,
        )

        return questions

    beginner_slots = None

    if request.difficulty == "초급":
        beginner_slots = resolve_beginner_generation_slots(
            topic=request.topic,
            count=request.count,
        )

    plans = select_question_formats(
        difficulty=request.difficulty,
        count=request.count,
        topic=request.topic,
        beginner_slots=beginner_slots,
    )

    questions: list[GeneratedQuestion] = []

    for plan in plans:
        effective_topic = request.topic
        beginner_slot = None

        if request.difficulty == "초급" and beginner_slots:
            beginner_slot = beginner_slots[plan.index - 1]
            effective_topic = beginner_slot.get("raw_slot") or request.topic

        if rag_context:
            evidence_pack = build_rag_evidence_pack(
                topic=effective_topic,
                difficulty=request.difficulty,
                plan=plan,
                rag_context=rag_context,
            )
        elif request.difficulty == "초급" and beginner_slot:
            evidence_pack = build_beginner_evidence_pack_from_slot(
                slot=beginner_slot,
                difficulty=request.difficulty,
                plan=plan,
            )
        else:
            evidence_pack = build_evidence_pack(
                topic=effective_topic,
                difficulty=request.difficulty,
                plan=plan,
            )
        last_error: Exception | None = None
        generated = False

        for attempt in range(1, 4):
            try:
                question = render_question_from_evidence(evidence_pack=evidence_pack)

                try:
                    validate_generated_question(question)
                except Exception as validation_exc:
                    last_error = validation_exc
                    logger.warning(
                        "AI Question V2 검증 실패 상세: format=%s, attempt=%s, error=%s, answer=%s, body=%s, lengths=%s, choices=%s",
                        plan.question_format,
                        attempt,
                        validation_exc,
                        question.answer,
                        question.body,
                        [len(choice.strip()) for choice in question.choices],
                        question.choices,
                    )
                    raise validation_exc

                questions.append(question)
                generated = True
                break

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "AI Question V2 생성 재시도: format=%s, attempt=%s, error=%s",
                    plan.question_format,
                    attempt,
                    exc,
                )

        if not generated:
            raise ValueError(
                f"AI Question V2 생성 실패: format={plan.question_format}, error={last_error}"
            )

    questions = rebalance_answer_positions(questions)
    validate_generated_questions(questions)

    return questions
