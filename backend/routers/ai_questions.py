import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Question
from ai.services.question_generator import generate_questions

router = APIRouter(prefix="/api/ai", tags=["AI Questions"])


class AIQuestionGenerateRequest(BaseModel):
    topic: str
    difficulty: str
    count: int = 1
    score: int = 1


@router.post("/generate-questions")
def generate_ai_questions(
    request: AIQuestionGenerateRequest,
    db: Session = Depends(get_db)
):
    try:
        generated_questions = generate_questions(
            topic=request.topic,
            difficulty=request.difficulty,
            count=request.count,
            score=request.score
        )

        saved_questions = []

        for q in generated_questions:
            # choices 정리
            choices = q.get("choices", [])
            if not isinstance(choices, list):
                choices = []

            # 혹시 choices가 [{"number":1,"text":"..."}] 형태로 오면 문자열 배열로 변환
            normalized_choices = []
            for choice in choices:
                if isinstance(choice, dict):
                    normalized_choices.append(choice.get("text") or choice.get("answer") or "")
                else:
                    normalized_choices.append(str(choice))

            # answer 정리: 반드시 int
            answer = q.get("answer", 0)
            try:
                answer = int(answer)
            except Exception:
                answer = 0

            # competency_tags 정리: 반드시 list[str]
            tags = q.get("competency_tags", [request.topic])

            if isinstance(tags, str):
                tags = [tags]

            if not isinstance(tags, list):
                tags = [request.topic]

            normalized_tags = []
            for tag in tags:
                if isinstance(tag, dict):
                    normalized_tags.extend([str(v) for v in tag.values()])
                else:
                    normalized_tags.append(str(tag))

            question = Question(
                source_type="ai",
                question_type="multiple_choice",
                title=q.get("title", ""),
                body=q.get("body", ""),
                choices_json=json.dumps(normalized_choices, ensure_ascii=False),
                answer_json=str(answer),
                explanation=q.get("explanation", ""),
                difficulty=q.get("difficulty", request.difficulty),
                competency_type=q.get("competency_type", request.topic),
                competency_tags_json=json.dumps(normalized_tags, ensure_ascii=False),
                score=q.get("score", request.score),
                review_status="pending",
                created_by=None
            )

            db.add(question)
            db.flush()

            saved_questions.append({
                "id": question.question_id,
                "title": question.title,
                "body": question.body,
                "choices": normalized_choices,
                "answer": answer,
                "explanation": question.explanation,
                "difficulty": question.difficulty,
                "competency_type": question.competency_type,
                "competency_tags": normalized_tags,
                "score": question.score,
                "review_status": question.review_status
            })

        db.commit()

        return {
            "message": "AI 문제가 생성되었습니다.",
            "count": len(saved_questions),
            "questions": saved_questions
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))