# backend/ai/services/question_planner.py

import json
from typing import Any

from ai.client import client


VALID_DIFFICULTIES = {"초급", "중급", "고급"}
VALID_QUESTION_TYPES = {"multiple_choice", "essay", "code"}


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """
    LLM 응답에서 JSON 배열만 안전하게 추출한다.
    """
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("문제 설계서 JSON 배열을 찾을 수 없습니다.")

    json_text = text[start : end + 1]

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"문제 설계서 JSON 파싱 실패: {e}") from e

    if not isinstance(data, list):
        raise ValueError("문제 설계서는 JSON 배열이어야 합니다.")

    return data


def _normalize_difficulty(difficulty: str) -> str:
    difficulty = (difficulty or "").strip()

    if difficulty in VALID_DIFFICULTIES:
        return difficulty

    if difficulty in {"easy", "beginner", "기초"}:
        return "초급"

    if difficulty in {"medium", "intermediate", "보통"}:
        return "중급"

    if difficulty in {"hard", "advanced", "상"}:
        return "고급"

    return "중급"


def _difficulty_planning_rule(difficulty: str) -> str:
    if difficulty == "초급":
        return """
- 초급 문제 설계 규칙:
  - 핵심 개념의 정의, 목적, 기본 특징을 확인하는 문제로 설계한다.
  - 조건은 1개 이상 포함한다.
  - 단순 암기형이어도 되지만, 정답과 오답의 구분 기준은 명확해야 한다.
  - 오답은 같은 주제 안에서 헷갈릴 수 있는 개념으로 구성한다.
"""

    if difficulty == "중급":
        return """
- 중급 문제 설계 규칙:
  - 단순 정의가 아니라 비교, 적용, 원인 분석, 결과 예측 중 하나를 평가하도록 설계한다.
  - 조건은 2개 이상 포함한다.
  - 문제 상황에는 실무 맥락을 넣는다.
  - 정답은 조건을 모두 만족해야 고를 수 있어야 한다.
  - 오답은 일부 조건만 만족하거나, 비슷하지만 핵심 기준이 다른 선택지가 되도록 설계한다.
"""

    return """
- 고급 문제 설계 규칙:
  - 단순 정의나 일반론을 묻지 않는다.
  - 장애 상황, 성능 저하, 보안 위험, 설계 트레이드오프, 요구사항 충돌, 운영 리스크 중 하나 이상을 포함한다.
  - 조건은 반드시 3개 이상 포함한다.
  - 정답은 여러 조건을 종합적으로 판단해야 선택할 수 있어야 한다.
  - 오답은 완전히 틀린 문장이 아니라, 특정 조건에서는 맞지만 현재 상황에서는 부적절한 선택지로 설계한다.
  - "가장 우선적으로", "가장 적절한", "가장 위험한", "가장 타당한" 판단 기준이 명확해야 한다.
  - 특정 기술명을 만능 해결책처럼 반복하지 않는다.
"""


def _competency_planning_rule(competency_type: str) -> str:
    rules = {
        "database": """
        [데이터베이스 역량 설계 규칙]
        - 인덱스, 정규화, 트랜잭션, 격리 수준, 실행 계획, 조인, 락, 성능 튜닝, 백업/복구 중 하나를 중심 개념으로 삼는다.
        - 고급 문제는 단순히 "인덱스를 추가한다"가 정답이 되지 않도록 한다.
        - 데이터 분포, 카디널리티, 조회 패턴, 쓰기 부하, 락 경합, 정합성 요구사항 같은 조건을 포함한다.
        - topic이 인덱스, 실행 계획, 조인, 쿼리 성능이면 보안, 개인정보, 접근 제어 중심 시나리오로 확장하지 않는다.
        - 인덱스 문제의 정답은 "인덱스를 추가한다"가 아니라 실행 계획, 선택도, 조건 컬럼, 정렬 여부, 쓰기 부하를 함께 고려한 판단이어야 한다.
        - 실행 계획 문제는 조인 순서, 스캔 방식, 인덱스 사용 여부, 예상/실제 행 수 차이 중 하나 이상을 조건에 포함한다.
        - 오답은 단순히 틀린 행동이 아니라, 일부 상황에서는 가능하지만 현재 쿼리 조건이나 데이터 분포에는 맞지 않는 전략으로 설계한다.
        """,

        "data_structure_algorithm": """
        [자료구조/알고리즘 역량 설계 규칙]
        - 시간복잡도, 공간복잡도, 입력 크기, 자료 접근 패턴, 삽입/삭제 빈도, 정렬 여부, 중복 여부 중 일부를 조건으로 포함한다.
        - 고급 문제는 "해시 테이블", "트리", "연결 리스트" 같은 자료구조명을 단순 정답으로 만들지 않는다.
        - 왜 해당 자료구조나 알고리즘이 조건에 적합한지 판단 기준을 포함한다.
        - topic이 해시 테이블과 트리 선택이면 인공지능, RAG, 데이터베이스 인덱스 문제로 확장하지 않는다.
        - 정답은 자료구조 이름이 아니라 입력 크기, 조회/삽입/삭제 빈도, 정렬/범위 검색 필요 여부를 기준으로 결정되게 한다.
        - 오답은 특정 연산에는 유리하지만 현재 요구되는 연산 패턴에는 부적절한 자료구조 선택으로 설계한다.
        """,

        "software_engineering": """
        [소프트웨어공학 역량 설계 규칙]
        - 요구사항, 설계, 테스트, 형상관리, 변경관리, 추적성, 품질 속성, 리스크 관리 중 하나를 중심 개념으로 삼는다.
        - 고급 문제는 일반 지식으로 우선순위를 단정하지 말고, 주어진 조건과 근거에 따라 판단하게 한다.
        - 기능 요구사항/비기능 요구사항/제약사항/검증 기준/이해관계자 충돌 같은 조건을 포함한다.
        """,

        "ai_data": """
        [AI 역량 설계 규칙]
        - 데이터 품질, 학습/검증 데이터 분리, 과적합, 평가 지표, 피처, 모델 선택, RAG, 임베딩, 검색 품질 중 하나를 중심 개념으로 삼는다.
        - 고급 문제에서 reranking, fine-tuning, RAG 같은 기법을 만능 정답처럼 반복하지 않는다.
        - 문제 상황에 데이터 분포, 검색 실패 원인, 평가 기준, 운영 제약 중 일부를 포함한다.
        - RAG 문제에서 reranking을 만능 정답으로 설계하지 않는다.
        - reranking은 검색 후보가 존재하지만 순서와 관련도 평가가 부정확한 경우에만 정답 전략으로 사용한다.
        - keyword search 또는 hybrid search는 정확한 용어, 약어, 코드, 고유명사를 vector search가 놓치는 상황에서 사용한다.
        - metadata filter는 category, 문서 유형, 출처, 날짜처럼 필터링 가능한 metadata가 있을 때만 정답 전략으로 사용한다.
        - chunking 개선은 문맥이 잘리거나 여러 주제가 한 chunk에 섞이는 경우에만 정답 전략으로 사용한다.
        """,

        "security": """
        [보안 역량 설계 규칙]
        - 인증, 인가, 암호화, 취약점, 로그, 접근통제, 개인정보 보호, 사고 대응 중 하나를 중심 개념으로 삼는다.
        - 고급 문제는 단순히 "암호화한다", "접근을 차단한다"가 아니라 위험도와 운영 제약을 함께 판단하게 한다.
        """,

        "web_development": """
        [웹 개발 역량 설계 규칙]
        - HTTP, REST API, 인증, 상태관리, CORS, 캐싱, 렌더링, 프론트/백엔드 연동, 에러 처리 중 하나를 중심 개념으로 삼는다.
        - 고급 문제는 요청 흐름, 상태 변화, 장애 원인, 사용자 영향까지 포함한다.
        """,

        "os_network": """
        [운영체제/네트워크 역량 설계 규칙]
        - 프로세스, 스레드, 메모리, 파일시스템, TCP/IP, DNS, HTTP, 로드밸런싱, 포트, 방화벽 중 하나를 중심 개념으로 삼는다.
        - 고급 문제는 병목 원인, 장애 전파, 동시성, 리소스 경합을 조건에 포함한다.
        """,

        "cloud_devops": """
        [Cloud/DevOps 역량 설계 규칙]
        - 배포, CI/CD, 컨테이너, 모니터링, 오토스케일링, 장애 복구, 로깅, 인프라 비용 중 하나를 중심 개념으로 삼는다.
        - 고급 문제는 안정성, 비용, 운영 복잡도, 장애 대응을 함께 판단하게 한다.
        """,

        "programming": """
        [프로그래밍 역량 설계 규칙]
        - 변수, 함수, 예외 처리, 객체지향, 모듈화, 테스트, 코드 품질, 성능 중 하나를 중심 개념으로 삼는다.
        - 고급 문제는 단순 문법이 아니라 유지보수성, 확장성, 오류 가능성을 판단하게 한다.
        """,
    }

    return rules.get(
        competency_type,
        """
        [공통 역량 설계 규칙]
        - 주어진 역량 유형에 맞는 핵심 개념을 중심으로 문제를 설계한다.
        - 단순 암기보다 조건 기반 판단이 가능하도록 설계한다.
        """,
    )


def _build_planner_prompt(
    topic: str,
    difficulty: str,
    count: int,
    question_type: str,
    competency_type: str,
) -> str:
    difficulty = _normalize_difficulty(difficulty)

    return f"""
너는 IT 역량진단 문제은행의 "문제 설계자"다.

너의 역할은 실제 문제를 바로 만드는 것이 아니라,
좋은 문제를 만들기 위한 "문제 설계서 JSON"만 작성하는 것이다.

반드시 JSON 배열만 출력해라.
마크다운, 설명문, 코드블록을 출력하지 마라.

[생성 요청]
- 주제: {topic}
- 난이도: {difficulty}
- 문제 수: {count}
- 문제 유형: {question_type}
- 역량 유형: {competency_type}

{_difficulty_planning_rule(difficulty)}

{_competency_planning_rule(competency_type)}

[문제 설계서 필드 규칙]
각 설계서는 반드시 아래 필드를 가진다.

- scenario:
  - 문제 상황
  - 초급은 짧아도 되지만, 중급/고급은 실무 상황이어야 한다.

- constraints:
  - 문제 판단에 필요한 조건 배열
  - 초급은 1개 이상
  - 중급은 2개 이상
  - 고급은 3개 이상

- target_concept:
  - 평가하려는 핵심 개념 1개

- cognitive_skill:
  - 다음 중 하나:
  - "개념 이해", "비교", "적용", "원인 분석", "결과 예측", "우선순위 판단", "리스크 분석", "트레이드오프 판단"

- correct_reason:
  - 정답이 되는 판단 기준
  - 특정 선택지 번호를 말하지 말고, 어떤 사고 과정을 거쳐야 정답인지 작성

- distractor_strategy:
  - 오답을 어떻게 설계할지 작성
  - 오답은 허무맹랑한 문장이 아니라 그럴듯하지만 조건에 맞지 않아야 한다.

- answer_decision_rule:
  - 정답과 오답을 구분하는 최종 기준
  - "가장 적절한 것"을 고르는 기준이 명확해야 한다.

- source_evidence:
  - 일반 생성에서는 "general_knowledge"로 둔다.
  - RAG 문서 기반 생성에서는 나중에 문서 근거를 넣을 예정이다.
  - 지금은 반드시 "general_knowledge"로 작성한다.

[설계 품질 강화 규칙]
- correct_reason에는 "분석한다", "판단한다", "고려한다" 같은 추상 표현만 쓰지 마라.
- correct_reason에는 어떤 기준으로 어떤 선택이 정답이 되는지 구체적으로 작성한다.
- answer_decision_rule에는 정답과 오답을 구분하는 최종 기준을 명확히 작성한다.
- distractor_strategy에는 쉽게 틀린 오답이 아니라, 일부 조건에서는 타당하지만 현재 조건에서는 부족한 오답 전략을 작성한다.
- "무시한다", "완전히 제거한다", "무조건 높인다", "무조건 낮춘다", "항상 적용한다", "성능만 고려한다", "보안을 무시한다" 같은 노골적인 오답 전략을 만들지 마라.
- 고급 문제 설계에서는 정답이 특정 기술명 하나로 결정되지 않게 한다.
- 고급 문제 설계에서는 정답이 현재 상황의 조건, 제약, 리스크, 트레이드오프를 종합해야 결정되도록 한다.
- 같은 생성 묶음 안에서 target_concept가 반복되지 않게 한다.
- topic에서 벗어난 역량으로 확장하지 않는다.

[금지 규칙]
- 문제 본문, choices, answer, explanation을 만들지 마라.
- 실제 객관식 선택지를 만들지 마라.
- 모든 설계서가 같은 target_concept를 반복하지 마라.
- 고급 문제에서 특정 기술 하나를 만능 정답처럼 설계하지 마라.
- "무조건", "항상", "오직", "삭제한다", "무시한다", "생략한다", "자동으로 해결된다" 같은 극단적 표현 중심으로 설계하지 마라.

[출력 예시]
[
  {{
    "scenario": "쇼핑몰 주문 조회 API에서 특정 시간대에 응답 지연이 발생하고 있으며, 최근 검색 조건이 추가되었다.",
    "constraints": [
      "주문 테이블은 쓰기 작업이 계속 발생한다.",
      "검색 조건은 회원 ID와 주문 상태를 함께 사용한다.",
      "응답 지연은 특정 상태값에 집중되어 있다."
    ],
    "target_concept": "복합 인덱스 설계와 데이터 분포",
    "cognitive_skill": "트레이드오프 판단",
    "correct_reason": "조회 조건, 데이터 분포, 쓰기 부하를 함께 고려하여 인덱스 설계의 적절성을 판단해야 한다.",
    "distractor_strategy": "단일 인덱스 추가, 무조건적인 정규화, 캐시 적용처럼 일부 상황에서는 가능하지만 현재 조건의 핵심 원인을 충분히 해결하지 못하는 선택지를 구성한다.",
    "answer_decision_rule": "현재 병목의 원인과 조회 조건을 가장 직접적으로 해결하면서 쓰기 부하까지 고려한 대안을 정답으로 판단한다.",
    "source_evidence": "general_knowledge"
  }}
]
"""


def validate_question_plan(
    plan: dict[str, Any],
    difficulty: str,
) -> list[str]:
    """
    설계서 자체 품질을 1차 검증한다.
    문제가 있으면 reject reason 목록을 반환한다.
    """
    reasons: list[str] = []

    required_fields = [
        "scenario",
        "constraints",
        "target_concept",
        "cognitive_skill",
        "correct_reason",
        "distractor_strategy",
        "answer_decision_rule",
        "source_evidence",
    ]

    for field in required_fields:
        if field not in plan:
            reasons.append(f"설계서 필드 누락: {field}")

    difficulty = _normalize_difficulty(difficulty)

    scenario = str(plan.get("scenario", "")).strip()
    target_concept = str(plan.get("target_concept", "")).strip()
    correct_reason = str(plan.get("correct_reason", "")).strip()
    distractor_strategy = str(plan.get("distractor_strategy", "")).strip()
    answer_decision_rule = str(plan.get("answer_decision_rule", "")).strip()

    constraints = plan.get("constraints", [])

    if not scenario:
        reasons.append("scenario가 비어 있습니다.")

    if not isinstance(constraints, list):
        reasons.append("constraints는 배열이어야 합니다.")
        constraints = []

    if difficulty == "초급" and len(constraints) < 1:
        reasons.append("초급 문제는 조건이 1개 이상 필요합니다.")

    if difficulty == "중급" and len(constraints) < 2:
        reasons.append("중급 문제는 조건이 2개 이상 필요합니다.")

    if difficulty == "고급" and len(constraints) < 3:
        reasons.append("고급 문제는 조건이 3개 이상 필요합니다.")

    if not correct_reason:
        reasons.append("correct_reason이 비어 있습니다.")

    if not answer_decision_rule:
        reasons.append("answer_decision_rule이 비어 있습니다.")

    if not distractor_strategy:
        reasons.append("distractor_strategy가 비어 있습니다.")

    if difficulty == "고급":
        weak_words = ["정의", "개념", "무엇인가", "설명하라"]
        joined = " ".join(
            [
                scenario,
                target_concept,
                correct_reason,
                answer_decision_rule,
            ]
        )

        if any(word in joined for word in weak_words) and len(constraints) < 4:
            reasons.append("고급 문제 설계가 단순 개념 확인형에 가깝습니다.")

        abstract_phrases = [
            "분석한다",
            "판단한다",
            "고려한다",
            "적절한 조치를 취한다",
            "적절한 방안을 선택한다",
            "최적화한다",
        ]

        if correct_reason in abstract_phrases:
            reasons.append("correct_reason이 너무 추상적입니다.")

        if answer_decision_rule in abstract_phrases:
            reasons.append("answer_decision_rule이 너무 추상적입니다.")

        if correct_reason and len(correct_reason) < 35:
            reasons.append("correct_reason이 고급 문제 설계 기준으로 너무 짧습니다.")

        if answer_decision_rule and len(answer_decision_rule) < 35:
            reasons.append("answer_decision_rule이 고급 문제 설계 기준으로 너무 짧습니다.")

    weak_distractor_words = [
        "무시한다",
        "삭제한다",
        "완전히 제거한다",
        "무조건",
        "항상",
        "오직",
        "성능만 고려한다",
        "보안을 무시한다",
        "단순히",
    ]

    if any(word in distractor_strategy for word in weak_distractor_words):
        reasons.append("distractor_strategy에 너무 쉽게 틀린 오답 전략이 포함되어 있습니다.")

    return reasons


def validate_question_plans(
    plans: list[dict[str, Any]],
    difficulty: str,
) -> list[dict[str, Any]]:
    """
    설계서 목록을 검증하고, 사용 가능한 설계서만 반환한다.
    지금 1단계에서는 너무 엄격하게 전체 실패시키지 않고,
    각 설계서에 plan_review를 붙여서 다음 단계에서 참고할 수 있게 한다.
    """
    validated: list[dict[str, Any]] = []

    for plan in plans:
        reasons = validate_question_plan(plan, difficulty)

        plan["plan_review"] = {
            "is_valid": len(reasons) == 0,
            "reject_reasons": reasons,
        }

        if len(reasons) == 0:
            validated.append(plan)

    if len(validated) == 0:
    # 임시 안정화:
        # 설계서 품질 검증이 너무 강하면 이후 문제 생성 단계까지 가지 못하고 400이 발생한다.
        # 리팩토링 전까지는 plan_review를 붙인 원본 설계서를 그대로 넘기고,
        # 실제 문제 생성/검증 단계에서 한 번 더 걸러낸다.
        return plans

    return validated


def generate_question_plans(
    topic: str,
    difficulty: str,
    count: int = 1,
    question_type: str = "multiple_choice",
    competency_type: str = "programming",
) -> list[dict[str, Any]]:
    """
    일반 문제 생성을 위한 문제 설계서 JSON을 생성한다.
    아직 RAG context는 사용하지 않는다.
    """
    difficulty = _normalize_difficulty(difficulty)

    if question_type not in VALID_QUESTION_TYPES:
        question_type = "multiple_choice"

    prompt = _build_planner_prompt(
        topic=topic,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
        competency_type=competency_type,
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "너는 IT 역량진단 문제은행의 문제 설계 전문가다. 반드시 JSON 배열만 출력한다.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.35,
    )

    content = response.choices[0].message.content or ""

    plans = _extract_json_array(content)

    if len(plans) == 0:
        raise ValueError("생성된 문제 설계서가 없습니다.")

    plans = plans[:count]

    return validate_question_plans(plans, difficulty)