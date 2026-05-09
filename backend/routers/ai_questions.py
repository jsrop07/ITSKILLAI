import re
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Question
from ai.services.topic_validator import validate_topic_for_competency
from ai.services.question_generator import (
    generate_questions,
    generate_questions_from_context
)
from ai.rag.document_service import build_context_from_search_results
from ai.services.competency_config import normalize_competency_type, COMPETENCY_KEYWORDS
from typing import Literal

router = APIRouter(prefix="/api/ai", tags=["AI Questions"])


class AIQuestionGenerateRequest(BaseModel):
    topic: str
    difficulty: Literal["초급", "중급", "고급"]
    count: int = 1
    question_type: Literal["multiple_choice", "essay", "coding"] = "multiple_choice"
    competency_type: str | None = None
    search_query: str | None = None


class AIQuestionGenerateFromDocumentRequest(BaseModel):
    topic: str
    difficulty: Literal["초급", "중급", "고급"]
    count: int = 1
    top_k: int = 5
    question_type: Literal["multiple_choice", "essay", "coding"] = "multiple_choice"
    competency_type: str | None = None
    search_query: str | None = None
    search_mode: Literal["vector", "keyword", "hybrid"] = "hybrid"

def save_generated_questions(
    generated_questions,
    db: Session,
    topic: str,
    difficulty: str,
    score: int,
    question_type: str = "multiple_choice",
    competency_type: str | None = None,
    ai_generation_type: str | None = None,
):
    saved_questions = []

    db_question_type = "essay" if question_type == "coding" else question_type

    for q in generated_questions:
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

            # 객관식 정답은 1~5 기준
            if answer < 1 or answer > 5:
                continue

            # 해설에 "정답은 N번"이 있는데 answer와 다르면 저장하지 않음
            explanation_match = re.search(
                r"(?:정답은|정답\s*:|답은)\s*(\d)\s*번|(\d)\s*번이\s*정답",
                str(explanation)
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
            # 서술형/코드작성형은 문자열 답안
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

        question = Question(
            source_type="ai",
            question_type=db_question_type,
            title=q.get("title", ""),
            body=q.get("body", ""),
            choices_json=json.dumps(normalized_choices, ensure_ascii=False),
            answer_json=answer_json,
            explanation=explanation,
            difficulty=q.get("difficulty", difficulty),
            competency_type=competency_type or topic,
            competency_tags_json=json.dumps(normalized_tags, ensure_ascii=False),
            score=q.get("score", score),
            review_status="pending",
            ai_generation_type=ai_generation_type,
            created_by=None
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
            "created_at": question.created_at.isoformat() if question.created_at else None
        })

    return saved_questions

@router.post("/generate-questions")
def generate_ai_questions(
    request: AIQuestionGenerateRequest,
    db: Session = Depends(get_db)
):
    try:
        # 역량 유형 정규화
        normalized_competency = normalize_competency_type(request.competency_type)

        validate_topic_for_competency(
            competency_type=normalized_competency,
            topic=request.topic,
        )

        score = get_score_by_difficulty(request.difficulty)

        generated_questions = generate_questions(
            topic=request.topic,
            difficulty=request.difficulty,
            count=request.count,
            score=score,
            question_type=request.question_type,
            competency_type=normalized_competency,
        )
        
        generated_questions = generated_questions[:request.count]

        saved_questions = save_generated_questions(
            generated_questions=generated_questions,
            db=db,
            topic=request.topic,
            difficulty=request.difficulty,
            score=score,
            question_type=request.question_type,
            competency_type=normalized_competency,
            ai_generation_type="general",
        )

        db.commit()

        return {
            "message": "AI 문제가 생성되었습니다.",
            "count": len(saved_questions),
            "questions": saved_questions
        }

    except HTTPException:
        db.rollback()
        raise

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-questions-from-document")
def generate_ai_questions_from_document(
    request: AIQuestionGenerateFromDocumentRequest,
    db: Session = Depends(get_db)
):
    try:
        # 역량 유형 정규화
        normalized_competency = normalize_competency_type(request.competency_type)

        validate_topic_for_competency(
            competency_type=normalized_competency,
            topic=request.topic,
        )

        score = get_score_by_difficulty(request.difficulty)

        rag_query = request.search_query or build_enhanced_rag_query(
            topic=request.topic,
            competency_type=normalized_competency,
        )

        context = build_context_from_search_results(
            db=db,
            query=rag_query,
            top_k=request.top_k,
            category=normalized_competency,
            search_mode=request.search_mode,
        )

        if not context or not context.strip():
            raise HTTPException(
                status_code=400,
                detail="검색된 문서 내용이 없습니다. 문서 업로드 후 인덱싱을 먼저 실행해주세요."
            )

        generated_questions = generate_questions_from_context(
            topic=request.topic,
            context=context,
            difficulty=request.difficulty,
            count=request.count,
            score=score,
            question_type=request.question_type,
            # role=request.role,
            competency_type=normalized_competency,
        )
        
        generated_questions = generated_questions[:request.count]
        
        saved_questions = save_generated_questions(
            generated_questions=generated_questions,
            db=db,
            topic=request.topic,
            difficulty=request.difficulty,
            score=score,
            question_type=request.question_type,
            competency_type=normalized_competency,
            ai_generation_type="rag",
        )

        db.commit()

        return {
            "message": "문서 기반 AI 문제가 생성되었습니다.",
            "source": "rag",
            "count": len(saved_questions),
            "questions": saved_questions
        }

    except HTTPException:
        db.rollback()
        raise

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def get_score_by_difficulty(difficulty: str, default_score: int = 1):
    score_map = {
        "초급": 1,
        "중급": 3,
        "고급": 5,
    }
    return score_map.get(difficulty, default_score)

def build_enhanced_rag_query(topic: str, competency_type: str | None = None) -> str:
    base_query = topic.strip()
    
    # 정규화
    normalized_type = normalize_competency_type(competency_type)
    
    # competency_config의 키워드 활용 (상위 5개 정도만 추가)
    extra_keywords = COMPETENCY_KEYWORDS.get(normalized_type or "", [])[:5]

    return " ".join([base_query] + extra_keywords)