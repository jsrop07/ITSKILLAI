from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session

from database import get_db
from ai.questions.topic_validator import validate_topic_for_competency
from ai.core.config import normalize_competency_type, COMPETENCY_KEYWORDS
from typing import Literal
from ai.questions.graph_runner import run_question_generation_graph

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