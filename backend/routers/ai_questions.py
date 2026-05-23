import json
from typing import Literal
from database import get_db
from sqlalchemy.orm import Session
from pydantic import BaseModel,Field
from fastapi import APIRouter, Depends, HTTPException
from ai.questions.graph_runner import run_question_generation_graph
from ai.questions.topic_validator import validate_topic_for_competency
from ai.core.config import normalize_competency_type, COMPETENCY_KEYWORDS
from models import Question

# 새로운 파일
from ai.question_v2.models import QuestionV2Request
from ai.question_v2.service import generate_ai_questions_v2


router = APIRouter(prefix="/api/ai", tags=["AI Questions"])


class AIQuestionGenerateRequest(BaseModel):
    topic: str
    difficulty: Literal["초급", "중급", "고급"]
    count: int = Field(default=1, ge=1, le=10)
    question_type: Literal["multiple_choice", "essay", "coding"] = "multiple_choice"
    competency_type: str | None = None

class AIQuestionGenerateFromDocumentRequest(BaseModel):
    topic: str
    difficulty: Literal["초급", "중급", "고급"]
    count: int = 1
    top_k: int = 5
    question_type: Literal["multiple_choice", "essay", "coding"] = "multiple_choice"
    competency_type: str | None = None
    search_query: str | None = None
    search_mode: Literal["vector", "keyword", "hybrid"] = "hybrid"

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

        initial_state = {
            "topic": request.topic,
            "difficulty": request.difficulty,
            "count": request.count,
            "score": score,
            "question_type": request.question_type,
            "competency_type": normalized_competency,
            "retry_count": 0,
            "max_retries": 1,
            "db": db,
        }

        result = run_question_generation_graph(initial_state)

        saved_questions = result.get("saved_questions", [])

        db.commit()

        return {
            "message": "AI 문제가 생성되었습니다.",
            "source": "general_graph",
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
        normalized_competency = normalize_competency_type(request.competency_type)

        score = get_score_by_difficulty(request.difficulty)

        search_query = request.search_query or build_enhanced_rag_query(
            request.topic,
            normalized_competency,
        )

        initial_state = {
            "generation_source": "rag",
            "topic": request.topic,
            "difficulty": request.difficulty,
            "count": request.count,
            "score": score,
            "question_type": request.question_type,
            "competency_type": normalized_competency,
            "search_query": search_query,
            "search_mode": request.search_mode,
            "top_k": request.top_k,
            "retry_count": 0,
            "max_retries": 1,
            "db": db,
        }

        result = run_question_generation_graph(initial_state)

        saved_questions = result.get("saved_questions", [])

        db.commit()

        return {
            "message": "문서 기반 AI 문제가 생성되었습니다.",
            "source": "rag",
            "count": len(saved_questions),
            "questions": saved_questions,
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


@router.post("/v2/generate-questions")
def generate_ai_questions_v2_api(
    request: QuestionV2Request,
    db: Session = Depends(get_db),
):
    try:
        questions = generate_ai_questions_v2(request)

        score = get_score_by_difficulty(request.difficulty)
        saved_questions = []

        for question in questions:
            choices = question.choices or []

            if len(choices) != 5:
                continue

            answer = int(question.answer)

            if answer < 1 or answer > 5:
                continue

            db_question = Question(
                source_type="ai",
                question_type=request.question_type,
                title=question.title,
                body=question.body,
                choices_json=json.dumps(choices, ensure_ascii=False),
                answer_json=str(answer),
                explanation=question.explanation,
                difficulty=request.difficulty,
                competency_type=request.competency_type,
                competency_tags_json=json.dumps(
                    [request.topic, question.question_format or ""],
                    ensure_ascii=False,
                ),
                score=score,
                review_status="pending",
                ai_generation_type="ai_question_v2",
                created_by=None,
            )

            db.add(db_question)
            db.flush()

            saved_questions.append({
                "id": db_question.question_id,
                "title": db_question.title,
                "body": db_question.body,
                "choices": choices,
                "answer": str(answer),
                "explanation": db_question.explanation,
                "difficulty": db_question.difficulty,
                "competency_type": db_question.competency_type,
                "competency_tags": [request.topic, question.question_format or ""],
                "score": db_question.score,
                "review_status": db_question.review_status,
                "ai_generation_type": db_question.ai_generation_type,
                "created_at": db_question.created_at.isoformat() if db_question.created_at else None,
            })

        if not saved_questions:
            raise ValueError("AI V2 문제가 생성되었지만 저장 가능한 문제가 없습니다.")

        db.commit()

        return {
            "message": "AI V2 문제가 생성되었습니다.",
            "source": "ai_question_v2",
            "count": len(saved_questions),
            "questions": saved_questions,
        }

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

