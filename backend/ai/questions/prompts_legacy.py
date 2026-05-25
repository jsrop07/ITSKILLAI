from ai.core.config import normalize_competency_type
def difficulty_rule(difficulty: str) -> str:
    if difficulty == "초급":
        return """
        [초급 난이도 출제 기준]
        - 개념 정의, 기본 용어, 기본 구분, 단순 동작 원리를 평가한다.
        - 문제 본문은 짧고 명확하게 작성한다.
        - 복잡한 실무 상황, 장애 분석, 우선순위 판단, 리스크 분석 문제는 출제하지 않는다.
        - 정답은 학습자가 기본 개념을 알고 있으면 명확히 고를 수 있어야 한다.
        - 단, 너무 뻔한 상식 문제나 말장난 문제는 금지한다.
        """
    if difficulty == "중급":
        return """
        [중급 난이도 출제 기준]
        - 단순 정의 암기 문제를 금지한다.
        - "무엇인가?", "어떤 요소인가?", "올바른 설명은?"처럼 개념만 묻는 문제를 반복하지 않는다.
        - 반드시 짧은 실무 상황을 제시한다.
        - 세부 주제의 개념을 실제 상황에 적용하거나 비교, 분류, 원인 판단, 검토 기준 선택을 요구한다.
        - 보기들은 모두 선택된 역량 유형과 같은 업무 맥락 안에서 그럴듯하게 작성한다.
        - 정답은 하나만 명확해야 하지만, 오답도 실무자가 헷갈릴 수 있는 수준으로 작성한다.
        - 초급 수준의 용어 정의 문제는 생성하지 않는다.
        """
    return """
        [고급 난이도 출제 기준]
        - 단순 정의형, 용어 암기형, 항목 나열형 문제를 금지한다.
        - "무엇인가?", "어떤 요소가 포함되어야 하는가?", "올바른 설명은?" 형태의 문제를 금지한다.
        - 반드시 실무 상황을 포함한다.
        - 문제 본문은 최소 3문장 이상으로 작성한다.
        - 문제 본문에는 반드시 다음 중 3개 이상을 포함한다:
        1) 현재 시스템/업무 상황
        2) 발생한 문제 또는 증상
        3) 제약 조건
        4) 잘못된 판단으로 인한 리스크
        5) 선택해야 할 대응 방향
        - 세부 주제와 관련된 원인, 영향, 리스크, 우선순위, 대응 방안, 트레이드오프를 판단하게 한다.
        - 보기들은 모두 그럴듯해야 하며, 정답은 문제 상황에서 가장 우선적으로 선택해야 하는 판단 또는 대응이어야 한다.
        - 오답은 완전히 엉뚱한 내용이 아니라, 관련은 있지만 우선순위가 낮거나 문제 상황의 핵심 원인을 해결하지 못하는 선택지로 작성한다.
        - 정답은 선택된 역량 유형과 세부 주제에 직접 연결되어야 한다.
        - 해설에는 정답이 가장 적절한 이유와 주요 오답이 왜 우선순위가 낮거나 문제 상황과 직접 맞지 않는지 포함한다.
        [고급 문제 금지 패턴]
        - "가장 중요한 요소는 무엇인가요?"
        - "가장 적절한 자료구조는 무엇인가요?"
        - "어념 조치를 취해야 하나요?"
        - "무엇을 고려해야 하나요?"
        - "어떤 컬럼에 인덱스를 추가해야 하나요?"
        위와 같은 질문은 구체적인 조건, 제약, 증상 없이 단독으로 사용하지 않는다.
        [고급 선택지 작성 규칙]
        - 선택지는 단어 하나 또는 짧은 명사구로 작성하지 않는다.
        - 선택지는 모두 구체적인 판단 또는 대응 문장으로 작성한다.
        - 예: "인덱스를 추가한다"처럼 짧게 쓰지 말고, "WHERE 동등 조건과 ORDER BY 조건을 함께 만족하도록 복합 인덱스를 설계한다"처럼 작성한다.
        - 예: "해시 테이블"처럼 단어만 쓰지 말고, "중복 여부 조회가 반복되므로 평균 O(1) 조회가 가능한 해시 기반 구조를 사용한다"처럼 작성한다.
        """

def competency_rule(competency_type: str | None, topic: str) -> str:
    competency_type = normalize_competency_type(competency_type)

    rules = {
        "software_engineering": """
        [소프트웨어공학 역량 출제 규칙]
        - 요구사항 분석, 설계, 테스트, 품질 속성, 형상관리, 변경관리, 유지보수, 검증/검토를 중심으로 출제한다.
        - 중급/고급 문제 body에는 요구사항 목록, 변경 요청, 테스트 실패 상황, 이해관계자 충돌, 품질 속성 누락 중 하나를 포함한다.
        - 중급 이상은 단순 용어 정의가 아니라 요구사항 누락, 변경 영향, 검증 가능성, 품질 속성 판단을 묻는다.
        - 고급은 요구사항 충돌, 추적성 부족, 검증 실패, 품질 리스크, 변경 요청 증가 가능성을 분석하게 한다.
        """,
        "java": """
        [Java 역량 출제 규칙]
        - 클래스/객체, 상속/다형성, 인터페이스, 예외 처리, 컬렉션, 제네릭, JVM 기초를 중심으로 출제한다.
        - 중급/고급 문제 body에는 반드시 Java 코드 조각, 클래스/인터페이스 구조, 예외 처리 코드, 컬렉션 사용 예시 중 하나를 포함한다.
        - 중급 문제는 코드 실행 결과, 컴파일 오류, 오버라이딩/오버로딩 차이, 컬렉션 선택 기준을 묻는다.
        - 고급 문제는 유지보수성, 확장성, 타입 안정성, 예외 처리 범위, 동시성 또는 성능 영향을 판단하게 한다.
        - 코드 없이 일반적인 설계 판단만 묻는 비문학형 문제를 만들지 않는다.
        """,
        "python": """
        [Python 역량 출제 규칙]
        - 리스트, 딕셔너리, 튜플, 셋, 함수, 클래스, 예외 처리, 반복문, 컴프리헨션을 중심으로 출제한다.
        - 중급/고급 문제 body에는 반드시 Python 코드 조각 또는 리스트/딕셔너리 데이터 예시를 포함한다.
        - 중급 문제는 실행 결과 예측, KeyError/TypeError 같은 오류 원인, 누락된 조건 보완, 적절한 자료형 선택을 묻는다.
        - 고급 문제는 예외 상황, 성능, 메모리 사용, 가독성, 유지보수성, 리팩토링 방향을 판단하게 한다.
        - 코드 없이 "입력 데이터를 분석한다", "가장 적절한 판단은 무엇인가?"처럼 긴 상황 설명만 있는 문제를 만들지 않는다.
        [Python 얕은 복사/참조 할당 출제 규칙]
        - topic이 "얕은 복사", "shallow copy", "리스트 복사"와 관련되면 copied = original 형태만 제시하지 않는다.
        - copied = original은 얕은 복사가 아니라 참조 할당으로 설명한다.
        - 얕은 복사 문제를 만들 때는 반드시 list.copy(), slicing [:], copy.copy() 중 하나를 코드에 포함한다.
        - 중급 이상에서는 가능하면 중첩 리스트를 사용해 내부 리스트 공유 여부를 묻는다.
        - 예: original = [[1, 2], [3, 4]]; copied = original.copy(); copied[0][0] = 99; print(original)
        - 정답은 실행 결과뿐 아니라 왜 내부 객체가 공유되는지 판단 가능해야 한다.
        """,

        "sql": """
        [SQL 역량 출제 규칙]
        - SELECT, WHERE, JOIN, GROUP BY, ORDER BY, 서브쿼리, 집계 함수, 인덱스, 실행 계획, 트랜잭션, 정규화를 중심으로 출제한다.
        - 중급/고급 문제 body에는 반드시 SQL 쿼리, 테이블 구조, 샘플 데이터, 실행 계획 설명 중 하나를 포함한다.
        - 중급 문제는 쿼리 결과 해석, JOIN 조건 오류, WHERE 조건 위치, GROUP BY/집계 결과, 서브쿼리 적용을 묻는다.
        - 고급 문제는 데이터 규모, 실행 빈도, 인덱스 선택도, 실행 계획, 락 대기, 쓰기 부하, 정규화/반정규화 판단을 포함한다.
        - 쿼리나 테이블 조건 없이 "가장 적절한 판단"만 묻는 문제를 만들지 않는다.
        """,
        "data_structure_algorithm": """
        [자료구조/알고리즘 역량 출제 규칙]
        - 배열, 리스트, 스택, 큐, 해시, 트리, 그래프, 정렬, 탐색, 재귀, BFS/DFS, 시간복잡도, 공간복잡도를 중심으로 출제한다.
        - 중급/고급 문제 body에는 반드시 입력 크기, 연산 빈도, 입력/출력 예시, 의사코드, 시간복잡도 조건 중 하나를 포함한다.
        - 중급 문제는 자료구조 선택, 연산별 시간복잡도, BFS/DFS 방문 순서, 정렬/탐색 과정 추론을 묻는다.
        - 고급 문제는 최악/평균 시간복잡도, 공간복잡도, 입력 제약에 따른 알고리즘 선택의 트레이드오프를 판단하게 한다.
        - 자료구조 이름만 고르는 문제나 일반론적 상황 판단 문제를 만들지 않는다.
        """,

        "ai": """
        [AI 역량 출제 규칙]
        - 데이터 전처리, 학습/검증 데이터 분리, 과적합, 평가 지표, LLM, RAG, 임베딩, 벡터 검색, 검색 품질을 중심으로 출제한다.
        - 중급/고급 문제 body에는 반드시 데이터 상태, 평가 지표, 검색 결과 예시, RAG 파이프라인 조건, 모델 성능 로그 중 하나를 포함한다.
        - RAG/검색 품질 문제는 SQL 인덱스나 DB 실행 계획 문제가 아니라 chunk 품질, embedding, vector search, keyword search, metadata filter, reranking, context filtering, top_k, hallucination 방지를 중심으로 만든다.
        - 중급 문제는 검색 결과가 부정확한 원인, chunk 품질, query 보강, metadata filter 적용 여부를 판단하게 한다.
        - 고급 문제는 hybrid search, reranker, context filtering, 평가 지표, latency/accuracy trade-off를 판단하게 한다.
        """,
    }
    base_rule = rules.get(competency_type, "")
    topic_rule = topic_specific_rule(competency_type, topic)
    return f"""{base_rule}
{topic_rule}"""

def topic_specific_rule(competency_type: str | None, topic: str) -> str:
    """
    특정 topic일 때만 적용하는 세부 출제 패턴.
    자주 쓰는 주제부터 점진적으로 추가한다.
    """
    topic_text = topic or ""
    if competency_type == "software_engineering" and "요구사항" in topic_text:
        return """
        [요구사항 관련 세부 출제 패턴]
        - 요구사항 목록의 완전성, 명확성, 일관성, 검증 가능성을 판단하게 한다.
        - 기능 요구사항과 비기능 요구사항의 구분 또는 누락 여부를 다룰 수 있다.
        - 요구사항 검토, 요구사항 명세서, 요구사항 검증 계획, 인수 테스트와 연결해 출제한다.
        - 중급/고급은 단순히 요구사항의 정의를 묻지 말고, 누락/변경/검증 실패 리스크를 판단하게 한다.
        """
    if competency_type == "sql" and any(keyword in topic_text for keyword in ["인덱스", "index", "Index"]):
        return """
        [인덱스 세부 출제 패턴]
        - 인덱스가 조회 성능에 미치는 영향과 쓰기 성능, 저장 공간, 유지 비용을 함께 판단하게 한다.
        - 중급은 WHERE, JOIN, ORDER BY, GROUP BY에 사용되는 컬럼을 보고 적절한 인덱스 후보를 고르게 한다.
        - 고급은 실행 계획, 선택도, 복합 인덱스의 선행 컬럼, 범위 조건, 정렬 조건, 커버링 인덱스, 쓰기 부하를 함께 고려하게 한다.
        """
    if competency_type == "sql" and any(keyword in topic_text for keyword in ["트랜잭션", "격리", "락", "동시성"]):
        return """
        [트랜잭션 세부 출제 패턴]
        - 원자성, 일관성, 격리성, 지속성을 실제 상황에 적용하게 한다.
        - 중급/고급은 동시성 문제, 락 경합, 격리 수준 선택, 롤백 필요 상황을 판단하게 한다.
        """

    if competency_type == "ai" and any(keyword in topic_text for keyword in ["RAG", "임베딩", "벡터", "검색"]):
        return """
        [RAG/임베딩 세부 출제 패턴]
        - 청킹, 임베딩, 벡터 검색, 검색 품질, 문서 근거, hallucination 방지를 중심으로 출제한다.
        - 중급은 검색 결과가 부정확한 원인, chunk 품질, query 보강, metadata filter 적용 여부를 상황 기반으로 판단하게 한다.
        - 고급은 vector search만으로 부족한 상황에서 keyword search, metadata filter, reranker, context filtering을 어떻게 조합할지 판단하게 한다.
        """
    return ""

def answer_distribution_rule(count: int, question_type: str) -> str:
    if question_type != "multiple_choice":
        return ""
    return f"""
    [이번 생성 정답 배치 규칙]
    - 객관식 문제의 answer는 1~5 중 하나여야 한다.
    - answer가 1번이나 2번에만 몰리지 않게 한다.
    - 여러 문제를 생성할 경우 정답 번호는 매번 랜덤하게 분산한다.
    - 단, 모든 문제의 answer가 같은 번호이면 안 된다.
    - answer가 [1, 1, 1], [2, 2, 2], [1, 2, 1], [2, 1, 2]처럼 낮은 번호에만 몰리면 안 된다.
    - 3번, 4번, 5번도 자연스럽게 정답 위치로 사용한다.
    - {count}개의 문제는 정답 위치 패턴이 항상 동일하면 안 된다.
    - 예시는 참고용일 뿐이며, 매번 같은 순서를 반복하지 않는다.
    """

def answer_explanation_consistency_rule() -> str:
    return """
    [answer/explanation 일치 규칙]
    - answer 값과 explanation 첫 문장의 "정답은 N번입니다."에서 N은 반드시 같아야 한다.
    - 객관식 explanation은 반드시 "정답은 N번입니다."로 시작한다.
    - N은 1~5 사이의 answer 값과 같아야 한다.
    - answer=2인데 explanation이 "정답은 1번입니다."로 시작하면 안 된다.
    - 실제 정답 선택지와 explanation에서 설명하는 정답 내용이 일치해야 한다.
    - 오답 설명은 선택지 번호가 아니라 선택지 내용 또는 개념 기준으로 작성한다.
    """
    
def question_type_rule(question_type: str) -> str:
    if question_type == "multiple_choice":
        return """
        [객관식 문제 생성 규칙]
        - choices는 반드시 문자열 5개 배열이어야 한다.
        - answer는 반드시 1~5 사이의 정답 번호로 작성한다.
        - answer는 0부터 시작하는 index가 아니다.
        - 첫 번째 보기가 정답이면 answer는 1이다.
        - 두 번째 보기가 정답이면 answer는 2이다.
        - 정답은 반드시 1개만 존재해야 한다.
        - JSON 예시의 answer 번호를 그대로 반복하지 말고 문제마다 정답 위치를 다르게 배치한다.
        - "모두 정답", "정답 없음", "위 내용 모두" 같은 선택지는 금지한다.
        - 오답은 그럴듯해야 하지만 정답으로 해석될 수 있으면 안 된다.
        - explanation에는 정답인 이유와 주요 오답이 틀린 이유를 포함한다.
        - 선택지 중 정답으로 볼 수 있는 문장이 2개 이상이면 해당 문제를 생성하지 않는다.
        - 정답 선택지와 오답 선택지는 같은 개념 영역에 있어도 판단 기준이 명확히 달라야 한다.
        - 해설에서 오답 선택지를 맞는 설명처럼 인정하지 않는다.
        - 오답 선택지가 일반론으로는 맞더라도, 문제 상황의 질문 기준에서는 가장 적절하지 않아야 한다.
        - 코드 실행 결과를 묻는 문제에서 print(), System.out.println()이 2개 이상이면 선택지는 전체 출력 순서를 포함해야 한다.
        - 예: 두 번 출력되는 코드는 "출력 결과는 0과 1이다.", "출력 결과는 1과 2이다."처럼 전체 출력값을 모두 포함한다.
        - 여러 출력이 있는 코드에서 마지막 출력값만 선택지로 작성하지 않는다.
        [객관식 JSON 형식]
        {
            "title": "문제 제목",
            "body": "문제 본문",
            "choices": ["보기1", "보기2", "보기3", "보기4", "보기5"],
            "answer": 3,
            "explanation": "정답은 3번입니다. ...",
            "difficulty": "초급",
            "competency_type": "python",
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
          "competency_type": "sql",
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
      "competency_type": "python",
      "competency_tags": ["Python", "Algorithm"],
      "score": 5
    }
    """
def explanation_rule(question_type: str) -> str:
    if question_type == "multiple_choice":
        return """
        [객관식 해설 작성 규칙]
        - 해설(explanation)은 반드시 '~입니다', '~합니다', '~수 있습니다' 등 존댓말(경어체)로만 작성한다. '~다', '~한다', '~않는다'와 같은 반말/평서형 종결 어미가 절대 섞이지 않도록 엄격하게 검수한다.
        - 정답 선택지가 왜 맞는지 설명한다.
        - 정답 선택지의 핵심 문구를 직접 언급해도 된다.
        - "다른 선택지는 관련이 없습니다"처럼 모든 오답을 한 문장으로 뭉뚱그려 설명하지 않는다.
        - 각 오답 선택지의 핵심 내용이 왜 문제 상황의 정답 기준과 맞지 않는지 구체적으로 설명한다.
        - 문서에 없는 새로운 기술명, 수치, 도구명, 절차를 추가하지 않는다.
        - 예: "명명 규칙 검토나 중복 여부 확인은 관련 활동일 수 있으나, 누락된 기능으로 인한 오류 방지의 핵심 검토 포인트와는 직접성이 낮다." (이런 반말형은 "직접성이 낮습니다."로 고쳐야 한다.)
        """
    if question_type == "essay":
        return """
        [서술형 해설 작성 규칙]
        - 해설(explanation)은 반드시 존댓말(경어체)로만 작성한다. 반말/평서형 어미가 섞이지 않도록 주의한다.
        - 서술형에는 정답 번호가 없으므로 explanation에 "정답 번호", "정답은 N번입니다", "N번이 정답" 같은 표현을 절대 쓰지 않는다.
        - explanation에는 채점 기준, 핵심 키워드, 문서 근거를 포함한다.
        - 모범답안에서 반드시 포함해야 할 개념을 설명한다.
        - 부족한 답안이 되는 경우도 간단히 설명한다.
        """
    return """
    [코드작성형 해설 작성 규칙]
    - 해설(explanation)은 반드시 존댓말(경어체)로만 작성한다. 반말/평서형 어미가 섞이지 않도록 주의한다.
    - 코드작성형에는 정답 번호가 없으므로 explanation에 "정답 번호", "정답은 N번입니다", "N번이 정답" 같은 표현을 절대 쓰지 않는다.
    - explanation에는 풀이 전략, 핵심 구현 포인트, 예외 처리 기준, 시간복잡도 또는 자료구조 선택 이유를 포함한다.
    - 채점 시 확인해야 할 기준을 설명한다.
    """

def choice_quality_rule() -> str:
    return """
    [선택지 품질 규칙]
    - 객관식 choices는 정확히 5개여야 한다.
    - 정답은 반드시 1개만 존재해야 한다.
    - 정답 선택지가 오답 선택지보다 눈에 띄게 길거나 자세하지 않도록, 모든 선택지의 길이를 최대한 비슷하게 맞춘다.
    - 가끔은 정답을 더 짧게 만들거나 오답을 더 길게 만들어 길이만으로 정답을 유추할 수 없도록 한다.
    - 오답은 완전히 엉뚱한 설명이 아니라 같은 개념 영역에서 헷갈릴 수 있는 설명으로 작성한다.
    - "항상", "무조건", "오직", "절대", "삭제한다", "무시한다", "생략한다", "자동으로 해결된다", "전혀", "유일한", "무관하게", "관계없이" 같은 쉽게 배제되는 표현을 남발하지 않는다.
    - 선택지에 "오해할 수 있다", "혼동할 수 있다", "착각할 수 있다", "잘못 이해할 수 있다" 같은 학습자 상태 표현을 쓰지 않는다.
    - choices는 시험 선택지체로 작성하고 존댓말을 사용하지 않는다.
    - explanation은 반드시 처음부터 끝까지 존댓말(~입니다, ~합니다, ~습니다)로 작성한다. 반말이나 평서형 종결 어미가 섞여 있으면 안 된다.
    """

def answer_leak_prevention_rule() -> str:
    return """
    [정답 누출 방지 규칙]
    - body에 정답 선택지와 거의 같은 문장을 직접 쓰지 않는다.
    - body에서 해결책이나 정답 판단을 직접 말하지 않는다.
    - body는 상황, 증상, 코드/쿼리/조건, 기대 결과만 제시한다.
    - 정답 판단에 필요한 단서는 제공하되, 정답 문장을 그대로 제공하지 않는다.
    - choices 중 하나가 body 문장을 거의 그대로 반복하면 안 된다.
    - 오답 선택지도 body의 일부 조건을 반영하되, 핵심 조건이나 판단 기준을 일부 놓치도록 구성한다.
    """

def compare_choice_balance_rule() -> str:
    return """
    [비교형 선택지 균형 규칙]
    - concepts가 2개 이상이거나 relation이 "compare"인 문제는 두 개념의 차이를 비교하게 한다.
    - 정답 선택지만 두 개념을 모두 설명하고 오답은 한 개념만 설명하는 방식으로 만들지 않는다.
    - 선택지 5개는 비슷한 비교 구조와 비슷한 길이를 가져야 한다.
    - 비교형 문제에서 body에 두 개념의 정확한 정의를 모두 직접 쓰지 않는다.
    """

def code_evidence_rule(competency_type: str | None, difficulty: str) -> str:
    competency_type = normalize_competency_type(competency_type)

    if difficulty not in {"중급", "고급"}:
        return ""

    if competency_type == "java":
        return """
        [Java 코드 evidence 규칙]
        - Java 중급/고급 문제 body에는 반드시 ```java 코드 블록을 포함한다.
        - 코드 블록 내의 코드는 한 줄로 길게 작성하지 말고, 반드시 적절한 줄바꿈(\\n)과 들여쓰기를 적용하여 가독성 있게 작성한다.
        - 코드 없는 설명형 문제는 생성하지 않는다.
        - 컬렉션 문제는 HashSet, HashMap, ArrayList, List, Map 중 하나 이상의 사용 코드를 포함한다.
        - equals/hashCode 문제는 class 코드, equals/hashCode 재정의, HashSet 또는 HashMap 사용 코드를 포함한다.
        - 오버라이딩/다형성 문제는 부모 타입 참조 변수와 자식 객체 생성 코드를 포함한다.
        - 예외 처리 문제는 try/catch 또는 throws 코드를 포함한다.
        """

    if competency_type == "python":
        return """
        [Python 코드 evidence 규칙]
        - Python 중급/고급 문제 body에는 반드시 ```python 코드 블록을 포함한다.
        - 코드 블록 내의 코드는 한 줄로 길게 작성하지 말고, 반드시 적절한 줄바꿈(\\n)과 들여쓰기를 적용하여 가독성 있게 작성한다.
        - 코드 없는 설명형 문제는 생성하지 않는다.
        - generator 문제는 yield, next(), generator 객체 생성 코드를 포함한다.
        - 얕은 복사 문제는 중첩 리스트와 list.copy(), slicing [:], copy.copy(), copy.deepcopy() 중 하나를 포함한다.
        - decorator 문제는 decorator 함수와 @decorator 적용 코드를 포함한다.
        - 예외 문제는 try/except 코드 또는 실제 오류 발생 코드를 포함한다.
        """

    return ""

def hallucination_guard_rule() -> str:
    return """
    [환각 방지 규칙]
    - 확실하지 않은 기술명, 버전, 수치, 공식 문서 내용은 임의로 만들지 않는다.
    - 존재하지 않는 함수명, 옵션명, 명령어, 설정값을 만들지 않는다.
    - 문제 본문과 보기 사이에 모순이 있으면 안 된다.
    - 약어가 포함된 주제는 임의로 풀어쓰지 않는다.
    - SLLM은 Small LLM 또는 Small Language Model 문맥으로 해석한다.
    - vLLM은 언어 모델 자체가 아니라 LLM 추론/서빙 엔진이다.
    - VLM은 Vision Language Model을 의미하며 vLLM과 혼동하지 않는다.
    """

def document_grounding_rule() -> str:
    return """
    [문서 기반 근거 제한 규칙]
    - 아래 [문서 내용]에 명시되어 있거나 직접적으로 추론 가능한 내용만 사용한다.
    - 문서에 없는 개념, 정의, 예시, 기술명, API, 명령어, 수치, 장단점은 추가하지 않는다.
    - 문서 내용만으로 문제와 정답을 만들 수 없으면 빈 JSON 배열 []을 반환한다.
    - 정답은 반드시 문서 내용에서 판단 가능해야 한다.
    - explanation에는 문서 근거 요약을 포함한다.
    """


# ═══════════════════════════════════════════════════════════════════════════════
# 멀티 스테이지 파이프라인 전용 프롬프트 빌더
# Stage-1 : 본문(body) · 코드 · 해설(explanation) · correct_statement 생성
# Stage-2 : correct_statement 기반 길이 균형 오답 4개 생성
# ═══════════════════════════════════════════════════════════════════════════════


def build_stage1_stem_prompt(
    topic: str,
    difficulty: str,
    count: int,
    score: int,
    question_type: str,
    competency_type: str | None,
    plans_json: str,
) -> str:
    """
    [Stage-1 프롬프트]
    문제 설계서(plans_json)를 기반으로,
    - title
    - body  (코드 포함)
    - explanation  (존댓말, 정답 근거+오답 판단 근거)
    - correct_statement  (정답이 되는 단 한 문장의 명제, 시험 선택지체)
    만 생성한다. choices / answer 는 생성하지 않는다.
    """
    return f"""
너는 IT 역량진단 문제은행의 전문 출제자다.
이번 단계에서 너는 아래 [문제 설계서]를 바탕으로 문제의 '본문·해설·정답 명제'만 작성한다.
**choices(보기 배열)는 절대 생성하지 않는다.**

[AI/RAG Stage-1 evidence 강제 규칙]
- 역량 유형이 ai이고 주제가 RAG, 검색, metadata filter, 메타데이터 필터, chunk, embedding, vector search, hybrid search, reranker와 관련 있으면 body에 반드시 구체적인 RAG 검색 로그를 포함한다.
- body에는 아래 검색 단서 중 최소 3개 이상을 포함한다:
  query, top_k, chunk, similarity, metadata, category, vector_score, keyword_score, hybrid_score
- body에는 아래 파이프라인 단서 중 최소 2개 이상을 포함한다:
  embedding, vector search, keyword search, hybrid search, metadata_filter, reranker, context filtering
- 중급 문제라도 단순히 "metadata filter를 적용해야 할까요?"처럼 일반론으로 묻지 않는다.
- 반드시 검색 조건과 검색 결과 예시를 제시한 뒤, metadata_filter 적용 여부를 판단하게 한다.
- body 마지막 문장은 반드시 물음표(?)로 끝낸다.

[Stage-1 자체 검증]
- competency_type이 ai이고 topic에 RAG, 검색, metadata filter, 메타데이터 필터가 포함되어 있으면 body에 query와 metadata 또는 category가 반드시 포함되어야 한다.
- 이 조건을 만족하지 못하면 해당 문제를 생성하지 않는다.
- correct_statement도 "검색 품질이 향상된다" 같은 일반론으로 쓰지 말고, body의 검색 로그에 근거한 판단 문장으로 작성한다.

[AI/RAG Stage-1 body 예시]
query="AI 기술"
top_k=5
metadata_filter 미적용
검색 결과:
- chunk #1: category=python, similarity=0.62, 내용="파이썬 리스트 처리..."
- chunk #2: category=ai, similarity=0.59, 내용="RAG에서 임베딩 검색..."
이 상황에서 metadata_filter 적용 여부에 대한 판단으로 가장 적절한 것은 무엇인가?

[출제 조건]
- 역량 유형: {competency_type or "미지정"}
- 세부 주제: {topic}
- 난이도: {difficulty}
- 배점: {score}
- 생성 개수: {count}
- 문제 유형: {question_type}

[문제 설계서]
{plans_json}

[출력 형식 - JSON 배열만 반환]
반드시 아래 JSON 배열만 출력한다. 마크다운 코드블록, 설명 문장은 절대 쓰지 않는다.
[
  {{
    "title": "문제 제목(짧은 명사형)",
    "body": "문제 본문(코드 포함, 마지막은 질문 문장으로 끝남)",
    "explanation": "존댓말 해설. '정답은 N번입니다.'로 시작하지 않음. 정답이 옳은 이유와 오답 방향을 설명.",
    "correct_statement": "정답이 되는 단 한 문장의 명제(시험 선택지체, 존댓말 금지, 30~80자 목표)",
    "difficulty": "{difficulty}",
    "competency_type": "{competency_type or topic}",
    "competency_tags": ["태그1", "태그2"],
    "score": {score}
  }}
]

[correct_statement 작성 규칙]
- 이 문장이 나중에 '정답 선택지'가 된다.
- 시험 선택지체(반말·명사형 종결)로 작성한다. 예: "~이다.", "~한다.", "~된다.", "~수 있다."
- 30자 이상 80자 이하를 목표로 한다.
- body의 질문에 직접 답하는 명제여야 한다.
- 선택지 형식이 아닌 설명문(~입니다 등 존댓말)으로 쓰지 않는다.

[body 작성 규칙]
- 마지막 문장은 반드시 물음표(?)로 끝나야 한다.
- body에서 correct_statement와 완전히 같은 문장을 쓰지 않는다(정답 누출 방지).

[explanation 작성 규칙]
- 반드시 존댓말(~입니다, ~합니다, ~됩니다)로만 작성한다.
- '정답은 N번입니다.' 같은 번호 선언은 포함하지 않는다(2단계에서 번호가 결정됨).
- 정답이 왜 옳은지와 주요 오답 방향이 왜 틀렸는지를 설명한다.

[correct_statement 작성 규칙]
- correct_statement는 일반론으로 쓰지 않는다.
- body에 제시된 query, top_k, chunk, similarity, category, metadata_filter 조건을 근거로 한 판단 문장이어야 한다.
- 나쁜 예: "메타데이터 필터를 적용하면 검색 품질이 향상된다."
- 좋은 예: "metadata_filter를 적용해 category=ai 청크만 검색하도록 제한하면, 다른 역량 문서가 context에 섞이는 문제를 줄일 수 있다."

{difficulty_rule(difficulty)}
{competency_rule(competency_type, topic)}
{code_evidence_rule(competency_type, difficulty)}
{hallucination_guard_rule()}
"""


def build_stage2_options_prompt(
    stem: dict,
    correct_statement: str,
    topic: str,
    competency_type: str | None,
    difficulty: str,
) -> str:
    """
    [Stage-2 프롬프트]
    correct_statement(정답 명제)를 받아,
    길이(Length) 차이가 ±15% 이내이고
    문장 종결 어미 구조가 완벽히 동일한 그럴싸한 오답 4개를 생성한다.

    반환: JSON 배열 (오답 문자열 4개)
    """
    correct_len = len(correct_statement)
    lower_bound = int(correct_len * 0.85)
    upper_bound = int(correct_len * 1.15)
    body = str(stem.get("body", "") or "")
    explanation = str(stem.get("explanation", "") or "")
    question_format = str(stem.get("question_format", "") or "")
    answer_style = str(stem.get("answer_style", "") or "")
    concepts = stem.get("concepts", [])
    relation = str(stem.get("relation", "") or "")
    target_misconception = str(stem.get("target_misconception", "") or "")
    distractor_strategy = str(stem.get("distractor_strategy", "") or "")
    answer_decision_rule = str(stem.get("answer_decision_rule", "") or "")
    normalized_competency = str(competency_type or "").strip()

    distractor_policy = ""
    if normalized_competency == "sql":
        distractor_policy = """
[SQL 오답 정책]
- WHERE/HAVING, GROUP BY/ORDER BY, JOIN 조건, NULL 처리, 실행 순서 혼동을 활용한다.
- 단순히 두 용어의 역할을 맞바꾸는 오답은 최대 1개까지만 허용한다.
- 선택지는 모두 SQL 개념 내부의 그럴듯한 설명이어야 한다.
"""
    elif normalized_competency == "python":
        distractor_policy = """
[Python 오답 정책]
- iterator/generator, mutable/immutable, scope, shallow/deep copy, exception 흐름 혼동을 활용한다.
- 코드 흐름을 추적해야 판단 가능한 선택지를 만든다.
- 단순 정의 반전형 오답은 최대 1개까지만 허용한다.
"""
    elif normalized_competency == "java":
        distractor_policy = """
[Java 오답 정책]
- override/overload, static/instance, inheritance, interface, access modifier 혼동을 활용한다.
- 일반적으로 참인 설명을 오답으로 만들지 않는다.
- 반드시 문제 코드 조건과 충돌하는 설명을 오답으로 만든다.
"""
    elif normalized_competency == "ai":
        distractor_policy = """
[AI 오답 정책]
- RAG, embedding, reranking, chunking, metadata filter, evaluation metric 혼동을 활용한다.
- 일반론 선택지를 피하고 검색 조건, 로그, 지표 해석과 연결한다.
"""
    return f"""
너는 IT 역량진단 문제은행의 오답 전문 작성자다.
아래 [정답 명제]를 기준으로 오답 4개를 작성한다.

[정답 명제]
{correct_statement}

[역량 유형] {competency_type or "미지정"}
[세부 주제] {topic}
[난이도] {difficulty}

[오답 작성 규칙 - 엄격 준수]
1. 길이(글자 수) 규칙
   - 정답 명제 길이: {correct_len}자
   - 각 오답은 {lower_bound}자 이상 {upper_bound}자 이하여야 한다.
   - 이 범위를 벗어나면 길이를 늘리거나 줄여서 반드시 범위 안에 맞춘다.

2. 종결 어미 규칙
   - 정답 명제의 종결 어미 구조와 완벽히 동일해야 한다.
   - 예: 정답이 "~이다."로 끝나면 오답도 모두 "~이다."로 끝내야 한다.
   - 예: 정답이 "~수 있다."로 끝나면 오답도 모두 "~수 있다."로 끝내야 한다.

3. 내용 규칙
   - 오답은 정답과 같은 개념 영역(역량 유형·세부 주제)에서 기술적으로 그럴싸하지만 틀린 설명이어야 한다.
   - "항상", "무조건", "절대", "전혀" 같이 너무 쉽게 제거되는 극단 표현을 남발하지 않는다.
   - 오답 4개끼리도 서로 길이가 비슷해야 한다(최대 길이 / 최소 길이 ≤ 1.3).
   - "오해할 수 있다", "혼동할 수 있다" 같은 학습자 상태 표현을 사용하지 않는다.

[문제 줄기 정보]
- 문제 본문:
{body}

- 정답 명제:
{correct_statement}

- 기존 해설:
{explanation}

- question_format:
{question_format}

- answer_style:
{answer_style}

- concepts:
{concepts}

- relation:
{relation}

- target_misconception:
{target_misconception}

- distractor_strategy:
{distractor_strategy}

- distractor_policy:
{distractor_policy}

- answer_decision_rule:
{answer_decision_rule}

[오답 생성 핵심 규칙]
- 오답은 correct_statement의 단순 부정문이나 단어 순서만 바꾼 문장으로 만들지 않는다.
- 오답은 반드시 문제 본문, concepts, target_misconception, distractor_strategy와 같은 범위 안에서 만든다.
- 오답은 기술적으로 틀렸지만 실제 학습자가 헷갈릴 만한 설명이어야 한다.
- "잘못된 설명:", "오답 후보:", "관련 없는 설명:", "혼동하기 쉬운 설명:" 같은 라벨을 선택지에 절대 쓰지 않는다.
- "항상", "무조건", "절대", "모든", "유일한" 같은 극단 표현으로 쉽게 제거되는 오답을 만들지 않는다.
- 선택지는 학습자의 심리 상태가 아니라 기술 동작, 코드 동작, 쿼리 동작, 개념 관계를 직접 설명해야 한다.
- "오해할 수 있다", "혼동할 수 있다", "착각할 수 있다", "잘못 이해할 수 있다" 같은 표현은 절대 쓰지 않는다.

[출력 형식 - JSON 배열만 반환, 마크다운 금지]
["오답1", "오답2", "오답3", "오답4"]
"""