# backend/ai/questions/graph_nodes.py
import json
import re
import logging
from models import Question
from ai.questions.models import QuestionV2Request
from ai.questions.service import generate_ai_questions_v2
from ai.core.config import normalize_competency_type
from ai.questions.graph_state import QuestionGenerationState
from ai.questions.topic_validator import validate_topic_for_competency
from ai.rag.document_service import build_context_and_evidence_from_search_results

logger = logging.getLogger("uvicorn.info")


# ───────────────────────────────────────────────────────────────────────────────
# 공통 노드
# ───────────────────────────────────────────────────────────────────────────────


def normalize_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    competency_type을 내부 표준 값으로 정규화한다.
    예:
    - database -> sql
    - ai_data  -> ai
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


def route_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    generation_source와 difficulty, competency_type에 따라 generation_mode를 결정한다.

    정책:
    - competency_type != "ai" → ValueError (현재 V2는 AI만 지원)
    - difficulty == "고급" → ValueError (V2 고급 template 이관 전)
    - generation_source == "rag" → question_v2_rag
    - 그 외 (초급/중급) → question_v2
    """
    difficulty = state.get("difficulty")
    normalized_competency_type = state.get("normalized_competency_type")
    generation_source = state.get("generation_source", "general")

    if normalized_competency_type != "ai":
        raise ValueError(
            f"현재 LangGraph V2는 competency_type='ai'만 지원합니다. "
            f"요청된 역량: {normalized_competency_type}"
        )

    if difficulty == "고급":
        raise ValueError(
            "AI 고급 문제는 현재 V2 통합 준비 중입니다. "
            "기존 고급 template을 V2 evidence 구조로 이관한 뒤 지원됩니다."
        )

    if generation_source == "rag":
        generation_mode = "question_v2_rag"
    else:
        generation_mode = "question_v2"

    logger.info(
        f"LangGraph [Route]: source={generation_source}, difficulty={difficulty}, "
        f"competency={normalized_competency_type}, generation_mode={generation_mode}"
    )

    return {
        **state,
        "generation_mode": generation_mode,
    }


def route_by_generation_mode(state: QuestionGenerationState) -> str:
    generation_mode = state.get("generation_mode", "question_v2")

    if generation_mode == "question_v2_rag":
        return "question_v2_rag"

    return "question_v2"


# ───────────────────────────────────────────────────────────────────────────────
# RAG 검색 노드
# ───────────────────────────────────────────────────────────────────────────────


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

    rag_payload = build_context_and_evidence_from_search_results(
        db=db,
        query=search_query,
        top_k=top_k,
        category=competency_type,
        search_mode=search_mode,
    )

    rag_context = rag_payload.get("context", "")
    rag_evidence = rag_payload.get("evidence")

    if not rag_context or not rag_context.strip():
        raise ValueError("RAG 검색 결과가 비어 있어 문서 기반 문제를 생성할 수 없습니다.")

    logger.info(
        f"LangGraph [Retrieval]: context_length={len(rag_context)}, "
        f"evidence_docs={len((rag_evidence or {}).get('documents', []))}"
    )

    return {
        **state,
        "rag_context": rag_context,
        "rag_evidence": rag_evidence,
    }


# ───────────────────────────────────────────────────────────────────────────────
# V2 문제 생성 노드 (메인)
# ───────────────────────────────────────────────────────────────────────────────


def question_generation_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    Question V2를 호출해 문제를 생성한다.
    일반 생성(question_v2)과 RAG 기반 생성(question_v2_rag) 모두 이 노드에서 처리한다.
    RAG의 경우 rag_context가 V2 service에서 EvidencePack.body_context로 주입된다.
    """
    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "중급")
    count = int(state.get("count", 1))
    question_type = state.get("question_type", "multiple_choice")
    competency_type = state.get("normalized_competency_type") or state.get("competency_type")
    rag_context = state.get("rag_context")

    if competency_type != "ai":
        raise ValueError("Question V2는 현재 AI 역량만 지원합니다.")

    request = QuestionV2Request(
        topic=topic,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
        competency_type="ai",
    )

    generated_questions = generate_ai_questions_v2(
        request=request,
        rag_context=rag_context,
    )

    raw_questions = []
    for q in generated_questions:
        raw_questions.append({
            "title": q.title,
            "body": q.body,
            "choices": q.choices,
            "answer": q.answer,
            "explanation": q.explanation,
            "difficulty": q.difficulty or difficulty,
            "competency_type": q.competency_type or "ai",
            "competency_tags": [topic, q.question_format or ""],
            "score": state.get("score", 1),
            "question_format": q.question_format,
            "answer_style": q.answer_style,
        })

    logger.info(
        f"LangGraph [Generation:V2]: generated={len(raw_questions)}, "
        f"difficulty={difficulty}, rag_context={bool(rag_context)}"
    )

    return {
        **state,
        "raw_questions": raw_questions,
    }


# ───────────────────────────────────────────────────────────────────────────────
# Validation 노드 (간소화)
# ───────────────────────────────────────────────────────────────────────────────


def validation_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    V2 service 내부에서 이미 validate_generated_question / validate_generated_questions를
    통과한 문제만 반환되므로, 여기서는 존재 여부와 수량만 확인한다.
    기존 validator를 다시 적용하면 규칙 충돌이 발생하므로 사용하지 않는다.
    """
    raw_questions = state.get("raw_questions", [])
    count = int(state.get("count", 1))

    if not raw_questions:
        raise ValueError("검증할 생성 문제가 없습니다.")

    if len(raw_questions) < count:
        raise ValueError(
            f"생성된 문제 수가 부족합니다. "
            f"generated={len(raw_questions)}, required={count}"
        )

    validated_questions = raw_questions[:count]

    logger.info(
        f"LangGraph [Validation]: raw={len(raw_questions)}, "
        f"validated={len(validated_questions)}"
    )

    return {
        **state,
        "validated_questions": validated_questions,
        "retry_count": state.get("retry_count", 0),
    }


# ───────────────────────────────────────────────────────────────────────────────
# Save 노드
# ───────────────────────────────────────────────────────────────────────────────


def save_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    검증된 문제를 questions 테이블에 pending 상태로 저장한다.

    ai_generation_type 구분:
    - generation_mode == "question_v2_rag" → "ai_question_v2_rag"
    - generation_mode == "question_v2"     → "ai_question_v2"
    - fallback: generation_source 기준
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
    generation_mode = state.get("generation_mode")
    generation_source = state.get("generation_source", "general")
    rag_evidence = state.get("rag_evidence")

    if not validated_questions:
        raise ValueError("저장할 검증 완료 문제가 없습니다.")

    # ai_generation_type 결정
    if generation_mode == "question_v2_rag":
        ai_generation_type = "ai_question_v2_rag"
    elif generation_mode == "question_v2":
        ai_generation_type = "ai_question_v2"
    elif generation_source == "rag":
        ai_generation_type = "rag"
    else:
        ai_generation_type = "general_graph"

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
        rag_evidence_json = None

        if ai_generation_type == "ai_question_v2_rag" and rag_evidence:
            rag_evidence_json = json.dumps(rag_evidence, ensure_ascii=False)

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
            rag_evidence_json=rag_evidence_json,
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
            "has_rag_evidence": bool(rag_evidence_json),
            "rag_evidence": rag_evidence if rag_evidence_json else None,
        })

    if not saved_questions:
        raise ValueError("검증된 문제가 있었지만 저장 가능한 문제가 없습니다.")

    logger.info(
        f"LangGraph [Save]: saved={len(saved_questions)}, "
        f"competency={normalized_competency_type}, difficulty={difficulty}, "
        f"ai_generation_type={ai_generation_type}"
    )

    return {
        **state,
        "saved_questions": saved_questions,
    }