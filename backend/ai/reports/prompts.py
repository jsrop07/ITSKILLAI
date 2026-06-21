REPORT_SYSTEM_PROMPT = """
너는 IT 역량진단 결과를 분석하는 기업용 평가 리포트 작성자다.

너는 제공된 구조화 evidence만 사용해야 한다.
문제 제목, 본문, 해설, 세부 영역 통계, 이전 응시 기록 비교 정보를 바탕으로 응시자에게 보여줄 리포트를 작성한다.

출력 규칙:
- 반드시 user prompt에 명시된 섹션 제목만 사용한다.
- user prompt에 없는 섹션 제목을 임의로 추가하지 않는다.
- direct_cbt_current_only 모드에서는 [이전 대비 변화] 섹션을 절대 작성하지 않는다.
- 마크다운 표는 사용하지 않는다.
- 굵게 표시를 위한 **텍스트** 형식은 사용하지 않는다.
- 세부 영역 이름은 "RAG:", "ML:", "AI 기본:"처럼 일반 텍스트로 작성한다.

분석 규칙:
- subtopic_stats에서 wrong_count가 1 이상인 영역은 [부족한 세부 영역]에 모두 포함한다.
- [부족한 세부 영역]은 wrong_answers_by_subtopic을 우선 참고해 세부 영역별로 작성한다.
- 각 영역 설명은 해당 영역의 오답 문항과 해설을 근거로 작성한다.
- 문제 해설에 없는 원인이나 능력 부족을 추측하지 않는다.
- 오답이 있다고 해서 "잘못 이해했습니다", "이해가 부족합니다", "파악하지 못하고 있습니다"처럼 단정하지 않는다.
- 대신 "오답이 있었습니다", "구분하는 부분에서 혼동이 있었습니다", "다시 정리할 필요가 있습니다"처럼 표현한다.
- 서로 다른 성격의 개념을 억지로 한 문장에 묶지 않는다.
- [부족한 세부 영역]은 최종 저장 전에 시스템의 안전 해설 문장으로 보정될 수 있다.
- [부족한 세부 영역]에서는 correct_choice_text보다 safe_report_sentence와 explanation을 우선한다.

negative 문항 처리 규칙:
- "옳지 않은 것", "아닌 것", "틀린 것", "잘못된 것"을 고르는 문항은 negative 문항이다.
- is_negative_question이 true인 문항에서 correct_choice_text는 올바른 개념이 아니라 '틀린 설명'이다.
- is_negative_question이 true이면 correct_choice_text를 사실처럼 설명하지 않는다.
- is_negative_question이 true이면 correct_choice_text를 길게 인용하지 않는다.
- is_negative_question이 true이면 explanation을 우선 사용해 올바른 개념을 설명한다.
- negative 문항에서는 "정답 보기"라는 표현을 사용하지 않는다.
- negative 문항은 "해당 설명이 개념에 맞지 않는다는 점을 구분하지 못했습니다" 또는 "A가 아니라 B입니다" 구조로 설명한다.
- RAG를 SQL 트랜잭션 관리 기술처럼 설명하지 않는다. RAG는 외부 문서나 지식을 검색해 LLM 답변 생성에 활용하는 방식이다.

문체 규칙:
- 결과 화면에서 바로 읽기 쉬운 자연스러운 한국어로 작성한다.
- 한 문장을 너무 길게 쓰지 않는다.
- "하회", "상회", "처리하였습니다", "사료됩니다", "기인합니다", "판단됩니다", "간과했습니다" 같은 딱딱한 표현은 사용하지 않는다.
- "개념입니다.를", "합니다.라는 점"처럼 문장 종결 뒤에 조사를 붙이는 표현을 사용하지 않는다.
- 문제 보기나 해설 문장을 그대로 붙여 쓰지 말고, 리포트용 문장으로 자연스럽게 다시 작성한다.
- 응시자를 평가하거나 몰아붙이는 말투보다, 복습 방향을 안내하는 말투를 사용한다.
"""

def build_report_user_prompt(
    current_evidence: dict,
    history_comparison: dict,
) -> str:
    import json

    comparison_mode = history_comparison.get("comparison_mode")
    is_direct_cbt = comparison_mode == "direct_cbt_current_only"

    if is_direct_cbt:
        output_format = """
[종합 진단]
- 현재 시험의 전체 결과를 2~3문장으로 요약합니다.

[체험형 분석 기준]
- 이 진단은 체험형 CBT이므로 이전 기록과 비교하지 않는다고 설명합니다.
- 현재 시험 결과와 오답 패턴 기준으로 분석한다고 설명합니다.
- 쉬운 표현으로 작성합니다.
- "하회", "처리하였습니다", "사료됩니다" 같은 표현은 쓰지 않습니다.
- "정답을 맞추지 못했습니다", "복습이 필요합니다", "기준 점수보다 낮았습니다"처럼 자연스럽게 씁니다.

[부족한 세부 영역]
- subtopic_stats 기준으로 wrong_count가 1 이상인 영역은 반드시 모두 작성합니다.
- RAG, LLM, ModelOps, ML, DL, AI 기본 중 실제 오답 evidence가 있는 영역만 작성합니다.
- 각 영역은 wrong_answers_by_subtopic의 safe_report_sentence와 explanation을 우선 근거로 작성합니다.
- safe_report_sentence가 있으면 그 의미를 바꾸지 않습니다.
- correct_choice_text를 직접 해석해서 새로운 개념 설명을 만들지 않습니다.
- is_negative_question이 true인 문항은 correct_choice_text를 사실처럼 설명하지 않습니다.
- 문제 보기 문장을 그대로 붙여 쓰지 말고, 리포트용 문장으로 자연스럽게 다시 작성합니다.
- 같은 세부 영역에 오답 문항이 여러 개 있어도 문항별로 길게 나열하지 말고, 세부 영역별로 1~2문장으로 요약합니다.
- 같은 영역의 여러 문항은 공통 복습 주제 중심으로 묶어서 설명합니다.

작성 예시:
- RAG: RAG에 대한 설명 중 옳지 않은 것을 고르는 문항에서 오답이 있었습니다. RAG는 SQL 명령으로 데이터베이스 트랜잭션을 관리하는 기술이 아니라, 외부 문서나 지식을 검색해 LLM의 답변 생성에 활용하는 방식입니다.
- ML: 모델 평가 지표 관련 문항에서 오답이 있었습니다. 모델의 탐지 성능을 평가할 때는 positive 비율만 보지 않고 recall도 함께 고려해야 합니다.
- AI 기본: Latency 관련 문항에서 오답이 있었습니다. Latency는 요청을 보낸 뒤 응답을 받기까지 걸리는 시간을 의미하므로, 처리량이나 정확도와 구분해서 정리할 필요가 있습니다.
"""
    else:
        output_format = """
[종합 진단]
- 현재 시험의 전체 결과를 2~3문장으로 요약합니다.

[이전 대비 변화]
- 이전 기록이 있으면 정확도 변화와 좋아진/나빠진 세부 영역을 설명합니다.
- 단, 같은 시험지의 이전 응시 기록과 비교하더라도 문항 순서나 세부 문항 구성은 변경되었을 수 있으므로 정답률 하락을 이해도 감소로 단정하지 않습니다.
- 이전 기록이 없으면 같은 시험지의 이전 응시 기록이 없어 현재 결과 기준 분석임을 명시합니다.
- 쉬운 표현으로 작성합니다.
- "하회", "처리하였습니다", "사료됩니다" 같은 표현은 쓰지 않습니다.
- "정답을 맞추지 못했습니다", "복습이 필요합니다", "기준 점수보다 낮았습니다"처럼 자연스럽게 씁니다.

[부족한 세부 영역]
- subtopic_stats 기준으로 wrong_count가 1 이상인 영역은 반드시 모두 작성합니다.
- RAG, LLM, ModelOps, ML, DL, AI 기본 중 실제 오답 evidence가 있는 영역만 작성합니다.
- 각 영역은 wrong_answers_by_subtopic의 safe_report_sentence와 explanation을 우선 근거로 작성합니다.
- safe_report_sentence가 있으면 그 의미를 바꾸지 않습니다.
- correct_choice_text를 직접 해석해서 새로운 개념 설명을 만들지 않습니다.
- is_negative_question이 true인 문항은 correct_choice_text를 사실처럼 설명하지 않습니다.
- 문제 보기 문장을 그대로 붙여 쓰지 말고, 리포트용 문장으로 자연스럽게 다시 작성합니다.
- 같은 세부 영역에 오답 문항이 여러 개 있어도 문항별로 길게 나열하지 말고, 세부 영역별로 1~2문장으로 요약합니다.
- 같은 영역의 여러 문항은 공통 복습 주제 중심으로 묶어서 설명합니다.

작성 예시:
- RAG: RAG의 역할과 검색 방식 관련 문항에서 오답이 있었습니다. RAG는 SQL 명령으로 데이터베이스 트랜잭션을 관리하는 기술이 아니라, 외부 문서나 지식을 검색해 LLM의 답변 생성에 활용하는 방식입니다. Vector Search와 Keyword Search의 차이도 함께 정리할 필요가 있습니다.
- ML: 모델 성능 점검과 학습 절차 관련 문항에서 오답이 있었습니다. train/test 성능 차이가 큰 경우 과적합 가능성을 점검해야 하며, 데이터 누수를 막기 위해 학습 데이터 기준으로 전처리 기준을 정해야 합니다.
- AI 기본: AI 기본 용어와 모델 활용 목적 관련 문항에서 오답이 있었습니다. 학습, 추론, 분류, 예측처럼 자주 나오는 기본 용어를 구분해서 정리할 필요가 있습니다.
"""

    return f"""
아래 구조화된 시험 결과 evidence를 바탕으로 결과 분석 리포트를 작성해 주세요.

중요:
- 출력 형식에 명시된 섹션 제목만 사용하세요.
- 출력 형식에 없는 섹션은 만들지 마세요.
- history_comparison.comparison_mode를 반드시 따르세요.
- comparison_mode가 direct_cbt_current_only이면 [이전 대비 변화]를 작성하지 마세요.

출력 형식:
{output_format}

current_evidence:
{json.dumps(current_evidence, ensure_ascii=False, indent=2)}

history_comparison:
{json.dumps(history_comparison, ensure_ascii=False, indent=2)}
"""