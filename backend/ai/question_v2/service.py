import logging

from ai.question_v2.evidence_builder import ( build_evidence_pack,select_beginner_topic_for_index )
from ai.question_v2.format_selector import select_question_formats
from ai.question_v2.models import GeneratedQuestion, QuestionV2Request
from ai.question_v2.renderer import render_question_from_evidence
from ai.question_v2.answer_position import rebalance_answer_positions
from ai.question_v2.validator import validate_generated_question, validate_generated_questions

logger = logging.getLogger(__name__)


def generate_ai_questions_v2(request: QuestionV2Request) -> list[GeneratedQuestion]:
    if request.competency_type != "ai":
        raise ValueError("V2 현재 버전은 competency_type='ai'만 지원합니다.")

    if request.question_type != "multiple_choice":
        raise ValueError("V2 현재 버전은 multiple_choice만 지원합니다.")

    plans = select_question_formats(
        difficulty=request.difficulty,
        count=request.count,
        topic=request.topic,
    )

    questions: list[GeneratedQuestion] = []

    for plan in plans:
        effective_topic = request.topic

        if request.difficulty == "초급":
            effective_topic = select_beginner_topic_for_index(
                topic=request.topic,
                index=plan.index,
            )

        evidence_pack = build_evidence_pack(
            topic=effective_topic,
            difficulty=request.difficulty,
            plan=plan,
        )

        last_error: Exception | None = None
        generated = False

        for attempt in range(1, 3):
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
