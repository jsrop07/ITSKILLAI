import os
import json
from typing import Any
from openai import OpenAI

from services.result_analysis import build_result_analysis_report


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


AI_REPORT_SYSTEM_PROMPT = """
너는 IT 역량진단 결과 분석가다.

응시자의 시험 결과, 정오답 정보, 문제 제목, 문제 본문, 해설을 바탕으로
AI 세부 영역별 이해도를 진단한다.

세부 영역 후보:
- RAG
- LLM
- ModelOps
- ML
- DL
- AI 기본 개념

규칙:
- 제공된 문제와 오답 근거에 기반해서만 분석한다.
- 없는 내용을 추측하지 않는다.
- 점수만 반복하지 말고, 어떤 개념 판단이 부족했는지 설명한다.
- 응시자에게 보여줄 수 있는 존댓말로 작성한다.
- 너무 길게 쓰지 말고, 결과 화면에서 읽기 좋은 분량으로 작성한다.
- 문제 번호나 선택지 번호를 과도하게 나열하지 않는다.
- 추천 학습 방향은 우선순위 중심으로 제시한다.
"""


def _normalize_answer(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _readable_choice_answer(value: Any, choices: Any) -> str:
    normalized = _normalize_answer(value)
    if not normalized:
        return "-"

    if not isinstance(choices, list):
        return normalized

    try:
        idx = int(normalized)
        if 1 <= idx <= len(choices):
            return f"{idx}번. {choices[idx - 1]}"
    except (TypeError, ValueError):
        pass

    return normalized


def _parse_question_ids(diagnosis) -> list[int]:
    if not diagnosis or not getattr(diagnosis, "question_idxs", None):
        return []

    return [
        int(x.strip())
        for x in str(diagnosis.question_idxs).split(",")
        if x.strip().isdigit()
    ]


def _parse_answer_data(record) -> list[str]:
    if not record or not getattr(record, "answer_data", None):
        return []

    return [x.strip() for x in str(record.answer_data).split(",")]


def build_ai_report_evidence(record, diagnosis, questions) -> dict[str, Any]:
    """
    AI 리포트 생성용 evidence 구성.
    통계 분석 결과 + 문제별 정오답 상세를 함께 구성한다.
    """

    analysis_report = build_result_analysis_report(
        record=record,
        diagnosis=diagnosis,
        questions=questions,
    )

    question_ids = _parse_question_ids(diagnosis)
    submitted_answers = _parse_answer_data(record)

    question_map = {
        int(q.question_id): q
        for q in questions
        if getattr(q, "question_id", None) is not None
    }

    answer_items = []

    for index, question_id in enumerate(question_ids):
        question = question_map.get(question_id)
        if not question:
            continue

        submitted_answer = submitted_answers[index] if index < len(submitted_answers) else ""
        correct_answer = _normalize_answer(getattr(question, "answer_json", None))
        is_correct = bool(submitted_answer) and submitted_answer == correct_answer

        choices = getattr(question, "choices_json", None)

        answer_items.append({
            "question_id": question.question_id,
            "title": getattr(question, "title", "") or "",
            "body": getattr(question, "body", "") or "",
            "difficulty": getattr(question, "difficulty", None),
            "competency_type": getattr(question, "competency_type", None),
            "is_correct": is_correct,
            "submitted_answer": _readable_choice_answer(submitted_answer, choices),
            "correct_answer": _readable_choice_answer(correct_answer, choices),
            "explanation": getattr(question, "explanation", None),
        })

    return {
        "record_id": record.record_id,
        "diagnosis_title": getattr(diagnosis, "title", "") if diagnosis else "",
        "summary": analysis_report.get("summary", {}),
        "competency_stats": analysis_report.get("competency_stats", []),
        "difficulty_stats": analysis_report.get("difficulty_stats", []),
        "wrong_answers": analysis_report.get("wrong_answers", []),
        "answer_items": answer_items,
    }


def generate_ai_result_report(record, diagnosis, questions) -> str:
    """
    LLM을 호출해서 응시자용 AI 종합 진단 리포트를 생성한다.
    """

    evidence = build_ai_report_evidence(
        record=record,
        diagnosis=diagnosis,
        questions=questions,
    )

    user_prompt = f"""
    아래 시험 결과 evidence를 바탕으로 응시자에게 보여줄 AI 종합 진단 리포트를 작성해줘.

    반드시 아래 형식을 지켜줘.

    [종합 진단]
    2~3문장으로 전체 결과를 요약한다.

    [부족한 세부 영역]
    - RAG / LLM / ModelOps / ML / DL / AI 기본 개념 중 실제 오답 근거가 있는 영역만 작성한다.
    - 각 항목은 "영역명: 부족한 판단 기준" 형태로 작성한다.
    - 오답이 1개뿐이면 억지로 여러 영역을 만들지 않는다.

    [추천 학습 순서]
    1. 가장 먼저 복습할 주제
    2. 그 다음 복습할 주제
    3. 확장 학습할 주제

    작성 규칙:
    - 없는 내용을 추측하지 마.
    - 오답 문제 제목, 본문, 해설에 근거해서만 판단해.
    - 점수만 반복하지 말고 왜 그런 결과가 나왔는지 설명해.
    - 응시자에게 보여줄 수 있는 존댓말로 작성해.
    - 마크다운 표는 쓰지 마.
    - 너무 길게 쓰지 마.
    - 각 섹션 제목은 반드시 [종합 진단], [부족한 세부 영역], [추천 학습 순서]를 사용해.
    - 정답률이 80% 이상이면 "부족하다"는 표현을 과하게 사용하지 말고,
    - 보완하면 좋은 부분과 심화 학습 방향 중심으로 작성한다.

    시험 결과 evidence:
    {json.dumps(evidence, ensure_ascii=False, indent=2)}
    """
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": AI_REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content
    return content.strip() if content else ""