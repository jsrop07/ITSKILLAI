# backend/ai/services/topic_validator.py

from fastapi import HTTPException


COMPETENCY_TOPIC_RULES = {
    "programming": {
        "label": "프로그래밍",
        "keywords": [
            "python", "java", "javascript", "typescript", "c", "c++",
            "변수", "함수", "클래스", "객체", "상속", "다형성",
            "예외", "반복문", "조건문", "자료형", "메모리", "포인터",
            "비동기", "동기", "모듈", "패키지", "문법"
        ],
    },
    "data_structure_algorithm": {
        "label": "자료구조/알고리즘",
        "keywords": [
            "배열", "리스트", "스택", "큐", "트리", "그래프",
            "해시", "힙", "정렬", "탐색", "dfs", "bfs",
            "동적계획법", "dp", "그리디", "분할정복",
            "시간복잡도", "공간복잡도", "빅오", "재귀",
            "최단경로", "다익스트라", "이진탐색",
            "이분탐색","다이나믹프로그래밍","동적계획법","동적계획","동적계획법 문제","DP","동적계획 문제",
            "자료구조",
        ],
    },
    "web_development": {
        "label": "웹 개발",
        "keywords": [
            "html", "css", "javascript", "typescript", "react", "vue",
            "dom", "브라우저", "렌더링", "상태관리", "api", "rest",
            "http", "https", "쿠키", "세션", "jwt", "인증", "인가",
            "csrf", "xss", "cors", "mvc", "fastapi", "spring",
            "백엔드", "프론트엔드", "서버", "클라이언트"
        ],
    },
    "database": {
        "label": "데이터베이스",
        "keywords": [
            "sql", "select", "insert", "update", "delete",
            "join", "index", "인덱스", "트랜잭션", "정규화",
            "반정규화", "락", "격리수준", "acid", "n+1",
            "쿼리", "실행계획", "rdbms", "mysql", "mariadb",
            "postgresql", "nosql", "redis"
        ],
    },
    "os_network": {
        "label": "운영체제/네트워크",
        "keywords": [
            "프로세스", "스레드", "동시성", "교착상태", "데드락",
            "메모리", "가상메모리", "스케줄링", "커널",
            "tcp", "udp", "ip", "dns", "http", "https",
            "소켓", "라우팅", "서브넷", "osi", "포트",
            "로드밸런싱", "패킷"
        ],
    },
    "security": {
        "label": "정보보안",
        "keywords": [
            "보안", "암호화", "해싱", "인증", "인가",
            "xss", "csrf", "sql injection", "인젝션",
            "취약점", "권한", "토큰", "jwt", "oauth",
            "세션 하이재킹", "방화벽", "개인정보", "접근제어"
        ],
    },
    "cloud_devops": {
        "label": "클라우드/DevOps",
        "keywords": [
            "aws", "ec2", "s3", "rds", "docker", "kubernetes",
            "k8s", "nginx", "ci", "cd", "배포", "컨테이너",
            "로드밸런서", "오토스케일링", "모니터링",
            "로그", "파이프라인", "github actions", "jenkins"
        ],
    },
    "ai_data": {
        "label": "인공지능/데이터",
        "keywords": [
            "ai", "인공지능", "머신러닝", "딥러닝", "llm",
            "rag", "embedding", "임베딩", "벡터db", "vector",
            "fine-tuning", "파인튜닝", "qlora", "transformer",
            "attention", "모델", "학습", "추론", "분류", "회귀",
            "데이터분석", "pandas", "numpy", "정확도", "재현율",
            "정밀도", "f1", "클러스터링"
        ],
    },
    "software_engineering": {
        "label": "소프트웨어공학",
        "keywords": [
            "요구사항", "설계", "테스트", "유지보수", "리팩토링",
            "디자인패턴", "객체지향", "solid", "uml",
            "애자일", "스크럼", "형상관리", "git",
            "테스트케이스", "단위테스트", "통합테스트",
            "아키텍처", "모듈화"
        ],
    },
}


BLOCKED_NON_IT_KEYWORDS = [
    "음식", "맛집", "요리", "레시피", "추천해줘",
    "연애", "소개팅", "여행", "호텔", "운세", "사주",
    "영화", "드라마", "노래", "가수", "쇼핑",
    "다이어트", "헬스", "운동 루틴", "화장품 추천"
]


def normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def validate_topic_for_competency(competency_type: str | None, topic: str | None):
    normalized_topic = normalize_text(topic)

    if not normalized_topic:
        raise HTTPException(
            status_code=400,
            detail="세부 주제를 입력해주세요."
        )

    if len(normalized_topic) < 2:
        raise HTTPException(
            status_code=400,
            detail="세부 주제는 2글자 이상 입력해주세요."
        )

    if not competency_type:
        raise HTTPException(
            status_code=400,
            detail="역량 유형을 선택해주세요."
        )

    if competency_type not in COMPETENCY_TOPIC_RULES:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 역량 유형입니다."
        )

    # 1차: 명백한 비IT 주제 차단
    for blocked in BLOCKED_NON_IT_KEYWORDS:
        if blocked.lower() in normalized_topic:
            raise HTTPException(
                status_code=400,
                detail="세부 주제는 IT 역량진단과 관련된 주제만 입력할 수 있습니다."
            )

    selected_rule = COMPETENCY_TOPIC_RULES[competency_type]
    selected_keywords = selected_rule["keywords"]

    # 2차: 선택한 역량 유형과 세부 주제 매칭 확인
    is_matched = any(keyword.lower() in normalized_topic for keyword in selected_keywords)

    if is_matched:
        return

    # 3차: 다른 역량 유형에 더 잘 맞는 주제인지 확인
    matched_other_competencies = []

    for key, rule in COMPETENCY_TOPIC_RULES.items():
        if key == competency_type:
            continue

        other_keywords = rule["keywords"]
        if any(keyword.lower() in normalized_topic for keyword in other_keywords):
            matched_other_competencies.append(rule["label"])

    if matched_other_competencies:
        raise HTTPException(
            status_code=400,
            detail=(
                f"세부 주제가 선택한 역량 유형({selected_rule['label']})과 맞지 않습니다. "
                f"'{topic}' 주제는 {', '.join(matched_other_competencies)} 역량 유형에 더 적합합니다."
            )
        )

    # 4차: IT 키워드가 아예 없는 애매한 주제 차단
    raise HTTPException(
        status_code=400,
        detail=(
            f"세부 주제가 선택한 역량 유형({selected_rule['label']})과 관련 있는지 확인하기 어렵습니다. "
            f"예: {', '.join(selected_keywords[:6])} 같은 주제로 입력해주세요."
        )
    )