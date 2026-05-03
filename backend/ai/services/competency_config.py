# backend/ai/services/competency_config.py
# 신규 역량 유형 8개 기준 공통 설정 모듈
# 이 파일을 수정하면 topic_validator, question_planner, question_generator, ai_documents, ai_questions 전체에 반영됨

SUPPORTED_COMPETENCIES = {
    "software_engineering": "소프트웨어공학",
    "java": "Java",
    "python": "Python",
    "c_language": "C언어",
    "sql": "SQL",
    "data_structure_algorithm": "자료구조/알고리즘",
    "security": "정보보안",
    "ai": "AI",
}

# 기존 legacy value → 신규 value 매핑
# DB 데이터는 그대로 두고, 새로 입력되는 값만 normalize한다.
LEGACY_COMPETENCY_MAP = {
    "programming": "python",
    "programming_language": "python",
    "database": "sql",
    "ai_data": "ai",
    "web_development": "java",
    "os_network": "software_engineering",
    "cloud_devops": "software_engineering",
}

# 표시용 레이블 맵 (신규 8개 + legacy 표시용)
COMPETENCY_LABEL_MAP = {
    **SUPPORTED_COMPETENCIES,
    # legacy display only
    "programming": "프로그래밍",
    "programming_language": "프로그래밍",
    "database": "데이터베이스",
    "ai_data": "인공지능/데이터",
    "web_development": "웹 개발",
    "os_network": "운영체제/네트워크",
    "cloud_devops": "클라우드/DevOps",
}

COMPETENCY_KEYWORDS = {
    "software_engineering": [
        "요구사항", "분석", "설계", "테스트", "품질", "형상관리",
        "변경관리", "유지보수", "검증", "검토", "명세서",
        "추적성", "애자일", "스크럼", "UML", "테스트케이스",
    ],
    "java": [
        "java", "자바", "jvm", "클래스", "객체", "상속", "다형성",
        "인터페이스", "예외", "컬렉션", "stream", "스트림",
        "제네릭", "오버로딩", "오버라이딩",
    ],
    "python": [
        "python", "파이썬", "리스트", "딕셔너리", "튜플", "셋",
        "함수", "클래스", "모듈", "패키지", "예외", "파일",
        "컴프리헨션", "이터레이터", "제너레이터",
    ],
    "c_language": [
        "c", "c언어", "포인터", "배열", "문자열", "구조체",
        "메모리", "malloc", "free", "함수", "전처리기",
        "파일 입출력", "주소", "값 전달", "참조",
    ],
    "sql": [
        "sql", "select", "insert", "update", "delete", "where",
        "join", "JOIN", "조인",
        "인덱스", "index", "실행 계획", "실행계획", "explain", "EXPLAIN",
        "쿼리", "최적화", "성능", "튜닝",
        "페이징", "페이지네이션", "pagination", "OFFSET", "offset", "LIMIT", "limit", "커서", "cursor",
        "GROUP BY", "group by", "group", "집계", "COUNT", "count", "SUM", "sum", "통계",
        "커버링", "covering", "커버링 인덱스", "covering index", "trade-off", "트레이드오프",
        "쓰기 비용", "버퍼풀",
        "락", "lock", "Lock", "트랜잭션", "transaction", "동시성", "concurrency",
        "격리", "isolation", "SELECT FOR UPDATE", "select for update",
    ],
    "data_structure_algorithm": [
        "자료구조", "알고리즘", "배열", "리스트", "스택", "큐",
        "트리", "그래프", "해시", "힙", "정렬", "탐색",
        "dfs", "bfs", "재귀", "동적계획법", "dp", "그리디",
        "시간복잡도", "공간복잡도", "빅오",
    ],
    "security": [
        "보안", "정보보안", "인증", "인가", "권한", "암호화",
        "해시", "해싱", "xss", "csrf", "sql injection",
        "인젝션", "취약점", "토큰", "jwt", "oauth",
        "접근제어", "개인정보",
    ],
    "ai": [
        "ai", "인공지능", "머신러닝", "딥러닝", "llm", "rag",
        "임베딩", "embedding", "벡터", "벡터db", "모델",
        "학습", "추론", "분류", "회귀", "과적합",
        "정확도", "정밀도", "재현율", "f1", "파인튜닝",
        "fine-tuning", "qlora",
    ],
}


def normalize_competency_type(value: str | None) -> str | None:
    """
    입력된 competency_type 값을 신규 8개 중 하나로 정규화한다.
    - 신규 값이면 그대로 반환
    - legacy 값이면 LEGACY_COMPETENCY_MAP을 통해 변환
    - 알 수 없는 값이면 그대로 반환 (강제 변환하지 않음)
    """
    if not value:
        return None

    normalized = value.strip()

    if normalized in SUPPORTED_COMPETENCIES:
        return normalized

    return LEGACY_COMPETENCY_MAP.get(normalized, normalized)


def get_competency_label(value: str | None) -> str:
    """
    competency_type 값을 사람이 읽을 수 있는 레이블로 변환한다.
    legacy 값도 표시용 레이블을 반환한다.
    """
    if not value:
        return "미분류"

    normalized = normalize_competency_type(value)
    return COMPETENCY_LABEL_MAP.get(normalized or value, value)
