# backend/ai/services/question_planner.py

import json
from typing import Any

from ai.client import client
from ai.services.competency_config import normalize_competency_type
from ai.services.question_format_config import (
    build_question_format_instruction,
    get_allowed_question_formats,
    get_expected_evidence_type,
)

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
    competency_type = normalize_competency_type(competency_type) or competency_type

    rules = {
        "sql": """
        [SQL 역량 설계 규칙]
        - SELECT, WHERE, JOIN, GROUP BY, ORDER BY, 서브쿼리, 집계 함수, 인덱스, 실행 계획, 트랜잭션, 정규화 중 하나를 중심 개념으로 삼는다.
        - 중급 이상은 반드시 SQL 쿼리, 테이블 구조, 샘플 데이터, 실행 계획 설명 중 하나를 포함하도록 설계한다.
        - 중급 문제는 쿼리 결과 해석, JOIN 조건 오류, WHERE 조건 위치, GROUP BY/집계 결과, 서브쿼리 적용을 묻는다.
        - 고급 문제는 데이터 규모, 실행 빈도, 인덱스 선택도, 실행 계획, 락 대기, 쓰기 부하, 정규화/반정규화 판단을 조건에 포함한다.
        - 단순히 "인덱스를 추가한다"가 정답이 되지 않게 하고, 쿼리/테이블/실행 계획을 근거로 판단하게 한다.
        """,

        "data_structure_algorithm": """
        [자료구조/알고리즘 역량 설계 규칙]
        - 시간복잡도, 공간복잡도, 입력 크기, 자료 접근 패턴, 삽입/삭제 빈도, 정렬 여부, 중복 여부 중 일부를 조건으로 포함한다.
        - 고급 문제는 "해시 테이블", "트리", "연결 리스트" 같은 자료구조명을 단순 정답으로 만들지 않는다.
        - 왜 해당 자료구조나 알고리즘이 조건에 적합한지 판단 기준을 포함한다.
        - 정답은 자료구조 이름이 아니라 입력 크기, 조회/삽입/삭제 빈도, 정렬/범위 검색 필요 여부를 기준으로 결정되게 한다.
        - 오답은 특정 연산에는 유리하지만 현재 요구되는 연산 패턴에는 부적절한 자료구조 선택으로 설계한다.
        """,

        "software_engineering": """
        [소프트웨어공학 역량 설계 규칙]
        - 요구사항 분석, 설계 원칙(SOLID), 테스트 전략, 형상관리, 변경관리, 추적성, 품질 속성, 리스크 관리, 디자인 패턴 중 하나를 중심 개념으로 삼는다.
        - 중급 이상은 요구사항 목록, 변경 요청, 테스트 실패 상황, 이해관계자 충돌, 품질 속성 누락 중 하나를 포함하도록 설계한다.
        - 고급 문제는 일반 지식으로 우선순위를 단정하지 말고, 주어진 조건과 근거에 따라 판단하게 한다.
        - 기능 요구사항/비기능 요구사항/제약사항/검증 기준/이해관계자 충돌 같은 조건을 포함한다.
        """,

        "ai": """
        [AI 역량 설계 규칙]
        - 데이터 전처리, 학습/검증 데이터 분리, 과적합, 모델 평가 지표, LLM, RAG, 임베딩, 벡터 검색, 검색 품질, 파인튜닝 중 하나를 중심 개념으로 삼는다.
        - 중급 이상은 반드시 데이터 상태, 평가 지표, 검색 결과 예시, RAG 파이프라인 조건, 모델 성능 로그 중 하나를 포함하도록 설계한다.
        - RAG/검색 품질 문제는 SQL 인덱스나 DB 실행 계획 문제가 아니라 chunk 품질, embedding, vector search, keyword search, metadata filter, reranking, context filtering, top_k, hallucination 방지 중 하나를 중심으로 설계한다.
        - 중급 문제는 검색 결과가 부정확한 원인, chunk 품질, query 보강, metadata filter 적용 여부를 판단하게 한다.
        - 고급 문제는 vector search만으로 부족한 상황에서 hybrid search, reranker, context filtering, 평가 지표, latency/accuracy trade-off를 판단하게 한다.
        """,

        "security": """
        [정보보안 역량 설계 규칙]
        - 인증(AuthN), 인가(AuthZ), 암호화, 해시, 취약점(XSS, CSRF, Injection), 로그, 접근통제, 개인정보 보호, 사고 대응 중 하나를 중심 개념으로 삼는다.
        - 중급 이상은 반드시 취약 코드, HTTP 요청/응답, 권한 정책, 로그, 공격 시나리오 중 하나를 포함하도록 설계한다.
        - 중급 문제는 공격 원리와 대응 방안, 권한 검증 누락, 보안 설정 문제를 상황 기반으로 묻는다.
        - 고급 문제는 위협 모델링, 권한 분리, 데이터 보호, 사고 대응 우선순위, 보안 설계 트레이드오프를 판단하게 한다.
        - 단순히 "암호화한다", "접근을 차단한다"가 정답이 되지 않게 한다.
        """,

        "java": """
        [Java 역량 설계 규칙]
        - 클래스/객체, 상속, 다형성, 인터페이스, 예외 처리, 컬렉션, 제네릭, JVM 기초 중 하나를 중심 개념으로 삼는다.
        - 중급 이상은 반드시 짧은 Java 코드 조각, 클래스/인터페이스 구조, 예외 처리 코드, 컬렉션 사용 예시 중 하나를 포함하도록 설계한다.
        - 중급 문제는 코드 실행 결과, 컴파일 오류 원인, 메서드 오버라이딩/오버로딩 차이, 컬렉션 선택 기준을 묻는다.
        - 고급 문제는 유지보수성, 확장성, 타입 안정성, 예외 처리 범위, 동시성 또는 성능 영향을 판단하게 한다.
        - 긴 상황 설명만 읽고 일반적인 설계 판단을 고르는 비문학형 문제로 설계하지 않는다.
        """,

        "python": """
        [Python 역량 설계 규칙]
        - 자료형 특징, 제너레이터/이터레이터, 데코레이터, 컨텍스트 매니저, 예외 처리, 비동기 프로그래밍(asyncio), 패키지 구조 중 하나를 중심 개념으로 삼는다.
        - 고급 문제는 Pythonic한 코드 작성 및 라이브러리 활용 효율성을 평가한다.
        - 중급 이상은 반드시 짧은 Python 코드 조각 또는 데이터 구조 예시를 포함하도록 설계한다.
        - 리스트, 딕셔너리, 함수, 예외 처리, 클래스, 반복문, 컴프리헨션 중 하나를 실제 코드 흐름 안에서 평가한다.
        - 중급 문제는 실행 결과 예측, 오류 원인 파악, 누락된 조건 보완, 적절한 자료형 선택을 묻는다.
        - 고급 문제는 예외 상황, 성능, 메모리 사용, 가독성, 유지보수성, 리팩토링 방향을 판단하게 한다.
        - “입력 데이터를 분석한다”, “구조를 파악한다”처럼 비문학형 판단 문제로 설계하지 않는다.
        - 문제 본문에는 코드 블록 또는 리스트/딕셔너리 예시가 포함되어야 한다.
        """,

        "c_language": """
        [C언어 역량 설계 규칙]
        - 포인터, 배열, 문자열, 구조체, 함수, 동적 메모리 할당, 주소, 값 전달, 파일 입출력 중 하나를 중심 개념으로 삼는다.
        - 중급 이상은 반드시 짧은 C 코드 조각, 포인터/배열 접근 예시, 문자열 처리 코드, 구조체/동적 할당 코드 중 하나를 포함하도록 설계한다.
        - 중급 문제는 실행 결과 예측, 포인터 접근 오류, 문자열 종료 문자, 배열 범위, 함수 인자 전달 방식을 묻는다.
        - 고급 문제는 메모리 누수, dangling pointer, buffer overflow, 동적 할당 해제, 구조체 설계 문제를 판단하게 한다.
        - 코드 없이 긴 상황 설명만 제시하는 문제로 설계하지 않는다.
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

{build_question_format_instruction(competency_type, difficulty)}

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

- evidence_type:
  - 중급/고급 문제에서 사용할 실전 자료 유형
  - competency_type에 따라 아래 중 하나를 사용한다.
  - java/python/c_language: "code_snippet"
  - sql: "sql_query", "table_schema", "execution_plan" 중 하나
  - data_structure_algorithm: "input_constraints", "pseudocode", "operation_pattern" 중 하나
  - ai: "retrieval_result", "metric_report", "pipeline_condition" 중 하나
  - security: "vulnerable_code", "request_response", "access_policy", "log" 중 하나
  - software_engineering: "requirement_list", "change_request", "test_failure" 중 하나
  - 초급이면 "concept"로 둘 수 있다.

- evidence_detail:
  - 실제 문제 본문에 반영할 코드/쿼리/입력 조건/로그/요구사항 목록의 요약
  - 중급/고급에서는 비워두지 않는다.

- source_evidence:
  - 일반 생성에서는 "general_knowledge"로 둔다.
  - RAG 문서 기반 생성에서는 나중에 문서 근거를 넣을 예정이다.
  - 지금은 반드시 "general_knowledge"로 작성한다.

- question_format:
  - 문제의 실제 형식
  - 반드시 [문제 형식 규칙]에서 허용한 값 중 하나를 사용한다.
  - 예: "code_output", "runtime_error", "join_where_bug", "rag_pipeline_diagnosis"

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

[고급 오답 설계 강화 규칙]
- 난이도가 고급이면 distractor_strategy는 반드시 "그럴듯하지만 현재 조건에서는 부족한 대안"으로 작성한다.
- 고급 오답은 "무시한다", "삭제한다", "완전히 제거한다", "모든", "무조건", "항상", "오직", "단순히", "차단한다" 같은 표현을 사용하지 않는다.
- 고급 오답은 실무자가 실제로 선택할 수 있는 대안이어야 한다.
- 고급 오답은 다음 유형 중 하나로 설계한다.
  1) 일부 조건만 해결하지만 핵심 원인을 해결하지 못하는 대안
  2) 조회 성능은 개선할 수 있지만 쓰기 부하나 락 경합을 악화시킬 수 있는 대안
  3) 보안은 강화할 수 있지만 성능 병목 원인을 직접 해결하지 못하는 대안
  4) 단기적으로 효과가 있어 보이나 데이터 분포, 실행 계획, 동시성 조건을 반영하지 못하는 대안
  5) 일반론으로는 맞지만 현재 문제의 제약 조건에서는 우선순위가 낮은 대안
- distractor_strategy에는 "틀린 선택지"가 아니라 "왜 헷갈릴 수 있지만 부족한지"를 포함한다.
- 고급 문제에서 정답만 길고 오답이 짧아지지 않도록, 오답도 정답과 비슷한 길이와 판단 구조를 갖도록 설계한다.
- 예를 들어 데이터베이스 고급 문제에서 "인덱스를 추가한다"는 오답으로 쓰지 말고, "조회 조건 일부에만 맞는 단일 인덱스를 추가하지만 조인 조건과 데이터 분포를 반영하지 못하는 대안"처럼 설계한다.
- 예를 들어 보안과 성능이 함께 있는 문제에서 "보안을 무시한다"는 오답으로 쓰지 말고, "접근 제어 정책은 유지하지만 쿼리 실행 계획과 인덱스 선택도 문제를 함께 보지 못하는 대안"처럼 설계한다.

[금지 규칙]
- 문제 본문, choices, answer, explanation을 만들지 마라.
- 실제 객관식 선택지를 만들지 마라.
- 모든 설계서가 같은 target_concept를 반복하지 마라.
- 고급 문제에서 특정 기술 하나를 만능 정답처럼 설계하지 마라.
- "무조건", "항상", "오직", "삭제한다", "무시한다", "생략한다", "자동으로 해결된다" 같은 극단적 표현 중심으로 설계하지 마라.

[출력 예시]
[
  {{
    "scenario": "쇼핑몰 주문 조회에서 주문이 없는 고객도 포함하려고 LEFT JOIN을 사용했지만 일부 고객이 결과에서 제외되는 상황이다.",
    "constraints": [
      "customers 테이블과 orders 테이블을 고객 ID로 조인한다.",
      "결제 완료 주문만 집계하려고 한다.",
      "주문이 없는 고객도 결과에 포함되어야 한다."
    ],
    "target_concept": "LEFT JOIN에서 WHERE 조건과 ON 조건의 차이",
    "cognitive_skill": "원인 분석",
    "question_format": "join_where_bug",
    "evidence_type": "sql_query",
    "evidence_detail": "LEFT JOIN 쿼리에서 WHERE o.status = 'PAID' 조건 때문에 주문이 없는 고객이 제외되는 예시를 포함한다.",
    "correct_reason": "LEFT JOIN의 NULL 보존을 유지하려면 결제 상태 조건을 WHERE가 아니라 ON 절에 두어야 한다.",
    "distractor_strategy": "JOIN 컬럼을 바꾸거나 기간 조건만 수정하는 등 일부 조건에는 관련 있어 보이지만 NULL 행 보존 문제를 해결하지 못하는 대안을 구성한다.",
    "answer_decision_rule": "주문이 없는 고객을 보존하면서 결제 완료 주문만 집계할 수 있는 조건 위치를 정답으로 판단한다.",
    "source_evidence": "general_knowledge"
  }}
]
"""


def validate_question_plan(
    plan: dict[str, Any],
    difficulty: str,
    competency_type: str | None = None,
) -> list[str]:
    reasons: list[str] = []

    competency_type = normalize_competency_type(competency_type)

    required_fields = [
        "scenario",
        "constraints",
        "target_concept",
        "cognitive_skill",
        "question_format",
        "correct_reason",
        "distractor_strategy",
        "answer_decision_rule",
        "evidence_type",
        "evidence_detail",
        "source_evidence",
    ]

    for field in required_fields:
        if field not in plan or plan.get(field) in (None, "", []):
            reasons.append(f"필수 필드가 누락되었습니다: {field}")

    scenario = str(plan.get("scenario", "")).strip()
    constraints = plan.get("constraints", [])
    question_format = str(plan.get("question_format", "")).strip()
    evidence_type = str(plan.get("evidence_type", "")).strip()
    evidence_detail = str(plan.get("evidence_detail", "")).strip()

    # 중요: 반드시 기본값을 먼저 선언한다.
    allowed_formats: list[str] = []
    expected_evidence_type: str | None = None

    if difficulty in {"중급", "고급"}:
        allowed_formats = get_allowed_question_formats(
            competency_type=competency_type,
            difficulty=difficulty,
        )

        if not question_format:
            reasons.append("중급/고급 문제 설계에는 question_format이 필요합니다.")

        if allowed_formats and question_format not in allowed_formats:
            reasons.append(
                f"{competency_type} {difficulty} 문제에 허용되지 않는 question_format입니다: {question_format}"
            )

        expected_evidence_type = get_expected_evidence_type(question_format)

        if expected_evidence_type and evidence_type != expected_evidence_type:
            reasons.append(
                f"question_format={question_format}에는 evidence_type={expected_evidence_type}이 필요합니다. 현재값: {evidence_type}"
            )

        if not evidence_type:
            reasons.append("중급/고급 문제 설계에는 evidence_type이 필요합니다.")

        if not evidence_detail:
            reasons.append("중급/고급 문제 설계에는 evidence_detail이 필요합니다.")

    if not isinstance(constraints, list) or len(constraints) == 0:
        reasons.append("constraints는 1개 이상의 문자열 배열이어야 합니다.")

    if difficulty == "고급":
        if len(scenario) < 40:
            reasons.append("고급 문제의 scenario가 너무 짧습니다.")

        if isinstance(constraints, list) and len(constraints) < 2:
            reasons.append("고급 문제는 constraints가 2개 이상 필요합니다.")

    return reasons


def validate_question_plans(
    plans: list[dict[str, Any]],
    difficulty: str,
    competency_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    설계서 목록을 검증하고, 사용 가능한 설계서만 반환한다.
    지금 1단계에서는 너무 엄격하게 전체 실패시키지 않고,
    각 설계서에 plan_review를 붙여서 다음 단계에서 참고할 수 있게 한다.
    """
    validated: list[dict[str, Any]] = []

    for plan in plans:
        reasons = validate_question_plan(
            plan=plan,
            difficulty=difficulty,
            competency_type=competency_type,
        )

        plan["plan_review"] = {
            "is_valid": len(reasons) == 0,
            "reject_reasons": reasons,
        }

        if len(reasons) == 0:
            validated.append(plan)

    if len(validated) == 0:
        return []

    return validated


def generate_question_plans(
    topic: str,
    difficulty: str,
    count: int = 1,
    question_type: str = "multiple_choice",
    competency_type: str = "software_engineering",
) -> list[dict[str, Any]]:
    """
    일반 문제 생성을 위한 문제 설계서 JSON을 생성한다.
    아직 RAG context는 사용하지 않는다.
    """
    # 역량 유형 정규화
    normalized_type = normalize_competency_type(competency_type) or "software_engineering"
    
    difficulty = _normalize_difficulty(difficulty)

    if question_type not in VALID_QUESTION_TYPES:
        question_type = "multiple_choice"

    prompt = _build_planner_prompt(
        topic=topic,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
        competency_type=normalized_type,
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

    validated_plans = validate_question_plans(
        plans=plans,
        difficulty=difficulty,
        competency_type=normalized_type,
    )

    if len(validated_plans) == 0:
        raise ValueError("문제 형식 조건을 만족하는 설계서를 생성하지 못했습니다.")

    return validated_plans