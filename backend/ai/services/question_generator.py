import json
from ai.client import client


def generate_questions(topic: str, difficulty: str, count: int = 1, score: int = 1):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
너는 IT 역량진단 문제은행의 문제 출제 전문가다.

반드시 JSON 배열만 출력해라.
마크다운 코드블록, 설명 문장, 추가 텍스트는 절대 출력하지 마라.

객관식 문제는 반드시 보기 5개를 생성한다.
정답은 반드시 1개만 존재해야 한다.
answer는 0부터 시작하는 보기 index로 반환한다.
예: 첫 번째 보기가 정답이면 0, 두 번째 보기가 정답이면 1.
"""
            },
            {
                "role": "user",
                "content": f"""
다음 조건에 맞는 객관식 5지선다 문제를 {count}개 생성해라.

조건:
- 주제: {topic}
- 난이도: {difficulty}
- 배점: {score}
- 문제 유형: multiple_choice

반환 형식은 반드시 아래 JSON 배열 구조를 따라라.

[
  {{
    "title": "문제 제목",
    "body": "문제 본문",
    "choices": ["보기1", "보기2", "보기3", "보기4", "보기5"],
    "answer": 1,
    "explanation": "해설",
    "difficulty": "{difficulty}",
    "competency_type": "{topic}",
    "competency_tags": ["{topic}"],
    "score": {score}
  }}
]
"""
            }
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"AI 응답을 JSON으로 파싱할 수 없습니다: {content}")