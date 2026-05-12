# backend/ai/questions/graph_nodes.py
import json
import re
import logging
from models import Question
from ai.core.config import normalize_competency_type
from ai.questions.validator import validate_questions
from ai.questions.planner import generate_question_plans
from ai.questions.graph_state import QuestionGenerationState
from ai.rag.document_service import build_context_from_search_results
from ai.questions.topic_validator import validate_topic_for_competency
from ai.questions.generator import ( generate_questions_from_plans, generate_questions_from_context )
from ai.questions.choice_generator import ( generate_choices_for_template_question, generate_choices_for_template_questions_batch,)
from ai.questions.templates import ( build_ai_advanced_template, build_sql_advanced_template, build_python_advanced_template, build_java_advanced_template,)
logger = logging.getLogger("uvicorn.info")


TARGET_TEMPLATE_COMPETENCIES = {"ai", "sql", "python", "java"}


def normalize_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    competency_type을 내부 표준 값으로 정규화한다.
    예:
    - database -> sql
    - ai_data -> ai
    - programming -> python
    """
    competency_type = state.get("competency_type")
    normalized_competency_type = normalize_competency_type(competency_type)

    if not normalized_competency_type:
        raise ValueError("역량 유형이 올바르지 않습니다.")

    logger.info(
        f"LangGraph [Normalize]: competency_type={competency_type}, "
        f"normalized={normalized_competency_type}"
    )

    return {
        **state,
        "normalized_competency_type": normalized_competency_type,
    }


def topic_validation_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    세부 주제가 선택한 역량과 관련 있는지 검증한다.
    기존 validate_topic_for_competency()를 그대로 사용한다.
    """
    topic = state.get("topic", "")
    normalized_competency_type = state.get("normalized_competency_type")

    validate_topic_for_competency(
        competency_type=normalized_competency_type,
        topic=topic,
    )

    logger.info(
        f"LangGraph [TopicValidation]: topic='{topic}', "
        f"competency={normalized_competency_type}"
    )

    return state

def retrieval_node(state: QuestionGenerationState) -> QuestionGenerationState:
    topic = state.get("topic", "")
    competency_type = state.get("normalized_competency_type") or state.get("competency_type")
    search_query = state.get("search_query") or topic
    top_k = state.get("top_k", 5)
    search_mode = state.get("search_mode", "hybrid")
    db = state.get("db")

    if db is None:
        raise ValueError("RAG 검색을 위한 DB 세션이 없습니다. state['db']가 필요합니다.")

    logger.info(
        f"LangGraph [Retrieval]: query='{search_query}', top_k={top_k}, "
        f"category={competency_type}, search_mode={search_mode}"
    )

    rag_context = build_context_from_search_results(
        db=db,
        query=search_query,
        top_k=top_k,
        category=competency_type,
        search_mode=search_mode,
    )

    if not rag_context or not rag_context.strip():
        raise ValueError("RAG 검색 결과가 비어 있어 문서 기반 문제를 생성할 수 없습니다.")

    logger.info(
        f"LangGraph [Retrieval]: context_length={len(rag_context)}"
    )

    return {
        **state,
        "rag_context": rag_context,
    }

def route_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    난이도와 역량에 따라 planner/template 경로를 결정한다.

    현재 정책:
    - ai/sql/python/java 고급: template
    - 그 외: planner
    """
    difficulty = state.get("difficulty")
    normalized_competency_type = state.get("normalized_competency_type")
    generation_source = state.get("generation_source", "general")

    if generation_source == "rag":
        logger.info(
            f"LangGraph [Route]: source=rag, difficulty={difficulty}, "
            f"competency={normalized_competency_type}, generation_mode=rag"
        )
        return {
            **state,
            "generation_mode": "rag",
        }

    if (
        difficulty == "고급"
        and normalized_competency_type in TARGET_TEMPLATE_COMPETENCIES
    ):
        generation_mode = "template"
    else:
        generation_mode = "planner"

    logger.info(
        f"LangGraph [Route]: difficulty={difficulty}, "
        f"competency={normalized_competency_type}, "
        f"generation_mode={generation_mode}"
    )

    return {
        **state,
        "generation_mode": generation_mode,
    }


def route_by_generation_mode(state: QuestionGenerationState) -> str:
    generation_mode = state.get("generation_mode", "planner")

    if generation_mode == "rag":
        return "rag"

    if generation_mode == "template":
        return "template"

    return "planner"

def planner_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    초급/중급 Planner 기반 경로.
    문제 설계서만 생성한다.
    실제 문제 생성은 다음 단계 generation_node에서 처리한다.
    """
    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "중급")
    count = int(state.get("count", 1))
    question_type = state.get("question_type", "multiple_choice")
    normalized_competency_type = state.get("normalized_competency_type")

    # Python/Java 중급은 속도와 안정성을 위해 count개만 생성한다.
    # 그 외는 기존 함수 내부 정책을 따르되 여기서는 일단 count로 넘긴다.
    plans = generate_question_plans(
        topic=topic,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
        competency_type=normalized_competency_type,
    )

    logger.info(
        f"LangGraph [Planner]: plans={len(plans)}, "
        f"topic='{topic}', competency={normalized_competency_type}, difficulty={difficulty}"
    )

    return {
        **state,
        "plans": plans,
    }


def template_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    고급 Template 기반 경로.
    base template 문제만 생성한다.
    choices/explanation 생성 또는 lock_choices 처리는 다음 단계 generation_node에서 처리한다.
    """
    topic = state.get("topic", "")
    count = int(state.get("count", 1))
    normalized_competency_type = state.get("normalized_competency_type")

    base_questions = []
    used_template_formats: list[str] = []

    for _ in range(count):
        if normalized_competency_type == "ai":
            base_question = build_ai_advanced_template(
                topic=topic,
                exclude_formats=used_template_formats,
            )
        elif normalized_competency_type == "sql":
            base_question = build_sql_advanced_template(
                topic=topic,
                exclude_formats=used_template_formats,
            )
        elif normalized_competency_type == "python":
            base_question = build_python_advanced_template(
                topic=topic,
                exclude_formats=used_template_formats,
            )
        elif normalized_competency_type == "java":
            base_question = build_java_advanced_template(
                topic=topic,
                exclude_formats=used_template_formats,
            )
        else:
            raise ValueError(
                f"템플릿 기반 생성을 지원하지 않는 역량입니다: {normalized_competency_type}"
            )

        selected_format = base_question.get("template_format")

        if selected_format:
            used_template_formats.append(str(selected_format))

        base_questions.append(base_question)

    logger.info(
        f"LangGraph [Template]: base_questions={len(base_questions)}, "
        f"competency={normalized_competency_type}, used_formats={used_template_formats}"
    )

    return {
        **state,
        "raw_questions": base_questions,
    }

def generation_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    planner/template 결과를 실제 문제 후보(raw_questions)로 변환한다.

    planner 경로:
    - plans 기반으로 LLM 문제 생성

    template 경로:
    - base template에 choices/explanation 생성
    - lock_choices=True인 경우 question_choice_generator 내부에서 고정 선택지를 사용
    """
    generation_mode = state.get("generation_mode")
    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "중급")
    count = int(state.get("count", 1))
    score = int(state.get("score", 1))
    question_type = state.get("question_type", "multiple_choice")
    normalized_competency_type = state.get("normalized_competency_type")

    if generation_mode == "planner":
        plans = state.get("plans", [])

        if not plans:
            raise ValueError("Planner 기반 생성을 위한 설계서가 없습니다.")

        generated_questions = generate_questions_from_plans(
            topic=topic,
            difficulty=difficulty,
            plans=plans,
            count=count,
            score=score,
            question_type=question_type,
            competency_type=normalized_competency_type,
        )

        logger.info(
            f"LangGraph [Generation:Planner]: generated={len(generated_questions)}, "
            f"competency={normalized_competency_type}, difficulty={difficulty}"
        )

        return {
            **state,
            "raw_questions": generated_questions,
        }

    if generation_mode == "template":
        base_questions = state.get("raw_questions", [])

        if not base_questions:
            raise ValueError("Template 기반 생성을 위한 base_questions가 없습니다.")

        if normalized_competency_type == "ai":
            generated_questions = generate_choices_for_template_questions_batch(
                base_questions
            )
        else:
            generated_questions = [
                generate_choices_for_template_question(base_question)
                for base_question in base_questions
            ]

        logger.info(
            f"LangGraph [Generation:Template]: generated={len(generated_questions)}, "
            f"competency={normalized_competency_type}, difficulty={difficulty}"
        )

        return {
            **state,
            "raw_questions": generated_questions,
        }

    raise ValueError(f"지원하지 않는 generation_mode입니다: {generation_mode}")

def rag_generation_node(state: QuestionGenerationState) -> QuestionGenerationState:
    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "중급")
    count = state.get("count", 1)
    score = state.get("score", 3)
    question_type = state.get("question_type", "multiple_choice")
    competency_type = state.get("normalized_competency_type") or state.get("competency_type")
    rag_context = state.get("rag_context")

    if not rag_context:
        raise ValueError("rag_context가 없어 RAG 기반 문제를 생성할 수 없습니다.")

    generated_questions = generate_questions_from_context(
        context=rag_context,
        topic=topic,
        difficulty=difficulty,
        count=count,
        score=score,
        question_type=question_type,
        competency_type=competency_type,
    )

    generated_questions = generated_questions[:count]

    logger.info(
        f"LangGraph [Generation:RAG]: generated={len(generated_questions)}, "
        f"competency={competency_type}, difficulty={difficulty}"
    )

    return {
        **state,
        "raw_questions": generated_questions,
    }
    
def validation_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    생성된 문제 후보를 validator로 검증한다.
    DB 저장은 다음 단계 save_node에서 처리한다.
    """
    raw_questions = state.get("raw_questions", [])
    question_type = state.get("question_type", "multiple_choice")
    difficulty = state.get("difficulty", "중급")
    score = int(state.get("score", 1))
    count = int(state.get("count", 1))

    if not raw_questions:
        raise ValueError("검증할 생성 문제가 없습니다.")

    validated_questions = validate_questions(
        questions=raw_questions,
        question_type=question_type,
        difficulty=difficulty,
        score=score,
    )

    if not validated_questions:
        raise ValueError("LangGraph 검증을 통과한 문제가 없습니다.")

    validated_questions = validated_questions[:count]

    logger.info(
        f"LangGraph [Validation]: input={len(raw_questions)}, "
        f"validated={len(validated_questions)}, difficulty={difficulty}"
    )

    return {
        **state,
        "validated_questions": validated_questions,
    }

def save_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    검증된 문제를 questions 테이블에 pending 상태로 저장한다.

    주의:
    - db 세션은 state["db"]로 전달받는다.
    - 기존 API의 save_generated_questions()와 동일한 저장 정책을 LangGraph 내부에서 수행한다.
    """
    db = state.get("db")

    if db is None:
        raise ValueError("DB 세션이 없습니다. state['db']가 필요합니다.")

    validated_questions = state.get("validated_questions", [])
    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "중급")
    score = int(state.get("score", 1))
    question_type = state.get("question_type", "multiple_choice")
    normalized_competency_type = state.get("normalized_competency_type")

    if not validated_questions:
        raise ValueError("저장할 검증 완료 문제가 없습니다.")

    saved_questions = []

    db_question_type = "essay" if question_type == "coding" else question_type

    for q in validated_questions:
        choices = q.get("choices", [])

        if not isinstance(choices, list):
            choices = []

        normalized_choices = []

        for choice in choices:
            if isinstance(choice, dict):
                normalized_choices.append(choice.get("text") or choice.get("answer") or "")
            else:
                normalized_choices.append(str(choice))

        answer = q.get("answer", "")
        explanation = q.get("explanation", "")

        if question_type == "multiple_choice":
            try:
                answer = int(answer)
            except Exception:
                continue

            if answer < 1 or answer > 5:
                continue

            if len(normalized_choices) != 5:
                continue

            explanation_match = re.search(
                r"(?:정답은|정답\s*:|답은)\s*(\d)\s*번|(\d)\s*번이\s*정답",
                str(explanation),
            )

            if explanation_match:
                explanation_answer = explanation_match.group(1) or explanation_match.group(2)

                try:
                    explanation_answer = int(explanation_answer)
                except Exception:
                    explanation_answer = None

                if explanation_answer is not None and explanation_answer != answer:
                    continue

            answer_json = str(answer)

        else:
            normalized_choices = []
            answer_json = str(answer or "")

        tags = q.get("competency_tags", [topic])

        if isinstance(tags, str):
            tags = [tags]

        if not isinstance(tags, list):
            tags = [topic]

        normalized_tags = []

        for tag in tags:
            if isinstance(tag, dict):
                normalized_tags.extend([str(v) for v in tag.values()])
            else:
                normalized_tags.append(str(tag))
        
        generation_source = state.get("generation_source", "general")
        ai_generation_type = "rag" if generation_source == "rag" else "general_graph"
        
        question = Question(
            source_type="ai",
            question_type=db_question_type,
            title=q.get("title", ""),
            body=q.get("body", ""),
            choices_json=json.dumps(normalized_choices, ensure_ascii=False),
            answer_json=answer_json,
            explanation=explanation,
            difficulty=q.get("difficulty", difficulty),
            competency_type=normalized_competency_type or topic,
            competency_tags_json=json.dumps(normalized_tags, ensure_ascii=False),
            score=q.get("score", score),
            review_status="pending",
            ai_generation_type=ai_generation_type,
            created_by=None,
        )

        db.add(question)
        db.flush()

        saved_questions.append({
            "id": question.question_id,
            "title": question.title,
            "body": question.body,
            "choices": normalized_choices,
            "answer": answer_json,
            "explanation": question.explanation,
            "difficulty": question.difficulty,
            "competency_type": question.competency_type,
            "competency_tags": normalized_tags,
            "score": question.score,
            "review_status": question.review_status,
            "ai_generation_type": question.ai_generation_type,
            "created_at": question.created_at.isoformat() if question.created_at else None,
        })

    if not saved_questions:
        raise ValueError("검증된 문제가 있었지만 저장 가능한 문제가 없습니다.")

    logger.info(
        f"LangGraph [Save]: saved={len(saved_questions)}, "
        f"competency={normalized_competency_type}, difficulty={difficulty}"
    )

    return {
        **state,
        "saved_questions": saved_questions,
    }