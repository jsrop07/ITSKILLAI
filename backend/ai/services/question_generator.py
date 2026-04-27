import re
import json
from ai.client import client

def _extract_answer_number_from_explanation(explanation: str):
    if not explanation:
        return None

    patterns = [
        r"정답은\s*(\d)\s*번",
        r"정답\s*:\s*(\d)\s*번",
        r"답은\s*(\d)\s*번",
        r"(\d)\s*번이\s*정답",
    ]

    for pattern in patterns:
        match = re.search(pattern, explanation)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None

    return None


def _validate_questions(questions: list, question_type: str, difficulty: str, score: int):
    if not isinstance(questions, list):
        raise ValueError("AI 응답이 JSON 배열이 아닙니다.")

    validated = []

    for q in questions:
        if not isinstance(q, dict):
            continue

        title = q.get("title")
        body = q.get("body")
        choices = q.get("choices")
        answer = q.get("answer")
        explanation = q.get("explanation")

        if not title or not body or explanation is None:
            continue

        if question_type == "multiple_choice":
            if not isinstance(choices, list) or len(choices) != 5:
                continue

            try:
                answer_int = int(answer)
            except Exception:
                continue

            # 반드시 1~5만 허용
            if answer_int < 1 or answer_int > 5:
                continue

            explanation_answer = _extract_answer_number_from_explanation(str(explanation))

            # 해설에 정답 번호가 적혀 있는데 answer와 다르면 폐기
            if explanation_answer is not None and explanation_answer != answer_int:
                continue

            q["answer"] = answer_int

        else:
            q["choices"] = []
            if answer is None or str(answer).strip() == "":
                continue
            q["answer"] = str(answer)

        q["difficulty"] = difficulty
        q["score"] = score

        if not isinstance(q.get("competency_tags"), list):
            q["competency_tags"] = []

        validated.append(q)

    return validated

def _clean_json_response(content: str):
    cleaned = content.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return json.loads(cleaned)


def _difficulty_rule(difficulty: str) -> str:
    if difficulty == "초급":
        return """
        [초급 난이도 출제 기준]
        - 개념 정의, 기본 용어, 기본 문법, 단순 동작 원리를 평가한다.
        - 복잡한 장애 상황, 아키텍처 설계, 성능 최적화 판단 문제는 출제하지 않는다.
        - 정답은 학습자가 기본 개념을 알고 있으면 명확히 고를 수 있어야 한다.
        - 단, 너무 뻔한 말장난식 문제나 상식 문제는 금지한다.
        - 보기에는 비슷한 용어를 섞되, 정답과 오답의 차이는 명확해야 한다.
        """

    if difficulty == "중급":
        return """
        [중급 난이도 출제 기준]
        - 단순 정의 암기가 아니라 개념 비교, 코드/쿼리 해석, 적용 상황 판단을 평가한다.
        - 실무에서 자주 만나는 사용 상황을 포함한다.
        - 보기들은 모두 그럴듯해야 하며, 하나의 정답만 명확해야 한다.
        - 초급 수준의 단순 용어 정의 문제는 금지한다.
        - 고급 수준의 과도한 시스템 설계나 복합 장애 분석까지 요구하지 않는다.
        """

    return """
    [고급 난이도 출제 기준]
    - 단순 정의형, 용어 암기형, '무엇인가?' 형태의 문제를 금지한다.
    - 반드시 실무 상황을 포함한다.
    - 다음 중 최소 1개 이상을 포함해야 한다:
      1) 장애 원인 분석
      2) 성능 병목 판단
      3) 설계상 트레이드오프
      4) 보안/운영 리스크 판단
      5) 복합 조건에서의 최적 선택
    - 정답은 명확해야 하지만, 피상적인 암기로 풀 수 없어야 한다.
    - 오답은 단순히 틀린 말이 아니라 실무자가 헷갈릴 수 있는 선택지로 작성한다.
    - 해설에는 정답인 이유와 주요 오답이 왜 부적절한지 포함한다.
    """


def _question_type_rule(question_type: str) -> str:
    if question_type == "multiple_choice":
        return """
        [객관식 문제 생성 규칙]
        - choices는 반드시 문자열 5개 배열이어야 한다.
        - answer는 반드시 1~5 사이의 정답 번호로 작성한다.
        - answer는 0부터 시작하는 index가 아니다.
        - 첫 번째 보기가 정답이면 answer는 1이다.
        - 두 번째 보기가 정답이면 answer는 2이다.
        - 정답은 반드시 1개만 존재해야 한다.
        - explanation에 적힌 정답 번호는 반드시 answer 값과 일치해야 한다.
        - explanation에서 "정답은 N번입니다"라고 쓸 경우 N은 반드시 answer와 같아야 한다.
        - "모두 정답", "정답 없음", "위 내용 모두" 같은 선택지는 금지한다.
        - 오답은 그럴듯해야 하지만 정답으로 해석될 수 있으면 안 된다.
        - explanation에는 정답인 이유와 주요 오답이 틀린 이유를 포함한다.

        [객관식 JSON 형식]
        {
        "title": "문제 제목",
        "body": "문제 본문",
        "choices": ["보기1", "보기2", "보기3", "보기4", "보기5"],
        "answer": 1,
        "explanation": "정답은 1번입니다. ...",
        "difficulty": "초급",
        "competency_type": "programming_language",
        "competency_tags": ["Python"],
        "score": 1
        }
        """

    if question_type == "essay":
        return """
        [서술형 문제 생성 규칙]
        - choices는 반드시 빈 배열 [] 이어야 한다.
        - answer는 모범답안 문자열이어야 한다.
        - body는 단순히 '설명하시오'가 아니라 평가 기준이 드러나도록 구체적으로 작성한다.
        - answer에는 핵심 키워드와 논리 흐름을 포함한다.
        - explanation에는 채점 기준을 포함한다.
        - 모범답안은 너무 짧지 않게 작성하되, 불필요한 장문은 피한다.

        [서술형 JSON 형식]
        {
          "title": "문제 제목",
          "body": "문제 본문",
          "choices": [],
          "answer": "모범답안",
          "explanation": "채점 기준 및 핵심 포인트",
          "difficulty": "중급",
          "competency_type": "database",
          "competency_tags": ["SQL"],
          "score": 3
        }
        """

    return """
    [코드작성형 문제 생성 규칙]
    - choices는 반드시 빈 배열 [] 이어야 한다.
    - body에는 반드시 다음 항목을 포함한다:
      1) 구현 요구사항
      2) 입력 조건
      3) 출력 조건
      4) 제한 조건 또는 예외 조건
    - answer에는 예시 코드 또는 핵심 풀이 방향을 작성한다.
    - explanation에는 풀이 전략, 시간복잡도 또는 주의할 점을 포함한다.
    - 단순 문법 확인 문제가 아니라 실제 구현 능력을 평가해야 한다.
    - 고급 난이도에서는 성능, 예외 처리, 자료구조 선택 이유 중 하나 이상을 포함한다.

    [코드작성형 JSON 형식]
    {
      "title": "문제 제목",
      "body": "문제 본문\\n\\n구현 요구사항:\\n- ...\\n\\n입력 조건:\\n- ...\\n\\n출력 조건:\\n- ...\\n\\n제한 조건:\\n- ...",
      "choices": [],
      "answer": "예시 코드 또는 핵심 풀이 방향",
      "explanation": "풀이 전략 및 채점 기준",
      "difficulty": "고급",
      "competency_type": "programming_language",
      "competency_tags": ["Python", "Algorithm"],
      "score": 5
    }
    """


def generate_questions(
    topic: str,
    difficulty: str,
    count: int = 1,
    score: int = 1,
    question_type: str = "multiple_choice",
    role: str | None = None,
    competency_type: str | None = None,
):
    prompt = f"""
    너는 IT 역량진단 문제은행의 전문 출제자다.
    목표는 실제 채용/역량진단에 사용할 수 있는 품질의 문제를 생성하는 것이다.

    반드시 JSON 배열만 출력해라.
    마크다운 코드블록, 설명 문장, 추가 텍스트는 절대 출력하지 마라.

    [출제 조건]
    - 대상 직무: {role or "미지정"}
    - 역량 유형: {competency_type or "미지정"}
    - 세부 주제: {topic}
    - 난이도: {difficulty}
    - 배점: {score}
    - 생성 개수: {count}
    - 문제 유형: {question_type}

    [환각 방지 규칙]
    - 확실하지 않은 기술명, 버전, 수치, 공식 문서 내용은 임의로 만들지 마라.
    - 특정 프레임워크/라이브러리의 세부 API 이름을 확신할 수 없으면 일반 개념 중심으로 출제해라.
    - 존재하지 않는 함수명, 옵션명, 명령어, 설정값을 만들어내지 마라.
    - 정답 근거가 불명확한 문제는 생성하지 마라.
    - 문제 본문과 보기 사이에 모순이 있으면 안 된다.
    - answer는 choices 배열 기준으로 정확히 하나의 정답만 가리켜야 한다.
    - 약어가 포함된 주제는 임의로 풀어쓰지 마라.
    - SLLM은 일반적으로 Small LLM 또는 Small Language Model 문맥으로 해석한다.
    - vLLM은 언어 모델 자체가 아니라 LLM 추론/서빙 엔진이다.
    - VLM은 Vision Language Model을 의미하며 vLLM과 혼동하지 마라.
    - 약어의 의미가 불명확하면 문제를 생성하지 말거나, 약어의 의미를 명시한 문제로 생성해라.

    [품질 기준]
    - 문제는 실제 IT 역량진단에 사용할 수 있어야 한다.
    - 너무 쉬운 상식 문제, 말장난 문제, 암기만 요구하는 문제는 피한다.
    - 문제 본문은 평가하려는 개념이 명확해야 한다.
    - 오답은 그럴듯해야 하지만, 정답과 명확히 구분되어야 한다.
    - 해설은 정답 이유만 쓰지 말고 핵심 개념과 오답 판단 근거를 포함해야 한다.
    - 같은 개념을 문장만 바꿔 반복 출제하지 마라.
    - {count}개의 문제는 서로 평가 포인트가 달라야 한다.

    {_difficulty_rule(difficulty)}

    {_question_type_rule(question_type)}

    [출력 검증 규칙]
    출력하기 전에 스스로 다음을 검증해라:
    1. JSON 배열만 출력했는가?
    2. 문제 개수가 정확히 {count}개인가?
    3. 각 문제에 title, body, choices, answer, explanation, difficulty, competency_type, competency_tags, score가 있는가?
    4. 객관식이면 choices가 정확히 5개인가?
    5. 객관식 answer가 1~5 숫자인가?
    6. answer는 0부터 시작하는 index가 아닌가?
    7. 정답이 실제로 choices 중 하나와 일치하는가?
    8. explanation에 적힌 정답 번호와 answer 값이 같은가?
    9. 난이도가 "{difficulty}"에 맞는가?
    10. score가 {score}인가?
    11. 존재하지 않는 기술/함수/API/명령어를 만들지 않았는가?

    [공통 출력 규칙]
    - 반드시 JSON 배열로만 반환한다.
    - 배열 안에는 정확히 {count}개의 문제 객체만 넣는다.
    - difficulty는 반드시 "{difficulty}"로 작성한다.
    - score는 반드시 {score}로 작성한다.
    - competency_type은 "{competency_type or topic}" 값으로 작성한다.
    - competency_tags는 세부 주제와 관련된 문자열 배열로 작성한다.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "너는 IT 역량진단 문제은행의 전문 출제자다. 반드시 유효한 JSON 배열만 출력한다.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    questions = _clean_json_response(content)
    return _validate_questions(questions, question_type, difficulty, score)


def generate_questions_from_context(
    topic: str,
    context: str,
    difficulty: str,
    count: int = 1,
    score: int = 1,
    question_type: str = "multiple_choice",
    role: str | None = None,
    competency_type: str | None = None,
):
    prompt = f"""
        너는 IT 역량진단 문제은행의 문서 기반 문제 출제 전문가다.
        목표는 제공된 문서 내용에 근거한 검증 가능한 문제만 생성하는 것이다.

        반드시 JSON 배열만 출력해라.
        마크다운 코드블록, 설명 문장, 추가 텍스트는 절대 출력하지 마라.

        [가장 중요한 규칙]
        아래 [문서 내용]에 명시되어 있거나 직접적으로 추론 가능한 내용만 사용해라.
        문서에 없는 개념, 정의, 예시, 기술명, API, 명령어, 수치, 장단점은 절대 추가하지 마라.
        문서 내용만으로 문제와 정답을 만들 수 없으면 억지로 만들지 말고 빈 JSON 배열 [] 을 반환해라.

        [출제 조건]
        - 대상 직무: {role or "미지정"}
        - 역량 유형: {competency_type or "미지정"}
        - 세부 주제: {topic}
        - 난이도: {difficulty}
        - 배점: {score}
        - 생성 개수: {count}
        - 문제 유형: {question_type}

        [문서 기반 환각 방지 규칙]
        - 문서에 없는 용어를 새로 추가하지 마라.
        - 문서에 없는 예시 상황을 임의로 만들지 마라.
        - 문서에 없는 도구명, 함수명, 라이브러리명, 명령어를 만들지 마라.
        - 문서의 표현을 그대로 복사하지 말고, 의미를 유지한 상태에서 문제로 재구성해라.
        - 단, 문서의 의미를 벗어난 해석은 금지한다.
        - 문서에 근거가 부족한 고급 문제는 생성하지 말고 더 낮은 수준의 문제로 만들거나 []를 반환해라.
        - 정답은 반드시 문서 내용에서 판단 가능해야 한다.
        - explanation에는 가능한 한 문서의 어떤 내용에 근거했는지 요약해서 포함한다.
        - 문서 내용과 무관한 일반 지식으로 정답을 만들지 마라.
        - 문서에서 약어의 의미가 정의되어 있지 않으면 약어를 임의로 확장하지 마라.
        - SLLM, vLLM, VLM처럼 비슷한 약어는 반드시 구분해라.
        - vLLM을 VLM 또는 다국어 모델로 설명하지 마라.

        [품질 기준]
        - 단순히 문장 일부를 빈칸처럼 바꾸는 문제는 피한다.
        - 같은 문장을 거의 그대로 반복하는 문제는 피한다.
        - 문제는 역량진단에 적합해야 한다.
        - 오답은 문서의 유사 개념을 활용해 그럴듯하게 만들되, 문서 기준으로 명확히 틀려야 한다.
        - 생성되는 {count}개의 문제는 서로 다른 평가 포인트를 가져야 한다.
        - 문서 내용이 부족하면 {count}개보다 적게 생성해도 된다.
        - 단, 이 경우에도 JSON 배열만 출력한다.

        {_difficulty_rule(difficulty)}

        {_question_type_rule(question_type)}

        [문서 내용]
        {context}

        [출력 검증 규칙]
        출력하기 전에 스스로 다음을 검증해라:
        1. JSON 배열만 출력했는가?
        2. 각 문제는 문서 내용에 근거하는가?
        3. 문서에 없는 개념/기술/API/명령어/수치를 추가하지 않았는가?
        4. 객관식이면 choices가 정확히 5개인가?
        5. 객관식 answer가 1~5 숫자인가?
        6. 정답이 문서 내용으로 판단 가능한가?
        7. 오답이 정답으로도 해석될 여지가 없는가?
        8. explanation에 문서 근거 요약이 포함되어 있는가?
        9. 난이도가 "{difficulty}"에 맞는가?
        10. 근거가 부족한 문제는 제거했는가?

        [공통 출력 규칙]
        - 반드시 JSON 배열로만 반환한다.
        - 모든 문제 객체는 title, body, choices, answer, explanation, difficulty, competency_type, competency_tags, score 필드를 가진다.
        - difficulty는 반드시 "{difficulty}"로 작성한다.
        - score는 반드시 {score}로 작성한다.
        - competency_type은 "{competency_type or topic}" 값으로 작성한다.
        - competency_tags는 문서 내용과 주제에 관련된 문자열 배열로 작성한다.
        - 문서 근거가 부족하면 빈 배열 [] 을 반환한다.
        """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "너는 문서 기반 IT 역량진단 문제 출제자다. 반드시 유효한 JSON 배열만 출력한다.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.1,
    )

    content = response.choices[0].message.content
    questions = _clean_json_response(content)
    return _validate_questions(questions, question_type, difficulty, score)