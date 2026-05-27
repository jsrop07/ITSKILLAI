import re
import json
import time
import logging
from ai.core.openai_client import client
from ai.core.config import normalize_competency_type
from ai.questions.validator import validate_questions
from ai.questions.planner import generate_question_plans
from ai.questions.text_normalizer import normalize_question_body_choice_styles
from ai.questions.templates import (build_ai_advanced_template, build_sql_advanced_template)
from ai.questions.answer_position import (rebalance_answer_positions,has_answer_position_bias)
from ai.questions.explanation_repair import (normalize_explanation_style_local,repair_multiple_choice_explanations,clean_json_response)
from ai.questions.choice_generator import (generate_choices_for_template_question,generate_choices_for_template_questions_batch,)
from ai.questions.prompts import (difficulty_rule,competency_rule,question_type_rule,explanation_rule,answer_distribution_rule,answer_explanation_consistency_rule,choice_quality_rule,answer_leak_prevention_rule,compare_choice_balance_rule,code_evidence_rule,hallucination_guard_rule,document_grounding_rule,build_stage1_stem_prompt,build_stage2_options_prompt)
logger = logging.getLogger("uvicorn.info")

USE_AI_ADVANCED_TEMPLATE = True
USE_SQL_ADVANCED_TEMPLATE = True    


def _request_llm_json(prompt: str, system_message: str, temperature: float = 0.1):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
    )
    content = response.choices[0].message.content
    logger.info(f"LLM raw response preview: {str(content)[:1000]}")
    return clean_json_response(content)

def _generate_with_retry(
    prompt: str,
    system_message: str,
    question_type: str,
    difficulty: str,
    score: int,
    temperature: float = 0.1,
    max_retries: int = 0,
    plans: list[dict] | None = None,
    competency_type: str | None = None,
):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            questions = _request_llm_json(
                prompt=prompt,
                system_message=system_message,
                temperature=temperature,
            )
            questions = _force_plan_evidence_into_generated_questions(
                questions=questions,
                plans=plans or [],
                competency_type=competency_type,
                difficulty=difficulty,
            )
            logger.info(
                f"LLM 원본 문제 생성 수: {len(questions) if isinstance(questions, list) else 'not_list'}"
            )

            if not isinstance(questions, list) or len(questions) == 0:
                raise ValueError("LLM이 문제 JSON 배열을 생성하지 못했습니다.")

            # LLM 원본 answer/explanation을 보존한다.
            # repair가 틀린 정답을 그럴듯한 해설로 덮어버리는 문제를 막기 위함.
            for q in questions:
                if isinstance(q, dict):
                    q["_llm_answer_before_rebalance"] = q.get("answer")
                    q["_llm_explanation_before_rebalance"] = q.get("explanation", "")

            questions = rebalance_answer_positions(
                questions,
                question_type,
            )

            # 재배치 이후 상태도 보존한다.
            for q in questions:
                if isinstance(q, dict):
                    q["_explanation_after_rebalance_before_repair"] = q.get("explanation", "")

            questions = repair_multiple_choice_explanations(questions)

            questions = normalize_question_body_choice_styles(
                questions
            )

            logger.info(
                f"객관식 정답 위치 재배치 완료: "
                f"final_answers={[q.get('answer') for q in questions if isinstance(q, dict)]}"
            )

            if has_answer_position_bias(questions, question_type):
                logger.warning("정답 번호 편향 경고: 정답 번호가 한쪽으로 몰릴 가능성이 있습니다.")

            return questions

        except Exception as e:
            last_error = e
            logger.warning(
                f"LLM 문제 생성 재시도 필요: attempt={attempt + 1}/{max_retries + 1}, error={str(e)}"
            )
    raise ValueError(f"AI 문제 생성 검증 실패: {str(last_error)}")


def _build_plan_based_generation_prompt(
    topic: str,
    difficulty: str,
    count: int,
    score: int,
    question_type: str,
    competency_type: str,
    plans: list[dict],
) -> str:
    """
    문제 설계서를 기반으로 실제 문제 JSON을 생성하는 프롬프트.
    기존 generate_questions()에 있던 긴 프롬프트 규칙을 버리는 것이 아니라,
    설계서 기반 생성 단계에서 다시 적용한다.
    """
    plans_json = json.dumps(plans, ensure_ascii=False, indent=2)

    # 설계서에서 answer_style 추출 (첫 번째 설계서 기준)
    first_plan_answer_style = ""
    if plans and isinstance(plans[0], dict):
        first_plan_answer_style = str(plans[0].get("answer_style", "")).strip()
    
    java_choice_instruction = """
    [Java 선택지 작성 규칙]
    - Java 선택지는 학습자의 오해나 착각을 설명하지 말고 실제 Java 동작, 타입 규칙, 컬렉션 동작, 예외 흐름을 설명한다.
    - "오해할 수 있다", "혼동할 수 있다", "착각할 수 있다", "잘못 이해할 수 있다" 같은 표현을 선택지에 절대 쓰지 않는다.
    - equals/hashCode 문제에서는 HashSet/HashMap이 객체 동등성과 해시 값을 어떤 기준으로 판단하는지 설명한다.
    - 선택지는 "학습자가 어떻게 이해한다"가 아니라 "코드가 어떻게 동작한다"를 설명해야 한다.
    - static/instance 메서드 문제에서는 정답 외 선택지가 일반적으로도 맞는 설명이 되면 안 된다.
    - 예를 들어 "인스턴스 메서드는 객체의 상태에 접근할 수 있다"는 일반적으로 맞는 설명이므로, 정답이 static 메서드 설명일 때 오답으로 사용하지 않는다.
    - 오답은 반드시 문제의 코드 조건과 충돌해야 한다.
    - static 메서드 문제의 오답 예시는 다음과 같은 방향으로 만든다:
      1) static 메서드가 this 키워드를 사용할 수 있다고 설명
      2) static 메서드가 인스턴스 필드에 직접 접근할 수 있다고 설명
      3) 인스턴스 메서드를 객체 생성 없이 호출할 수 있다고 설명
      4) static 메서드와 인스턴스 메서드의 호출 방식이 동일하다고 설명
    - "일반적으로 맞는 설명이지만 정답보다 덜 적절한 선택지"를 만들지 않는다.
    - 정답이 static 메서드의 특징이면, 오답에는 "인스턴스 메서드는 객체의 상태에 접근할 수 있다"처럼 일반적으로 참인 설명을 넣지 않는다.
    - 정답이 instance 메서드의 특징이면, 오답에는 "static 메서드는 클래스에 속한다"처럼 일반적으로 참인 설명을 넣지 않는다.
    - 오답은 반드시 코드 조건과 충돌하는 문장이어야 한다.
    - static/instance 비교 문제의 선택지는 모두 같은 판단 축으로 작성한다.
    - 예: 호출 주체, this 사용 가능 여부, 인스턴스 필드 직접 접근 가능 여부, 객체 생성 필요 여부 중 하나의 축으로 통일한다.
    - "static 메서드는 클래스에 속한다"와 "인스턴스 메서드는 객체 상태에 접근한다"처럼 둘 다 참인 문장을 동시에 선택지로 두지 않는다.
    - static/instance 메서드 비교 문제에서 오답은 반드시 틀린 설명을 포함해야 한다.
    - 오답에 일반적으로 참인 설명만 단독으로 넣지 않는다.
    - 예를 들어 "static 메서드는 클래스 레벨에서 호출할 수 있으며 인스턴스 변수에 접근할 수 없다"는 일반적으로 참인 설명이므로 오답으로 사용하지 않는다.
    - 예를 들어 "인스턴스 메서드는 객체를 통해 호출해야 하며 인스턴스 변수에 접근할 수 있다"는 일반적으로 참인 설명이므로 오답으로 사용하지 않는다.
    - 오답은 다음처럼 명확히 틀린 문장을 포함해야 한다:
      1) static 메서드는 this 키워드를 사용할 수 있다.
      2) static 메서드는 인스턴스 변수에 직접 접근할 수 있다.
      3) 인스턴스 메서드는 클래스 이름으로 호출할 수 있다.
      4) static 메서드와 인스턴스 메서드는 동일한 방식으로 호출된다.
    """
    ai_evidence_instruction = """
    [AI 중급 evidence 작성 규칙]
    - AI 중급 문제는 일반적인 응답 품질 문제가 아니라 topic에 포함된 기술 단서를 body에 직접 포함해야 한다.
    - topic에 LLM, JSON, schema, structured output, validation, tool calling 중 하나가 있으면 body에 최소 2개 이상의 구체 단서를 포함한다.
    - JSON schema 문제는 body에 요구 schema, LLM 응답 예시, validation error 로그 중 2개 이상을 포함한다.
    - structured output 문제는 출력 형식 요구사항과 실제 LLM 응답의 불일치를 포함한다.
    - choices는 일반론이 아니라 오류 원인, 검증 실패 원인, schema 불일치 원인, prompt 제약 부족 중 하나를 판단하게 만든다.
    - "모델이 키워드를 인식한다" 같은 일반 챗봇 품질 문제로 바꾸지 않는다.
    """
    # answer_style별 추가 지시문
    # 기본값: 일반 정답형 문제
    answer_style_instruction = """
    [관리자 출제 의도: find_correct - 옳은 것 찾기]
    - 이 문제는 "옳은 것", "적절한 것", "정확한 설명"을 고르는 문제다.
    - choices 5개 중 정확히 1개만 올바른 설명이어야 한다.
    - 나머지 4개 선택지는 같은 주제 범위 안에서 그럴듯하지만 기술적으로 틀린 설명이어야 한다.
    - answer는 올바른 설명의 번호여야 한다.
    - body 마지막 질문은 "다음 중 옳은 설명은 무엇인가?", "다음 중 가장 적절한 설명은 무엇인가?", "다음 중 정확한 설명은 무엇인가?" 형태여야 한다.
    - "다음 중 옳지 않은 설명은 무엇인가?", "틀린 설명은 무엇인가?"처럼 오답을 고르는 질문 형태로 만들지 않는다.
    - 선택지에는 "오해할 수 있다", "혼동할 수 있다", "착각할 수 있다", "잘못 이해할 수 있다" 같은 메타 표현을 쓰지 않는다.
    - explanation은 정답 선택지가 왜 옳은지 설명하고, 주요 오답이 왜 틀렸는지도 함께 설명한다.
    """

    # answer_style별 추가 지시문
    if first_plan_answer_style == "find_incorrect":
        answer_style_instruction = """
        [관리자 출제 의도: find_incorrect - 틀린 것 찾기]
        - 이 문제는 "틀린 것", "옳지 않은 것", "잘못된 것"을 고르는 문제다.
        - choices 5개 중 정확히 4개는 올바른 설명이어야 하고, 정확히 1개만 틀린 설명이어야 한다.
        - answer는 틀린 설명의 번호여야 한다.
        - body 마지막 질문은 반드시 "다음 중 옳지 않은 설명은 무엇인가?" 또는 "가장 부적절한 설명은 무엇인가?" 형태여야 한다.
        - explanation은 정답 선택지(틀린 설명)가 왜 틀렸는지 설명하고, 나머지 선택지는 왜 올바른 설명인지 확인해야 한다.
        - explanation에서 올바른 4개 선택지를 "틀렸다"고 설명하면 절대 안 된다.
        - 설계서의 target_misconception을 반드시 틀린 선택지의 핵심 내용으로 사용한다.
        - 설계서의 relation이 "compare"이면 concepts에 있는 두 개념의 역할 차이를 기준으로 선택지를 만든다.
        - target_misconception과 무관한 임의의 틀린 설명을 정답으로 만들지 않는다.
        - "가장 적절한 것은?"처럼 올바른 것을 고르는 질문 형태로 만들지 않는다.
        """
    elif first_plan_answer_style == "output_prediction":
        answer_style_instruction = """
    [관리자 출제 의도: output_prediction - 출력 결과 예측]
    - 출력 결과 선택지는 숫자만 단독으로 쓰지 않는다.
    - 선택지는 "출력 결과는 2이다.", "users.size()는 2를 출력한다."처럼 문장형으로 작성한다.
    - 모든 선택지는 비슷한 길이의 출력 결과 설명으로 작성한다.
    - body에는 반드시 실행 가능한 코드 블록이 포함되어야 한다.
    - choices는 모두 출력 결과 후보여야 한다 (예: "0", "1", "None", "[1, 2]" 등).
    - answer는 실제 코드 실행 결과의 번호여야 한다.
    - 반드시 코드를 스스로 실행해본다고 가정하고, 조건문(if)이나 반복문(for)의 결과를 정확히 계산하여 실제 정답과 answer 인덱스가 일치하도록 작성한다.
    - body 마지막 질문은 "위 코드의 출력 결과는 무엇인가?" 형태여야 한다.
    - 코드에 print()가 2개 이상 있으면 선택지는 단일 출력값이 아니라 전체 출력 순서를 표현해야 한다.
    - 예: print(next(g))가 두 번이면 "출력 결과는 0과 1이다."처럼 두 줄 또는 두 값을 모두 포함해야 한다.
    - body가 "전체 실행 결과"를 묻는 경우 "출력 결과는 1이다."처럼 마지막 출력값만 선택지로 만들지 않는다.
    - 특정 호출 결과만 묻고 싶다면 body에 반드시 "두 번째 next() 호출 결과"처럼 명확히 작성해야 한다.
    """
    elif first_plan_answer_style == "error_reason":
        answer_style_instruction = """
    [관리자 출제 의도: error_reason - 오류 원인 찾기]
    - body에는 반드시 오류가 발생하는 코드 블록이 포함되어야 한다.
    - choices는 오류 원인 또는 수정 방향 후보여야 한다.
    - choices 5개는 모두 같은 코드 또는 조건을 기준으로 판단 가능한 오류 원인 설명이어야 한다.
    - 정답 선택지만 길게 쓰지 말고, 5개 선택지의 문장 길이와 구체성 수준을 비슷하게 맞춘다.
    - 오답은 완전히 엉뚱한 설명이 아니라, 비슷한 문법/타입/스코프/실행 흐름 개념을 헷갈렸을 때 나올 수 있는 설명으로 만든다.
    - "오해할 수 있다", "혼동할 수 있다", "착각할 수 있다", "잘못 이해할 수 있다" 같은 메타 표현을 쓰지 않는다.
    - answer는 실제 오류 원인에 해당하는 번호여야 한다.
    - body 마지막 질문은 "오류 원인으로 가장 적절한 것은 무엇인가?" 형태여야 한다.
    """

    return f"""
    너는 IT 역량진단 문제은행의 전문 출제자다.
    목표는 실제 채용/역량진단에 사용할 수 있는 품질의 문제를 생성하는 것이다.
    중요:
    너는 문제를 처음부터 자유롭게 만드는 것이 아니라,
    아래 [문제 설계서]를 기반으로 실제 문제 JSON만 생성해야 한다.
    반드시 JSON 배열만 출력해라.
    마크다운 코드블록, 설명 문장, 추가 텍스트는 절대 출력하지 마라.
    [출제 조건]
    - 역량 유형: {competency_type or "미지정"}
    - 세부 주제: {topic}
    - 난이도: {difficulty}
    - 배점: {score}
    - 생성 개수: {count}
    - 문제 유형: {question_type}
    [문제 설계서]
    {plans_json}
    {answer_style_instruction}
    {choice_quality_rule()}
    {answer_leak_prevention_rule()}
    {compare_choice_balance_rule()}
    {answer_explanation_consistency_rule()}
    {code_evidence_rule(competency_type, difficulty)}
    {java_choice_instruction if normalize_competency_type(competency_type) == "java" else ""}
    {ai_evidence_instruction if normalize_competency_type(competency_type) == "ai" else ""}
    [중요 검증 규칙]
    - 문제는 반드시 IT 역량진단과 관련된 내용이어야 한다.
    - 세부 주제가 음식, 여행, 연애, 취미, 쇼핑 등 IT와 무관하면 문제를 생성하지 않는다.
    - 선택된 역량 유형과 세부 주제가 맞지 않으면 문제를 생성하지 않는다.

    [출제 기준]
    - 사용자가 선택한 역량 유형을 최우선 기준으로 문제를 생성한다.
    - 세부 주제는 역량 유형 안에서 더 좁은 출제 범위로만 사용한다.
    - 세부 주제가 역량 유형보다 우선하면 안 된다.
    - 문제 설계서의 target_concept를 문제의 평가 대상으로 삼는다.
    - 문제 설계서의 scenario와 constraints를 문제 본문에 반영한다.
    - 문제 설계서의 correct_reason과 answer_decision_rule을 정답 판단 기준으로 사용한다.
    - 문제 설계서의 distractor_strategy를 기준으로 오답을 만든다.
    
    {hallucination_guard_rule()}

    [품질 기준]
    - 문제는 실제 IT 역량진단에 사용할 수 있어야 한다.
    - 너무 쉬운 상식 문제, 말장난 문제, 암기만 요구하는 문제는 피한다.
    - 문제 본문은 평가하려는 개념이 명확해야 한다.
    - 오답은 그럴듯해야 하지만, 정답과 명확히 구분되어야 한다.
    - 해설은 정답 이유만 쓰지 말고 핵심 개념과 오답 판단 근거를 포함해야 한다.
    - 같은 개념을 문장만 바꿔 반복 출제하지 마라.
    - {count}개의 문제는 서로 평가 포인트가 달라야 한다.
    [문제 본문 질문형 작성 규칙]
    - body는 상황 설명만으로 끝내지 않는다.
    - body의 마지막 문장은 반드시 설계서의 answer_style에 맞는 질문이어야 한다.
    - 객관식 문제의 body는 반드시 물음표(?)로 끝나야 한다.
    - answer_style이 "find_incorrect"이면 body 마지막 문장은 반드시 "다음 중 옳지 않은 설명은 무엇인가?" 또는 "다음 중 잘못된 설명은 무엇인가?"로 끝낸다.
    - answer_style이 "find_correct"이면 body 마지막 문장은 반드시 "다음 중 옳은 설명은 무엇인가?"로 끝낸다.
    - answer_style이 "output_prediction"이면 body 마지막 문장은 반드시 "위 코드의 실행 결과는 무엇인가?" 또는 "위 쿼리의 실행 결과는 무엇인가?"로 끝낸다.
    - answer_style이 "error_reason"이면 body 마지막 문장은 반드시 "오류 원인으로 가장 적절한 것은 무엇인가?"로 끝낸다.
    - answer_style이 "behavior_reason"이면 body 마지막 문장은 "가장 적절한 판단은 무엇인가?" 또는 "가장 타당한 대응은 무엇인가?"로 끝낸다.
    - find_incorrect 유형에서 "가장 적절한 판단은 무엇인가?", "가장 타당한 대응은 무엇인가?", "가장 적절한 것은 무엇인가?"처럼 올바른 것을 고르는 질문 문장을 사용하지 않는다.
    - "이러한 상황에서 쿼리 성능 저하의 원인을 분석해야 합니다."처럼 평서문으로 끝내지 않는다.
    [역량별 문제 형식 강제 규칙]
    - 중급/고급 문제는 단순히 긴 상황 설명만으로 구성하지 않는다.
    - 문제는 선택한 역량의 실제 작업 단위를 평가해야 한다.
    - 역량이 "sql"이면 중급/고급 body에 반드시 SQL 쿼리, 테이블 구조, WHERE/JOIN/GROUP BY 조건, 실행 계획 설명 중 하나를 포함한다.
    - 역량이 "data_structure_algorithm"이면 중급/고급 body에 반드시 입력 크기, 연산 빈도, 의사코드, 시간복잡도 조건, 자료구조 선택 조건 중 하나를 포함한다.
    - 역량이 "ai"이면 중급/고급 body에 반드시 데이터 상태, 평가 지표, 검색 결과 예시, RAG 파이프라인 조건, 모델 성능 문제 중 하나를 포함한다.
    - 역량이 "software_engineering"이면 중급/고급 body에 요구사항 목록, 변경 요청, 테스트 실패, 이해관계자 충돌, 품질 속성 누락 중 하나를 포함한다.
    - java, python, sql 문제에서 코드나 쿼리 없이 "가장 적절한 판단은 무엇인가?"만 묻는 비문학형 문제를 만들지 않는다.
    - 선택지는 단순 태도나 일반론이 아니라 코드/쿼리/조건을 근거로 판단 가능한 수정안 또는 해석이어야 한다.
    [question_format별 body 작성 규칙]
    - 각 문제는 반드시 해당 설계서의 question_format을 따른다.
    - question_format을 무시하고 일반 상황 설명형 문제로 만들지 않는다.

    - code_output:
    - body에는 반드시 코드 블록 또는 코드 조각이 포함되어야 한다.
    - 질문은 코드의 실행 결과와 그 이유를 물어야 한다.

    - override_behavior:
    - body에는 반드시 Java 상속/오버라이딩 코드가 포함되어야 한다.
    - 부모 타입 참조 변수와 자식 객체 생성 코드가 포함되어야 한다.
    - 질문은 실제 호출되는 메서드와 그 이유를 물어야 한다.

    - runtime_error:
    - body에는 반드시 오류가 발생할 수 있는 Python 코드가 포함되어야 한다.
    - 질문은 발생 가능한 오류와 가장 적절한 수정 방법을 물어야 한다.

    - data_structure_fix:
    - body에는 반드시 리스트/딕셔너리 리터럴 또는 실제 Python 데이터 예시가 포함되어야 한다.
    - 질문은 자료 접근 방식 또는 수정 방법을 물어야 한다.

    - join_where_bug:
    - body에는 반드시 SQL 쿼리가 포함되어야 한다.
    - 질문은 JOIN 조건과 WHERE 조건 중 어떤 부분이 결과에 영향을 주는지 물어야 한다.
    - compile_error:
    - body에는 반드시 컴파일 오류가 발생하는 Java 코드 블록이 포함되어야 한다.
    - 질문은 컴파일 오류 원인과 가장 적절한 수정 방향을 물어야 한다.
    - 선택지는 모두 Java 문법 또는 타입 규칙 기준으로 판단 가능해야 한다.

    - polymorphism_dispatch:
    - body에는 반드시 Java 상속 코드가 포함되어야 한다.
    - 부모 클래스 타입 참조 변수에 자식 객체를 대입하는 코드가 포함되어야 한다.
    - 질문은 실제 호출되는 오버라이딩 메서드와 그 이유를 물어야 한다.

    - collection_behavior:
    - body에는 반드시 Java 컬렉션 사용 코드가 포함되어야 한다.
    - HashSet, HashMap, ArrayList, List, Map 중 하나 이상을 사용해야 한다.
    - 질문은 contains, add, get, put, size, 중복 처리, key 비교 중 하나의 동작을 물어야 한다.

    - equals_hashcode:
    - body에는 반드시 equals 또는 hashCode를 재정의한 Java class 코드가 포함되어야 한다.
    - body에는 반드시 HashSet 또는 HashMap 사용 코드가 포함되어야 한다.
    - 질문은 equals/hashCode 규약이 컬렉션 동작에 미치는 영향을 물어야 한다.

    - interface_abstract:
    - body에는 반드시 interface, abstract class, implements, extends 중 하나 이상이 포함된 Java 코드가 있어야 한다.
    - 질문은 default method 충돌, 추상 메서드 구현, 참조 타입 사용 가능 여부 중 하나를 물어야 한다.

    - exception_flow:
    - Java 문제라면 body에는 반드시 try/catch/finally 또는 throws 코드가 포함되어야 한다.
    - Python 문제라면 body에는 반드시 try/except/finally 코드가 포함되어야 한다.
    - 질문은 예외 발생 흐름, catch 순서, finally 실행 여부 중 하나를 물어야 한다.
    
    - list_dict_mutation:
    - body에는 반드시 Python 리스트 또는 딕셔너리 수정 코드가 포함되어야 한다.
    - 질문은 코드 실행 후 값 변화, 참조 공유, mutable 객체 변경 결과를 물어야 한다.

    - shallow_deep_copy:
    - body에는 반드시 list.copy(), slicing [:], copy.copy(), copy.deepcopy() 중 하나가 포함되어야 한다.
    - 중첩 리스트를 사용해 내부 객체 공유 여부를 판단하게 한다.
    - copied = original만 사용하는 문제는 얕은 복사 문제가 아니라 참조 할당 문제로 다룬다.

    - generator_behavior:
    - body에는 반드시 yield, next(), generator 객체 생성 코드가 포함되어야 한다.
    - 질문은 generator 함수 호출 시점과 next() 호출 시점의 실행 흐름을 물어야 한다.

    - decorator_behavior:
    - body에는 반드시 decorator 함수와 @decorator 적용 코드가 포함되어야 한다.
    - 질문은 함수 호출 순서, wrapper 실행, 반환값 변화를 물어야 한다.

    - scope_closure:
    - body에는 반드시 nested function, closure, nonlocal 중 하나 이상이 포함된 Python 코드가 있어야 한다.
    - 질문은 변수 스코프와 상태 유지 여부를 물어야 한다.
    
    - query_result:
    - body에는 반드시 SQL 쿼리와 테이블/데이터 조건이 포함되어야 한다.
    - 질문은 쿼리 결과 또는 결과가 달라지는 이유를 물어야 한다.

    - index_plan_choice:
    - body에는 반드시 실행 계획, 인덱스 후보, 데이터 규모, WHERE/JOIN/ORDER BY 조건 중 2개 이상이 포함되어야 한다.
    - 질문은 어떤 인덱스 또는 실행 계획 검토가 가장 타당한지 물어야 한다.

    - retrieval_result_analysis:
    - body에는 반드시 query, top_k, 검색 결과 chunk 예시, similarity 또는 score가 포함되어야 한다.
    - 질문은 검색 결과가 부정확한 원인이나 우선 개선 지점을 물어야 한다.

    - rag_pipeline_diagnosis:
    - body에는 반드시 아래 5개 항목을 모두 포함한다.
      1) 실제 query 문자열
      2) top_k 값
      3) metadata filter 적용 여부
      4) reranker 적용 여부
      5) 검색 결과 chunk 예시 2개 이상과 similarity 또는 score
    - 예:
    query="요구사항 변경 영향 분석"
    top_k=5
    metadata_filter 미적용
    reranker 미적용
    검색 결과:
    - chunk #1: category=database, similarity=0.41, 내용="인덱스 실행 계획..."
    - chunk #2: category=software_engineering, similarity=0.38, 내용="요구사항 검토..."
    - 질문은 단순히 "무엇이 가장 좋은가"가 아니라, 검색 결과가 부정확해진 가장 직접적인 원인 또는 가장 우선적인 개선 지점을 묻는다.
    - 위 5개 항목 중 하나라도 빠지면 해당 문제는 생성하지 않는다.

    - hybrid_search_choice:
    - body에는 반드시 vector search 결과와 keyword search 필요성이 드러나는 조건을 포함한다.
    - body에는 query, top_k, 검색 결과 chunk 예시, similarity 또는 score를 포함한다.
    - keyword가 정확히 일치해야 하는 용어, 코드명, 약어, 버전명, 자격증 용어 중 하나를 포함한다.
    - 질문은 vector search만 사용할 때의 한계와 keyword search를 결합해야 하는 이유를 판단하게 한다.
    - reranker_tradeoff:
    - body에는 반드시 first-stage retrieval 결과와 reranker 적용 후 기대 효과 또는 비용 조건을 포함한다.
    - body에는 top_k, candidate 수, latency 또는 p95 응답 시간, similarity/score 중 하나 이상을 포함한다.
    - 질문은 reranker를 무조건 적용하는 것이 아니라 accuracy 개선 효과와 latency 증가를 함께 판단하게 한다.

    - metric_interpretation:
    - body에는 반드시 precision, recall, F1, accuracy 중 하나 이상의 수치가 포함되어야 한다.
    - 질문은 지표 해석 또는 개선 방향을 물어야 한다.

    [설계서 반영 규칙]
    - 각 문제는 문제 설계서 1개를 기반으로 생성한다.
    - 설계서 개수가 생성 개수보다 적더라도, 같은 설계서를 기반으로 선택지 구성, 정답 판단 축, 오답 유형을 다르게 하여 최대 생성 개수만큼 후보 문제를 생성한다.
    - 단, 서로 완전히 같은 문제를 반복하지 않는다.
    - 각 후보는 같은 개념을 평가하더라도 오답 구성과 판단 포인트가 달라야 한다.
    - 설계서에 있는 scenario를 문제 본문에 자연스럽게 반영한다.
    - 설계서에 있는 constraints를 문제 본문에 반드시 반영한다.
    - 설계서에 있는 target_concept를 벗어난 문제를 만들지 않는다.
    - 설계서에 있는 correct_reason과 answer_decision_rule에 따라 정답을 결정한다.
    - 설계서에 있는 distractor_strategy에 따라 오답을 구성한다.
    - plan_review.is_valid가 false인 설계서는 가능한 한 보완하되, 보완이 어렵다면 해당 설계서 문제는 생성하지 않는다.
    
    [자연어 출제 의도 반영 규칙]
    - 각 문제는 설계서의 concepts, relation, target_misconception, must_include, avoid를 반드시 반영한다.
    - concepts에 2개 이상의 개념이 있고 relation이 "compare"이면, 두 개념의 차이를 직접 비교하는 문제로 만든다.
    - relation이 "compare"인데 한 개념만 설명하는 문제를 만들지 않는다.
    - target_misconception이 있으면, 그 오개념의 의미가 선택지 또는 해설에 반드시 반영되어야 한다.
    - find_incorrect 유형에서는 target_misconception의 의미를 실제로 틀린 기술 설명 문장으로 변환해 정답 선택지로 만든다.
    - must_include에 있는 요소는 문제 본문에 반드시 포함한다.
    - avoid에 있는 방향의 문제는 만들지 않는다.
    - target_misconception은 선택지에 그대로 쓰지 않는다.
    - target_misconception에 "오해", "혼동", "착각" 같은 표현이 있으면, 이를 제거하고 실제로 틀린 기술 설명 문장으로 바꾼다.
    - choices에는 "오해할 수 있다", "혼동할 수 있다", "착각할 수 있다", "잘못 이해할 수 있다" 같은 학습자 상태 설명을 쓰지 않는다.
    - 특정 기술명 예시를 그대로 반복하지 말고, 설계서의 concepts와 target_misconception에 맞춰 선택지를 구성한다.

    [문제 문체 규칙]
    - title은 짧은 명사형으로 작성한다.
    - body는 시험 문제 본문체로 작성한다.
    - body는 존댓말을 사용하지 않는다.
    - body에서 "~까요?", "~해야 할까요?", "~선택해야 할까요?", "~검토해야 할까요?" 같은 표현을 사용하지 않는다.
    - explanation만 존댓말로 작성한다.
    - body의 마지막 질문 문장은 반드시 설계서의 answer_style을 따른다.

    {difficulty_rule(difficulty)}
    {competency_rule(competency_type, topic)}
    {question_type_rule(question_type)}
    {explanation_rule(question_type)}
    {answer_distribution_rule(count, question_type)}

    [출력 검증 규칙]
    출력하기 전에 스스로 다음을 검증해라:
    1. JSON 배열만 출력했는가?
    2. 문제 개수가 최대 {count}개인가?
    3. 각 문제에 title, body, choices, answer, explanation, difficulty, competency_type, competency_tags, score가 있는가?
    4. 객관식이면 choices가 정확히 5개인가?
    5. 객관식 answer가 1~5 숫자인가?
    6. answer는 0부터 시작하는 index가 아닌가?
    7. 정답이 실제로 choices 중 하나와 일치하는가?
    8. explanation에 적힌 정답 번호와 answer 값이 같은가?
    9. 난이도가 "{difficulty}"에 맞는가?
    10. score가 {score}인가?
    11. 존재하지 않는 기술/함수/API/명령어를 만들지 않았는가?
    12. 문제 설계서의 constraints가 문제 본문에 반영되었는가?
    13. 정답이 answer_decision_rule에 의해 결정되는가?
    14. 오답이 distractor_strategy에 맞게 구성되었는가?
    [공통 출력 규칙]
    - 반드시 JSON 배열로만 반환한다.
    - 배열 안에는 최대 {count}개의 문제 객체만 넣는다.
    - difficulty는 반드시 "{difficulty}"로 작성한다.
    - score는 반드시 {score}로 작성한다.
    - competency_type은 "{competency_type or topic}" 값으로 작성한다.
    - competency_tags는 세부 주제와 관련된 문자열 배열로 작성한다.
    """

def generate_questions_from_plans(
    topic: str,
    difficulty: str,
    plans: list[dict],
    count: int = 1,
    score: int = 1,
    question_type: str = "multiple_choice",
    competency_type: str | None = None,
):
    """
    문제 설계서 기반으로 실제 문제 JSON을 생성한다.
    기존 _generate_with_retry()를 그대로 사용해서
    JSON 검증, 정답 번호 검증, 정답 위치 재배치, 해설 재생성을 모두 유지한다.
    """
    prompt = _build_plan_based_generation_prompt(
        topic=topic,
        difficulty=difficulty,
        count=count,
        score=score,
        question_type=question_type,
        competency_type=competency_type or "미지정",
        plans=plans,
    )
    last_error = None

    for attempt in range(3):
        try:
            generated_questions = _generate_with_retry(
                prompt=prompt,
                system_message=(
                    "너는 IT 역량진단 문제은행의 문제 출제 전문가다. 반드시 유효한 JSON 배열만 출력한다. "
                    "Python/Java 중급·고급 문제는 반드시 코드 블록을 포함해야 한다. "
                    "코드 없는 설명형 문제는 절대 생성하지 않는다. "
                    "find_incorrect 유형이면 4개는 맞는 설명, 1개만 틀린 설명으로 구성한다."
                ),
                question_type=question_type,
                difficulty=difficulty,
                score=score,
                temperature=0.1 + (attempt * 0.05),
                max_retries=0,
                plans=plans,
                competency_type=competency_type,
            )

            validated_questions = validate_questions(
                questions=generated_questions,
                question_type=question_type,
                difficulty=difficulty,
                score=score,
            )

            if validated_questions:
                return validated_questions[:count]

            last_error = "생성된 문제 중 validator를 통과한 문제가 없습니다."

            logger.warning(
                f"설계서 기반 문제 후보 검증 실패: attempt={attempt + 1}/3, "
                f"generated={len(generated_questions) if isinstance(generated_questions, list) else 'not_list'}, "
                f"validated=0"
            )

        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"설계서 기반 문제 생성 재시도: attempt={attempt + 1}/3, error={last_error}"
            )

    raise ValueError(f"설계서 기반 문제 생성 검증 실패: {last_error}")

def generate_questions(
    topic: str,
    difficulty: str,
    count: int = 1,
    score: int = 1,
    question_type: str = "multiple_choice",
    competency_type: str | None = None,
):
    """
    일반 AI 문제 생성.

    현재 생성 정책:
    - AI/SQL 고급 문제는 Templates 기반으로 안정화한다.
    - Python/Java를 포함한 그 외 문제는 planner -> generator -> validator 흐름을 사용한다.
    - Templates 기반 고급 문제는 body는 템플릿으로 고정하고 choices/explanation만 LLM으로 생성한다.
    """
    start_time = time.time()
    logger.info(
        f"LLM Pipeline [Generate]: 설계서 기반 AI 문제 생성 시작 "
        f"(주제: '{topic}', 유형: {question_type}, 난이도: {difficulty}, 개수: {count}, 역량: {competency_type})"
    )

    try:
        normalized_competency_type = normalize_competency_type(competency_type) or "software_engineering"
        # ─────────────────────────────────────────────
        # AI 고급 문제는 topic 기반 템플릿 라우터로 생성
        # - RAG / LLM / Agent / ModelOps / ML 템플릿 중 topic에 맞게 선택
        # - body는 템플릿으로 고정하고 choices/explanation만 LLM이 생성
        # ─────────────────────────────────────────────────────────────────────────────────────────
        if USE_AI_ADVANCED_TEMPLATE and normalized_competency_type == "ai" and difficulty == "고급":
            base_questions = []
            used_ai_template_formats: list[str] = []
            used_ai_titles: set[str] = set()

            for _ in range(count):
                base_question = build_ai_advanced_template(
                    topic=topic,
                    exclude_formats=used_ai_template_formats,
                )

                selected_title = str(base_question.get("title") or "").strip()

                if selected_title in used_ai_titles:
                    for _retry_title in range(5):
                        retry_question = build_ai_advanced_template(
                            topic=topic,
                            exclude_formats=used_ai_template_formats,
                        )
                        retry_title = str(retry_question.get("title") or "").strip()

                        if retry_title and retry_title not in used_ai_titles:
                            base_question = retry_question
                            selected_title = retry_title
                            break

                selected_format = base_question.get("template_format")

                if selected_format and str(selected_format) not in used_ai_template_formats:
                    used_ai_template_formats.append(str(selected_format))

                if selected_title:
                    used_ai_titles.add(selected_title)

                base_questions.append(base_question)

            template_questions = generate_choices_for_template_questions_batch(
                base_questions
            )

            validated_questions = validate_questions(
                questions=template_questions,
                question_type=question_type,
                difficulty=difficulty,
                score=score,
            )

            if len(validated_questions) == 0:
                raise ValueError("AI 고급 템플릿 문제 검증을 통과하지 못했습니다.")

            validated_questions = rebalance_answer_positions(
                validated_questions,
                question_type,
            )
            
            validated_questions = normalize_question_body_choice_styles(
                validated_questions
            )

            validated_questions = repair_multiple_choice_explanations(validated_questions)
            # DB 저장/응답에는 내부 템플릿 필드가 필요 없으므로 최종 반환 전에 제거한다.
            for question in validated_questions:
                question.pop("answer_intent", None)
                question.pop("distractor_intents", None)
                question.pop("template_format", None)
                question.pop("lock_choices", None)

            logger.info(
                "AI 고급 템플릿 정답 위치 재배치 완료: "
                f"final_answers={[q.get('answer') for q in validated_questions]}"
            )

            logger.info(
                "AI 고급 템플릿 선택 완료: "
                f"used_formats={used_ai_template_formats}"
            )

            if has_answer_position_bias(validated_questions, question_type):
                logger.warning("AI 고급 정답 번호 편향 경고: 정답 번호가 한쪽으로 몰릴 가능성이 있습니다.")

            elapsed_time = time.time() - start_time
            logger.info(
                f"LLM Pipeline [Generate]: AI 고급 템플릿 + LLM 선택지 기반 문제 생성 완료 "
                f"(생성된 문제 수: {count}, 소요 시간: {elapsed_time:.3f}초)"
            )

            return validated_questions[:count]

        # ─────────────────────────────────────────────
        # SQL 고급 문제는 템플릿 기반으로 우선 생성
        # - planner/generator를 타지 않음
        # - 테이블 구조, SQL 쿼리, 데이터 규모, 실행 계획, 인덱스/락 조건이 포함된 문제를 생성
        # ─────────────────────────────────────────────
        if USE_SQL_ADVANCED_TEMPLATE and normalized_competency_type == "sql" and difficulty == "고급":
            template_questions = []
            used_sql_template_formats: list[str] = []

            for _ in range(count):
                base_question = build_sql_advanced_template(
                    topic=topic,
                    exclude_formats=used_sql_template_formats,
                )

                selected_format = base_question.get("template_format")
                if selected_format:
                    used_sql_template_formats.append(str(selected_format))

                generated_question = generate_choices_for_template_question(base_question)

                # DB 저장/응답에는 내부 필드가 필요 없으므로 제거한다.
                generated_question.pop("answer_intent", None)
                generated_question.pop("distractor_intents", None)
                generated_question.pop("lock_choices", None)
                generated_question.pop("template_format", None)

                template_questions.append(generated_question)

            validated_questions = validate_questions(
                questions=template_questions,
                question_type=question_type,
                difficulty=difficulty,
                score=score,
            )

            if len(validated_questions) == 0:
                raise ValueError("SQL 고급 템플릿 문제 검증을 통과하지 못했습니다.")
            
            validated_questions = rebalance_answer_positions(
                validated_questions,
                question_type,
            )

            validated_questions = normalize_question_body_choice_styles(
                validated_questions
            )

            validated_questions = repair_multiple_choice_explanations(validated_questions)
            logger.info(
                "SQL 고급 템플릿 선택 완료: "
                f"used_formats={used_sql_template_formats}"
            )
            elapsed_time = time.time() - start_time
            logger.info(
                f"LLM Pipeline [Generate]: SQL 고급 템플릿 + LLM 선택지 기반 문제 생성 완료 "
                f"(생성된 문제 수: {count}, 소요 시간: {elapsed_time:.3f}초)"
            )

            return validated_questions[:count]
        
        # ─────────────────────────────────────────────
        # 그 외 역량/난이도는 기존 설계서 기반 생성 흐름 사용
        # ─────────────────────────────────────────────
        if normalized_competency_type in {"python", "java"} and difficulty == "초급":
            candidate_count = count
        else:
            candidate_count = min(count + 2, 4)

        plans = generate_question_plans(
            topic=topic,
            difficulty=difficulty,
            count=candidate_count,
            question_type=question_type,
            competency_type=normalized_competency_type,
        )

        logger.info(
            f"LLM Pipeline [Planner]: 문제 설계서 생성 완료 "
            f"(생성된 설계서 수: {len(plans)}/{candidate_count})"
        )

        validated_questions = generate_questions_from_plans(
            topic=topic,
            difficulty=difficulty,
            plans=plans,
            count=candidate_count,
            score=score,
            question_type=question_type,
            competency_type=normalized_competency_type,
        )

        elapsed_time = time.time() - start_time
        logger.info(
            f"LLM Pipeline [Generate]: 설계서 기반 AI 문제 생성 완료 "
            f"(생성된 문제 수: {count}, "
            f"후보 통과 수: {len(validated_questions)}, 소요 시간: {elapsed_time:.3f}초)"
        )

        return validated_questions[:count]

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(
            f"LLM Pipeline [Generate]: 설계서 기반 AI 문제 생성 실패 "
            f"(소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}"
        )
        raise

def generate_questions_from_context(
    topic: str,
    context: str,
    difficulty: str,
    count: int = 1,
    score: int = 1,
    question_type: str = "multiple_choice",
    competency_type: str | None = None,
):
    normalized_competency_type = normalize_competency_type(competency_type)
    candidate_count = count

    if question_type == "multiple_choice" and difficulty in ["중급", "고급"]:
        candidate_count = min(count + 2, 5)

    start_time = time.time()
    logger.info(
        f"LLM Pipeline [RAG Generate]: RAG 기반 AI 문제 생성 시작 "
        f"(주제: '{topic}', 유형: {question_type}, 난이도: {difficulty}, 개수: {count})"
    )
    prompt = f"""
        너는 IT 역량진단 문제은행의 문서 기반 문제 출제 전문가다.
        목표는 제공된 문서 내용에 근거한 검증 가능한 문제만 생성하는 것이다.
        반드시 JSON 배열만 출력해라.
        마크다운 코드블록, 설명 문장, 추가 텍스트는 절대 출력하지 마라.

        [출제 조건]
        - 역량 유형: {normalized_competency_type or "미지정"}
        - 세부 주제: {topic}
        - 난이도: {difficulty}
        - 배점: {score}
        - 생성 개수: {candidate_count}
        - 문제 유형: {question_type}

        {document_grounding_rule()}
        {hallucination_guard_rule()}
        [역량 유형 제한 규칙]
        - 문제는 반드시 선택된 역량 유형에 맞아야 한다.
        - 세부 주제가 선택된 역량 유형과 충돌하면 문제를 생성하지 말고 빈 JSON 배열 [] 을 반환한다.
        - 역량 유형이 자료구조/알고리즘이면 LLM, RAG, 딥러닝 같은 인공지능 문제를 만들지 않는다.
        - 역량 유형이 sql이면 SQL 쿼리, 테이블 구조, JOIN, GROUP BY, 인덱스, 실행 계획, 트랜잭션, 정규화 중심 문제만 만든다.
        - 역량 유형이 ai이면 LLM, RAG, 임베딩, 벡터 검색, 모델 평가, 머신러닝, 데이터 전처리 중심 문제만 만든다.
        
        [문서 기반 중급 문제 생성 규칙]
        - 중급 문제는 문서에 있는 용어를 그대로 묻는 단순 정의형으로 만들지 않는다.
        - 문서의 절차, 검토 기준, 비교 기준, 판단 조건을 활용해 상황 판단형으로 만든다.
        - "가장 우선적으로 고려해야 할 사항"처럼 문서 순서만 맞히는 문제를 피한다.
        - 선택지는 모두 같은 범주의 개념으로 구성하되, 정답만 문서 근거와 직접 연결되게 한다.
        - 해설에는 정답 근거와 오답이 부족한 이유를 함께 설명한다.
        [품질 기준]
        - 단순히 문장 일부를 빈칸처럼 바꾸는 문제는 피한다.
        - 같은 문장을 거의 그대로 반복하는 문제는 피한다.
        - 문제는 역량진단에 적합해야 한다.
        - 오답은 문서의 유사 개념을 활용해 그럴듯하게 만들되, 문서 기준으로 명확히 틀려야 한다.
        - 생성되는 {candidate_count}개의 문제는 서로 다른 평가 포인트를 가져야 한다.
        - 문서 내용이 부족하면 {count}개보다 적게 생성해도 된다.
        - 단, 이 경우에도 JSON 배열만 출력한다.
        [문제 본문 질문형 작성 규칙]
        - body는 문서 내용 설명만으로 끝내지 마라.
        - body의 마지막 문장은 반드시 학습자가 무엇을 판단하거나 선택해야 하는지 묻는 질문이어야 한다.
        - 객관식 문제의 body는 반드시 물음표(?)로 끝나야 한다.
        - 중급/고급 문제는 상황 설명 후 판단 기준이 드러나는 질문으로 끝낸다.
        - 예: "이 상황에서 가장 적절한 검토 기준은 무엇인가?"
        - 예: "가장 우선적으로 확인해야 할 사항은 무엇인가?"
        - 예: "가장 타당한 대응은 무엇인가?"
        [문서 기반 중급/고급 문제 강화 규칙]
        - 중급/고급 문제는 문서의 문장을 그대로 확인하는 문제로 만들지 않는다.
        - 중급 문제는 문서 내용을 실제 상황에 적용하게 만든다.
        - 고급 문제는 문서 내용을 바탕으로 원인, 영향, 리스크, 우선순위, 대응 방안을 판단하게 만든다.
        - 단, 문서에 근거가 없는 상황은 만들지 않는다.
        [문서 기반 고급 문제 강제 규칙]
        - 난이도가 "고급"이면 문제 본문은 최소 3문장 이상으로 작성한다.
        - 문서에 나온 개념을 단순히 고르는 문제를 만들지 않는다.
        - 문서에 나온 개념 2개 이상을 연결해 판단하게 한다.
        - 예: 요구사항 완전성 + 변경 요청 증가
        - 예: 비기능 요구사항 + 검증 가능성
        - 예: 추적성 부족 + 변경 영향 분석 실패
        - 예: 기술적 타당성 + 성능/용량 제약
        - 선택지는 단어 또는 짧은 명사구로 쓰지 않는다.
        - 선택지는 모두 실무자가 실제로 선택할 수 있는 검토 기준 또는 대응 방안 문장으로 작성한다.
        - 문제 본문에 이미 정답 키워드를 직접 노출하지 않는다.
        - 예: 정답이 "완전성"이면 본문에 "누락", "모든 기능" 같은 단서를 과도하게 반복하지 않는다.
        [AI/RAG 고급 문제 evidence 강제 규칙]
        - 역량 유형이 "ai"이고 난이도가 "고급"이며 주제가 RAG, 검색, 임베딩, 벡터, hybrid search와 관련된 경우 body에는 반드시 검색 결과 단서와 RAG 파이프라인 단서를 함께 포함한다.
        - body에는 반드시 아래 표현 중 검색 결과 단서 4개 이상을 포함한다:
        query, top_k, chunk, similarity, vector_score, keyword_score, hybrid_score, metadata, category
        - body에는 반드시 아래 표현 중 파이프라인 단서 4개 이상을 포함한다:
        embedding, vector search, keyword search, hybrid search, metadata_filter, reranker, context filtering
        - body에는 반드시 최소 1개 이상의 수치를 포함한다.
        - 예: top_k=5, similarity=0.61, vector_score=0.58, keyword_score=0.40, hybrid_score=0.526
        - 단순히 "검색 품질이 낮다", "RAG 시스템을 개선해야 한다"처럼 일반론만 쓰는 문제는 생성하지 않는다.
        - 검색 결과 단서와 파이프라인 단서가 모두 포함되지 않으면 해당 문제는 생성하지 않는다.

        [AI/RAG 고급 문제 evidence 포함 및 본문 다양화 규칙]
        - 역량 유형이 "ai"이고 난이도가 "고급"이며 주제가 RAG, 검색, 임베딩, 벡터, hybrid search와 관련된 경우 body에는 반드시 검색 결과 단서와 RAG 파이프라인 단서를 함께 포함한다.
        - 단, 모든 문제를 같은 문장 구조로 작성하지 않는다.
        - "현재 RAG 검색 로그는 다음과 같습니다"로 모든 문제를 시작하지 않는다.
        - 같은 query, top_k, metadata_filter, chunk 정보를 매 문제마다 동일한 순서와 동일한 표현으로 반복하지 않는다.
        - 각 문제는 아래 5개 출제 패턴 중 서로 다른 패턴을 사용한다.

        [AI/RAG 고급 문제 출제 패턴]
        1. 정확 키워드 누락 상황
        - vector search 결과의 similarity는 높지만 정확 키워드가 누락된 상황을 제시한다.
        - keyword search 또는 hybrid search 도입 필요성을 판단하게 한다.

        2. metadata_filter 누락 상황
        - category가 다른 chunk가 context에 섞인 상황을 제시한다.
        - metadata_filter 적용 여부와 category 기반 필터링 필요성을 판단하게 한다.

        3. chunk 품질 및 context filtering 상황
        - 검색된 chunk 중 일부가 문맥상 부적절하거나 API 파라미터 설명처럼 얕은 내용인 상황을 제시한다.
        - context filtering 또는 chunk 품질 개선 기준을 판단하게 한다.

        4. reranker 적용 trade-off 상황
        - first-stage retrieval 결과는 충분하지만 순위 품질이 낮고, reranker 적용 시 latency가 증가하는 상황을 제시한다.
        - 정확도 개선과 응답 시간 증가 사이의 trade-off를 판단하게 한다.

        5. hybrid_score 해석 상황
        - vector_score와 keyword_score가 서로 다르게 나타나는 검색 결과를 제시한다.
        - similarity만 볼지, keyword_score만 볼지, hybrid_score를 종합할지 판단하게 한다.

        [AI/RAG evidence 최소 포함 기준]
        - 각 문제 body에는 아래 검색 결과 단서 중 4개 이상을 포함한다:
        query, top_k, chunk, similarity, vector_score, keyword_score, hybrid_score, metadata, category
        - 각 문제 body에는 아래 파이프라인 단서 중 3개 이상을 포함한다:
        embedding, vector search, keyword search, hybrid search, metadata_filter, reranker, context filtering
        - 각 문제 body에는 숫자 단서를 최소 2개 이상 포함한다.
        - 예: top_k=5, similarity=0.61, vector_score=0.68, keyword_score=1.0, hybrid_score=0.78, p95 latency=850ms
        - chunk 예시는 필요한 경우 1~2개만 사용하고, 모든 문제에서 동일한 chunk #1, chunk #2 표현을 반복하지 않는다.
        - body 마지막 문장은 반드시 물음표(?)로 끝낸다.

        [AI/RAG 문제 반복 방지 규칙]
        - {candidate_count}개의 문제는 제목, 문제 상황, 판단 기준이 서로 달라야 한다.
        - 같은 query 문자열을 사용하더라도 문제마다 평가 포인트가 달라야 한다.
        - "검색 결과의 적합성 평가", "hybrid search의 필요성", "검색 품질 개선 방안"처럼 제목만 바꾸고 같은 본문을 반복하지 않는다.
        - 같은 로그 형식을 복사한 뒤 마지막 질문만 바꾸는 문제는 생성하지 않는다.

        [중급/고급 문제 본문 작성 방식]
        - 난이도가 "중급" 또는 "고급"이면 문제 본문은 반드시 상황 설명 + 판단 질문 구조로 작성한다.
        - 중급 문제 본문 구조:
            "프로젝트/검토/명세 상황 설명 → 이때 가장 적절한 검토 기준은?"
        - 고급 문제 본문 구조:
            "문제 상황 + 제약 조건 + 발생 가능한 리스크 → 가장 우선적으로 판단하거나 대응해야 할 것은?"
        - 고급 문제는 최소 2문장 이상으로 작성한다.
        [중급/고급 금지 문제 유형]
        - 난이도가 "중급" 또는 "고급"이면 다음 유형의 문제를 만들지 않는다.
        - 단순히 문서에 있는 항목을 고르는 문제
        - "어떤 요소가 포함되어야 하는가?"처럼 목록 암기만 요구하는 문제
        - "올바른 설명은 무엇인가?"처럼 상황이 없는 문제
        - "다음 중 정의로 맞는 것은?" 형태의 문제
        - 정답만 명확하고 오답이 너무 쉽게 배제되는 문제
        - 선택지 중 3개 이상이 명백히 엉뚱한 문제
        [난이도별 문제 특성 규칙]
        - 문제는 반드시 요청된 난이도 "{difficulty}"에 맞게 생성한다.
        - 초급은 기본 개념, 용어 이해, 단순 구분을 평가한다.
        - 중급은 단순 정의 암기가 아니라 문서 내용을 바탕으로 한 비교, 적용, 검토 기준 선택, 상황 판단을 평가한다.
        - 고급은 문서 내용을 바탕으로 원인, 영향, 리스크, 우선순위, 대응 방안을 판단하게 한다.
        - "{difficulty}"가 중급 또는 고급이면 문제 본문에 짧은 실무 상황을 포함한다.
        [선택지 재배치 대응 규칙]
        - 시스템은 생성 후 선택지 순서를 재배치할 수 있다.
        - 따라서 explanation에서 오답을 설명할 때 "1번은", "2번은", "4번과 5번은"처럼 선택지 번호를 기준으로 설명하지 마라.
        - 정답 번호는 "정답은 N번입니다." 첫 문장에만 사용합니다.
        - 오답 설명은 번호가 아니라 선택지 내용 또는 개념 기준으로 작성합니다.
        - 예: "명명 규칙 검토는 요구사항 완전성 확인과 직접 관련이 낮습니다."
        [문서 기반 우선순위 판단 제한 규칙]
        - 문서에 여러 검토 기준이 나열되어 있을 뿐 우선순위가 명시되어 있지 않다면, 특정 기준을 "가장 우선"이라고 단정하지 않는다.
        - "가장 우선적으로 고려해야 할 사항"을 묻는 문제는 본문에 우선순위를 결정할 수 있는 구체적 상황을 반드시 포함한다.
        - 시장 성숙도, 상호 운용성, 기술 의존성, 성능/용량, 검증 여부처럼 모두 타당한 선택지가 있을 경우, 문서 근거 없이 하나만 정답으로 만들지 않는다.
        - 선택지들이 모두 문서상 타당한 검토 항목이면 문제를 생성하지 않는다.
        - 정답은 문서 내용과 문제 상황을 함께 보았을 때 다른 보기보다 명확히 우선되어야 한다.
        {difficulty_rule(difficulty)}
        {competency_rule(normalized_competency_type, topic)}
        {question_type_rule(question_type)}
        {explanation_rule(question_type)}
        {answer_distribution_rule(candidate_count, question_type)}
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
        - competency_type은 "{normalized_competency_type or topic}" 값으로 작성한다.
        - competency_tags는 문서 내용과 주제에 관련된 문자열 배열로 작성한다.
        - 문서 근거가 부족하면 빈 배열 [] 을 반환한다.
        """
    try:
        validated_questions = _generate_with_retry(
            prompt=prompt,
            system_message="너는 문서 기반 IT 역량진단 문제 출제자다. 반드시 제공된 문서 내용에 근거한 유효한 JSON 배열만 출력한다.",
            question_type=question_type,
            difficulty=difficulty,
            score=score,
            temperature=0.1,
            max_retries=0,
        )
        elapsed_time = time.time() - start_time
        logger.info(f"LLM Pipeline [RAG Generate]: RAG 기반 AI 문제 생성 완료 (생성된 문제 수: {count}, 소요 시간: {elapsed_time:.3f}초)")
        return validated_questions[:count]
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"LLM Pipeline [RAG Generate]: RAG 기반 AI 문제 생성 실패 (소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}")
        raise

def _has_code_evidence_in_body(body: str, competency_type: str | None) -> bool:
    body = str(body or "")
    competency_type = normalize_competency_type(competency_type)

    if competency_type == "java":
        if "```java" in body:
            return True

        strong_code_signals = [
            "\nclass ",
            "\ninterface ",
            "\npublic ",
            "\nprivate ",
            "\nvoid ",
            "@Override",
            "new ",
            "System.out.println",
            "HashSet<",
            "HashMap<",
            "ArrayList<",
            "List<",
            "Map<",
            "equals(",
            "hashCode(",
        ]

        return any(signal in body for signal in strong_code_signals)

    if competency_type == "python":
        # 단어만 있는 설명형 body를 코드로 오인하지 않기 위해
        # 코드 블록 또는 실제 코드 구조가 있을 때만 True로 판단한다.
        if "```python" in body:
            return True

        strong_code_signals = [
            "\ndef ",
            "\nclass ",
            "\nprint(",
            "\ntry:",
            "\nexcept",
            "\nfor ",
            "\nwhile ",
            "self.",
            "yield ",
            "next(",
            ".copy()",
            "copy.copy",
            "copy.deepcopy",
            "nonlocal ",
        ]

        return any(signal in body for signal in strong_code_signals)

    return True


def _reformat_java_oneliner(code: str) -> str:
    """
    Planner가 줄바꿈 없이 한 줄로 넘긴 Java 코드를 가독성 있게 재포맷한다.
    """
    c = code
    # 세미콜론 뒤 줄바꿈 (단, for loop 안 제외)
    c = re.sub(r";(?!\s*\))\s*(?=[^\s])", ";\n    ", c)
    # { 뒤 줄바꿈
    c = re.sub(r"\{\s*(?=[^\n])", "{\n    ", c)
    # } 앞에 줄바꿈
    c = re.sub(r"([^\n])\}", r"\1\n}", c)
    # @Override 앞에 줄바꿈
    c = c.replace("@Override", "\n    @Override")
    # 빈 줄 제거 후 정리
    lines = [line.rstrip() for line in c.splitlines() if line.strip()]
    return "\n".join(lines)


def _format_evidence_as_code_block(evidence_detail: str, competency_type: str | None) -> str:
    evidence_detail = str(evidence_detail or "").strip()
    # Planner가 "\\n" 문자열로 넘긴 코드를 실제 줄바꿈으로 변환한다.
    evidence_detail = evidence_detail.replace("\\n", "\n")
    evidence_detail = evidence_detail.replace("\\t", "    ")

    competency_type = normalize_competency_type(competency_type)

    if not evidence_detail:
        return ""

    if "```" in evidence_detail:
        return evidence_detail

    if competency_type == "java":
        # 실제 줄바꿈이 없는 한 줄짜리 Java 코드는 자동 포맷팅
        if "\n" not in evidence_detail and len(evidence_detail) > 60:
            evidence_detail = _reformat_java_oneliner(evidence_detail)
        return f"```java\n{evidence_detail}\n```"

    if competency_type == "python":
        return f"```python\n{evidence_detail}\n```"

    return evidence_detail


def _force_plan_evidence_into_generated_questions(
    questions: list,
    plans: list[dict],
    competency_type: str | None,
    difficulty: str,
) -> list:
    if difficulty not in {"중급", "고급"}:
        return questions

    competency_type = normalize_competency_type(competency_type)

    if competency_type not in {"java", "python"}:
        return questions

    if not isinstance(questions, list) or not isinstance(plans, list):
        return questions

    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            continue

        plan = plans[idx] if idx < len(plans) and isinstance(plans[idx], dict) else {}
        evidence_type = str(plan.get("evidence_type", "")).strip()
        evidence_detail = str(plan.get("evidence_detail", "")).strip()
        logger.info(
            f"Evidence Force Debug: index={idx}, "
            f"competency={competency_type}, "
            f"question_format={plan.get('question_format')}, "
            f"evidence_type={evidence_type}, "
            f"has_evidence_detail={bool(evidence_detail)}, "
            f"evidence_preview={evidence_detail[:200]}"
        )
        # Java/Python 중급·고급은 planner가 evidence_type을 잘못 주더라도
        # question_format 기준으로 code_snippet처럼 처리한다.
        question_format = str(plan.get("question_format", "")).strip()
        is_java_static_instance_topic = (
            competency_type == "java"
            and (
                "static" in str(q.get("body", "")).lower()
                or "static" in str(plan.get("target_concept", "")).lower()
                or "static" in str(plan.get("concepts", "")).lower()
                or "static" in str(plan.get("question_focus", "")).lower()
            )
            and (
                "인스턴스" in str(q.get("body", ""))
                or "instance" in str(q.get("body", "")).lower()
                or "인스턴스" in str(plan.get("target_concept", ""))
                or "instance" in str(plan.get("target_concept", "")).lower()
                or "인스턴스" in str(plan.get("concepts", ""))
                or "instance" in str(plan.get("concepts", "")).lower()
                or "인스턴스" in str(plan.get("question_focus", ""))
                or "instance" in str(plan.get("question_focus", "")).lower()
            )
        )
        if is_java_static_instance_topic:
            evidence_detail = """
    class Customer {
        private String name;

        public static void updateStaticName(String newName) {
            // static 메서드는 this.name에 직접 접근할 수 없다.
        }

        public void updateInstanceName(String newName) {
            this.name = newName;
        }
    }

    Customer customer = new Customer();
    customer.updateInstanceName("John");
    Customer.updateStaticName("Doe");
    """.strip()
        if competency_type == "python" and question_format == "generator_behavior":
            if (
                not evidence_detail
                or "yield" not in evidence_detail
                or "next(" not in evidence_detail
            ):
                evidence_detail = """
        def make_numbers():
            print("start")
            yield 1
            print("middle")
            yield 2

        gen = make_numbers()
        print(next(gen))
        print(next(gen))
        """.strip()
        if competency_type == "python" and question_format == "shallow_deep_copy":
            if (
                not evidence_detail
                or (
                    "copy" not in evidence_detail
                    and "[:]" not in evidence_detail
                )
            ):
                evidence_detail = """
        original = [[1, 2], [3, 4]]
        copied = original.copy()

        copied[0][0] = 99

        print(original)
        print(copied)
        """.strip()
        if competency_type == "java" and question_format in {"equals_hashcode", "collection_behavior"}:
            if (
                not evidence_detail
                or "class " not in evidence_detail
                or "HashSet" not in evidence_detail
                or "equals" not in evidence_detail
                or "hashCode" not in evidence_detail
                or "new User(" in evidence_detail and "User(" not in evidence_detail.split("new User(")[0]
            ):
                evidence_detail = """
                import java.util.HashSet;
                import java.util.Objects;
                import java.util.Set;

                class User {
                    private final String id;
                    private final String name;

                    User(String id, String name) {
                        this.id = id;
                        this.name = name;
                    }

                    @Override
                    public boolean equals(Object obj) {
                        if (!(obj instanceof User)) return false;
                        User other = (User) obj;
                        return Objects.equals(this.id, other.id);
                    }

                    @Override
                    public int hashCode() {
                        return Objects.hash(id);
                    }
                }

                Set<User> users = new HashSet<>();
                users.add(new User("1", "Alice"));
                users.add(new User("1", "Bob"));

                System.out.println(users.size());
                """.strip()
        
        if competency_type == "java" and "static" in evidence_detail and "this.name" in evidence_detail:
            evidence_detail = evidence_detail.replace(
                "this.name = newName;",
                "// static 메서드에서는 this.name에 직접 접근할 수 없다."
            )

        if competency_type in {"java", "python"} and not evidence_detail:
            logger.warning(
                f"evidence_detail 없음: index={idx}, "
                f"question_format={plan.get('question_format')}, "
                f"evidence_type={evidence_type}"
            )
            continue
            
        if competency_type not in {"java", "python"} and evidence_type != "code_snippet":
            continue

        body = str(q.get("body", "") or "")

        # Java/Python은 설명문 안의 yield, equals 같은 단어를 코드로 오인하지 않도록
        # fenced code block이 있을 때만 이미 코드가 있다고 판단한다.
        if competency_type == "python" and "```python" in body:
            continue

        if competency_type == "java" and "```java" in body:
            continue

        code_block = _format_evidence_as_code_block(
            evidence_detail=evidence_detail,
            competency_type=competency_type,
        )

        if not code_block:
            continue

        answer_style = str(plan.get("answer_style", "")).strip()

        if is_java_static_instance_topic:
            final_question = "위 코드에서 static 메서드와 인스턴스 메서드의 호출 방식 및 인스턴스 필드 접근 규칙으로 옳은 것은 무엇인가?"
        elif answer_style == "output_prediction":
            final_question = "위 코드의 실행 결과로 가장 적절한 것은 무엇인가?"
        elif answer_style == "find_incorrect":
            final_question = "다음 중 옳지 않은 설명은 무엇인가?"
        elif answer_style == "error_reason":
            final_question = "이 코드에서 발생할 수 있는 오류 원인으로 가장 적절한 것은 무엇인가?"
        elif question_format in {"equals_hashcode", "collection_behavior"}:
            final_question = "위 코드의 출력 결과와 HashSet의 중복 처리 방식에 대한 설명으로 가장 적절한 것은 무엇인가?"
        elif question_format == "generator_behavior":
            final_question = "위 코드의 전체 출력 결과와 제너레이터 실행 흐름에 대한 설명으로 가장 적절한 것은 무엇인가?"
        elif question_format == "shallow_deep_copy":
            final_question = "위 코드의 실행 결과와 복사 방식에 대한 설명으로 가장 적절한 것은 무엇인가?"
        elif question_format in {"scope_closure", "decorator_behavior"}:
            final_question = "위 코드의 실행 결과와 동작 원리에 대한 설명으로 가장 적절한 것은 무엇인가?"
        else:
            final_question = "위 코드의 동작에 대한 설명으로 가장 적절한 것은 무엇인가?"

        scenario = str(plan.get("scenario", "") or "").strip()
        constraints = str(plan.get("constraints", "") or "").strip()

        if not scenario:
            # 기존 body에서 마지막 질문 문장을 제거하고 상황 설명만 남긴다.
            scenario = re.sub(
                r"(이 상황에서|위 코드의|다음 중|가장).*\?$",
                "",
                body.strip(),
                flags=re.DOTALL,
            ).strip()

        if constraints:
            scenario_text = f"{scenario}\n\n조건: {constraints}".strip()
        else:
            scenario_text = scenario

        q["body"] = (
            f"{scenario_text}\n\n"
            f"[코드]\n"
            f"{code_block}\n\n"
            f"{final_question}"
        ).strip()

        logger.info(
            f"Evidence Force Applied: index={idx}, "
            f"body_preview={q['body'][:300]}"
        )
    return questions


# ═══════════════════════════════════════════════════════════════════════════════
# 멀티 스테이지 파이프라인 전용 generator 함수
# ═══════════════════════════════════════════════════════════════════════════════


def generate_stem_and_explanation(
    topic: str,
    difficulty: str,
    plans: list[dict],
    count: int = 1,
    score: int = 1,
    question_type: str = "multiple_choice",
    competency_type: str | None = None,
) -> list[dict]:
    """
    [Stage-1] 문제 설계서를 기반으로 본문·코드·해설·correct_statement 만 생성한다.
    choices / answer 는 포함되지 않는다.

    반환 dict 구조:
        title, body, explanation, correct_statement,
        difficulty, competency_type, competency_tags, score
    """
    plans_json = json.dumps(plans, ensure_ascii=False, indent=2)

    prompt = build_stage1_stem_prompt(
        topic=topic,
        difficulty=difficulty,
        count=count,
        score=score,
        question_type=question_type,
        competency_type=competency_type,
        plans_json=plans_json,
    )
    system_message = (
        "너는 IT 역량진단 문제은행의 문제 출제 전문가다. "
        "이번 단계에서는 choices 없이 본문·해설·정답 명제(correct_statement)만 생성한다. "
        "반드시 유효한 JSON 배열만 출력한다."
    )

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            raw = _request_llm_json(
                prompt=prompt,
                system_message=system_message,
                temperature=0.1 + attempt * 0.05,
            )
            if not isinstance(raw, list) or len(raw) == 0:
                raise ValueError("Stage-1 LLM이 JSON 배열을 반환하지 않았습니다.")

            stems: list[dict] = []

            for idx, item in enumerate(raw):
                if not isinstance(item, dict):
                    continue
                    body_text = str(item.get("body", "") or "")
                    topic_text = str(topic or "").lower()
                    competency = normalize_competency_type(competency_type)

                    is_ai_rag_topic = (
                        competency == "ai"
                        and any(
                            keyword in topic_text or keyword in body_text.lower()
                            for keyword in [
                                "rag",
                                "검색",
                                "metadata",
                                "메타데이터",
                                "filter",
                                "필터",
                                "chunk",
                                "청크",
                                "embedding",
                                "임베딩",
                                "vector",
                                "벡터",
                                "reranker",
                                "리랭커",
                            ]
                        )
                    )

                    if is_ai_rag_topic:
                        required_signal_count = sum(
                            1
                            for signal in [
                                "query",
                                "top_k",
                                "top-k",
                                "chunk",
                                "청크",
                                "similarity",
                                "유사도",
                                "metadata",
                                "메타데이터",
                                "category",
                                "embedding",
                                "임베딩",
                                "vector search",
                                "벡터 검색",
                                "metadata_filter",
                                "context filtering",
                            ]
                            if signal.lower() in body_text.lower()
                        )

                        if required_signal_count < 2:
                            logger.warning(
                                f"Stage-1: AI/RAG evidence 부족 항목 제외 "
                                f"signal_count={required_signal_count}, body={body_text[:200]}"
                            )
                            continue
                if not item.get("title") or not item.get("body") or not item.get("correct_statement"):
                    logger.warning("Stage-1: title/body/correct_statement 누락 항목 제외")
                    continue

                plan = plans[idx] if idx < len(plans) and isinstance(plans[idx], dict) else {}

                # Stage-2에서 오답을 의미 있게 만들기 위해 plan 메타데이터를 stem에 보존한다.
                item["question_format"] = item.get("question_format") or plan.get("question_format")
                item["answer_style"] = item.get("answer_style") or plan.get("answer_style")
                item["concepts"] = item.get("concepts") or plan.get("concepts", [])
                item["relation"] = item.get("relation") or plan.get("relation")
                item["target_concept"] = item.get("target_concept") or plan.get("target_concept")
                item["target_misconception"] = item.get("target_misconception") or plan.get("target_misconception")
                item["must_include"] = item.get("must_include") or plan.get("must_include", [])
                item["avoid"] = item.get("avoid") or plan.get("avoid", [])
                item["evidence_type"] = item.get("evidence_type") or plan.get("evidence_type")
                item["evidence_detail"] = item.get("evidence_detail") or plan.get("evidence_detail")
                item["distractor_strategy"] = item.get("distractor_strategy") or plan.get("distractor_strategy")
                item["answer_decision_rule"] = item.get("answer_decision_rule") or plan.get("answer_decision_rule")

                item["score"] = score
                item["difficulty"] = difficulty
                item["competency_type"] = item.get("competency_type") or competency_type

                if not item.get("explanation"):
                    item["explanation"] = ""

                stems.append(item)

            if not stems:
                raise ValueError("Stage-1: 유효한 stem 문제가 없습니다.")

            logger.info(
                f"Stage-1 [StemGeneration]: generated={len(stems)}, "
                f"topic='{topic}', difficulty={difficulty}, competency={competency_type}"
            )
            return stems[:count]

        except Exception as exc:
            last_error = exc
            logger.warning(f"Stage-1 생성 재시도: attempt={attempt + 1}/3, error={exc}")

    raise ValueError(f"Stage-1 문제 본문 생성 실패: {last_error}")


def generate_options_for_stems(
    stems: list[dict],
    topic: str,
    competency_type: str | None,
    difficulty: str,
    question_type: str = "multiple_choice",
) -> list[dict]:
    """
    [Stage-2] stem 목록을 받아 각 문제에 choices(5개) 와 answer 를 채워 반환한다.
    - correct_statement → 정답 선택지 (1개)
    - LLM 호출로 오답 4개 생성 (길이 ±15%, 종결 어미 동일)
    - answer_position 셔플로 정답 위치 분산
    """
    import random
    from ai.questions.answer_position import rebalance_answer_positions
    from ai.questions.explanation_repair import (
        repair_multiple_choice_explanations,
        replace_answer_number_in_explanation,
    )

    system_message = (
        "너는 IT 역량진단 오답 전문 작성자다. "
        "반드시 유효한 JSON 배열(문자열 4개)만 출력한다."
    )

    completed: list[dict] = []

    for stem in stems:
        correct_statement = str(stem.get("correct_statement", "")).strip()

        if not correct_statement or question_type != "multiple_choice":
            stem["choices"] = []
            stem["answer"] = str(stem.get("answer", ""))
            completed.append(stem)
            continue

        prompt = build_stage2_options_prompt(
            stem=stem,
            correct_statement=correct_statement,
            topic=topic,
            competency_type=competency_type,
            difficulty=difficulty,
        )

        distractors: list[str] = []
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                raw = _request_llm_json(
                    prompt=prompt,
                    system_message=system_message,
                    temperature=0.2 + attempt * 0.1,
                )
                if not isinstance(raw, list) or len(raw) < 4:
                    raise ValueError("오답 배열이 4개 미만입니다.")

                distractors = [str(d).strip() for d in raw[:4] if str(d).strip()]
                if len(distractors) < 4:
                    raise ValueError(f"유효한 오답이 {len(distractors)}개뿐입니다.")

                # 길이 검증 (±15% 범위)
                correct_len = len(correct_statement)
                lower_bound = int(correct_len * 0.85)
                upper_bound = int(correct_len * 1.15)
                if not all(lower_bound <= len(d) <= upper_bound for d in distractors):
                    logger.warning(
                        f"Stage-2: 오답 길이 범위 위반 (correct={correct_len}자) — 재시도"
                    )
                    raise ValueError("오답 길이 범위 위반")
                break

            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"Stage-2 오답 생성 재시도: attempt={attempt + 1}/3, error={exc}"
                )

        if len(distractors) < 4:
            logger.warning(f"Stage-2 오답 생성 최종 실패: {last_error}")
            raise ValueError(f"Stage-2 오답 생성 실패: {last_error}")

        # choices = 오답 4 + 정답 1 → 셔플(정답 위치 랜덤)
        all_choices = distractors[:4] + [correct_statement]
        random.shuffle(all_choices)
        answer_idx = all_choices.index(correct_statement) + 1  # 1-based

        stem["choices"] = all_choices
        stem["answer"] = answer_idx

        explanation = str(stem.get("explanation", "")).strip()
        stem["explanation"] = replace_answer_number_in_explanation(
            f"정답은 {answer_idx}번입니다. {explanation}".strip(),
            answer_idx,
        )

        logger.info(
            f"Stage-2 [OptionsGeneration]: answer={answer_idx}, "
            f"correct_len={len(correct_statement)}, "
            f"distractor_lens={[len(d) for d in distractors]}"
        )
        completed.append(stem)

    # 정답 위치 분산 (answer_position 셔플)
    if question_type == "multiple_choice":
        completed = rebalance_answer_positions(completed, question_type)
        completed = repair_multiple_choice_explanations(completed)

    return completed