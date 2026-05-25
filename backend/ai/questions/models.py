from typing import Any, Literal

from pydantic import BaseModel, Field


Difficulty = Literal["초급", "중급"]
QuestionType = Literal["multiple_choice"]
CompetencyType = Literal["ai"]


class QuestionV2Request(BaseModel):
    topic: str = Field(..., min_length=1)
    difficulty: Difficulty
    count: int = Field(default=5, ge=1, le=5)
    question_type: QuestionType = "multiple_choice"
    competency_type: CompetencyType = "ai"


class QuestionFormatPlan(BaseModel):
    index: int
    question_format: str
    answer_style: str
    focus: str


class EvidencePack(BaseModel):
    topic: str
    normalized_topic: str
    difficulty: str
    question_format: str
    answer_style: str
    focus: str
    concepts: list[str]
    correct_points: list[str]
    wrong_points: list[str]
    scenario: str | None = None
    log_or_metric: dict[str, Any] | None = None
    body_context: str | None = None


class GeneratedQuestion(BaseModel):
    title: str
    body: str
    choices: list[str]
    answer: int
    explanation: str
    question_format: str | None = None
    answer_style: str | None = None
    difficulty: str | None = None
    competency_type: str | None = None