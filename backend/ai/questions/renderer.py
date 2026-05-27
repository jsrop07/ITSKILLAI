import json
import os
from typing import Any
from dotenv import load_dotenv


from openai import OpenAI

from ai.questions.models import EvidencePack, GeneratedQuestion
from ai.questions.prompts import QUESTION_RENDER_SYSTEM_PROMPT

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or start >= end:
        raise ValueError("LLM 응답에서 JSON 객체를 찾을 수 없습니다.")

    json_text = cleaned[start : end + 1]
    return json.loads(json_text)

def _build_renderer_payload(evidence_pack: EvidencePack) -> dict[str, Any]:
    payload = {
        "evidence_pack": evidence_pack.model_dump(),
    }

    if evidence_pack.answer_style == "find_incorrect":
        payload["find_incorrect_mapping"] = {
            "answer_choice_must_come_from": "inappropriate_points",
            "distractor_choices_must_come_from": "appropriate_points",
            "inappropriate_points": evidence_pack.correct_points,
            "appropriate_points": evidence_pack.wrong_points,
            "critical_rule": (
                "이 문제는 오답 고르기입니다. "
                "정답 선택지는 현재 scenario의 목표에 맞지 않는 부적절한 대응이어야 합니다. "
                "오답 선택지들은 현재 scenario의 목표에 맞는 적절한 대응이어야 합니다. "
                "evidence_pack.correct_points는 이름과 달리 이 문제에서는 부적절한 대응 정답 선택지의 근거입니다. "
                "evidence_pack.wrong_points는 이 문제에서는 적절한 대응 오답 선택지의 근거입니다."
            ),
        }

    return payload

def render_question_from_evidence(
    *,
    evidence_pack: EvidencePack,
    model: str = "gpt-4o-mini",
) -> GeneratedQuestion:
    user_payload = _build_renderer_payload(evidence_pack)

    response = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": QUESTION_RENDER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
            },
        ],
    )

    content = response.choices[0].message.content or ""
    data = _extract_json_object(content)

    question = GeneratedQuestion(
        title=data["title"],
        body=data["body"],
        choices=data["choices"],
        answer=data["answer"],
        explanation=data["explanation"],
        question_format=evidence_pack.question_format,
        answer_style=evidence_pack.answer_style,
        difficulty=evidence_pack.difficulty,
        competency_type="ai",
    )
    # question = _ensure_body_context_in_question(
    #     question=question,
    #     evidence_pack=evidence_pack,
    # )
    return question

def _ensure_body_context_in_question(
    *,
    question: GeneratedQuestion,
    evidence_pack: EvidencePack,
) -> GeneratedQuestion:
    if not evidence_pack.body_context:
        return question

    if evidence_pack.body_context.strip() in question.body:
        return question

    question.body = (
        f"{evidence_pack.body_context.strip()}\n\n"
        f"{question.body.strip()}"
    ).strip()

    return question