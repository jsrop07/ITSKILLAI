import re
import random 
from typing import Any, Dict, List, Optional
from ai.questions.models import EvidencePack, QuestionFormatPlan

AI_TOPIC_PRESETS = {
    "rag": {
        "aliases": ["rag", "RAG", "RAG 품질 개선", "검색 품질", "하이브리드 RAG"],
        "normalized_topic": "RAG 검색 품질 개선",
        "concepts": [
            "retrieval",
            "embedding",
            "vector search",
            "chunk",
            "metadata filter",
            "reranker",
            "hybrid search",
            "top_k",
        ],
        "correct_points": [
            "RAG는 외부 문서를 검색해 LLM 답변 생성에 활용하는 방식입니다.",
            "검색 결과에 관련 없는 문서가 섞이면 metadata filter로 검색 범위를 제한할 수 있습니다.",
            "chunk 품질이 낮으면 검색 결과의 관련성이 떨어질 수 있습니다.",
            "vector search와 keyword search를 함께 사용하면 의미 기반 검색과 키워드 기반 검색의 장점을 함께 활용할 수 있습니다.",
            "reranker는 1차 검색 결과의 순서를 다시 평가해 더 관련성 높은 문서를 상위에 배치하는 데 사용할 수 있습니다.",
        ],
        "wrong_points": [
            "RAG는 모델 파라미터를 직접 수정해 지식을 저장하는 방식입니다.",
            "top_k를 무조건 크게 하면 항상 검색 품질이 좋아집니다.",
            "metadata filter는 검색 결과의 범위를 제한하는 데 영향을 주지 않습니다.",
            "chunk 품질이 낮아도 프롬프트만 수정하면 검색 품질 문제가 항상 해결됩니다.",
            "RAG는 외부 문서 검색 없이 LLM 내부 지식만 사용하는 방식입니다.",
        ],
        "scenario": (
            "사내 문서 기반 QA 시스템에서 사용자가 특정 주제를 질문했지만, "
            "검색 결과에 다른 카테고리 문서가 함께 섞이고 있습니다."
        ),
        "log_or_metric": {
            "query": "RAG 검색 품질 개선",
            "top_k": 5,
            "result_summary": [
                {"chunk": "RAG chunk 분리 전략", "similarity": 0.71, "category": "ai"},
                {"chunk": "프론트엔드 라우팅 설정", "similarity": 0.64, "category": "web"},
                {"chunk": "metadata filter 적용 방법", "similarity": 0.62, "category": "ai"},
            ],
            "issue": "검색 결과에 관련 없는 카테고리 문서가 섞임",
        },
    },
    "llm": {
        "aliases": ["llm", "LLM", "프롬프트", "답변 품질", "환각"],
        "normalized_topic": "LLM 답변 품질과 프롬프트 제어",
        "concepts": [
            "LLM",
            "prompt",
            "system prompt",
            "temperature",
            "hallucination",
            "context",
            "output format",
        ],
        "correct_points": [
            "LLM은 입력된 문맥과 프롬프트를 바탕으로 자연어 응답을 생성합니다.",
            "프롬프트가 구체적일수록 원하는 형식과 조건에 맞는 답변을 유도하기 쉽습니다.",
            "temperature를 낮추면 일반적으로 응답의 무작위성을 줄이는 데 도움이 됩니다.",
            "근거가 필요한 답변에서는 RAG나 별도 검증 절차를 함께 사용할 수 있습니다.",
            "system prompt는 모델의 역할과 응답 규칙을 지정하는 데 사용할 수 있습니다.",
        ],
        "wrong_points": [
            "LLM은 항상 최신 정보를 자동으로 알고 있으므로 외부 검색이 필요 없습니다.",
            "temperature는 모델의 학습 데이터 크기를 의미합니다.",
            "프롬프트를 수정하면 모델의 파라미터가 직접 변경됩니다.",
            "LLM은 입력 문맥과 무관하게 항상 동일한 답변만 생성합니다.",
            "hallucination은 서버 응답 시간이 느려지는 현상만을 의미합니다.",
        ],
        "scenario": (
            "사용자 질문에 대해 LLM이 그럴듯하지만 근거가 부족한 답변을 생성하고 있습니다."
        ),
        "log_or_metric": {
            "prompt": "최신 보안 정책을 알려줘",
            "context_provided": False,
            "temperature": 0.9,
            "issue": "근거 없는 답변 생성 가능성이 높음",
        },
    },
    "ml": {
        "aliases": ["ml", "ML", "머신러닝", "모델 평가"],
        "normalized_topic": "머신러닝 모델 학습과 평가",
        "concepts": [
            "training data",
            "test data",
            "supervised learning",
            "overfitting",
            "accuracy",
            "precision",
            "recall",
            "data leakage",
        ],
        "correct_points": [
            "머신러닝은 데이터를 기반으로 패턴을 학습해 예측이나 분류를 수행합니다.",
            "지도학습은 정답 라벨이 있는 데이터를 사용해 모델을 학습합니다.",
            "학습 데이터와 테스트 데이터를 분리하면 모델의 일반화 성능을 평가할 수 있습니다.",
            "학습 성능은 높지만 테스트 성능이 낮다면 과적합을 의심할 수 있습니다.",
            "클래스 불균형 상황에서는 accuracy만으로 모델을 평가하기 어려울 수 있습니다.",
        ],
        "wrong_points": [
            "테스트 데이터는 모델이 더 잘 외우도록 반복 학습에 사용해야 합니다.",
            "지도학습은 정답 라벨이 전혀 없는 데이터만 사용하는 방식입니다.",
            "정확도는 모든 문제에서 항상 가장 적절한 평가 지표입니다.",
            "과적합은 모델이 학습 데이터를 거의 학습하지 못한 상태를 의미합니다.",
            "데이터 누수는 모델 성능 평가에 영향을 주지 않습니다.",
        ],
        "scenario": (
            "모델의 학습 데이터 성능은 매우 높지만, 테스트 데이터 성능은 크게 낮게 나타났습니다."
        ),
        "log_or_metric": {
            "train_accuracy": 0.98,
            "test_accuracy": 0.71,
            "issue": "학습 성능과 테스트 성능 차이가 큼",
        },
    },
    "dl": {
        "aliases": ["dl", "DL", "딥러닝", "신경망", "과적합"],
        "normalized_topic": "딥러닝 모델 구조와 과적합",
        "concepts": [
            "neural network",
            "hidden layer",
            "epoch",
            "loss function",
            "validation loss",
            "dropout",
            "regularization",
        ],
        "correct_points": [
            "딥러닝은 여러 층의 신경망을 사용해 데이터의 복잡한 패턴을 학습할 수 있습니다.",
            "은닉층은 입력 데이터로부터 특징을 변환하고 조합하는 역할을 합니다.",
            "epoch는 전체 학습 데이터를 한 번 학습하는 단위를 의미합니다.",
            "학습 손실은 낮아지지만 검증 손실이 증가하면 과적합을 의심할 수 있습니다.",
            "dropout이나 regularization은 과적합 완화에 사용할 수 있습니다.",
        ],
        "wrong_points": [
            "딥러닝은 규칙 기반 if문만으로 예측을 수행하는 방식입니다.",
            "epoch는 모델이 출력할 클래스의 개수를 의미합니다.",
            "은닉층은 학습 데이터를 저장하는 데이터베이스 역할만 합니다.",
            "검증 손실이 계속 증가해도 학습 손실만 낮으면 항상 좋은 모델입니다.",
            "dropout은 테스트 데이터를 삭제하는 전처리 기법입니다.",
        ],
        "scenario": (
            "딥러닝 모델 학습 중 train loss는 계속 감소하지만 validation loss는 증가하고 있습니다."
        ),
        "log_or_metric": {
            "epoch": 20,
            "train_loss": 0.12,
            "validation_loss": 0.48,
            "issue": "과적합 가능성",
        },
    },
    "modelops": {
        "aliases": ["modelops", "ModelOps", "모델옵스", "모델 배포", "모니터링", "서빙"],
        "normalized_topic": "모델 배포와 운영 모니터링",
        "concepts": [
            "model serving",
            "monitoring",
            "latency",
            "drift",
            "versioning",
            "batch inference",
            "real-time inference",
        ],
        "correct_points": [
            "ModelOps는 모델을 안정적으로 배포, 운영, 모니터링하기 위한 과정입니다.",
            "모델 배포 후에는 성능, 지연 시간, 오류율 등을 지속적으로 모니터링해야 합니다.",
            "데이터 drift가 발생하면 학습 시점과 운영 시점의 데이터 분포가 달라질 수 있습니다.",
            "실시간 응답이 필요한 서비스에서는 latency를 중요한 운영 지표로 관리해야 합니다.",
            "모델 버전 관리는 새 모델 배포 후 문제 발생 시 롤백에 도움이 됩니다.",
        ],
        "wrong_points": [
            "ModelOps는 모델 학습 코드 작성만을 의미하며 운영과는 관련이 없습니다.",
            "모델은 한 번 배포하면 성능을 다시 확인할 필요가 없습니다.",
            "latency는 모델의 정답률과 완전히 같은 의미입니다.",
            "데이터 drift는 서버를 재부팅하면 항상 해결됩니다.",
            "모델 버전 관리는 운영 환경에서 필요하지 않습니다.",
        ],
        "scenario": (
            "모델 API 배포 후 평균 응답 시간이 증가하고 일부 요청에서 timeout이 발생하고 있습니다."
        ),
        "log_or_metric": {
            "avg_latency_ms": 1800,
            "timeout_rate": "7%",
            "recent_deploy": True,
            "issue": "서빙 지연 증가",
        },
    },
}

AI_BEGINNER_TOPIC_PRESETS: Dict[str, Dict[str, Any]] = {
    "llm": {
        "aliases": ["llm", "LLM", "대규모 언어 모델", "large language model"],
        "normalized_topic": "LLM 기본 개념",
        "concepts": ["LLM", "prompt", "context", "natural language generation"],
        "definition": "LLM은 대량의 텍스트 데이터를 기반으로 자연어를 이해하고 생성하는 모델입니다.",
        "purpose": "질문 답변, 요약, 분류, 문장 생성 같은 자연어 작업에 사용됩니다.",
        "role": "입력 문맥과 프롬프트를 바탕으로 자연어 응답을 생성합니다.",
        "wrong_points": [
            "LLM은 항상 최신 정보를 자동으로 알고 있습니다.",
            "LLM은 입력 문맥과 무관하게 항상 같은 답변만 생성합니다.",
            "LLM은 매 요청마다 모델 파라미터를 직접 수정합니다.",
            "LLM은 데이터베이스처럼 모든 사실을 항상 정확히 조회합니다.",
        ],
        "compare": {
            "target": "검색 엔진",
            "point": "LLM은 자연어 응답 생성에 초점이 있고, 검색 엔진은 관련 문서나 웹페이지 탐색에 초점이 있습니다.",
        },
        "term_role": "LLM은 자연어 입력을 바탕으로 응답을 생성하는 역할을 합니다.",
    },
    "gpt": {
        "aliases": ["gpt", "GPT"],
        "normalized_topic": "GPT 기본 개념",
        "concepts": ["GPT", "generative model", "autoregressive model"],
        "definition": "GPT는 이전 문맥을 바탕으로 다음 토큰을 예측하며 문장을 생성하는 언어 모델 계열입니다.",
        "purpose": "대화, 문장 생성, 요약, 코드 작성 같은 생성형 작업에 사용됩니다.",
        "role": "주어진 문맥 다음에 올 가능성이 높은 텍스트를 생성합니다.",
        "wrong_points": [
            "GPT는 문장을 생성하지 않고 이미 저장된 문서만 검색합니다.",
            "GPT는 양방향 문맥 이해만을 위해 설계된 인코더 모델입니다.",
            "GPT는 입력 없이 항상 동일한 고정 답변만 출력합니다.",
            "GPT는 자연어 생성과 관련이 없는 이미지 전용 모델입니다.",
        ],
        "compare": {
            "target": "BERT",
            "point": "GPT는 주로 텍스트 생성에 강점이 있고, BERT는 문맥 이해와 분류 작업에 자주 사용됩니다.",
        },
        "term_role": "GPT는 문맥을 이어 자연어를 생성하는 역할을 합니다.",
    },
    "bert": {
        "aliases": ["bert", "BERT"],
        "normalized_topic": "BERT 기본 개념",
        "concepts": ["BERT", "bidirectional context", "encoder"],
        "definition": "BERT는 문장의 앞뒤 문맥을 함께 활용해 텍스트 의미를 이해하는 언어 모델 계열입니다.",
        "purpose": "문장 분류, 의미 유사도, 개체명 인식 같은 이해 중심 작업에 사용됩니다.",
        "role": "문장 전체의 양방향 문맥을 반영해 텍스트 표현을 만듭니다.",
        "wrong_points": [
            "BERT는 주로 다음 단어를 이어 쓰는 생성형 모델입니다.",
            "BERT는 문맥을 보지 않고 단어를 독립적으로 처리합니다.",
            "BERT는 텍스트 이해 작업에 사용할 수 없습니다.",
            "BERT는 데이터 전처리 없이 항상 최신 지식을 제공합니다.",
        ],
        "compare": {
            "target": "GPT",
            "point": "BERT는 문맥 이해에 강점이 있고, GPT는 문맥을 이어 텍스트를 생성하는 데 강점이 있습니다.",
        },
        "term_role": "BERT는 문장의 양방향 문맥을 이해하는 역할을 합니다.",
    },
    "prompt": {
        "aliases": ["prompt", "프롬프트", "프롬프트 작성"],
        "normalized_topic": "프롬프트 기본 개념",
        "concepts": ["prompt", "instruction", "context"],
        "definition": "프롬프트는 LLM에게 수행할 작업, 조건, 맥락을 전달하는 입력 문장입니다.",
        "purpose": "모델이 원하는 형식과 기준에 맞춰 응답하도록 유도하기 위해 사용됩니다.",
        "role": "모델의 응답 방향과 출력 조건을 지정합니다.",
        "wrong_points": [
            "프롬프트는 모델의 학습 데이터를 직접 삭제합니다.",
            "프롬프트는 서버의 CPU 사용량만 조절합니다.",
            "프롬프트는 모델 파라미터를 영구적으로 변경합니다.",
            "프롬프트는 데이터베이스 인덱스를 생성하는 명령입니다.",
        ],
        "compare": {
            "target": "system prompt",
            "point": "일반 프롬프트는 사용자 요청에 가깝고, system prompt는 모델의 역할과 기본 규칙을 지정합니다.",
        },
        "term_role": "프롬프트는 모델에게 작업 지시와 맥락을 전달하는 역할을 합니다.",
    },
    "system_prompt": {
        "aliases": ["system prompt", "시스템 프롬프트", "system_prompt"],
        "normalized_topic": "시스템 프롬프트 기본 개념",
        "concepts": ["system prompt", "role", "output rule"],
        "definition": "시스템 프롬프트는 모델의 역할, 응답 방식, 제한 조건을 지정하는 상위 지시입니다.",
        "purpose": "모델 응답의 톤, 범위, 출력 형식을 일관되게 제어하기 위해 사용됩니다.",
        "role": "사용자 요청보다 앞선 기본 행동 규칙을 제공합니다.",
        "wrong_points": [
            "시스템 프롬프트는 모델 가중치를 다시 학습시키는 데이터셋입니다.",
            "시스템 프롬프트는 벡터 DB의 검색 속도만 조절합니다.",
            "시스템 프롬프트는 사용자의 질문을 저장하는 테이블입니다.",
            "시스템 프롬프트는 모델 응답과 전혀 관련이 없습니다.",
        ],
        "compare": {
            "target": "user prompt",
            "point": "시스템 프롬프트는 기본 역할과 규칙을 정하고, 사용자 프롬프트는 개별 요청 내용을 전달합니다.",
        },
        "term_role": "시스템 프롬프트는 모델의 기본 역할과 응답 규칙을 정하는 역할을 합니다.",
    },
    "temperature": {
        "aliases": ["temperature", "온도", "무작위성"],
        "normalized_topic": "temperature 기본 개념",
        "concepts": ["temperature", "randomness", "generation setting"],
        "definition": "temperature는 LLM 응답 생성에서 출력의 무작위성 정도를 조절하는 설정값입니다.",
        "purpose": "응답을 더 일관되게 하거나 더 다양하게 만들기 위해 조정합니다.",
        "role": "낮을수록 일관성이 높아지고, 높을수록 다양한 표현이 나올 가능성이 커집니다.",
        "wrong_points": [
            "temperature는 모델 학습 데이터의 개수를 의미합니다.",
            "temperature는 서버의 실제 물리적 온도만 의미합니다.",
            "temperature는 벡터 DB의 저장 용량을 조절합니다.",
            "temperature는 모델의 최신 지식 여부를 보장합니다.",
        ],
        "compare": {
            "target": "top_k 검색 수",
            "point": "temperature는 생성 무작위성 설정이고, top_k는 검색이나 후보 수와 관련된 설정입니다.",
        },
        "term_role": "temperature는 생성 응답의 무작위성을 조절하는 역할을 합니다.",
    },
    "hallucination": {
        "aliases": ["hallucination", "환각", "LLM 환각"],
        "normalized_topic": "LLM 환각 기본 개념",
        "concepts": ["hallucination", "factuality", "grounding"],
        "definition": "hallucination은 LLM이 근거가 부족하거나 사실과 다른 내용을 그럴듯하게 생성하는 현상입니다.",
        "purpose": "환각 개념은 LLM 답변의 신뢰성과 근거 확인 필요성을 설명할 때 사용됩니다.",
        "role": "LLM 응답 품질에서 사실성 문제를 나타내는 개념입니다.",
        "wrong_points": [
            "hallucination은 서버 응답 시간이 느려지는 현상만 의미합니다.",
            "hallucination은 모델이 항상 정답만 말하는 현상입니다.",
            "hallucination은 벡터 DB 저장 공간이 부족한 상태입니다.",
            "hallucination은 GPU 메모리를 자동으로 줄이는 기능입니다.",
        ],
        "compare": {
            "target": "latency",
            "point": "hallucination은 답변 사실성 문제이고, latency는 응답 지연 시간 문제입니다.",
        },
        "term_role": "hallucination은 근거 없는 답변 생성 위험을 설명하는 역할을 합니다.",
    },
    "rag": {
        "aliases": ["rag", "RAG", "검색 증강 생성", "retrieval augmented generation"],
        "normalized_topic": "RAG 기본 개념",
        "concepts": ["RAG", "retrieval", "context", "LLM"],
        "definition": "RAG는 외부 문서를 검색한 뒤 그 결과를 LLM 답변 생성에 활용하는 방식입니다.",
        "purpose": "모델 내부 지식만으로 부족한 정보를 외부 근거와 함께 활용하기 위해 사용됩니다.",
        "role": "검색 결과를 답변 생성 context로 제공해 근거성을 높입니다.",
        "wrong_points": [
            "RAG는 모델 파라미터를 직접 수정해 지식을 저장하는 방식입니다.",
            "RAG는 외부 문서 검색 없이 LLM 내부 지식만 사용하는 방식입니다.",
            "RAG는 이미지 압축률을 조절하는 딥러닝 기법입니다.",
            "RAG는 데이터베이스 트랜잭션을 관리하는 SQL 명령입니다.",
        ],
        "compare": {
            "target": "fine-tuning",
            "point": "RAG는 외부 문서를 검색해 활용하고, fine-tuning은 모델을 추가 학습해 동작을 조정합니다.",
        },
        "term_role": "RAG는 검색 결과를 LLM 답변 근거로 제공하는 역할을 합니다.",
    },
    "embedding": {
        "aliases": ["embedding", "임베딩", "벡터 임베딩"],
        "normalized_topic": "Embedding 기본 개념",
        "concepts": ["embedding", "vector", "semantic similarity"],
        "definition": "embedding은 텍스트나 데이터를 의미를 담은 숫자 벡터로 변환한 표현입니다.",
        "purpose": "문장이나 문서 간 의미 유사도를 계산하기 위해 사용됩니다.",
        "role": "텍스트 의미를 벡터 공간에서 비교할 수 있게 만듭니다.",
        "wrong_points": [
            "embedding은 원문 텍스트를 사람이 읽기 쉽게 번역하는 작업입니다.",
            "embedding은 모델 응답의 존댓말 여부만 조절합니다.",
            "embedding은 데이터베이스 테이블을 삭제하는 명령입니다.",
            "embedding은 서버 응답 시간을 표시하는 운영 지표입니다.",
        ],
        "compare": {
            "target": "keyword",
            "point": "embedding은 의미 유사도 비교에 강점이 있고, keyword는 정확한 단어 일치에 초점이 있습니다.",
        },
        "term_role": "embedding은 텍스트 의미를 숫자 벡터로 표현하는 역할을 합니다.",
    },
    "vector_db": {
        "aliases": ["vector db", "vector database", "벡터 DB", "벡터 데이터베이스"],
        "normalized_topic": "Vector DB 기본 개념",
        "concepts": ["vector database", "embedding", "similarity search"],
        "definition": "Vector DB는 embedding 벡터를 저장하고 유사도 검색을 수행하는 데이터베이스입니다.",
        "purpose": "의미가 비슷한 문서나 데이터를 빠르게 찾기 위해 사용됩니다.",
        "role": "벡터화된 문서를 저장하고 질문과 가까운 문서를 검색합니다.",
        "wrong_points": [
            "Vector DB는 SQL 문법 오류를 자동 수정하는 컴파일러입니다.",
            "Vector DB는 모델 파라미터를 학습시키는 신경망 계층입니다.",
            "Vector DB는 자연어 답변을 직접 생성하는 언어 모델입니다.",
            "Vector DB는 운영 서버의 CPU 온도만 저장합니다.",
        ],
        "compare": {
            "target": "일반 관계형 DB",
            "point": "Vector DB는 벡터 유사도 검색에 초점이 있고, 관계형 DB는 정형 데이터의 관계와 조건 검색에 강점이 있습니다.",
        },
        "term_role": "Vector DB는 embedding 벡터를 저장하고 유사 문서를 찾는 역할을 합니다.",
    },
    "chunk": {
        "aliases": ["chunk", "청크", "문서 청크"],
        "normalized_topic": "Chunk 기본 개념",
        "concepts": ["chunk", "document split", "RAG"],
        "definition": "chunk는 긴 문서를 검색에 활용하기 쉽도록 나눈 작은 문서 조각입니다.",
        "purpose": "필요한 근거를 적절한 단위로 검색하고 context에 넣기 위해 사용됩니다.",
        "role": "긴 문서 내용을 검색 가능한 작은 단위로 나눕니다.",
        "wrong_points": [
            "chunk는 모델의 정답 번호를 무작위로 바꾸는 기능입니다.",
            "chunk는 서버 배포 버전을 관리하는 도구입니다.",
            "chunk는 학습률을 자동으로 계산하는 수식입니다.",
            "chunk는 사용자의 비밀번호를 암호화하는 인증 방식입니다.",
        ],
        "compare": {
            "target": "전체 문서",
            "point": "chunk는 검색에 적합한 작은 단위이고, 전체 문서는 여러 주제가 함께 들어 있어 검색 단위로 무거울 수 있습니다.",
        },
        "term_role": "chunk는 문서를 검색 가능한 작은 단위로 나누는 역할을 합니다.",
    },
    "metadata_filter": {
        "aliases": ["metadata filter", "메타데이터 필터", "metadata"],
        "normalized_topic": "Metadata Filter 기본 개념",
        "concepts": ["metadata filter", "category", "retrieval"],
        "definition": "metadata filter는 문서의 category, 날짜, 출처 같은 속성을 기준으로 검색 범위를 제한하는 방법입니다.",
        "purpose": "관련 없는 범주의 문서가 검색 결과에 섞이는 것을 줄이기 위해 사용됩니다.",
        "role": "검색 대상 문서를 지정한 속성 조건에 맞게 좁힙니다.",
        "wrong_points": [
            "metadata filter는 LLM의 답변 말투만 바꾸는 설정입니다.",
            "metadata filter는 모델을 추가 학습시키는 데이터셋입니다.",
            "metadata filter는 모든 문서를 무조건 검색 결과에 포함합니다.",
            "metadata filter는 서버의 네트워크 지연 시간을 의미합니다.",
        ],
        "compare": {
            "target": "reranker",
            "point": "metadata filter는 검색 범위를 먼저 제한하고, reranker는 검색된 후보의 순서를 다시 평가합니다.",
        },
        "term_role": "metadata filter는 문서 속성 기준으로 검색 범위를 제한하는 역할을 합니다.",
    },
    "reranker": {
        "aliases": ["reranker", "리랭커", "재정렬"],
        "normalized_topic": "Reranker 기본 개념",
        "concepts": ["reranker", "ranking", "retrieval"],
        "definition": "reranker는 1차로 검색된 후보 문서의 관련도를 다시 평가해 순서를 조정하는 방법입니다.",
        "purpose": "더 관련성 높은 문서가 상위에 오도록 검색 품질을 개선하기 위해 사용됩니다.",
        "role": "검색 후보의 순위를 질문 관련도 기준으로 다시 정렬합니다.",
        "wrong_points": [
            "reranker는 검색 전 문서 저장소를 삭제하는 기능입니다.",
            "reranker는 모델의 학습 데이터를 자동 생성하는 계층입니다.",
            "reranker는 사용자 질문을 음성으로 변환하는 도구입니다.",
            "reranker는 API 응답 시간을 측정하는 지표 이름입니다.",
        ],
        "compare": {
            "target": "metadata filter",
            "point": "reranker는 후보 순서를 조정하고, metadata filter는 검색할 문서 범위를 제한합니다.",
        },
        "term_role": "reranker는 검색 후보를 관련도 기준으로 재정렬하는 역할을 합니다.",
    },
    "fine_tuning": {
        "aliases": ["fine-tuning", "파인튜닝", "fine tuning"],
        "normalized_topic": "Fine-tuning 기본 개념",
        "concepts": ["fine-tuning", "model training", "adaptation"],
        "definition": "fine-tuning은 기존 모델을 특정 데이터나 작업에 맞게 추가 학습하는 방법입니다.",
        "purpose": "특정 도메인이나 작업에 모델 동작을 더 잘 맞추기 위해 사용됩니다.",
        "role": "기존 모델의 가중치를 추가 학습으로 조정합니다.",
        "wrong_points": [
            "fine-tuning은 외부 문서를 검색해 답변에 붙이는 방식만 의미합니다.",
            "fine-tuning은 데이터베이스에서 유사 문서를 찾는 검색 설정입니다.",
            "fine-tuning은 모델 응답의 무작위성만 조절하는 값입니다.",
            "fine-tuning은 서버의 timeout 비율을 표시하는 지표입니다.",
        ],
        "compare": {
            "target": "RAG",
            "point": "fine-tuning은 모델을 추가 학습하고, RAG는 외부 문서를 검색해 답변 생성에 활용합니다.",
        },
        "term_role": "fine-tuning은 모델을 특정 작업에 맞게 추가 학습하는 역할을 합니다.",
    },
    "mcp": {
        "aliases": ["mcp", "MCP", "model context protocol", "모델 컨텍스트 프로토콜"],
        "normalized_topic": "MCP 기본 개념",
        "concepts": ["MCP", "tool connection", "context protocol"],
        "definition": "MCP는 AI 애플리케이션이 외부 도구, 데이터 소스, 시스템과 연결될 수 있도록 돕는 표준 프로토콜입니다.",
        "purpose": "모델이 필요한 외부 context와 도구를 일관된 방식으로 사용할 수 있게 하기 위해 사용됩니다.",
        "role": "AI 애플리케이션과 외부 도구 또는 데이터 소스 사이의 연결 방식을 표준화합니다.",
        "wrong_points": [
            "MCP는 딥러닝 모델의 dropout 비율을 정하는 학습 기법입니다.",
            "MCP는 SQL 테이블의 기본키를 자동 생성하는 명령입니다.",
            "MCP는 LLM의 모든 환각을 자동으로 제거하는 모델입니다.",
            "MCP는 이미지 분류 전용 CNN 구조를 의미합니다.",
        ],
        "compare": {
            "target": "A2A Protocol",
            "point": "MCP는 모델과 도구·데이터 연결에 초점이 있고, A2A Protocol은 에이전트 간 상호작용에 초점이 있습니다.",
        },
        "term_role": "MCP는 AI 애플리케이션이 외부 도구와 데이터를 연결하는 역할을 합니다.",
    },
    "a2a_protocol": {
        "aliases": ["a2a", "A2A", "A2A Protocol", "agent to agent", "agent2agent"],
        "normalized_topic": "A2A Protocol 기본 개념",
        "concepts": ["A2A Protocol", "agent communication", "agent interoperability"],
        "definition": "A2A Protocol은 서로 다른 AI agent가 작업과 정보를 주고받도록 돕는 agent 간 통신 프로토콜입니다.",
        "purpose": "여러 agent가 각자의 기능을 유지하면서 협업할 수 있게 하기 위해 사용됩니다.",
        "role": "agent 사이의 요청, 응답, 작업 위임 흐름을 연결합니다.",
        "wrong_points": [
            "A2A Protocol은 신경망의 은닉층 개수를 정하는 학습 파라미터입니다.",
            "A2A Protocol은 문서를 embedding으로 변환하는 수식입니다.",
            "A2A Protocol은 데이터베이스 인덱스를 생성하는 SQL 문법입니다.",
            "A2A Protocol은 모델의 validation loss를 직접 낮추는 정규화 기법입니다.",
        ],
        "compare": {
            "target": "MCP",
            "point": "A2A Protocol은 agent 간 통신에 초점이 있고, MCP는 모델과 외부 도구·데이터 연결에 초점이 있습니다.",
        },
        "term_role": "A2A Protocol은 여러 AI agent가 서로 작업을 주고받게 하는 역할을 합니다.",
    },
    "agent": {
        "aliases": ["agent", "AI agent", "에이전트", "AI 에이전트"],
        "normalized_topic": "AI Agent 기본 개념",
        "concepts": ["AI agent", "tool use", "planning"],
        "definition": "AI Agent는 목표를 수행하기 위해 판단, 도구 사용, 단계적 실행을 조합하는 AI 시스템입니다.",
        "purpose": "단순 답변을 넘어 여러 단계의 작업을 수행하기 위해 사용됩니다.",
        "role": "목표를 해석하고 필요한 작업이나 도구 호출을 선택합니다.",
        "wrong_points": [
            "AI Agent는 항상 단일 문장 답변만 생성하는 정적 문서입니다.",
            "AI Agent는 데이터베이스의 외래키 관계만 의미합니다.",
            "AI Agent는 GPU 메모리를 자동으로 늘리는 하드웨어입니다.",
            "AI Agent는 모델 평가 지표 중 accuracy와 같은 의미입니다.",
        ],
        "compare": {
            "target": "LLM",
            "point": "LLM은 자연어 생성 모델이고, AI Agent는 LLM과 도구 사용을 조합해 작업을 수행하는 구조입니다.",
        },
        "term_role": "AI Agent는 목표 달성을 위해 판단과 도구 사용을 조합하는 역할을 합니다.",
    },
    "langchain": {
        "aliases": [
            "langchain",
            "LangChain",
            "랭체인",
            "lang chain",
        ],
        "normalized_topic": "LangChain 기본 개념",
        "concepts": ["LangChain", "LLM application", "chain", "tool", "memory"],
        "definition": "LangChain은 LLM 애플리케이션에서 프롬프트, 모델 호출, 도구 사용, 외부 데이터 연결을 구성하는 데 사용하는 프레임워크입니다.",
        "purpose": "LLM 기반 기능을 여러 단계의 처리 흐름으로 연결하고 재사용하기 위해 사용됩니다.",
        "role": "프롬프트, LLM, 도구, 검색, 메모리 같은 구성 요소를 애플리케이션 흐름으로 연결합니다.",
        "wrong_points": [
            "LangChain은 CNN 이미지 분류를 위한 신경망 구조입니다.",
            "LangChain은 SQL 테이블의 기본키를 자동 생성하는 명령입니다.",
            "LangChain은 LLM의 temperature 값을 의미합니다.",
            "LangChain은 모델 학습 데이터의 라벨을 삭제하는 전처리입니다.",
        ],
        "compare": {
            "target": "단일 LLM 호출",
            "point": "LangChain은 여러 구성 요소를 연결한 LLM 애플리케이션 흐름이고, 단일 LLM 호출은 한 번의 요청과 응답에 가깝습니다.",
        },
        "term_role": "LangChain은 LLM 애플리케이션의 여러 구성 요소를 연결하는 역할을 합니다.",
    },
    "langgraph": {
        "aliases": [
            "langgraph",
            "LangGraph",
            "랭그래프",
            "lang graph",
            "lnaggraph",
            "LNAGGRAPH",
        ],
        "normalized_topic": "LangGraph 기본 개념",
        "concepts": ["LangGraph", "state", "node", "edge", "workflow"],
        "definition": "LangGraph는 LLM 애플리케이션에서 상태 기반 workflow를 그래프 형태로 구성하는 데 사용하는 도구입니다.",
        "purpose": "여러 단계의 LLM 호출, 도구 호출, 조건 분기, 재시도 흐름을 구조화하기 위해 사용됩니다.",
        "role": "노드와 엣지를 통해 AI workflow의 실행 순서와 상태 변화를 관리합니다.",
        "wrong_points": [
            "LangGraph는 CNN 이미지 분류를 위한 신경망 구조입니다.",
            "LangGraph는 SQL 테이블의 기본키를 자동 생성하는 명령입니다.",
            "LangGraph는 LLM의 temperature 값을 의미합니다.",
            "LangGraph는 문서를 embedding으로 변환하는 벡터 모델 자체입니다.",
        ],
        "compare": {
            "target": "LangChain",
            "point": "LangGraph는 상태와 분기가 있는 그래프형 workflow에 강점이 있고, LangChain은 LLM 구성 요소 연결에 넓게 사용됩니다.",
        },
        "term_role": "LangGraph는 AI workflow의 단계와 상태 전이를 구성하는 역할을 합니다.",
    },
    "pretrained_model": {
        "aliases": [
            "pretrained",
            "pre-trained",
            "pretrained model",
            "pretrain",
            "pre-training",
            "사전학습",
            "사전 학습",
            "사전학습 모델",
            "프리트레인",
        ],
        "normalized_topic": "Pretrained Model 기본 개념",
        "concepts": ["pretrained model", "pre-training", "fine-tuning", "transfer learning"],
        "definition": "Pretrained model은 대규모 데이터로 미리 학습된 모델입니다.",
        "purpose": "새 작업에서 학습 효율을 높이고 적은 데이터로도 성능을 확보하기 위해 사용됩니다.",
        "role": "기존에 학습한 표현을 새로운 작업의 출발점으로 제공합니다.",
        "wrong_points": [
            "Pretrained model은 학습되지 않은 빈 모델을 의미합니다.",
            "Pretrained model은 외부 문서를 검색해 답변에 붙이는 RAG 방식만 의미합니다.",
            "Pretrained model은 LLM의 temperature 값을 조정하는 설정입니다.",
            "Pretrained model은 SQL 쿼리의 실행 순서를 정하는 명령입니다.",
        ],
        "compare": {
            "target": "fine-tuning",
            "point": "Pretrained model은 미리 학습된 모델 자체이고, fine-tuning은 그 모델을 특정 작업에 맞게 추가 학습하는 과정입니다.",
        },
        "term_role": "Pretrained model은 새로운 작업에 활용할 수 있는 사전학습된 출발점 역할을 합니다.",
    },
    "tokenizer": {
        "aliases": [
            "tokenizer",
            "tokenization",
            "토크나이저",
            "토큰화",
            "token",
            "토큰",
        ],
        "normalized_topic": "Tokenizer 기본 개념",
        "concepts": ["tokenizer", "token", "text preprocessing"],
        "definition": "Tokenizer는 텍스트를 모델이 처리할 수 있는 token 단위로 나누는 도구입니다.",
        "purpose": "자연어 문장을 모델 입력 형식으로 변환하기 위해 사용됩니다.",
        "role": "문장을 단어, 부분 단어, 기호 같은 token 단위로 분리합니다.",
        "wrong_points": [
            "Tokenizer는 모델의 정답률을 계산하는 평가 지표입니다.",
            "Tokenizer는 벡터 DB에서 문서를 검색하는 랭킹 알고리즘입니다.",
            "Tokenizer는 모델 API의 timeout 비율을 의미합니다.",
            "Tokenizer는 SQL 인덱스를 생성하는 데이터베이스 명령입니다.",
        ],
        "compare": {
            "target": "embedding",
            "point": "Tokenizer는 텍스트를 token으로 나누고, embedding은 token이나 문장을 숫자 벡터로 표현합니다.",
        },
        "term_role": "Tokenizer는 텍스트를 모델 입력 단위로 나누는 역할을 합니다.",
    },
    "inference": {
        "aliases": [
            "inference",
            "추론",
            "모델 추론",
            "llm inference",
        ],
        "normalized_topic": "Inference 기본 개념",
        "concepts": ["inference", "model prediction", "serving"],
        "definition": "Inference는 학습된 모델이 입력을 받아 예측이나 응답을 생성하는 과정입니다.",
        "purpose": "학습된 모델을 실제 요청에 적용해 결과를 얻기 위해 사용됩니다.",
        "role": "사용자 입력이나 데이터에 대해 모델의 출력 결과를 생성합니다.",
        "wrong_points": [
            "Inference는 모델을 처음부터 학습시키는 과정만 의미합니다.",
            "Inference는 SQL 테이블의 외래키를 설정하는 명령입니다.",
            "Inference는 문서를 token 단위로 나누는 전처리만 의미합니다.",
            "Inference는 LLM의 system prompt를 저장하는 데이터베이스입니다.",
        ],
        "compare": {
            "target": "training",
            "point": "Training은 모델이 데이터를 학습하는 과정이고, inference는 학습된 모델로 결과를 생성하는 과정입니다.",
        },
        "term_role": "Inference는 학습된 모델을 사용해 예측이나 응답을 생성하는 역할을 합니다.",
    },
    "tool_calling": {
        "aliases": ["tool calling", "tool_calling", "도구 호출", "function calling", "함수 호출"],
        "normalized_topic": "Tool Calling 기본 개념",
        "concepts": ["tool calling", "function calling", "external tool"],
        "definition": "tool calling은 LLM이 필요한 작업을 수행하기 위해 외부 함수나 도구 호출을 선택하는 방식입니다.",
        "purpose": "계산, 검색, API 호출처럼 모델 내부 생성만으로 부족한 작업을 처리하기 위해 사용됩니다.",
        "role": "모델 응답 과정에서 외부 기능을 호출하도록 연결합니다.",
        "wrong_points": [
            "tool calling은 모델이 외부 기능 없이 항상 답변만 생성하는 방식입니다.",
            "tool calling은 학습 데이터의 label을 자동으로 삭제합니다.",
            "tool calling은 validation loss를 계산하는 손실 함수입니다.",
            "tool calling은 관계형 데이터베이스의 조인 조건입니다.",
        ],
        "compare": {
            "target": "일반 프롬프트 응답",
            "point": "일반 응답은 텍스트 생성에 그치지만, tool calling은 외부 함수나 API 실행과 연결될 수 있습니다.",
        },
        "term_role": "tool calling은 LLM이 외부 도구를 호출하게 하는 역할을 합니다.",
    },
    "supervised_learning": {
        "aliases": ["supervised learning", "지도학습", "지도 학습"],
        "normalized_topic": "지도학습 기본 개념",
        "concepts": ["supervised learning", "label", "training data"],
        "definition": "지도학습은 정답 라벨이 있는 데이터를 사용해 입력과 출력의 관계를 학습하는 방법입니다.",
        "purpose": "분류나 회귀처럼 정답이 있는 예측 문제를 해결하기 위해 사용됩니다.",
        "role": "라벨이 있는 학습 데이터로 예측 모델을 만듭니다.",
        "wrong_points": [
            "지도학습은 정답 라벨이 전혀 없는 데이터만 사용합니다.",
            "지도학습은 검색 결과 순위를 재정렬하는 RAG 기법입니다.",
            "지도학습은 LLM의 응답 말투만 바꾸는 프롬프트입니다.",
            "지도학습은 운영 서버의 latency를 측정하는 지표입니다.",
        ],
        "compare": {
            "target": "비지도학습",
            "point": "지도학습은 정답 라벨을 사용하고, 비지도학습은 라벨 없이 데이터 구조나 패턴을 찾습니다.",
        },
        "term_role": "지도학습은 라벨 데이터로 예측 모델을 학습하는 역할을 합니다.",
    },
    "unsupervised_learning": {
        "aliases": ["unsupervised learning", "비지도학습", "비지도 학습"],
        "normalized_topic": "비지도학습 기본 개념",
        "concepts": ["unsupervised learning", "clustering", "pattern"],
        "definition": "비지도학습은 정답 라벨 없이 데이터의 구조나 패턴을 찾는 학습 방법입니다.",
        "purpose": "군집화, 차원 축소, 패턴 탐색 등에 사용됩니다.",
        "role": "라벨 없이 데이터 안의 유사한 구조를 찾아냅니다.",
        "wrong_points": [
            "비지도학습은 반드시 정답 라벨이 있어야만 동작합니다.",
            "비지도학습은 LLM 응답의 출력 형식만 지정합니다.",
            "비지도학습은 벡터 DB의 category 필터와 같은 의미입니다.",
            "비지도학습은 API timeout을 줄이는 배포 전략입니다.",
        ],
        "compare": {
            "target": "지도학습",
            "point": "비지도학습은 라벨 없이 패턴을 찾고, 지도학습은 라벨을 사용해 예측 관계를 학습합니다.",
        },
        "term_role": "비지도학습은 라벨 없이 데이터 패턴을 찾는 역할을 합니다.",
    },
    "classification": {
        "aliases": ["classification", "분류", "분류 모델"],
        "normalized_topic": "분류 기본 개념",
        "concepts": ["classification", "class", "label"],
        "definition": "분류는 입력 데이터를 미리 정해진 클래스 중 하나로 예측하는 머신러닝 작업입니다.",
        "purpose": "스팸 여부, 이탈 여부, 불량 여부처럼 범주를 판단하기 위해 사용됩니다.",
        "role": "입력 데이터가 어떤 클래스에 속하는지 예측합니다.",
        "wrong_points": [
            "분류는 연속적인 숫자 값을 예측하는 작업만 의미합니다.",
            "분류는 문서를 chunk로 나누는 RAG 전처리입니다.",
            "분류는 LLM temperature를 낮추는 설정입니다.",
            "분류는 모델 배포 버전을 관리하는 절차입니다.",
        ],
        "compare": {
            "target": "회귀",
            "point": "분류는 범주를 예측하고, 회귀는 연속적인 숫자 값을 예측합니다.",
        },
        "term_role": "분류는 입력을 정해진 범주 중 하나로 예측하는 역할을 합니다.",
    },
    "regression": {
        "aliases": ["regression", "회귀", "회귀 모델"],
        "normalized_topic": "회귀 기본 개념",
        "concepts": ["regression", "continuous value", "prediction"],
        "definition": "회귀는 연속적인 숫자 값을 예측하는 머신러닝 작업입니다.",
        "purpose": "가격, 매출, 온도처럼 숫자로 표현되는 값을 예측하기 위해 사용됩니다.",
        "role": "입력 데이터를 바탕으로 연속적인 수치를 예측합니다.",
        "wrong_points": [
            "회귀는 데이터를 반드시 두 개의 클래스 중 하나로만 분류합니다.",
            "회귀는 검색 후보의 순서를 다시 평가하는 기법입니다.",
            "회귀는 모델 응답의 무작위성을 조절하는 설정입니다.",
            "회귀는 외부 도구를 호출하는 agent 프로토콜입니다.",
        ],
        "compare": {
            "target": "분류",
            "point": "회귀는 숫자 값을 예측하고, 분류는 정해진 범주를 예측합니다.",
        },
        "term_role": "회귀는 연속적인 값을 예측하는 역할을 합니다.",
    },
    "overfitting": {
        "aliases": ["overfitting", "과적합"],
        "normalized_topic": "과적합 기본 개념",
        "concepts": ["overfitting", "generalization", "validation"],
        "definition": "과적합은 모델이 학습 데이터에 지나치게 맞춰져 새로운 데이터에서 성능이 낮아지는 현상입니다.",
        "purpose": "모델의 일반화 성능 문제를 설명할 때 사용됩니다.",
        "role": "학습 성능과 검증 성능의 차이를 해석하는 기준이 됩니다.",
        "wrong_points": [
            "과적합은 모델이 학습 데이터를 전혀 학습하지 못한 상태입니다.",
            "과적합은 API 서버의 응답 시간이 증가하는 현상만 의미합니다.",
            "과적합은 문서를 embedding으로 바꾸는 과정입니다.",
            "과적합은 검색 범위를 metadata로 제한하는 방법입니다.",
        ],
        "compare": {
            "target": "과소적합",
            "point": "과적합은 학습 데이터에 지나치게 맞춘 상태이고, 과소적합은 데이터의 패턴을 충분히 학습하지 못한 상태입니다.",
        },
        "term_role": "과적합은 일반화 성능 저하를 설명하는 역할을 합니다.",
    },
    "train_test_split": {
        "aliases": ["train/test split", "train test split", "학습 테스트 분리", "데이터 분리"],
        "normalized_topic": "Train/Test Split 기본 개념",
        "concepts": ["train data", "test data", "generalization"],
        "definition": "train/test split은 데이터를 학습용과 평가용으로 나누는 절차입니다.",
        "purpose": "모델이 보지 않은 데이터에서 얼마나 잘 동작하는지 평가하기 위해 사용됩니다.",
        "role": "학습과 평가 데이터를 분리해 일반화 성능을 확인합니다.",
        "wrong_points": [
            "train/test split은 모든 데이터를 한 번에 학습에만 사용하는 절차입니다.",
            "train/test split은 LLM의 system prompt를 저장하는 방식입니다.",
            "train/test split은 검색 결과의 category를 제한하는 필터입니다.",
            "train/test split은 모델 API의 timeout 비율입니다.",
        ],
        "compare": {
            "target": "교차 검증",
            "point": "train/test split은 한 번 나누는 방식이고, 교차 검증은 여러 분할로 반복 평가합니다.",
        },
        "term_role": "train/test split은 학습 데이터와 평가 데이터를 분리하는 역할을 합니다.",
    },
    "data_leakage": {
        "aliases": ["data leakage", "데이터 누수", "target leakage", "타깃 누수"],
        "normalized_topic": "데이터 누수 기본 개념",
        "concepts": ["data leakage", "evaluation", "prediction time"],
        "definition": "데이터 누수는 예측 시점에 사용할 수 없는 정보가 학습이나 평가에 포함되는 문제입니다.",
        "purpose": "모델 평가가 실제보다 과도하게 좋게 나오는 원인을 설명할 때 사용됩니다.",
        "role": "평가 신뢰성을 떨어뜨리는 데이터 구성 문제를 나타냅니다.",
        "wrong_points": [
            "데이터 누수는 모델 성능 평가에 아무 영향을 주지 않습니다.",
            "데이터 누수는 벡터 DB의 저장 공간이 부족한 현상입니다.",
            "데이터 누수는 LLM의 응답 말투를 조절하는 설정입니다.",
            "데이터 누수는 GPU 메모리 사용량을 줄이는 학습 기법입니다.",
        ],
        "compare": {
            "target": "과적합",
            "point": "데이터 누수는 평가 데이터 구성 문제이고, 과적합은 학습 데이터에 지나치게 맞춰지는 모델 문제입니다.",
        },
        "term_role": "데이터 누수는 평가를 왜곡하는 잘못된 정보 포함 문제를 설명합니다.",
    },
    "accuracy": {
        "aliases": ["accuracy", "정확도"],
        "normalized_topic": "Accuracy 기본 개념",
        "concepts": ["accuracy", "metric", "classification"],
        "definition": "accuracy는 전체 예측 중 맞게 예측한 비율을 나타내는 평가 지표입니다.",
        "purpose": "분류 모델의 전체적인 정답 비율을 확인하기 위해 사용됩니다.",
        "role": "전체 샘플 기준으로 예측이 맞은 비율을 계산합니다.",
        "wrong_points": [
            "accuracy는 양성으로 예측한 것 중 실제 양성의 비율만 의미합니다.",
            "accuracy는 실제 양성 중 찾아낸 비율만 의미합니다.",
            "accuracy는 LLM 응답의 무작위성 설정입니다.",
            "accuracy는 검색 후보 문서 수를 의미합니다.",
        ],
        "compare": {
            "target": "recall",
            "point": "accuracy는 전체 정답 비율이고, recall은 실제 양성 중 모델이 찾아낸 비율입니다.",
        },
        "term_role": "accuracy는 전체 예측 중 맞은 비율을 나타내는 역할을 합니다.",
    },
    "precision": {
        "aliases": ["precision", "정밀도"],
        "normalized_topic": "Precision 기본 개념",
        "concepts": ["precision", "positive prediction", "metric"],
        "definition": "precision은 양성으로 예측한 것 중 실제 양성인 비율을 나타내는 지표입니다.",
        "purpose": "양성 예측의 정확성을 확인하기 위해 사용됩니다.",
        "role": "모델이 양성이라고 판단한 결과가 얼마나 정확한지 평가합니다.",
        "wrong_points": [
            "precision은 실제 양성 중 모델이 찾아낸 비율만 의미합니다.",
            "precision은 전체 데이터 중 정답을 맞힌 비율만 의미합니다.",
            "precision은 문서를 벡터로 변환하는 과정입니다.",
            "precision은 LLM의 context 길이를 의미합니다.",
        ],
        "compare": {
            "target": "recall",
            "point": "precision은 양성 예측의 정확성이고, recall은 실제 양성을 얼마나 찾아냈는지입니다.",
        },
        "term_role": "precision은 양성 예측이 얼마나 정확한지 평가하는 역할을 합니다.",
    },
    "recall": {
        "aliases": ["recall", "재현율"],
        "normalized_topic": "Recall 기본 개념",
        "concepts": ["recall", "positive class", "metric"],
        "definition": "recall은 실제 양성 중 모델이 양성으로 찾아낸 비율을 나타내는 지표입니다.",
        "purpose": "놓치면 안 되는 대상을 얼마나 잘 찾았는지 확인하기 위해 사용됩니다.",
        "role": "실제 양성 데이터를 모델이 얼마나 많이 탐지했는지 평가합니다.",
        "wrong_points": [
            "recall은 양성으로 예측한 것 중 실제 양성인 비율만 의미합니다.",
            "recall은 전체 예측 중 맞은 비율만 의미합니다.",
            "recall은 모델 응답의 말투를 정하는 system prompt입니다.",
            "recall은 RAG의 chunk 크기 설정입니다.",
        ],
        "compare": {
            "target": "precision",
            "point": "recall은 실제 양성을 찾는 비율이고, precision은 양성 예측의 정확성입니다.",
        },
        "term_role": "recall은 실제 양성을 얼마나 잘 찾아냈는지 평가하는 역할을 합니다.",
    },
    "neural_network": {
        "aliases": ["neural network", "신경망", "인공신경망"],
        "normalized_topic": "신경망 기본 개념",
        "concepts": ["neural network", "layer", "weight"],
        "definition": "신경망은 여러 노드와 층을 통해 입력 데이터를 변환하며 패턴을 학습하는 모델 구조입니다.",
        "purpose": "복잡한 데이터 패턴을 학습해 분류나 예측을 수행하기 위해 사용됩니다.",
        "role": "입력 특징을 여러 층에서 변환해 출력 결과를 만듭니다.",
        "wrong_points": [
            "신경망은 SQL 테이블을 조인하는 데이터베이스 명령입니다.",
            "신경망은 검색 결과의 category만 제한하는 필터입니다.",
            "신경망은 LLM 응답의 무작위성만 조절하는 값입니다.",
            "신경망은 모델 배포 후 timeout 비율만 나타내는 지표입니다.",
        ],
        "compare": {
            "target": "규칙 기반 모델",
            "point": "신경망은 데이터에서 패턴을 학습하고, 규칙 기반 모델은 사람이 정한 조건에 따라 동작합니다.",
        },
        "term_role": "신경망은 입력 데이터를 여러 층에서 변환해 패턴을 학습하는 역할을 합니다.",
    },
    "cnn": {
        "aliases": ["cnn", "CNN", "convolutional neural network", "합성곱 신경망"],
        "normalized_topic": "CNN 기본 개념",
        "concepts": ["CNN", "convolution", "image"],
        "definition": "CNN은 이미지처럼 격자 구조를 가진 데이터에서 지역적 특징을 학습하는 신경망 구조입니다.",
        "purpose": "이미지 분류, 객체 인식 같은 시각 데이터 처리에 자주 사용됩니다.",
        "role": "합성곱 연산으로 이미지의 지역 특징을 추출합니다.",
        "wrong_points": [
            "CNN은 문서 검색 결과를 재정렬하는 RAG 전용 모듈입니다.",
            "CNN은 LLM의 system prompt를 저장하는 방식입니다.",
            "CNN은 데이터베이스에서 SQL 인덱스를 생성하는 명령입니다.",
            "CNN은 모델 API의 latency를 측정하는 운영 지표입니다.",
        ],
        "compare": {
            "target": "일반 완전연결 신경망",
            "point": "CNN은 이미지의 지역 특징을 추출하는 데 강점이 있고, 완전연결 신경망은 모든 입력을 직접 연결해 처리합니다.",
        },
        "term_role": "CNN은 이미지의 지역적 특징을 추출하는 역할을 합니다.",
    },
    "epoch": {
        "aliases": ["epoch", "에폭"],
        "normalized_topic": "Epoch 기본 개념",
        "concepts": ["epoch", "training loop", "dataset"],
        "definition": "epoch는 전체 학습 데이터를 한 번 모두 학습에 사용한 단위를 의미합니다.",
        "purpose": "모델이 학습 데이터를 몇 번 반복해서 학습했는지 나타내기 위해 사용됩니다.",
        "role": "학습 반복 횟수를 표현하는 기준이 됩니다.",
        "wrong_points": [
            "epoch는 모델이 출력할 클래스의 개수를 의미합니다.",
            "epoch는 검색 결과의 similarity 점수를 의미합니다.",
            "epoch는 LLM 응답의 무작위성 설정입니다.",
            "epoch는 API timeout 비율을 나타내는 운영 지표입니다.",
        ],
        "compare": {
            "target": "batch size",
            "point": "epoch는 전체 데이터 반복 단위이고, batch size는 한 번에 학습하는 샘플 수입니다.",
        },
        "term_role": "epoch는 전체 학습 데이터 반복 횟수를 나타내는 역할을 합니다.",
    },
    "loss_function": {
        "aliases": ["loss function", "손실 함수", "loss"],
        "normalized_topic": "손실 함수 기본 개념",
        "concepts": ["loss function", "error", "training"],
        "definition": "손실 함수는 모델 예측과 실제 정답의 차이를 수치로 나타내는 함수입니다.",
        "purpose": "모델이 얼마나 틀렸는지 계산하고 학습 방향을 정하기 위해 사용됩니다.",
        "role": "예측 오차를 계산해 모델 가중치 업데이트의 기준을 제공합니다.",
        "wrong_points": [
            "손실 함수는 문서를 category별로 필터링하는 검색 조건입니다.",
            "손실 함수는 LLM이 외부 도구를 호출하는 프로토콜입니다.",
            "손실 함수는 서버 응답 시간이 증가한 비율입니다.",
            "손실 함수는 데이터베이스의 기본키를 설정하는 명령입니다.",
        ],
        "compare": {
            "target": "평가 지표",
            "point": "손실 함수는 학습 최적화에 사용되고, 평가 지표는 모델 성능을 해석하는 데 사용됩니다.",
        },
        "term_role": "손실 함수는 예측과 정답의 차이를 계산하는 역할을 합니다.",
    },
    "dropout": {
        "aliases": ["dropout", "드롭아웃"],
        "normalized_topic": "Dropout 기본 개념",
        "concepts": ["dropout", "regularization", "overfitting"],
        "definition": "dropout은 학습 중 일부 뉴런을 임의로 비활성화해 과적합을 줄이는 정규화 기법입니다.",
        "purpose": "모델이 특정 뉴런에 과도하게 의존하는 것을 줄이기 위해 사용됩니다.",
        "role": "과적합을 완화하고 일반화 성능을 높이는 데 도움을 줍니다.",
        "wrong_points": [
            "dropout은 테스트 데이터를 삭제하는 전처리 기법입니다.",
            "dropout은 RAG 검색 결과를 재정렬하는 방식입니다.",
            "dropout은 LLM의 최신 지식 여부를 보장하는 설정입니다.",
            "dropout은 모델 API의 timeout 로그를 의미합니다.",
        ],
        "compare": {
            "target": "data augmentation",
            "point": "dropout은 모델 내부 의존도를 줄이고, data augmentation은 학습 데이터 다양성을 늘립니다.",
        },
        "term_role": "dropout은 학습 중 일부 뉴런을 비활성화해 과적합을 줄이는 역할을 합니다.",
    },
    "transfer_learning": {
        "aliases": ["transfer learning", "전이학습", "fine-tuning"],
        "normalized_topic": "전이학습 기본 개념",
        "concepts": ["transfer learning", "pretrained model", "fine-tuning"],
        "definition": "전이학습은 이미 학습된 모델의 지식을 새로운 작업에 활용하는 방법입니다.",
        "purpose": "데이터가 적은 상황에서도 학습 효율과 성능을 높이기 위해 사용됩니다.",
        "role": "사전학습 모델의 특징 표현을 새로운 문제에 재사용합니다.",
        "wrong_points": [
            "전이학습은 외부 문서를 검색해 LLM 답변에 붙이는 방식만 의미합니다.",
            "전이학습은 데이터베이스에서 유사 문서를 찾는 검색 인덱스입니다.",
            "전이학습은 모델 응답의 무작위성만 조절하는 설정입니다.",
            "전이학습은 API 응답 시간을 측정하는 운영 지표입니다.",
        ],
        "compare": {
            "target": "처음부터 학습",
            "point": "전이학습은 사전학습 모델을 활용하고, 처음부터 학습은 모든 표현을 새 데이터로 새로 학습합니다.",
        },
        "term_role": "전이학습은 기존 모델의 학습된 표현을 새 작업에 활용하는 역할을 합니다.",
    },
    "model_serving": {
        "aliases": ["model serving", "모델 서빙", "serving"],
        "normalized_topic": "모델 서빙 기본 개념",
        "concepts": ["model serving", "inference", "API"],
        "definition": "모델 서빙은 학습된 모델을 API나 서비스 형태로 배포해 예측 요청을 처리하는 과정입니다.",
        "purpose": "사용자나 시스템이 모델 예측 결과를 실제 서비스에서 사용할 수 있게 하기 위해 필요합니다.",
        "role": "학습된 모델을 운영 환경에서 호출 가능한 형태로 제공합니다.",
        "wrong_points": [
            "모델 서빙은 모델 학습 데이터의 라벨을 수동으로 삭제하는 과정입니다.",
            "모델 서빙은 LLM 프롬프트의 말투만 수정하는 작업입니다.",
            "모델 서빙은 문서를 embedding으로 변환하는 수식입니다.",
            "모델 서빙은 SQL 쿼리의 GROUP BY 조건입니다.",
        ],
        "compare": {
            "target": "모델 학습",
            "point": "모델 학습은 모델을 만드는 과정이고, 모델 서빙은 학습된 모델을 운영 환경에서 제공하는 과정입니다.",
        },
        "term_role": "모델 서빙은 학습된 모델을 서비스에서 사용할 수 있게 제공하는 역할을 합니다.",
    },
    "latency": {
        "aliases": ["latency", "지연 시간", "응답 시간"],
        "normalized_topic": "Latency 기본 개념",
        "concepts": ["latency", "response time", "serving"],
        "definition": "latency는 요청을 보낸 뒤 응답을 받기까지 걸리는 시간을 의미합니다.",
        "purpose": "서비스 응답 속도와 사용자 경험을 평가하기 위해 사용됩니다.",
        "role": "모델 API나 서비스의 응답 지연 정도를 나타냅니다.",
        "wrong_points": [
            "latency는 모델의 정답률과 완전히 같은 의미입니다.",
            "latency는 실제 양성 중 찾아낸 비율을 의미합니다.",
            "latency는 문서를 벡터로 변환하는 과정입니다.",
            "latency는 LLM이 외부 지식을 항상 최신으로 아는 기능입니다.",
        ],
        "compare": {
            "target": "accuracy",
            "point": "latency는 응답 시간 지표이고, accuracy는 예측이 맞은 비율을 나타내는 성능 지표입니다.",
        },
        "term_role": "latency는 서비스 응답 지연 시간을 나타내는 역할을 합니다.",
    },
    "drift": {
        "aliases": ["drift", "data drift", "데이터 드리프트"],
        "normalized_topic": "Data Drift 기본 개념",
        "concepts": ["data drift", "monitoring", "distribution"],
        "definition": "data drift는 학습 시점의 데이터 분포와 운영 시점의 데이터 분포가 달라지는 현상입니다.",
        "purpose": "운영 중 모델 성능 저하 원인을 모니터링하기 위해 사용됩니다.",
        "role": "운영 데이터가 학습 데이터와 달라졌는지 확인하는 기준이 됩니다.",
        "wrong_points": [
            "data drift는 서버를 재부팅하면 항상 해결되는 네트워크 오류입니다.",
            "data drift는 LLM 응답의 문장 길이를 제한하는 설정입니다.",
            "data drift는 문서를 chunk로 나누는 전처리 방법입니다.",
            "data drift는 SQL 테이블의 기본키를 의미합니다.",
        ],
        "compare": {
            "target": "latency",
            "point": "data drift는 데이터 분포 변화이고, latency는 응답 지연 시간입니다.",
        },
        "term_role": "data drift는 운영 데이터 분포 변화를 감지하는 역할을 합니다.",
    },
    "monitoring": {
        "aliases": ["monitoring", "모니터링", "모델 모니터링"],
        "normalized_topic": "모델 모니터링 기본 개념",
        "concepts": ["monitoring", "metric", "operation"],
        "definition": "모델 모니터링은 배포된 모델의 성능, 오류율, 지연 시간, 데이터 변화를 지속적으로 확인하는 과정입니다.",
        "purpose": "운영 중 품질 저하나 장애를 빠르게 발견하기 위해 사용됩니다.",
        "role": "모델 운영 상태와 품질 변화를 추적합니다.",
        "wrong_points": [
            "모델 모니터링은 모델을 한 번 학습한 뒤 절대 확인하지 않는 절차입니다.",
            "모델 모니터링은 프롬프트 문장만 예쁘게 바꾸는 작업입니다.",
            "모델 모니터링은 문서 유사도를 계산하는 embedding 자체입니다.",
            "모델 모니터링은 학습 데이터를 무조건 삭제하는 보안 기능입니다.",
        ],
        "compare": {
            "target": "모델 학습",
            "point": "모델 학습은 모델을 만드는 과정이고, 모니터링은 배포 후 상태를 지속적으로 확인하는 과정입니다.",
        },
        "term_role": "모델 모니터링은 배포된 모델의 품질과 운영 상태를 추적하는 역할을 합니다.",
    },
}

AI_BEGINNER_TOPIC_KEYS = list(AI_BEGINNER_TOPIC_PRESETS.keys())

AI_BEGINNER_COMPARE_PRESETS: Dict[str, Dict[str, Any]] = {
    "gpt_vs_bert": {
        "aliases": [
            "gpt와 bert",
            "gpt랑 bert",
            "gpt bert",
            "gpt와 bert 차이",
            "gpt랑bert차이",
            "gpt bert 차이",
            "gpt와 bert의 차이",
            "bert와 gpt",
            "bert gpt",
        ],
        "normalized_topic": "GPT와 BERT 기본 차이",
        "concepts": [
            "GPT",
            "BERT",
            "text generation",
            "bidirectional context",
            "language model",
        ],
        "concept_a": "GPT",
        "concept_b": "BERT",
        "correct_points": [
            "GPT는 주로 문맥을 이어 텍스트를 생성하는 데 강점이 있습니다.",
            "BERT는 문장의 앞뒤 문맥을 함께 반영해 텍스트 의미를 이해하는 데 강점이 있습니다.",
            "GPT는 생성형 작업에 자주 사용되고, BERT는 분류나 의미 이해 작업에 자주 사용됩니다.",
        ],
        "wrong_points": [
            "GPT와 BERT는 완전히 동일한 구조와 목적을 가진 모델입니다.",
            "GPT는 텍스트 생성과 관련이 없고 저장된 문서만 검색합니다.",
            "BERT는 앞뒤 문맥을 함께 반영하지 않고 다음 토큰 생성만 수행합니다.",
            "BERT는 텍스트 이해나 분류 작업에 사용할 수 없습니다.",
            "GPT와 BERT는 모두 외부 문서를 검색해야만 동작하는 RAG 방식입니다.",
        ],
    },
    "mcp_vs_a2a": {
        "aliases": [
            "mcp와 a2a",
            "mcp랑 a2a",
            "mcp a2a",
            "mcp와 a2a protocol",
            "mcp랑 a2a protocol",
            "mcp와 a2a protocol의 차이",
            "mcp a2a protocol 차이",
            "a2a와 mcp",
            "a2a mcp",
        ],
        "normalized_topic": "MCP와 A2A Protocol 기본 차이",
        "concepts": [
            "MCP",
            "A2A Protocol",
            "tool connection",
            "agent communication",
            "agent interoperability",
        ],
        "concept_a": "MCP",
        "concept_b": "A2A Protocol",
        "correct_points": [
            "MCP는 AI 애플리케이션이 외부 도구와 데이터 소스에 연결되는 방식에 초점이 있습니다.",
            "A2A Protocol은 서로 다른 AI agent가 작업과 정보를 주고받는 방식에 초점이 있습니다.",
            "MCP는 도구·데이터 연결을, A2A Protocol은 agent 간 상호작용을 다루는 개념입니다.",
        ],
        "wrong_points": [
            "MCP와 A2A Protocol은 완전히 같은 개념입니다.",
            "MCP는 agent 간 작업 위임만을 위한 프로토콜이고 외부 도구 연결과는 관련이 없습니다.",
            "A2A Protocol은 모델과 데이터베이스 연결만을 위한 프로토콜입니다.",
            "MCP와 A2A Protocol은 모두 딥러닝 학습률을 조정하는 기법입니다.",
            "A2A Protocol은 agent 간 통신과 관련이 없습니다.",
        ],
    },
    "rag_vs_fine_tuning": {
        "aliases": [
            "rag와 fine-tuning",
            "rag와 fine tuning",
            "rag랑 fine-tuning",
            "rag fine-tuning",
            "rag와 파인튜닝",
            "rag 파인튜닝",
            "rag 파인튜닝 차이",
            "rag와 fine-tuning 차이",
            "rag와 fine tuning 차이",
            "fine-tuning과 rag",
            "파인튜닝과 rag",
        ],
        "normalized_topic": "RAG와 Fine-tuning 기본 차이",
        "concepts": [
            "RAG",
            "fine-tuning",
            "retrieval",
            "model training",
            "external knowledge",
        ],
        "concept_a": "RAG",
        "concept_b": "Fine-tuning",
        "correct_points": [
            "RAG는 외부 문서를 검색해 답변 생성에 활용하는 방식입니다.",
            "Fine-tuning은 기존 모델을 특정 데이터나 작업에 맞게 추가 학습하는 방식입니다.",
            "RAG는 검색 근거 활용에 가깝고, fine-tuning은 모델 동작 자체를 조정하는 방식에 가깝습니다.",
        ],
        "wrong_points": [
            "RAG와 fine-tuning은 모두 모델 파라미터를 매번 직접 수정하는 같은 방식입니다.",
            "RAG는 외부 문서 검색과 관련이 없고 모델 추가 학습만 의미합니다.",
            "Fine-tuning은 모델을 학습하지 않고 검색 결과만 붙이는 방식입니다.",
            "RAG와 fine-tuning은 모두 SQL 인덱스를 생성하는 데이터베이스 기법입니다.",
            "Fine-tuning은 LLM 응답의 temperature만 조절하는 설정입니다.",
        ],
    },
    "embedding_vs_vector_db": {
        "aliases": [
            "embedding과 vector db",
            "embedding vector db",
            "임베딩과 벡터 db",
            "임베딩 벡터 db",
            "embedding과 vector database",
            "임베딩과 벡터 데이터베이스",
            "embedding과 vector db 차이",
            "임베딩과 벡터 db 차이",
        ],
        "normalized_topic": "Embedding과 Vector DB 기본 차이",
        "concepts": [
            "embedding",
            "Vector DB",
            "vector representation",
            "similarity search",
        ],
        "concept_a": "Embedding",
        "concept_b": "Vector DB",
        "correct_points": [
            "Embedding은 텍스트나 데이터를 의미를 담은 숫자 벡터로 표현하는 방식입니다.",
            "Vector DB는 embedding 벡터를 저장하고 유사도 검색을 수행하는 저장소입니다.",
            "Embedding은 표현 방식에 가깝고, Vector DB는 그 표현을 저장하고 검색하는 시스템에 가깝습니다.",
        ],
        "wrong_points": [
            "Embedding과 Vector DB는 완전히 같은 개념입니다.",
            "Embedding은 벡터를 저장하고 검색하는 데이터베이스 자체를 의미합니다.",
            "Vector DB는 텍스트를 벡터로 변환하는 모델 자체만 의미합니다.",
            "Embedding과 Vector DB는 모두 모델의 dropout 비율을 조정하는 기법입니다.",
            "Vector DB는 자연어 답변을 직접 생성하는 언어 모델입니다.",
        ],
    },
    "metadata_filter_vs_reranker": {
        "aliases": [
            "metadata filter와 reranker",
            "metadata filter reranker",
            "메타데이터 필터와 리랭커",
            "메타데이터 필터 리랭커",
            "metadata와 reranker 차이",
            "메타데이터 필터와 reranker 차이",
        ],
        "normalized_topic": "Metadata Filter와 Reranker 기본 차이",
        "concepts": [
            "metadata filter",
            "reranker",
            "retrieval",
            "ranking",
        ],
        "concept_a": "Metadata Filter",
        "concept_b": "Reranker",
        "correct_points": [
            "Metadata filter는 문서 속성 조건으로 검색 범위를 제한하는 방식입니다.",
            "Reranker는 1차 검색된 후보의 관련도를 다시 평가해 순서를 조정하는 방식입니다.",
            "Metadata filter는 검색 전 범위 제한에 가깝고, reranker는 검색 후 순위 조정에 가깝습니다.",
        ],
        "wrong_points": [
            "Metadata filter와 reranker는 완전히 같은 기능입니다.",
            "Metadata filter는 검색 후보의 순서만 다시 평가하는 기능입니다.",
            "Reranker는 문서 category 조건으로 검색 범위를 제한하는 기능입니다.",
            "Metadata filter와 reranker는 모두 LLM의 temperature를 조절하는 설정입니다.",
            "Reranker는 문서를 embedding으로 변환하는 모델 자체를 의미합니다.",
        ],
    },
    "vector_search_vs_keyword_search": {
        "aliases": [
            "vector search와 keyword search",
            "vector search keyword search",
            "벡터 검색과 키워드 검색",
            "벡터 검색 키워드 검색",
            "vector와 keyword 검색 차이",
            "벡터 검색과 keyword search 차이",
        ],
        "normalized_topic": "Vector Search와 Keyword Search 기본 차이",
        "concepts": [
            "vector search",
            "keyword search",
            "semantic similarity",
            "exact match",
        ],
        "concept_a": "Vector Search",
        "concept_b": "Keyword Search",
        "correct_points": [
            "Vector search는 embedding 기반 의미 유사도를 활용해 관련 문서를 찾습니다.",
            "Keyword search는 사용자가 입력한 단어와 문서의 단어 일치를 활용해 검색합니다.",
            "Vector search는 의미가 비슷한 표현에 강하고, keyword search는 정확한 용어 일치에 강합니다.",
        ],
        "wrong_points": [
            "Vector search와 keyword search는 완전히 같은 검색 방식입니다.",
            "Vector search는 단어가 정확히 일치하는 문서만 찾는 방식입니다.",
            "Keyword search는 embedding 의미 유사도만 사용하고 단어 일치는 보지 않습니다.",
            "Vector search와 keyword search는 모두 모델 가중치를 추가 학습하는 방식입니다.",
            "Keyword search는 LLM 응답의 무작위성을 조절하는 설정입니다.",
        ],
    },
    "pretrained_vs_fine_tuning": {
        "aliases": [
            "pretrained와 fine-tuning",
            "pretrained fine-tuning",
            "pretrained와 fine tuning",
            "pretrained와 파인튜닝",
            "pretrain과 fine-tuning",
            "pretrain fine-tuning",
            "pretrain과 파인튜닝",
            "사전학습과 파인튜닝",
            "사전 학습과 파인튜닝",
            "사전학습 모델과 fine-tuning",
            "pretrained와 fine-tuning 차이",
        ],
        "normalized_topic": "Pretrained Model과 Fine-tuning 기본 차이",
        "concepts": [
            "Pretrained Model",
            "Fine-tuning",
            "transfer learning",
        ],
        "concept_a": "Pretrained Model",
        "concept_b": "Fine-tuning",
        "correct_points": [
            "Pretrained model은 미리 학습된 모델이고, fine-tuning은 그 모델을 특정 작업에 맞게 추가 학습하는 과정입니다.",
            "Pretrained model은 시작점에 가깝고, fine-tuning은 작업에 맞게 조정하는 학습 과정에 가깝습니다.",
            "두 개념은 전이학습 흐름에서 함께 쓰일 수 있지만 같은 의미는 아닙니다.",
        ],
        "wrong_points": [
            "Pretrained model과 fine-tuning은 완전히 같은 개념입니다.",
            "Pretrained model은 추가 학습 과정이고, fine-tuning은 미리 학습된 모델 자체입니다.",
            "Pretrained model과 fine-tuning은 모두 외부 문서를 검색하는 RAG 방식입니다.",
            "Fine-tuning은 모델을 학습하지 않고 temperature만 조절하는 설정입니다.",
            "Pretrained model은 SQL 인덱스를 생성하는 데이터베이스 기능입니다.",
        ],
    },
    "langchain_vs_langgraph": {
        "aliases": [
            "langchain과 langgraph",
            "langchain langgraph",
            "langchain과 langgraph 차이",
            "langchain랑 langgraph",
            "랭체인과 랭그래프",
            "랭체인 랭그래프 차이",
        ],
        "normalized_topic": "LangChain과 LangGraph 기본 차이",
        "concepts": [
            "LangChain",
            "LangGraph",
            "LLM application",
            "workflow",
            "state graph",
        ],
        "concept_a": "LangChain",
        "concept_b": "LangGraph",
        "correct_points": [
            "LangChain은 LLM 애플리케이션 구성 요소 연결에 넓게 사용되고, LangGraph는 상태 기반 그래프 workflow 구성에 강점이 있습니다.",
            "LangGraph는 node, edge, state를 활용한 실행 흐름에 초점이 있고, LangChain은 prompt, model, tool, retriever 연결에 넓게 사용됩니다.",
            "두 도구는 함께 사용할 수 있지만 역할과 초점이 완전히 같지는 않습니다.",
        ],
        "wrong_points": [
            "LangChain과 LangGraph는 완전히 같은 개념입니다.",
            "LangChain은 CNN 이미지 분류 모델이고, LangGraph는 SQL 인덱스 생성 명령입니다.",
            "LangGraph는 단일 프롬프트 문자열만 저장하고 workflow와는 관련이 없습니다.",
            "LangChain과 LangGraph는 모두 LLM의 temperature만 조절하는 설정입니다.",
            "LangChain은 agent workflow와 관련이 없고 LangGraph만 자연어 생성을 수행합니다.",
        ],
    },
    "precision_vs_recall": {
        "aliases": [
            "precision과 recall",
            "precision recall",
            "정밀도와 재현율",
            "정밀도 재현율",
            "precision과 recall 차이",
            "정밀도와 재현율 차이",
        ],
        "normalized_topic": "Precision과 Recall 기본 차이",
        "concepts": [
            "precision",
            "recall",
            "positive prediction",
            "actual positive",
        ],
        "concept_a": "Precision",
        "concept_b": "Recall",
        "correct_points": [
            "Precision은 양성으로 예측한 것 중 실제 양성인 비율입니다.",
            "Recall은 실제 양성 중 모델이 양성으로 찾아낸 비율입니다.",
            "Precision은 양성 예측의 정확성에 가깝고, recall은 실제 양성을 놓치지 않는 정도에 가깝습니다.",
        ],
        "wrong_points": [
            "Precision과 recall은 완전히 같은 평가 지표입니다.",
            "Precision은 실제 양성 중 찾아낸 비율만 의미합니다.",
            "Recall은 양성으로 예측한 것 중 실제 양성인 비율만 의미합니다.",
            "Precision과 recall은 모두 LLM 응답의 무작위성을 조절하는 설정입니다.",
            "Recall은 검색된 문서 chunk 개수를 의미합니다.",
        ],
    },
    "accuracy_vs_f1_score": {
        "aliases": [
            "accuracy와 f1",
            "accuracy f1",
            "accuracy와 f1-score",
            "정확도와 f1",
            "정확도 f1 score",
            "accuracy와 f1 차이",
            "정확도와 f1 차이",
        ],
        "normalized_topic": "Accuracy와 F1-score 기본 차이",
        "concepts": [
            "accuracy",
            "F1-score",
            "precision",
            "recall",
            "classification metric",
        ],
        "concept_a": "Accuracy",
        "concept_b": "F1-score",
        "correct_points": [
            "Accuracy는 전체 예측 중 맞게 예측한 비율입니다.",
            "F1-score는 precision과 recall을 함께 고려한 조화 평균 지표입니다.",
            "Accuracy는 전체 정답 비율에 가깝고, F1-score는 precision과 recall의 균형에 가깝습니다.",
        ],
        "wrong_points": [
            "Accuracy와 F1-score는 완전히 같은 지표입니다.",
            "Accuracy는 precision과 recall의 조화 평균만 의미합니다.",
            "F1-score는 전체 예측 중 맞은 비율만 의미합니다.",
            "Accuracy와 F1-score는 모두 모델 API 응답 시간을 의미합니다.",
            "F1-score는 LLM의 context 길이를 조절하는 설정입니다.",
        ],
    },
    "classification_vs_regression": {
        "aliases": [
            "classification과 regression",
            "classification regression",
            "분류와 회귀",
            "분류 회귀",
            "분류와 회귀 차이",
            "classification과 regression 차이",
        ],
        "normalized_topic": "Classification과 Regression 기본 차이",
        "concepts": [
            "classification",
            "regression",
            "class prediction",
            "continuous value prediction",
        ],
        "concept_a": "Classification",
        "concept_b": "Regression",
        "correct_points": [
            "Classification은 입력 데이터를 정해진 범주 중 하나로 예측하는 작업입니다.",
            "Regression은 연속적인 숫자 값을 예측하는 작업입니다.",
            "Classification은 클래스 예측에 가깝고, regression은 수치 예측에 가깝습니다.",
        ],
        "wrong_points": [
            "Classification과 regression은 완전히 같은 예측 작업입니다.",
            "Classification은 연속적인 숫자 값만 예측하는 작업입니다.",
            "Regression은 미리 정해진 클래스 중 하나만 예측하는 작업입니다.",
            "Classification과 regression은 모두 RAG 검색 결과 재정렬 기법입니다.",
            "Regression은 LLM의 system prompt를 저장하는 방식입니다.",
        ],
    },
    "supervised_vs_unsupervised": {
        "aliases": [
            "supervised와 unsupervised",
            "supervised unsupervised",
            "지도학습과 비지도학습",
            "지도 학습과 비지도 학습",
            "지도학습 비지도학습 차이",
            "supervised learning과 unsupervised learning 차이",
        ],
        "normalized_topic": "지도학습과 비지도학습 기본 차이",
        "concepts": [
            "supervised learning",
            "unsupervised learning",
            "label",
            "pattern discovery",
        ],
        "concept_a": "지도학습",
        "concept_b": "비지도학습",
        "correct_points": [
            "지도학습은 정답 라벨이 있는 데이터를 사용해 모델을 학습합니다.",
            "비지도학습은 정답 라벨 없이 데이터의 구조나 패턴을 찾습니다.",
            "지도학습은 라벨 기반 예측에, 비지도학습은 패턴 탐색에 가깝습니다.",
        ],
        "wrong_points": [
            "지도학습과 비지도학습은 모두 정답 라벨이 반드시 필요합니다.",
            "지도학습은 라벨 없이 데이터 구조만 찾는 방식입니다.",
            "비지도학습은 정답 라벨이 있는 데이터로만 학습합니다.",
            "지도학습과 비지도학습은 모두 LLM 응답 형식을 정하는 프롬프트입니다.",
            "비지도학습은 검색 결과의 category만 제한하는 기능입니다.",
        ],
    },
    "overfitting_vs_underfitting": {
        "aliases": [
            "overfitting과 underfitting",
            "overfitting underfitting",
            "과적합과 과소적합",
            "과적합 과소적합",
            "과적합과 과소적합 차이",
        ],
        "normalized_topic": "과적합과 과소적합 기본 차이",
        "concepts": [
            "overfitting",
            "underfitting",
            "generalization",
            "model complexity",
        ],
        "concept_a": "과적합",
        "concept_b": "과소적합",
        "correct_points": [
            "과적합은 학습 데이터에 지나치게 맞춰져 새로운 데이터 성능이 낮아지는 상태입니다.",
            "과소적합은 데이터의 기본 패턴을 충분히 학습하지 못한 상태입니다.",
            "과적합은 학습 데이터에 과하게 맞춘 문제이고, 과소적합은 학습 자체가 부족한 문제에 가깝습니다.",
        ],
        "wrong_points": [
            "과적합과 과소적합은 완전히 같은 상태입니다.",
            "과적합은 데이터의 패턴을 거의 학습하지 못한 상태만 의미합니다.",
            "과소적합은 학습 데이터만 지나치게 외운 상태만 의미합니다.",
            "과적합과 과소적합은 모두 API latency를 나타내는 운영 지표입니다.",
            "과소적합은 검색 결과를 재정렬하는 RAG 기능입니다.",
        ],
    },
    "train_loss_vs_validation_loss": {
        "aliases": [
            "train loss와 validation loss",
            "train loss validation loss",
            "학습 손실과 검증 손실",
            "train loss와 validation loss 차이",
            "training loss와 validation loss",
        ],
        "normalized_topic": "Train Loss와 Validation Loss 기본 차이",
        "concepts": [
            "train loss",
            "validation loss",
            "training data",
            "validation data",
        ],
        "concept_a": "Train Loss",
        "concept_b": "Validation Loss",
        "correct_points": [
            "Train loss는 학습 데이터 기준으로 계산한 손실입니다.",
            "Validation loss는 검증 데이터 기준으로 계산한 손실입니다.",
            "Train loss와 validation loss를 함께 보면 모델의 일반화 상태를 점검할 수 있습니다.",
        ],
        "wrong_points": [
            "Train loss와 validation loss는 항상 완전히 같은 값이어야 합니다.",
            "Train loss는 검증 데이터 기준 손실만 의미합니다.",
            "Validation loss는 학습 데이터 기준 손실만 의미합니다.",
            "Train loss와 validation loss는 모두 LLM의 temperature 설정입니다.",
            "Validation loss는 벡터 DB의 검색 결과 개수를 의미합니다.",
        ],
    },
    "dropout_vs_regularization": {
        "aliases": [
            "dropout과 regularization",
            "dropout regularization",
            "드롭아웃과 정규화",
            "dropout과 regularization 차이",
            "드롭아웃 정규화 차이",
        ],
        "normalized_topic": "Dropout과 Regularization 기본 차이",
        "concepts": [
            "dropout",
            "regularization",
            "overfitting",
            "generalization",
        ],
        "concept_a": "Dropout",
        "concept_b": "Regularization",
        "correct_points": [
            "Dropout은 학습 중 일부 뉴런을 비활성화해 과적합을 줄이는 방법입니다.",
            "Regularization은 모델이 지나치게 복잡해지는 것을 줄여 일반화를 돕는 방법입니다.",
            "Dropout은 정규화 방법 중 하나로 볼 수 있으며, 둘 다 과적합 완화와 관련이 있습니다.",
        ],
        "wrong_points": [
            "Dropout과 regularization은 모두 테스트 데이터를 삭제하는 전처리입니다.",
            "Dropout은 validation loss를 저장하는 데이터베이스입니다.",
            "Regularization은 RAG 검색 결과의 category를 제한하는 기능입니다.",
            "Dropout과 regularization은 모두 LLM의 최신 지식 여부를 보장합니다.",
            "Regularization은 agent 간 통신 프로토콜을 의미합니다.",
        ],
    },
}

BEGINNER_BASIC_RANDOM_KEYWORDS = [
    "ai기본",
    "ai 기본",
    "ai기본문제",
    "ai 기본 문제",
    "기본문제",
    "기본 문제",
    "랜덤",
    "ai문제",
    "ai 문제",
    "인공지능 기본",
    "인공지능 문제",
]

BEGINNER_COMPARE_RANDOM_KEYWORDS = [
    "비교문제",
    "비교 문제",
    "비교",
    "차이",
    "차이점",
]

BEGINNER_INCORRECT_RANDOM_KEYWORDS = [
    "옳지 않은",
    "옳지않은",
    "틀린",
    "오답",
    "잘못된",
    "부적절",
]


def _normalize_slot_text(text: str) -> str:
    return text.strip().lower()


def split_beginner_topic_slots(topic: str) -> list[str]:
    slots = [part.strip() for part in topic.split(",") if part.strip()]
    return slots or [topic.strip()]


def _contains_any(text: str, keywords: list[str]) -> bool:
    compact = text.replace(" ", "")
    return any(keyword.replace(" ", "") in compact for keyword in keywords)


def _match_beginner_topic_key(slot_text: str) -> str | None:
    normalized = _normalize_slot_text(slot_text)

    for key, preset in AI_BEGINNER_TOPIC_PRESETS.items():
        for alias in preset.get("aliases", []):
            if alias.lower().replace(" ", "") in normalized.replace(" ", ""):
                return key

    topic_key = normalize_ai_beginner_topic(slot_text)
    if topic_key != "__unknown__":
        return topic_key

    return None


def _match_beginner_compare_key(slot_text: str) -> str | None:
    return normalize_ai_beginner_compare(slot_text)


def _pick_unused_key(
    keys: list[str],
    used_keys: set[str],
) -> str:
    candidates = [key for key in keys if key not in used_keys]
    if not candidates:
        candidates = keys[:]

    selected = random.choice(candidates)
    used_keys.add(selected)
    return selected


def _pick_unused_compare_key(
    used_compare_keys: set[str],
) -> str:
    keys = list(AI_BEGINNER_COMPARE_PRESETS.keys())
    return _pick_unused_key(keys, used_compare_keys)


def _pick_unused_basic_key(
    used_topic_keys: set[str],
) -> str:
    keys = list(AI_BEGINNER_TOPIC_PRESETS.keys())
    return _pick_unused_key(keys, used_topic_keys)


def resolve_beginner_generation_slots(
    *,
    topic: str,
    count: int,
) -> list[dict[str, str | None]]:
    raw_slots = split_beginner_topic_slots(topic)

    if len(raw_slots) == 1 and is_broad_ai_beginner_topic(topic):
        raw_slots = ["ai기본"] * count

    raw_slots = raw_slots[:count]

    used_topic_keys: set[str] = set()
    used_compare_keys: set[str] = set()
    resolved: list[dict[str, str | None]] = []

    for raw_slot in raw_slots:
        slot_text = _normalize_slot_text(raw_slot)
        compare_key = _match_beginner_compare_key(slot_text)

        if compare_key:
            used_compare_keys.add(compare_key)
            resolved.append({
                "raw_slot": raw_slot,
                "slot_type": "compare",
                "topic_key": None,
                "compare_key": compare_key,
                "question_format": "ai_concept_compare_basic",
            })
            continue

        topic_key = _match_beginner_topic_key(slot_text)

        if topic_key:
            used_topic_keys.add(topic_key)

            question_format = None
            if _contains_any(slot_text, BEGINNER_INCORRECT_RANDOM_KEYWORDS):
                question_format = "ai_basic_concept_find_incorrect"
            elif _contains_any(slot_text, BEGINNER_COMPARE_RANDOM_KEYWORDS):
                question_format = "ai_concept_compare_basic"

            resolved.append({
                "raw_slot": raw_slot,
                "slot_type": "topic",
                "topic_key": topic_key,
                "compare_key": None,
                "question_format": question_format,
            })
            continue

        if _contains_any(slot_text, BEGINNER_INCORRECT_RANDOM_KEYWORDS):
            topic_key = _pick_unused_basic_key(used_topic_keys)
            resolved.append({
                "raw_slot": raw_slot,
                "slot_type": "topic",
                "topic_key": topic_key,
                "compare_key": None,
                "question_format": "ai_basic_concept_find_incorrect",
            })
            continue

        if _contains_any(slot_text, BEGINNER_COMPARE_RANDOM_KEYWORDS):
            compare_key = _pick_unused_compare_key(used_compare_keys)
            resolved.append({
                "raw_slot": raw_slot,
                "slot_type": "compare",
                "topic_key": None,
                "compare_key": compare_key,
                "question_format": "ai_concept_compare_basic",
            })
            continue

        if _contains_any(slot_text, BEGINNER_BASIC_RANDOM_KEYWORDS):
            topic_key = _pick_unused_basic_key(used_topic_keys)
            resolved.append({
                "raw_slot": raw_slot,
                "slot_type": "topic",
                "topic_key": topic_key,
                "compare_key": None,
                "question_format": None,
            })
            continue

        topic_key = _pick_unused_basic_key(used_topic_keys)
        resolved.append({
            "raw_slot": raw_slot,
            "slot_type": "topic",
            "topic_key": topic_key,
            "compare_key": None,
            "question_format": None,
        })

    while len(resolved) < count:
        topic_key = _pick_unused_basic_key(used_topic_keys)
        resolved.append({
            "raw_slot": "ai기본",
            "slot_type": "topic",
            "topic_key": topic_key,
            "compare_key": None,
            "question_format": None,
        })

    return resolved

RAG_INTERMEDIATE_VARIANTS: Dict[str, List[Dict[str, Any]]] = {
    "ai_scenario_best_action": [
        {
            "variant_id": "rag_metadata_filter_category_mixing",
            "scenario": (
                "사내 문서 기반 QA 시스템에서 사용자가 '보안 정책'을 질문했지만, "
                "검색 결과에 보안 문서와 프론트엔드 개발 문서가 함께 포함되고 있습니다. "
                "문서에는 category metadata가 저장되어 있지만 검색 요청에는 category 조건이 적용되지 않았습니다."
            ),
            "correct_points": [
                "검색 요청에 category 조건을 추가해 보안 문서 범위로 제한합니다."
            ],
            "wrong_points": [
                "사용자 질문을 더 구체적인 표현으로 재작성합니다.",
                "검색된 후보 문서의 순서를 reranker로 다시 평가합니다.",
                "chunk size와 overlap을 조정해 문서 분리 단위를 바꿉니다.",
                "top_k를 늘려 더 많은 검색 후보를 확인합니다.",
            ],
            "log_or_metric": {
                "query": "보안 정책",
                "top_k": 5,
                "result_summary": [
                    {"chunk": "보안 정책 접근 권한 기준", "similarity": 0.78, "category": "security"},
                    {"chunk": "프론트엔드 라우팅 설정", "similarity": 0.72, "category": "frontend"},
                    {"chunk": "보안 정책 예외 승인 절차", "similarity": 0.69, "category": "security"},
                ],
                "issue": "category 조건이 적용되지 않아 다른 범주 문서가 함께 검색됨",
            },
        },
        {
            "variant_id": "rag_query_rewrite_ambiguous_query",
            "scenario": (
                "사용자가 '성능 문제 해결 방법'처럼 넓은 질문을 입력하면, "
                "RAG 시스템이 데이터베이스 튜닝 문서, API 성능 문서, 모델 추론 최적화 문서를 함께 검색합니다. "
                "검색 범주는 크게 벗어나지 않지만, 질문 의도가 구체화되지 않아 상위 결과의 초점이 자주 흔들립니다."
            ),
            "correct_points": [
                "질문에 장애 대상과 상황 단서를 추가해 검색 의도를 구체화합니다."
            ],
            "wrong_points": [
                "문서 category 조건을 추가해 검색 범위를 제한합니다.",
                "top_k를 늘려 더 많은 후보 문서를 반환합니다.",
                "chunk size를 조정해 문서 조각의 길이를 바꿉니다.",
                "검색된 후보를 reranker로 다시 정렬합니다.",
            ],
            "log_or_metric": {
                "query": "성능 문제 해결 방법",
                "top_k": 5,
                "result_summary": [
                    {"chunk": "DB 인덱스 튜닝", "similarity": 0.74, "category": "performance"},
                    {"chunk": "API 응답 시간 개선", "similarity": 0.72, "category": "performance"},
                    {"chunk": "모델 추론 latency 최적화", "similarity": 0.70, "category": "performance"},
                ],
                "issue": "질문 의도가 넓어 검색 결과의 초점이 분산됨",
            },
        },
        {
            "variant_id": "rag_reranker_relevant_chunk_lower_rank",
            "scenario": (
                "RAG 검색 결과 후보 안에는 질문과 직접 관련된 chunk가 포함되어 있습니다. "
                "하지만 상위 1~2개에는 일반 설명 chunk가 먼저 노출되고, "
                "핵심 근거가 되는 chunk는 4~5위에 머물러 최종 답변에 충분히 반영되지 않습니다."
            ),
            "correct_points": [
                "후보 chunk를 질문 관련도 기준으로 다시 평가해 상위 순서를 조정합니다."
            ],
            "wrong_points": [
                "검색할 문서 category 범위를 metadata로 제한합니다.",
                "반환되는 후보 문서 수를 top_k 설정으로 조정합니다.",
                "사용자 질문 표현을 더 구체적인 검색어로 바꿉니다.",
                "인덱싱된 원본 문서를 다시 업로드해 저장소를 갱신합니다.",
            ],
            "log_or_metric": {
                "query": "RAG 검색 품질 개선",
                "top_k": 5,
                "result_summary": [
                    {"chunk": "RAG 개념 소개", "similarity": 0.77, "category": "ai"},
                    {"chunk": "벡터 검색 기본 구조", "similarity": 0.73, "category": "ai"},
                    {"chunk": "metadata filter 적용 기준", "similarity": 0.69, "category": "ai"},
                    {"chunk": "reranker를 활용한 후보 재정렬", "similarity": 0.66, "category": "ai"},
                ],
                "issue": "관련 chunk는 후보에 있으나 핵심 근거가 상위에 오지 않음",
            },
        },
    ],

    "ai_scenario_find_incorrect_action": [
        {
            "variant_id": "rag_incorrect_top_k_only_for_category_mixing",
            "scenario": (
                "RAG 기반 QA 시스템에서 HR 문서와 개발 문서가 같은 저장소에 저장되어 있습니다. "
                "사용자는 HR 규정에 대해 질문했지만 개발 문서 chunk가 함께 검색됩니다. "
                "각 문서에는 category metadata가 존재하며, 팀은 HR 문서 범위로 검색 결과를 좁히려 합니다."
            ),
            "correct_points": [
                "category 조건은 그대로 두고 top_k만 늘려 더 많은 후보를 확인합니다."
            ],
            "wrong_points": [
                "검색 요청에 HR category 조건을 추가합니다.",
                "검색 로그에서 혼입된 문서의 category를 확인합니다.",
                "필터 적용 전후의 검색 결과 차이를 비교합니다.",
                "문서 업로드 시 category metadata 누락 여부를 점검합니다.",
            ],
            "log_or_metric": {
                "query": "휴가 신청 규정",
                "top_k": 5,
                "result_summary": [
                    {"chunk": "휴가 신청 승인 절차", "similarity": 0.81, "category": "hr"},
                    {"chunk": "React 라우터 설정", "similarity": 0.67, "category": "frontend"},
                    {"chunk": "근태 예외 처리 규정", "similarity": 0.64, "category": "hr"},
                ],
                "issue": "category filter가 없어 다른 범주 문서가 함께 검색됨",
            },
        },
        {
            "variant_id": "rag_incorrect_reranker_when_candidate_missing",
            "scenario": (
                "사용자가 특정 제품 매뉴얼 내용을 질문했지만, 검색 결과 후보 10개 안에 해당 제품 문서 chunk가 전혀 포함되지 않습니다. "
                "검색 로그를 보면 사용자 표현과 문서 표현이 달라 정답 근거가 후보군에 들어오지 못하고 있습니다. "
                "팀은 우선 정답 근거가 검색 후보에 포함되도록 개선하려 합니다."
            ),
            "correct_points": [
                "현재 후보군을 유지한 채 reranker만 적용해 순서를 조정합니다."
            ],
            "wrong_points": [
                "사용자 질문을 문서 표현에 가깝게 재작성합니다.",
                "vector search와 keyword search를 함께 사용합니다.",
                "제품명과 설정명을 문서 본문이나 metadata에 포함합니다.",
                "검색 실패 query를 수집해 반복 패턴을 분석합니다.",
            ],
            "log_or_metric": {
                "query": "알림 설정이 안 켜짐",
                "top_k": 10,
                "result_summary": [
                    {"chunk": "일반 알림 정책", "similarity": 0.59, "category": "manual"},
                    {"chunk": "권한 설정 개요", "similarity": 0.55, "category": "manual"},
                ],
                "issue": "정답 근거가 후보군에 포함되지 않음",
            },
        },
    ],

    "ai_quality_issue_diagnosis": [
        {
            "variant_id": "rag_diagnosis_metadata_filter_missing",
            "scenario": (
                "검색 결과 상위 chunk의 similarity 점수는 높지만, 사용자의 질문 범주와 다른 문서가 반복적으로 포함됩니다. "
                "검색 로그에는 category 조건이 비어 있고, 문서별 category metadata는 정상 저장되어 있습니다."
            ),
            "correct_points": [
                "검색 요청에서 category 조건이 빠져 metadata가 활용되지 않았습니다."
            ],
            "wrong_points": [
                "embedding 표현이 맞지 않아 같은 범주 문서도 검색되지 않았습니다.",
                "chunk 분리 단위가 커서 서로 다른 주제가 한 조각에 섞였습니다.",
                "관련 후보는 있으나 reranker가 없어 순서가 뒤로 밀렸습니다.",
                "top_k가 작아 하위에 있는 관련 후보가 context에서 제외되었습니다.",
            ],
            "log_or_metric": {
                "query": "보안 정책 예외 승인",
                "top_k": 5,
                "result_summary": [
                    {"chunk": "보안 정책 예외 승인", "similarity": 0.84, "category": "security"},
                    {"chunk": "프론트엔드 배포 가이드", "similarity": 0.79, "category": "frontend"},
                ],
                "issue": "category metadata는 있으나 검색 조건이 비어 있음",
            },
        },
        {
            "variant_id": "rag_diagnosis_chunk_noise",
            "scenario": (
                "문서 기반 문제 생성에서 검색된 chunk에 본문 개념보다 '교수자 질문', '학습 목표', '평가 방법' 같은 안내 문구가 자주 포함됩니다. "
                "검색 범주와 query는 맞지만, 생성된 문제는 핵심 개념보다 수업 안내 문구에 영향을 받습니다."
            ),
            "correct_points": [
                "context 구성 단계에서 핵심 개념보다 부가 문구가 우선 포함되었습니다."
            ],
            "wrong_points": [
                "category 조건이 빠져 서로 다른 문서 범주가 함께 검색되었습니다.",
                "top_k가 작아 필요한 근거 chunk가 후보에서 제외되었습니다.",
                "관련 후보는 있으나 reranker가 없어 상위 순서가 흔들렸습니다.",
                "사용자 질문이 모호해 검색 의도가 여러 방향으로 분산되었습니다.",
            ],
            "log_or_metric": {
                "query": "요구사항 변경 영향 분석",
                "top_k": 5,
                "result_summary": [
                    {"chunk": "교수자 질문 및 학습 목표", "similarity": 0.76, "category": "software_engineering"},
                    {"chunk": "요구사항 추적성 설명", "similarity": 0.72, "category": "software_engineering"},
                ],
                "issue": "검색 범주는 맞지만 chunk에 안내성 noise가 많음",
            },
        },
    ],
    "ai_method_compare_decision": [
        {
            "variant_id": "rag_compare_metadata_filter_vs_reranker",
            "scenario": (
                "RAG 검색 결과에 서로 다른 업무 범주의 문서가 섞이고 있습니다. "
                "문서에는 category metadata가 있고, 검색 후보군에는 관련 문서와 무관한 category 문서가 함께 포함됩니다. "
                "팀은 검색 후보에 들어오는 문서 범주를 먼저 줄이려 합니다."
            ),
            "correct_points": [
                "metadata filter로 검색 문서 범주를 제한합니다."
            ],
            "wrong_points": [
                "reranker로 검색 후보 순서를 다시 조정합니다.",
                "top_k를 조정해 검색 후보 수를 바꿉니다.",
                "query rewrite로 질문 표현을 구체화합니다.",
                "embedding 모델을 변경해 의미 유사도 품질을 개선합니다.",
            ],
            "log_or_metric": {
                "query": "보안 정책",
                "top_k": 5,
                "result_summary": [
                    {"chunk": "보안 정책", "similarity": 0.81, "category": "security"},
                    {"chunk": "프론트엔드 설정", "similarity": 0.75, "category": "frontend"},
                ],
                "issue": "filter 없이 검색되어 다른 category 문서가 후보군에 포함됨",
            },
        },
        {
            "variant_id": "rag_compare_hybrid_vs_vector_only",
            "scenario": (
                "사용자가 정확한 오류 코드와 설정 키워드를 포함해 질문했지만, vector search만 사용할 때는 "
                "의미적으로 비슷한 일반 설명 문서가 상위에 노출됩니다. "
                "정확한 키워드가 포함된 운영 문서는 낮은 순위에 머무릅니다. "
                "팀은 의미 유사도와 정확한 키워드 단서를 함께 반영하려 합니다."
            ),
            "correct_points": [
                "hybrid search로 vector와 keyword 검색을 함께 사용합니다."
            ],
            "wrong_points": [
                "vector query를 오류 코드 중심으로 보강합니다.",
                "metadata filter로 운영 문서 범위를 제한합니다.",
                "top_k를 늘려 오류 코드가 포함된 후보를 확인합니다.",
                "chunk size를 조정해 설정 키워드가 같은 chunk에 포함되게 합니다.",
            ],
            "log_or_metric": {
                "query": "ERR_CONN_TIMEOUT nginx proxy_read_timeout",
                "top_k": 5,
                "result_summary": [
                    {"chunk": "일반적인 네트워크 오류 설명", "similarity": 0.77, "category": "ops"},
                    {"chunk": "nginx proxy_read_timeout 설정", "similarity": 0.69, "category": "ops"},
                ],
                "issue": "정확한 키워드 단서가 중요하지만 vector-only 검색에서 일반 설명이 상위에 노출됨",
            },
        },
    ],

    "ai_log_or_metric_interpretation": [
        {
            "variant_id": "rag_log_similarity_high_wrong_category",
            "scenario": (
                "검색 로그에서 상위 chunk의 similarity는 높지만, category가 사용자의 요청 범주와 다릅니다. "
                "반면 similarity가 조금 낮은 다른 chunk는 category가 요청 범주와 일치하고 본문 근거도 더 직접적입니다."
            ),
            "correct_points": [
                "similarity 점수와 category 일치 여부를 함께 확인합니다."
            ],
            "wrong_points": [
                "similarity 점수를 기준으로 상위 chunk를 우선 배치합니다.",
                "검색 점수 기준으로 후보 chunk의 순서를 조정합니다.",
                "본문 근거를 기준으로 context 포함 여부를 판단합니다.",
                "metadata 조건 적용 전후의 검색 결과를 비교합니다.",
            ],
            "log_or_metric": {
                "query": "보안 정책 예외 승인",
                "top_k": 5,
                "result_summary": [
                    {"chunk": "프론트엔드 권한 라우팅", "similarity": 0.86, "category": "frontend"},
                    {"chunk": "보안 정책 예외 승인 절차", "similarity": 0.78, "category": "security"},
                ],
                "issue": "similarity는 높지만 category가 맞지 않는 결과가 상위에 있음",
            },
        },
        {
            "variant_id": "rag_log_rrf_hybrid_rank",
            "scenario": (
                "검색 로그에서 vector 검색 1위 문서는 일반적인 개념 설명이고, "
                "keyword 검색 1위 문서는 사용자의 오류 코드와 정확히 일치합니다. "
                "두 검색 결과의 순위가 서로 달라 최종 순서를 정하는 기준이 필요합니다."
            ),
            "correct_points": [
                "RRF로 vector rank와 keyword rank를 순위 기반으로 병합합니다."
            ],
            "wrong_points": [
                "vector rank를 기준으로 후보 순서를 먼저 조정합니다.",
                "keyword rank를 기준으로 정확히 일치한 문서를 우선 배치합니다.",
                "similarity 점수를 기준으로 두 결과의 순서를 맞춥니다.",
                "top_k를 늘려 두 검색 결과의 후보 범위를 넓힙니다.",
            ],
            "log_or_metric": {
                "query": "ERR_CONN_TIMEOUT proxy_read_timeout",
                "top_k": 5,
                "result_summary": [
                    {
                        "chunk": "네트워크 오류 일반 설명",
                        "similarity": 0.82,
                        "category": "ops",
                        "vector_rank": 1,
                        "keyword_rank": 5,
                    },
                    {
                        "chunk": "proxy_read_timeout 설정",
                        "similarity": 0.74,
                        "category": "ops",
                        "vector_rank": 3,
                        "keyword_rank": 1,
                    },
                ],
                "issue": "vector 검색과 keyword 검색의 상위 결과가 서로 다르게 나타남",
            },
        },
    ],
}

LLM_INTERMEDIATE_VARIANTS: Dict[str, List[Dict[str, Any]]] = {
    "ai_scenario_best_action": [
        {
            "variant_id": "llm_context_missing_latest_policy",
            "scenario": (
                "사내 챗봇이 사용자의 최신 보안 정책 질문에 답변하고 있습니다. "
                "운영 로그를 확인한 결과, 현재 요청에는 참고 문서나 검색 결과가 context로 제공되지 않았고, "
                "답변에는 정책 개정일이나 출처 문서명이 포함되지 않습니다. "
                "모델 응답은 문장 자체는 자연스럽지만, 실제 최신 정책 문서와 일치하는지 검증하기 어렵습니다. "
                "팀은 단순히 답변 표현을 안정화하는 것보다, 최신성과 근거성을 우선 확보하려고 합니다."
            ),
            "correct_points": [
                "최신 정책처럼 근거와 개정 시점이 중요한 질문에는 관련 정책 문서를 검색해 context로 제공하고, 답변에 사용된 출처를 함께 남기도록 구성합니다."
            ],
            "wrong_points": [
                "temperature를 낮춰 동일 질문에 대한 표현 변동성을 줄이되, 참고 문서가 없는 상태에서는 최신 정책의 사실성을 보장하지 못합니다.",
                "system prompt에 출처 기반 답변 원칙을 추가하되, 실제 검색된 정책 문서가 없으면 모델이 근거를 만들어낼 위험은 남습니다.",
                "사용자 질문에 정책명과 적용 시점을 포함하도록 재작성하되, 문서 검색 없이 질문만 구체화하면 최신 문서 확인에는 한계가 있습니다.",
                "생성 답변에 대한 사용자 피드백을 수집하되, 사후 피드백만으로는 현재 응답 생성 시점의 근거 부족을 직접 해결하지 못합니다.",
            ],
            "log_or_metric": {
                "prompt": "최신 보안 정책을 알려줘",
                "context_provided": False,
                "source_count": 0,
                "source_policy_date": None,
                "temperature": 0.7,
                "issue": "최신 정책 질문에 대한 근거 문서와 출처 정보가 제공되지 않음",
            },
        },
        {
            "variant_id": "llm_output_format_unstable",
            "scenario": (
                "LLM을 이용해 고객 문의를 내부 처리 시스템으로 전달하고 있습니다. "
                "최근 일부 응답이 후처리 단계에서 실패하며, 실패 사례를 보면 요청마다 응답 구조가 조금씩 달라집니다. "
                "팀은 모델 호출 단계에서 저장 가능한 응답 구조를 더 안정적으로 만들려 합니다."
            ),
            "correct_points": [
                "응답 구조와 필수 항목을 모델 호출 조건에 명시합니다."
            ],
            "wrong_points": [
                "대표 입력과 기대 응답 예시를 추가해 출력 패턴을 유도합니다.",
                "후처리 단계에서 실패 응답을 별도 큐로 분리합니다.",
                "temperature를 낮춰 동일 입력의 표현 변동을 줄입니다.",
                "실패 로그를 유형별로 모아 반복되는 구조 오류를 분석합니다.",
            ],
            "log_or_metric": {
                "prompt": "고객 문의를 분류해줘",
                "expected_format": {
                    "category": "string",
                    "priority": "string",
                    "reason": "string",
                },
                "observed_outputs": [
                    "JSON 뒤에 설명 문장 포함",
                    "priority 필드 누락",
                    "category_name 필드 사용",
                ],
                "temperature": 0.5,
                "issue": "출력 형식이 일정하지 않아 후처리 파싱이 실패함",
            },
        },
    ],

    "ai_scenario_find_incorrect_action": [
        {
            "variant_id": "llm_incorrect_temperature_for_factuality",
            "scenario": (
                "LLM이 사내 규정 질문에 답변할 때 문장 표현은 자연스럽지만, "
                "근거 문서가 없는 상태에서 일부 내용을 추정해 답변하고 있습니다. "
                "동일 질문을 여러 번 실행하면 표현은 조금씩 달라지지만, 실제 문제는 답변이 규정 문서에 근거했는지 확인할 수 없다는 점입니다. "
                "팀은 우선 사실성과 근거 확인을 개선하려고 하며, 생성 다양성 자체를 줄이는 것이 주된 목표는 아닙니다."
            ),
            "correct_points": [
                "temperature를 낮추고 동일 질문에 대한 답변 변동성만 줄이는 조치는 표현 안정화에는 도움이 되지만, 근거 없는 추정 답변 문제를 직접 해결하지 못합니다."
            ],
            "wrong_points": [
                "관련 규정 문서를 검색해 답변 context로 제공하고, 답변 생성 시 해당 문서 범위 안에서만 응답하도록 제한합니다.",
                "답변에 사용된 규정 문서의 제목, 버전, 조항 정보를 함께 기록해 사후 검토가 가능하도록 만듭니다.",
                "근거 문서가 검색되지 않은 경우에는 추정 답변 대신 답변 불가 또는 추가 확인 요청으로 응답 범위를 제한합니다.",
                "생성된 답변을 저장하거나 사용자에게 제공하기 전에 규정 문서와의 일치 여부를 검증하는 절차를 둡니다.",
            ],
            "log_or_metric": {
                "prompt": "복리후생 규정을 알려줘",
                "context_provided": False,
                "source_count": 0,
                "temperature": 0.9,
                "same_input_runs": 3,
                "observed_issue": "표현은 달라지지만 모든 실행에서 근거 문서가 없음",
                "issue": "근거 없는 추정 답변이 생성됨",
            },
        },
    ],

    "ai_quality_issue_diagnosis": [
        {
            "variant_id": "llm_diagnosis_hallucination_no_context",
            "scenario": (
                "LLM이 최신 정책에 대한 답변을 생성했지만, 요청 로그에는 참고 문서가 제공되지 않은 것으로 나타납니다. "
                "답변에는 구체적인 시행일과 예외 조건이 포함되어 있으나, 실제 정책 문서의 조항이나 버전 정보와 연결되어 있지 않습니다. "
                "응답 형식은 안정적이고 파싱 오류도 발생하지 않았지만, 답변이 최신 정책과 일치하는지 확인하기 어렵습니다. "
                "팀은 이 품질 저하가 출력 형식 문제인지, 근거 부족 문제인지 구분하려고 합니다."
            ),
            "correct_points": [
                "최신 사실을 확인할 근거 문서나 검색 결과가 제공되지 않아, 모델이 그럴듯하지만 검증되지 않은 내용을 생성했을 가능성이 큽니다."
            ],
            "wrong_points": [
                "응답 형식 제약이 부족해 출력 구조가 흔들린 문제라면 JSON 필드 누락이나 파싱 실패가 함께 관찰되어야 합니다.",
                "temperature 설정으로 답변 표현의 변동성이 커진 문제라면 동일 입력 반복 실행에서 표현 차이가 핵심 증상으로 나타나야 합니다.",
                "system prompt의 역할 지시가 답변 범위를 넓힌 문제라면 모델이 허용되지 않은 역할이나 범위까지 답변하는 증상이 중심이 됩니다.",
                "생성 후 검증 절차가 없는 문제는 오류 탐지 지연의 원인이 될 수 있지만, 현재 답변 생성 단계의 근거 부재 자체를 설명하는 핵심 원인은 아닙니다.",
            ],
            "log_or_metric": {
                "prompt": "최신 개인정보 처리 기준을 알려줘",
                "context_provided": False,
                "source_count": 0,
                "schema_error": False,
                "temperature": 0.6,
                "answer_contains_policy_date": True,
                "issue": "최신 사실 답변에 사용할 근거 문서가 없음",
            },
        },
        {
            "variant_id": "llm_diagnosis_high_temperature_variance",
            "scenario": (
                "같은 고객 문의를 여러 번 분류했을 때, 실행할 때마다 분류 결과와 설명이 조금씩 달라집니다. "
                "참고 문서는 필요하지 않은 분류 작업이지만, 운영 환경에서는 일관된 결과가 중요합니다."
            ),
            "correct_points": [
                "temperature가 높아 응답 변동성이 커졌습니다."
            ],
            "wrong_points": [
                "최신 사실 확인용 근거 문서가 없습니다.",
                "검색 결과의 category filter가 빠졌습니다.",
                "chunk 분리 단위가 커서 문맥이 섞였습니다.",
                "모델 API latency가 증가했습니다.",
            ],
            "log_or_metric": {
                "prompt": "문의 내용을 billing, technical, account 중 하나로 분류해줘",
                "context_provided": False,
                "temperature": 1.0,
                "same_input_runs": 5,
                "observed_variance": "분류 결과가 실행마다 달라짐",
                "issue": "동일 입력에 대한 분류 일관성이 낮음",
            },
        },
    ],

    "ai_method_compare_decision": [
        {
            "variant_id": "llm_compare_rag_vs_prompt_only",
            "scenario": (
                "사용자가 최신 사내 보안 정책을 질문하고 있습니다. "
                "팀은 두 가지 개선안을 비교하고 있습니다. 하나는 system prompt에 '근거 중심으로 답변하라'는 규칙을 추가하는 방식이고, "
                "다른 하나는 정책 문서를 검색해 관련 조항을 context로 제공한 뒤 답변하게 하는 방식입니다. "
                "현재 문제는 답변 문체가 아니라 최신 정책의 개정 내용과 예외 조건을 정확히 반영하는 것입니다. "
                "팀은 운영 환경에서 답변의 근거성과 최신성을 높이는 방법을 선택하려 합니다."
            ),
            "correct_points": [
                "최신 정책 문서를 검색해 답변 context에 포함하면 모델이 실제 문서 조항과 개정 시점을 근거로 답변할 수 있어 근거성과 최신성을 직접 개선할 수 있습니다."
            ],
            "wrong_points": [
                "system prompt에 근거 중심 답변 원칙을 추가하는 것은 응답 태도를 제어하는 데 도움이 되지만, 실제 최신 문서를 제공하지 않으면 사실 확인에는 한계가 있습니다.",
                "temperature를 낮추는 것은 답변 표현의 변동성을 줄이는 데 유효하지만, 모델이 모르는 최신 정책 내용을 새로 확인하게 만들지는 못합니다.",
                "질문에 정책명과 적용 시점을 포함하도록 재작성하는 것은 검색 의도를 구체화하는 보조 수단이지만, 문서 검색이나 context 제공 없이는 충분하지 않습니다.",
                "생성 답변에 대한 사후 검증 로그를 수집하는 것은 품질 관리에 도움이 되지만, 답변 생성 시점의 근거 부족을 직접 해결하는 방법은 아닙니다.",
            ],
            "log_or_metric": {
                "prompt": "최신 사내 보안 정책을 알려줘",
                "context_provided": False,
                "source_count": 0,
                "policy_freshness_required": True,
                "issue": "최신 정책 근거가 필요한 질문임",
            },
        },
        {
            "variant_id": "llm_compare_schema_vs_free_text",
            "scenario": (
                "LLM 응답을 백엔드에서 자동 파싱해 저장해야 합니다. "
                "최근 저장 실패 사례를 보면 응답에 설명 문장이 섞이거나 항목 구성이 요청마다 달라집니다. "
                "팀은 모델 응답을 후처리 시스템이 안정적으로 읽을 수 있는 형태로 만들려 합니다."
            ),
            "correct_points": [
                "응답 구조와 필수 항목을 명시해 저장 가능한 형태로 생성하게 합니다."
            ],
            "wrong_points": [
                "대표 예시를 제공해 모델이 기대 응답 패턴을 참고하게 합니다.",
                "후처리 파서에서 누락 항목 탐지와 예외 처리를 강화합니다.",
                "temperature를 낮춰 동일 요청의 표현 변동을 줄입니다.",
                "저장 실패 로그를 수집해 반복되는 형식 오류를 분류합니다.",
            ],
            "log_or_metric": {
                "prompt": "문의 내용을 분류하고 저장 가능한 형태로 반환해줘",
                "required_fields": ["category", "priority", "reason"],
                "parse_error_rate": "18%",
                "issue": "자유 문장 응답이 섞여 필드 파싱이 실패함",
            },
        },
    ],

    "ai_log_or_metric_interpretation": [
        {
            "variant_id": "llm_log_no_context_high_temperature",
            "scenario": (
                "응답 설정 로그를 확인한 결과, 최신 정책 질문에 대한 요청에서 참고 문서가 제공되지 않았고 "
                "source_count도 0으로 기록되어 있습니다. temperature는 비교적 높게 설정되어 있어 답변 표현의 변동성도 커질 수 있습니다. "
                "하지만 팀이 우선 해결하려는 문제는 표현 다양성이 아니라, 최신 정책 답변이 실제 문서에 근거하는지 여부입니다. "
                "아래 로그를 바탕으로 가장 먼저 적용할 개선 방향을 판단하려 합니다."
            ),
            "correct_points": [
                "context_provided가 False이고 source_count가 0이면 temperature 조정보다 근거 문서를 검색해 context로 제공하는 개선이 우선입니다."
            ],
            "wrong_points": [
                "temperature를 낮춰 답변 표현의 변동성을 줄이는 것은 보조 조치가 될 수 있지만, 근거 문서가 없는 문제를 직접 해결하지는 못합니다.",
                "system prompt에 근거 기반 답변 원칙을 추가하는 것은 필요하지만, 실제 context가 없으면 모델이 출처를 임의로 생성할 위험이 남습니다.",
                "질문에 정책명과 적용 시점을 포함하도록 재작성하는 것은 검색 질의를 개선할 수 있지만, 현재 로그의 핵심 원인인 source_count 0을 직접 해결해야 합니다.",
                "생성 답변에 대한 사후 검증 로그를 수집하는 것은 운영 모니터링에 도움이 되지만, 현재 요청의 근거 부족을 먼저 해소해야 합니다.",
            ],
            "log_or_metric": {
                "prompt": "최신 보안 정책을 알려줘",
                "context_provided": False,
                "source_count": 0,
                "temperature": 0.9,
                "policy_freshness_required": True,
                "issue": "최신 정책 질문에 대한 근거 문서가 없음",
            },
        },
        {
            "variant_id": "llm_log_parse_error_schema_missing",
            "scenario": (
                "LLM 응답을 후처리 단계에서 파싱하는 과정에서 오류가 반복되고 있습니다. "
                "로그에는 모델 호출 조건에 고정된 응답 구조가 포함되지 않았고, 응답에 설명 문장과 데이터 항목이 함께 섞여 있는 것으로 나타납니다."
            ),
            "correct_points": [
                "응답 구조와 데이터만 반환하는 규칙을 명확히 지정해 파싱 가능한 출력을 유도합니다."
            ],
            "wrong_points": [
                "후처리 파서에서 일부 누락 항목을 보정합니다.",
                "대표 예시로 원하는 응답 형태를 보여줍니다.",
                "temperature를 낮춰 응답 형식의 변동성을 줄입니다.",
                "파싱 실패 로그를 수집해 오류 패턴을 분석합니다.",
            ],
            "log_or_metric": {
                "prompt": "문의 내용을 분류해서 반환해줘",
                "schema_provided": False,
                "json_only_required": False,
                "parse_error_rate": "22%",
                "observed_output": "JSON 앞뒤에 설명 문장이 포함됨",
                "issue": "출력 형식 제약이 부족해 파싱 실패가 반복됨",
            },
        },
    ],
}

MODELOPS_INTERMEDIATE_VARIANTS: Dict[str, List[Dict[str, Any]]] = {
    "ai_scenario_best_action": [
        {
            "variant_id": "modelops_latency_after_deploy",
            "scenario": (
                "모델 API의 평균 응답 시간이 최근 배포 이후 증가했습니다. "
                "운영 로그에서는 timeout 비율도 함께 높아졌고, 입력 데이터 분포 변화는 아직 뚜렷하지 않습니다. "
                "팀은 먼저 서비스 장애 가능성을 줄이는 조치를 검토하고 있습니다."
            ),
            "correct_points": [
                "최근 배포 버전의 추론 시간과 서빙 리소스 사용량을 확인하고 롤백 가능성을 검토합니다."
            ],
            "wrong_points": [
                "운영 데이터의 입력 분포 변화를 drift 기준으로 비교합니다.",
                "학습 데이터셋을 확장해 다음 모델 재학습 계획을 세웁니다.",
                "배치 추론 작업의 실행 주기를 조정해 처리량을 비교합니다.",
                "모델 설명 가능성 리포트를 생성해 예측 근거를 분석합니다.",
            ],
            "log_or_metric": {
                "avg_latency_ms": 1850,
                "p95_latency_ms": 3200,
                "timeout_rate": "8%",
                "recent_deploy": True,
                "drift_score": 0.03,
                "issue": "최근 배포 이후 latency와 timeout이 증가함",
            },
        },
        {
            "variant_id": "modelops_drift_detected_prediction_drop",
            "scenario": (
                "운영 중인 분류 모델의 예측 성능이 최근 주간 리포트에서 하락했습니다. "
                "서빙 latency와 timeout은 안정적이지만, 운영 입력 데이터의 주요 피처 분포가 학습 시점과 달라졌습니다. "
                "팀은 성능 저하 원인을 먼저 확인하려고 합니다."
            ),
            "correct_points": [
                "운영 입력 데이터와 학습 데이터의 피처 분포 차이를 drift 기준으로 분석합니다."
            ],
            "wrong_points": [
                "최근 배포 버전의 추론 latency와 timeout 로그를 우선 점검합니다.",
                "API 서버 인스턴스 수를 늘려 요청 처리량 변화를 확인합니다.",
                "응답 캐시 전략을 적용해 반복 요청의 지연 시간을 줄입니다.",
                "모델 버전별 롤백 절차 문서를 먼저 정비합니다.",
            ],
            "log_or_metric": {
                "weekly_accuracy": 0.71,
                "baseline_accuracy": 0.82,
                "avg_latency_ms": 240,
                "timeout_rate": "0.3%",
                "drift_score": 0.41,
                "recent_deploy": False,
                "issue": "성능 하락과 함께 입력 데이터 drift가 관찰됨",
            },
        },
    ],

    "ai_scenario_find_incorrect_action": [
        {
            "variant_id": "modelops_incorrect_retrain_first_for_latency",
            "scenario": (
                "모델 API 배포 직후 p95 latency와 timeout 비율이 증가했습니다. "
                "최근 입력 데이터 분포 변화는 크지 않고, 성능 지표 하락도 아직 확인되지 않았습니다. "
                "팀은 서빙 안정성을 회복하기 위한 대응을 검토하고 있습니다."
            ),
            "correct_points": [
                "학습 데이터 확장과 재학습 계획을 먼저 검토합니다."
            ],
            "wrong_points": [
                "최근 배포 버전의 추론 시간 변화를 이전 버전과 비교합니다.",
                "서빙 서버의 CPU와 메모리 사용량을 함께 확인합니다.",
                "timeout이 증가한 요청 구간의 p95 latency를 분석합니다.",
                "문제가 배포 이후 시작됐다면 롤백 가능성을 검토합니다.",
            ],
            "log_or_metric": {
                "p95_latency_ms": 4100,
                "timeout_rate": "9%",
                "recent_deploy": True,
                "drift_score": 0.02,
                "accuracy_drop": False,
                "issue": "배포 직후 서빙 지연과 timeout이 증가함",
            },
        },
        {
            "variant_id": "modelops_incorrect_scale_out_first_for_drift",
            "scenario": (
                "모델의 응답 속도와 서버 오류율은 안정적이지만, 최근 예측 결과의 정확도가 떨어지고 있습니다. "
                "운영 데이터의 일부 핵심 피처 분포가 학습 데이터와 다르게 나타났습니다. "
                "팀은 품질 저하 원인을 먼저 확인하려고 합니다."
            ),
            "correct_points": [
                "API 서버를 증설해 요청 처리량을 먼저 늘립니다."
            ],
            "wrong_points": [
                "운영 입력 데이터의 피처 분포 변화를 학습 데이터와 비교합니다.",
                "성능 하락이 특정 사용자군이나 입력 구간에 집중되는지 확인합니다.",
                "최근 데이터로 재학습이 필요한지 평가 기준을 점검합니다.",
                "drift 감지 결과와 예측 오류 증가 시점을 함께 비교합니다.",
            ],
            "log_or_metric": {
                "avg_latency_ms": 210,
                "error_rate": "0.2%",
                "weekly_accuracy": 0.69,
                "baseline_accuracy": 0.81,
                "drift_score": 0.46,
                "issue": "서빙은 안정적이지만 데이터 drift와 성능 하락이 발생함",
            },
        },
    ],

    "ai_quality_issue_diagnosis": [
        {
            "variant_id": "modelops_diagnosis_serving_bottleneck",
            "scenario": (
                "모델 API의 정확도 지표는 이전과 비슷하지만, 최근 요청에서 응답 지연과 timeout이 증가했습니다. "
                "장애는 새 모델 버전 배포 이후 시작되었고, 운영 데이터 분포 변화는 크지 않습니다."
            ),
            "correct_points": [
                "새 모델 버전의 추론 비용 증가나 서빙 리소스 병목이 원인일 가능성이 큽니다."
            ],
            "wrong_points": [
                "운영 입력 데이터의 drift로 예측 기준이 달라졌을 가능성이 있습니다.",
                "학습 데이터 라벨 품질 저하로 모델 정확도가 낮아졌을 가능성이 있습니다.",
                "배치 추론 주기 설정으로 실시간 응답이 지연됐을 가능성이 있습니다.",
                "모델 설명 리포트가 부족해 예측 근거 해석이 어려웠을 가능성이 있습니다.",
            ],
            "log_or_metric": {
                "accuracy": 0.84,
                "previous_accuracy": 0.85,
                "p95_latency_ms": 3600,
                "timeout_rate": "7%",
                "recent_deploy": True,
                "drift_score": 0.04,
                "issue": "정확도는 유지되지만 배포 이후 서빙 지연이 증가함",
            },
        },
        {
            "variant_id": "modelops_diagnosis_data_drift",
            "scenario": (
                "운영 모델의 주간 정확도가 하락했지만 API 응답 시간과 timeout 비율은 안정적입니다. "
                "최근 사용자 입력의 피처 분포가 학습 데이터 기준과 달라졌고, 새 모델 배포는 없었습니다."
            ),
            "correct_points": [
                "운영 입력 데이터의 분포 변화로 모델 예측 품질이 낮아졌을 가능성이 큽니다."
            ],
            "wrong_points": [
                "새 모델 버전의 추론 시간이 늘어 timeout이 증가했을 가능성이 있습니다.",
                "서빙 서버 리소스 부족으로 요청 처리 지연이 발생했을 가능성이 있습니다.",
                "출력 포맷 변경으로 API 응답 파싱이 실패했을 가능성이 있습니다.",
                "모델 버전 롤백 절차가 없어 장애 복구가 지연됐을 가능성이 있습니다.",
            ],
            "log_or_metric": {
                "weekly_accuracy": 0.68,
                "baseline_accuracy": 0.82,
                "avg_latency_ms": 230,
                "timeout_rate": "0.2%",
                "recent_deploy": False,
                "drift_score": 0.52,
                "issue": "서빙은 안정적이지만 성능 저하와 데이터 drift가 관찰됨",
            },
        },
    ],

    "ai_method_compare_decision": [
        {
            "variant_id": "modelops_compare_rollback_vs_monitoring",
            "scenario": (
                "새 모델 버전 배포 직후 latency와 timeout이 증가했습니다. "
                "서비스 영향이 커지고 있어 팀은 빠르게 안정성을 회복해야 합니다. "
                "동시에 원인 분석을 위한 운영 로그는 이미 수집되고 있습니다."
            ),
            "correct_points": [
                "이전 안정 버전으로 롤백한 뒤 리소스 사용량을 분석합니다."
            ],
            "wrong_points": [
                "운영 대시보드의 latency와 timeout 추이를 계속 관찰합니다.",
                "사용자 피드백을 수집해 응답 품질 만족도를 비교합니다.",
                "학습 데이터 샘플을 추가해 다음 재학습 후보를 준비합니다.",
                "모델 설명 리포트를 생성해 예측 근거의 일관성을 점검합니다.",
            ],
            "log_or_metric": {
                "recent_deploy": True,
                "p95_latency_ms": 4300,
                "timeout_rate": "11%",
                "rollback_available": True,
                "monitoring_enabled": True,
                "issue": "배포 직후 서비스 안정성 문제가 커지고 있음",
            },
        },
        {
            "variant_id": "modelops_compare_realtime_vs_batch",
            "scenario": (
                "추천 모델 결과를 하루에 한 번 갱신해도 서비스 요구사항을 만족할 수 있습니다. "
                "현재는 모든 요청마다 실시간 추론을 수행해 피크 시간대 latency가 높아지고 있습니다. "
                "팀은 응답 지연을 줄이면서 운영 비용도 낮추려 합니다."
            ),
            "correct_points": [
                "일 단위 배치 추론으로 추천 결과를 미리 계산하고 요청 시 저장된 결과를 제공합니다."
            ],
            "wrong_points": [
                "실시간 추론 서버를 증설해 피크 시간대 처리량을 늘립니다.",
                "모델 입력 feature를 늘려 추천 결과의 설명력을 높입니다.",
                "사용자 피드백 로그를 수집해 다음 재학습에 반영합니다.",
                "추천 API 응답 포맷을 단순화해 클라이언트 처리 비용을 줄입니다.",
            ],
            "log_or_metric": {
                "real_time_required": False,
                "refresh_interval": "daily",
                "peak_p95_latency_ms": 2900,
                "inference_cost": "high",
                "issue": "실시간 추론 요구가 낮지만 모든 요청에서 추론을 수행함",
            },
        },
    ],

    "ai_log_or_metric_interpretation": [
        {
            "variant_id": "modelops_log_latency_timeout_after_deploy",
            "scenario": (
                "운영 로그에서 최근 배포 이후 latency와 timeout이 함께 증가했습니다. "
                "정확도 하락이나 데이터 drift는 아직 뚜렷하지 않습니다."
            ),
            "correct_points": [
                "recent_deploy가 True이고 p95 latency와 timeout이 증가했으므로 배포 버전과 서빙 리소스를 우선 점검합니다."
            ],
            "wrong_points": [
                "운영 입력 데이터의 분포 변화를 기준으로 재학습 필요성을 검토합니다.",
                "정확도 지표를 중심으로 모델 품질 변화를 먼저 점검합니다.",
                "사용자 피드백 수집을 진행해 응답 만족도 변화를 확인합니다.",
                "출력 포맷을 단순화해 클라이언트 처리 비용을 줄입니다.",
            ],
            "log_or_metric": {
                "recent_deploy": True,
                "avg_latency_ms": 1900,
                "p95_latency_ms": 4200,
                "timeout_rate": "10%",
                "accuracy": 0.84,
                "drift_score": 0.03,
                "issue": "최근 배포 이후 latency와 timeout이 증가함",
            },
        },
        {
            "variant_id": "modelops_log_drift_accuracy_drop",
            "scenario": (
                "운영 지표에서 모델 정확도 하락과 drift score 상승이 함께 확인되었습니다. "
                "latency와 timeout은 안정적이고 최근 배포도 없었습니다."
            ),
            "correct_points": [
                "drift score 상승과 정확도 하락이 함께 나타났으므로 운영 데이터 분포 변화를 우선 분석합니다."
            ],
            "wrong_points": [
                "recent_deploy가 False여도 새 모델 버전의 추론 비용을 먼저 비교합니다.",
                "latency와 timeout 추이를 중심으로 운영 상태를 계속 관찰합니다.",
                "timeout이 낮으므로 API 서버 증설을 우선 진행합니다.",
                "응답 포맷을 단순화해 예측 품질 저하를 먼저 개선합니다.",
            ],
            "log_or_metric": {
                "recent_deploy": False,
                "weekly_accuracy": 0.69,
                "baseline_accuracy": 0.82,
                "avg_latency_ms": 220,
                "timeout_rate": "0.2%",
                "drift_score": 0.55,
                "issue": "정확도 하락과 drift score 상승이 함께 나타남",
            },
        },
    ],
}

ML_INTERMEDIATE_VARIANTS: Dict[str, List[Dict[str, Any]]] = {
    "ai_scenario_best_action": [
        {
            "variant_id": "ml_best_action_data_leakage_split_before_preprocess",
            "scenario": (
                "이탈 예측 모델의 검증 성능은 매우 높게 나왔지만, 운영 테스트에서는 성능이 크게 낮아졌습니다. "
                "확인 결과 전체 데이터에 대해 scaling과 결측치 대체를 먼저 수행한 뒤 train/test split을 적용했습니다. "
                "팀은 평가 결과가 실제 일반화 성능을 반영하도록 학습 절차를 점검하려 합니다."
            ),
            "correct_points": [
                "split 이후 학습 데이터 기준으로 전처리합니다."
            ],
            "wrong_points": [
                "threshold를 조정해 예측 비율을 비교합니다.",
                "class weight로 소수 클래스 비중을 조정합니다.",
                "교차 검증으로 fold별 성능 차이를 확인합니다.",
                "feature importance로 변수 영향을 분석합니다.",
            ],
            "log_or_metric": {
                "train_accuracy": 0.96,
                "test_accuracy": 0.94,
                "holdout_accuracy": 0.71,
                "preprocessing_order": "scaling_before_split",
                "leakage_signal": True,
                "issue": "split 전에 전체 데이터 기준 전처리를 수행해 data leakage 가능성이 있음",
            },
        },
        {
            "variant_id": "ml_best_action_class_imbalance_low_recall",
            "scenario": (
                "불량 탐지 모델의 전체 accuracy는 0.96으로 높지만, 실제 불량 클래스의 recall은 0.28에 머물고 있습니다. "
                "정상 데이터가 대부분을 차지해 모델이 정상 클래스를 잘 맞히는 방향으로 평가되고 있습니다. "
                "팀은 불량 탐지 목적에 맞게 모델 평가와 개선 방향을 조정하려 합니다."
            ),
            "correct_points": [
                "recall과 precision을 함께 보고 불균형 대응을 검토합니다."
            ],
            "wrong_points": [
                "전체 accuracy 기준으로 모델 버전을 선택합니다.",
                "fold별 accuracy 변동을 교차 검증으로 확인합니다.",
                "feature importance로 주요 변수를 분석합니다.",
                "학습 기간을 늘려 전체 표본 수를 확장합니다.",
            ],
            "log_or_metric": {
                "accuracy": 0.96,
                "positive_class_ratio": "3%",
                "precision": 0.62,
                "recall": 0.28,
                "threshold": 0.5,
                "issue": "class imbalance 상황에서 accuracy는 높지만 positive recall이 낮음",
            },
        },
    ],

    "ai_scenario_find_incorrect_action": [
        {
            "variant_id": "ml_incorrect_accuracy_only_for_imbalanced_data",
            "scenario": (
                "고객 이탈 예측 모델에서 이탈 고객 비율은 8%입니다. "
                "새 모델은 accuracy가 높지만 이탈 고객 recall이 낮아, 실제 캠페인 대상자를 충분히 찾지 못하고 있습니다. "
                "팀은 이탈 탐지 목적에 맞는 평가 기준을 검토하려 합니다."
            ),
            "correct_points": [
                "전체 accuracy만 기준으로 모델을 선택합니다."
            ],
            "wrong_points": [
                "이탈 클래스의 recall과 precision을 비교합니다.",
                "threshold별 캠페인 대상자 규모를 비교합니다.",
                "class weight 적용 전후 성능을 비교합니다.",
                "confusion matrix로 미탐지 비율을 확인합니다.",
            ],
            "log_or_metric": {
                "positive_class_ratio": "8%",
                "accuracy": 0.93,
                "precision": 0.41,
                "recall": 0.24,
                "threshold": 0.5,
                "issue": "전체 accuracy는 높지만 이탈 고객 탐지 recall이 낮음",
            },
        },
        {
            "variant_id": "ml_incorrect_random_split_for_time_series",
            "scenario": (
                "월별 매출 예측 모델을 평가하고 있습니다. "
                "데이터는 시간 순서에 따라 분포가 변하고 있으며, 운영에서는 미래 월 데이터를 예측해야 합니다. "
                "팀은 운영 환경과 비슷한 방식으로 검증 데이터를 구성하려 합니다."
            ),
            "correct_points": [
                "전체 기간을 섞어 random split으로 평가합니다."
            ],
            "wrong_points": [
                "과거 기간으로 학습하고 이후 기간으로 평가합니다.",
                "검증 기간 성능으로 모델 선택 기준을 정합니다.",
                "기간별 성능 차이로 분포 변화를 확인합니다.",
                "예측 시점 이후 feature 포함 여부를 점검합니다.",
            ],
            "log_or_metric": {
                "split_method": "random_split",
                "train_period": "2024-01~2025-12 mixed",
                "test_period": "2024-01~2025-12 mixed",
                "deployment_target": "future_month",
                "issue": "시간 순서가 중요한 예측 문제에서 random split은 운영 평가와 다를 수 있음",
            },
        },
    ],

    "ai_quality_issue_diagnosis": [
        {
            "variant_id": "ml_diagnosis_overfitting_train_test_gap",
            "scenario": (
                "분류 모델의 train accuracy는 0.99로 매우 높지만 test accuracy는 0.72에 머물고 있습니다. "
                "train loss는 계속 낮아졌지만 validation 성능은 일정 시점 이후 개선되지 않았습니다. "
                "팀은 성능 차이가 발생한 원인을 진단하려 합니다."
            ),
            "correct_points": [
                "학습 데이터에 지나치게 맞춰져 일반화 성능이 낮아진 상황입니다."
            ],
            "wrong_points": [
                "소수 클래스 탐지가 부족해 recall이 낮은 상황입니다.",
                "결정 기준값이 높아 positive 예측 수가 줄어든 상황입니다.",
                "전체 정답 비율만 보고 양성 예측 품질을 놓친 상황입니다.",
                "학습 기간이 짧아 최근 패턴이 반영되지 않은 상황입니다.",
            ],
            "log_or_metric": {
                "train_accuracy": 0.99,
                "test_accuracy": 0.72,
                "train_loss": 0.03,
                "validation_accuracy": 0.73,
                "issue": "train 성능과 test 성능 차이가 크게 나타남",
            },
        },
        {
            "variant_id": "ml_diagnosis_target_leakage_feature",
            "scenario": (
                "대출 연체 예측 모델의 검증 성능이 비정상적으로 높게 나타났습니다. "
                "feature 목록을 확인하니 실제 연체 발생 이후에 생성되는 납부 지연 일수가 입력 변수에 포함되어 있었습니다. "
                "팀은 평가 성능이 과도하게 높게 나온 원인을 확인하려 합니다."
            ),
            "correct_points": [
                "예측 시점 이후 생성되는 feature가 포함된 target leakage 상황입니다."
            ],
            "wrong_points": [
                "class imbalance로 소수 클래스 recall이 낮아진 상황입니다.",
                "threshold가 낮아 positive 예측 비율이 증가한 상황입니다.",
                "교차 검증 fold 수가 부족해 분산을 놓친 상황입니다.",
                "feature importance 분석이 부족해 설명력이 낮은 상황입니다.",
            ],
            "log_or_metric": {
                "validation_accuracy": 0.98,
                "test_accuracy": 0.97,
                "feature_name": "days_late_after_due_date",
                "available_at_prediction_time": False,
                "leakage_signal": True,
                "issue": "예측 시점 이후 생성되는 target 관련 feature가 포함됨",
            },
        },
    ],

    "ai_method_compare_decision": [
        {
            "variant_id": "ml_compare_precision_recall_for_campaign",
            "scenario": (
                "마케팅 팀은 이탈 가능성이 높은 고객 상위 5%를 선정해 리텐션 캠페인을 진행하려 합니다. "
                "캠페인 예산이 제한되어 있어 모든 고객을 대상으로 할 수 없고, 실제 이탈 고객을 최대한 포함하는 것이 중요합니다. "
                "팀은 운영 목적에 맞는 평가 기준을 선택하려 합니다."
            ),
            "correct_points": [
                "상위 타겟 구간의 적중률, 탐지 비율, 기준 대비 향상도를 함께 평가합니다."
            ],
            "wrong_points": [
                "전체 고객 기준 정답 비율이 높은 모델을 선택합니다.",
                "전체 데이터의 평균 손실값만 비교해 선택합니다.",
                "주요 변수 영향이 단순하게 설명되는 모델을 선택합니다.",
                "학습 데이터 규모가 큰 모델을 우선 선택합니다.",
            ],
            "log_or_metric": {
                "targeting_ratio": "top_5%",
                "accuracy": 0.91,
                "top_k_precision": 0.37,
                "top_k_recall": 0.22,
                "lift": 2.8,
                "issue": "운영 목적이 전체 분류보다 top-K 타겟팅 성능에 가까움",
            },
        },
        {
            "variant_id": "ml_compare_threshold_vs_retrain",
            "scenario": (
                "부정 거래 탐지 모델에서 기본 threshold 0.5를 적용하면 precision은 높지만 recall이 낮습니다. "
                "운영팀은 탐지 누락을 줄이고 싶지만, 재학습 전에 현재 모델의 의사결정 기준을 먼저 조정해 보려 합니다. "
                "팀은 즉시 비교 가능한 방법을 선택하려 합니다."
            ),
            "correct_points": [
                "threshold를 낮춰 recall과 precision 변화를 비교합니다."
            ],
            "wrong_points": [
                "학습 데이터를 확장해 다음 재학습 계획을 세웁니다.",
                "교차 검증으로 fold별 accuracy 변동을 확인합니다.",
                "feature importance로 주요 변수 순위를 분석합니다.",
                "class weight를 조정한 새 모델을 별도 학습합니다.",
            ],
            "log_or_metric": {
                "threshold": 0.5,
                "precision": 0.82,
                "recall": 0.31,
                "false_negative_cost": "high",
                "retrain_available_now": False,
                "issue": "현재 모델에서 탐지 누락을 줄이기 위한 threshold 검토가 필요함",
            },
        },
    ],

    "ai_log_or_metric_interpretation": [
        {
            "variant_id": "ml_log_train_test_gap_overfitting",
            "scenario": (
                "모델 학습 결과에서 train 성능과 test 성능의 차이가 크게 나타났습니다. "
                "팀은 아래 평가 지표를 바탕으로 모델 품질 문제를 해석하려 합니다."
            ),
            "correct_points": [
                "train/test 성능 차이로 overfitting을 우선 점검합니다."
            ],
            "wrong_points": [
                "class imbalance에 따른 recall 저하를 먼저 확인합니다.",
                "threshold 조정으로 예측 비율 변화를 비교합니다.",
                "time-based split으로 기간별 성능 차이를 확인합니다.",
                "feature importance로 주요 변수 영향을 분석합니다.",
            ],
            "log_or_metric": {
                "train_accuracy": 0.99,
                "test_accuracy": 0.70,
                "train_loss": 0.02,
                "test_loss": 0.61,
                "issue": "train 성능은 높지만 test 성능이 낮아 일반화 차이가 큼",
            },
        },
        {
            "variant_id": "ml_log_imbalance_accuracy_recall",
            "scenario": (
                "불균형 데이터로 학습한 분류 모델의 평가 결과입니다. "
                "팀은 아래 지표를 바탕으로 모델이 실제 양성 클래스를 충분히 탐지하는지 판단하려 합니다."
            ),
            "correct_points": [
                "positive 비율과 recall을 함께 보고 탐지 성능을 점검합니다."
            ],
            "wrong_points": [
                "train/test accuracy 차이로 overfitting 여부를 확인합니다.",
                "feature importance로 주요 변수 영향을 분석합니다.",
                "교차 검증 평균 accuracy로 모델을 선택합니다.",
                "학습 데이터 수를 늘려 전체 accuracy를 확인합니다.",
            ],
            "log_or_metric": {
                "accuracy": 0.95,
                "positive_class_ratio": "4%",
                "precision": 0.58,
                "recall": 0.21,
                "threshold": 0.5,
                "issue": "전체 accuracy는 높지만 positive recall이 낮음",
            },
        },
    ],
}

DL_INTERMEDIATE_VARIANTS: Dict[str, List[Dict[str, Any]]] = {
    "ai_scenario_best_action": [
        {
            "variant_id": "dl_best_action_overfitting_validation_loss",
            "scenario": (
                "이미지 분류 모델 학습 중 train loss는 계속 낮아지고 있지만 validation loss는 증가하고 있습니다. "
                "train accuracy는 높아지는 반면 validation accuracy는 일정 시점 이후 개선되지 않습니다. "
                "팀은 모델의 일반화 성능을 개선하려 합니다."
            ),
            "correct_points": [
                "dropout과 regularization으로 과적합 완화를 검토합니다."
            ],
            "wrong_points": [
                "epoch 수를 늘려 train loss를 더 낮춥니다.",
                "batch size를 키워 학습 속도를 먼저 높입니다.",
                "입력 이미지 해상도를 낮춰 연산량을 줄입니다.",
                "출력 클래스 수를 줄여 예측 범위를 제한합니다.",
            ],
            "log_or_metric": {
                "epoch": 30,
                "train_loss": 0.08,
                "validation_loss": 0.52,
                "train_accuracy": 0.98,
                "validation_accuracy": 0.74,
                "issue": "train loss는 감소하지만 validation loss가 증가함",
            },
        },
        {
            "variant_id": "dl_best_action_gpu_memory_batch_size",
            "scenario": (
                "CNN 모델 학습 중 GPU 메모리 부족 오류가 반복적으로 발생합니다. "
                "모델 구조와 입력 이미지 크기는 유지해야 하지만, 현재 batch size가 커서 학습이 중단되고 있습니다. "
                "팀은 학습을 안정적으로 진행할 수 있는 조치를 먼저 검토하려 합니다."
            ),
            "correct_points": [
                "batch size를 줄여 GPU 메모리 사용량을 낮춥니다."
            ],
            "wrong_points": [
                "epoch 수를 늘려 모델이 더 오래 학습되게 합니다.",
                "dropout 비율을 높여 과적합을 완화합니다.",
                "validation split을 조정해 평가 데이터를 늘립니다.",
                "learning rate를 낮춰 loss 변동을 줄입니다.",
            ],
            "log_or_metric": {
                "batch_size": 128,
                "gpu_memory_error": True,
                "input_resolution": "224x224",
                "model_type": "CNN",
                "issue": "큰 batch size로 GPU 메모리 부족이 발생함",
            },
        },
    ],

    "ai_scenario_find_incorrect_action": [
        {
            "variant_id": "dl_incorrect_more_epochs_for_overfitting",
            "scenario": (
                "딥러닝 모델의 train loss는 계속 감소하지만 validation loss는 증가하고 있습니다. "
                "validation accuracy도 더 이상 개선되지 않아 과적합 가능성이 의심됩니다. "
                "팀은 일반화 성능을 개선하기 위한 대응을 검토하고 있습니다."
            ),
            "correct_points": [
                "epoch 수를 늘려 train loss를 더 낮춥니다."
            ],
            "wrong_points": [
                "dropout을 적용해 특정 뉴런 의존도를 낮춥니다.",
                "regularization으로 가중치가 과도해지는 것을 줄입니다.",
                "early stopping으로 validation 성능 기준 학습을 멈춥니다.",
                "데이터 증강으로 학습 샘플 다양성을 높입니다.",
            ],
            "log_or_metric": {
                "epoch": 40,
                "train_loss": 0.05,
                "validation_loss": 0.63,
                "train_accuracy": 0.99,
                "validation_accuracy": 0.72,
                "issue": "과적합 징후가 있는데 train loss만 더 낮추려 함",
            },
        },
        {
            "variant_id": "dl_incorrect_shuffle_for_sequence_model",
            "scenario": (
                "시계열 데이터를 입력으로 사용하는 딥러닝 모델을 학습하고 있습니다. "
                "입력 순서 정보가 예측에 중요하며, 팀은 sequence 패턴이 유지되도록 데이터 구성을 점검하려 합니다. "
                "학습 안정성을 위해 적용할 전처리와 검증 방식을 검토하고 있습니다."
            ),
            "correct_points": [
                "시점 순서를 재배열해 학습 데이터를 구성합니다."
            ],
            "wrong_points": [
                "시간 순서가 유지되도록 입력 window를 구성합니다.",
                "미래 시점 정보가 feature에 섞였는지 점검합니다.",
                "검증 데이터는 이후 기간 기준으로 분리합니다.",
                "sequence 길이에 따른 성능 변화를 비교합니다.",
            ],
            "log_or_metric": {
                "data_type": "time_series",
                "sequence_order_required": True,
                "window_size": 30,
                "issue": "sequence 내부 순서를 유지해야 하는 예측 문제임",
            },
        },
    ],

    "ai_quality_issue_diagnosis": [
        {
            "variant_id": "dl_diagnosis_overfitting_loss_gap",
            "scenario": (
                "딥러닝 모델 학습 로그에서 train loss는 지속적으로 감소하지만 validation loss는 일정 시점 이후 증가합니다. "
                "train accuracy는 높지만 validation accuracy는 정체되어 있습니다. "
                "팀은 이 현상의 원인을 진단하려 합니다."
            ),
            "correct_points": [
                "학습 데이터에 과도하게 맞춰진 overfitting 상황입니다."
            ],
            "wrong_points": [
                "batch size가 작아 GPU 메모리가 부족한 상황입니다.",
                "learning rate가 낮아 loss가 전혀 줄지 않는 상황입니다.",
                "출력층 클래스 설정이 맞지 않아 예측 범위가 어긋난 상황입니다.",
                "입력 해상도가 낮아 추론 latency가 증가한 상황입니다.",
            ],
            "log_or_metric": {
                "epoch": 25,
                "train_loss": 0.06,
                "validation_loss": 0.49,
                "train_accuracy": 0.97,
                "validation_accuracy": 0.73,
                "issue": "train 성능과 validation 성능 차이가 커짐",
            },
        },
        {
            "variant_id": "dl_diagnosis_learning_rate_unstable_loss",
            "scenario": (
                "딥러닝 모델 학습 초반부터 loss가 크게 진동하며 안정적으로 감소하지 않습니다. "
                "같은 데이터와 모델 구조에서 learning rate를 낮춘 실험은 더 안정적인 loss 감소를 보였습니다. "
                "팀은 학습 불안정의 원인을 확인하려 합니다."
            ),
            "correct_points": [
                "learning rate가 커서 loss가 불안정하게 변동하는 상황입니다."
            ],
            "wrong_points": [
                "dropout이 없어 validation loss만 증가하는 상황입니다.",
                "batch size가 너무 커서 GPU 메모리가 부족한 상황입니다.",
                "데이터 증강이 부족해 일반화 성능이 낮은 상황입니다.",
                "epoch 수가 부족해 학습 기회가 모자란 상황입니다.",
            ],
            "log_or_metric": {
                "learning_rate": 0.1,
                "loss_pattern": "oscillating",
                "stable_with_lower_lr": True,
                "issue": "높은 learning rate에서 loss가 크게 진동함",
            },
        },
    ],

    "ai_method_compare_decision": [
        {
            "variant_id": "dl_compare_transfer_learning_vs_scratch",
            "scenario": (
                "이미지 분류 프로젝트에서 학습 데이터가 많지 않습니다. "
                "처음부터 CNN을 학습하는 방법과 사전학습 모델을 fine-tuning하는 방법을 비교하고 있습니다. "
                "팀은 제한된 데이터에서 일반화 성능을 높이는 방법을 선택하려 합니다."
            ),
            "correct_points": [
                "사전학습 모델을 fine-tuning해 특징 표현을 활용합니다."
            ],
            "wrong_points": [
                "처음부터 깊은 CNN을 학습해 전체 특징을 새로 학습합니다.",
                "학습 반복 횟수를 늘려 train 성능을 먼저 높입니다.",
                "한 번에 학습할 샘플 수를 늘려 업데이트 단위를 키웁니다.",
                "출력 클래스 수를 줄여 예측 범위를 단순화합니다.",
            ],
            "log_or_metric": {
                "dataset_size": "small",
                "task": "image_classification",
                "pretrained_model_available": True,
                "issue": "데이터가 적어 scratch 학습보다 전이학습 검토가 필요함",
            },
        },
        {
            "variant_id": "dl_compare_early_stopping_vs_more_epochs",
            "scenario": (
                "모델 학습 중 초반에는 validation loss가 감소했지만 이후 다시 증가하기 시작했습니다. "
                "train loss는 계속 낮아지고 있어 더 오래 학습하면 train 성능은 좋아질 수 있습니다. "
                "팀은 validation 성능 기준으로 학습 종료 전략을 선택하려 합니다."
            ),
            "correct_points": [
                "early stopping으로 validation 악화 전에 학습을 멈춥니다."
            ],
            "wrong_points": [
                "epoch 수를 늘려 train loss를 계속 낮춥니다.",
                "batch size를 키워 한 번의 업데이트 샘플 수를 늘립니다.",
                "입력 해상도를 낮춰 학습 연산량을 먼저 줄입니다.",
                "출력층 노드 수를 줄여 예측 클래스를 단순화합니다.",
            ],
            "log_or_metric": {
                "best_validation_epoch": 12,
                "current_epoch": 30,
                "train_loss": 0.04,
                "validation_loss": 0.55,
                "issue": "validation loss가 증가하는데 학습이 계속 진행됨",
            },
        },
    ],

    "ai_log_or_metric_interpretation": [
        {
            "variant_id": "dl_log_train_val_loss_overfitting",
            "scenario": (
                "딥러닝 모델 학습 로그입니다. "
                "팀은 아래 학습 지표를 바탕으로 모델의 일반화 문제를 해석하려 합니다."
            ),
            "correct_points": [
                "dropout과 regularization으로 overfitting을 완화합니다."
            ],
            "wrong_points": [
                "GPU 메모리 부족 여부를 batch size 기준으로 확인합니다.",
                "learning rate를 높여 loss 감소 속도를 빠르게 합니다.",
                "출력 클래스 수를 줄여 예측 문제를 단순화합니다.",
                "입력 해상도를 낮춰 추론 latency를 줄입니다.",
            ],
            "log_or_metric": {
                "epoch": 30,
                "train_loss": 0.04,
                "validation_loss": 0.58,
                "train_accuracy": 0.99,
                "validation_accuracy": 0.71,
                "issue": "train loss는 낮지만 validation loss가 높음",
            },
        },
        {
            "variant_id": "dl_log_learning_rate_loss_oscillation",
            "scenario": (
                "딥러닝 모델 학습 중 loss가 안정적으로 감소하지 않고 크게 진동하고 있습니다. "
                "팀은 아래 로그를 보고 학습 설정을 해석하려 합니다."
            ),
            "correct_points": [
                "loss 진동이 크므로 learning rate를 낮춰 안정성을 확인합니다."
            ],
            "wrong_points": [
                "현재 설정을 유지한 채 epoch 수를 늘립니다.",
                "출력 클래스 수를 줄여 loss 계산 대상을 줄입니다.",
                "validation 비율을 낮춰 학습 데이터 비중을 늘립니다.",
                "입력 feature를 줄여 모델의 표현력을 낮춥니다.",
            ],
            "log_or_metric": {
                "learning_rate": 0.1,
                "loss_pattern": "oscillating",
                "loss_values": [1.8, 0.9, 1.5, 0.7, 1.3],
                "issue": "loss가 안정적으로 감소하지 않고 크게 진동함",
            },
        },
    ],
}

AI_INTERMEDIATE_VARIANT_POOLS: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "rag": RAG_INTERMEDIATE_VARIANTS,
    "llm": LLM_INTERMEDIATE_VARIANTS,
    "modelops": MODELOPS_INTERMEDIATE_VARIANTS,
    "ml": ML_INTERMEDIATE_VARIANTS,
    "dl": DL_INTERMEDIATE_VARIANTS,
}

def normalize_ai_topic(topic: str) -> str:
    text = topic.strip().lower()

    dl_keywords = [
        "dl",
        "딥러닝",
        "deep learning",
        "신경망",
        "neural network",
        "cnn",
        "rnn",
        "lstm",
        "validation loss",
        "train loss",
        "dropout",
        "regularization",
        "batch size",
        "gpu",
        "gpu memory",
        "fine-tuning",
        "transfer learning",
        "early stopping",
    ]

    if any(keyword in text for keyword in dl_keywords):
        return "dl"

    modelops_keywords = [
        "modelops",
        "모델옵스",
        "모델 배포",
        "모니터링",
        "서빙",
        "latency",
        "timeout",
        "drift",
        "rollback",
        "batch inference",
        "real-time inference",
    ]

    if any(keyword in text for keyword in modelops_keywords):
        return "modelops"

    rag_keywords = [
        "rag",
        "검색 품질",
        "retrieval",
        "chunk",
        "metadata",
        "metadata filter",
        "reranker",
        "hybrid search",
        "top_k",
        "vector search",
        "keyword search",
    ]

    if any(keyword in text for keyword in rag_keywords):
        return "rag"

    ml_keywords = [
        "ml",
        "머신러닝",
        "machine learning",
        "모델 평가",
        "train/test",
        "data leakage",
        "target leakage",
        "class imbalance",
        "precision",
        "recall",
        "threshold",
        "cross validation",
        "feature leakage",
        "top-k",
        "top k",
    ]

    if any(keyword in text for keyword in ml_keywords):
        return "ml"

    llm_keywords = [
        "llm",
        "프롬프트",
        "prompt",
        "환각",
        "hallucination",
        "temperature",
        "답변 품질",
        "system prompt",
        "출력 형식",
    ]

    if any(keyword in text for keyword in llm_keywords):
        return "llm"

    general_ai_keywords = [
        "ai",
        "인공지능",
        "ai 관련",
        "ai 문제",
        "ai 실무",
        "ai 역량",
    ]

    if any(keyword in text for keyword in general_ai_keywords):
        return random.choice(["rag", "llm", "modelops", "ml", "dl"])

    return "llm"

def normalize_ai_beginner_compare(topic: str) -> str | None:
    text = topic.strip().lower().replace(" ", "")

    for key, preset in AI_BEGINNER_COMPARE_PRESETS.items():
        for alias in preset.get("aliases", []):
            normalized_alias = alias.lower().replace(" ", "")
            if normalized_alias in text:
                return key

    return None

def _build_ai_beginner_compare_evidence(
    *,
    topic: str,
) -> tuple[str, list[str], list[str], list[str], str | None, dict | None, str | None]:
    compare_key = normalize_ai_beginner_compare(topic)

    if not compare_key:
        raise ValueError(f"초급 비교 문제에 맞는 비교 preset을 찾을 수 없습니다: {topic}")

    preset = AI_BEGINNER_COMPARE_PRESETS[compare_key]

    concept_a = preset.get("concept_a", "개념 A")
    concept_b = preset.get("concept_b", "개념 B")

    correct_points = [
        *preset["correct_points"],
        f"{concept_a}와 {concept_b}는 목적과 사용 방식이 서로 다릅니다.",
    ]

    wrong_points = [
        *preset["wrong_points"],
        f"{concept_a}와 {concept_b}는 목적과 사용 방식이 완전히 같습니다.",
        f"{concept_a}와 {concept_b}의 역할을 서로 반대로 설명합니다.",
    ]

    return (
        preset["normalized_topic"],
        preset["concepts"],
        correct_points,
        wrong_points,
        None,
        None,
        None,
    )

def normalize_ai_beginner_topic(topic: str) -> str:
    text = topic.strip().lower()

    for key, preset in AI_BEGINNER_TOPIC_PRESETS.items():
        aliases = preset.get("aliases", [])
        for alias in aliases:
            if alias.lower() in text:
                return key

    if any(keyword in text for keyword in ["gpt", "생성형"]):
        return "gpt"

    if any(keyword in text for keyword in ["bert", "양방향"]):
        return "bert"

    if any(keyword in text for keyword in ["mcp", "model context protocol", "모델 컨텍스트"]):
        return "mcp"

    if any(keyword in text for keyword in ["a2a", "agent to agent", "agent2agent"]):
        return "a2a_protocol"

    if any(keyword in text for keyword in ["rag", "검색 증강", "retrieval"]):
        return "rag"

    if any(keyword in text for keyword in ["embedding", "임베딩"]):
        return "embedding"

    if any(keyword in text for keyword in ["vector db", "벡터 db", "벡터 데이터베이스"]):
        return "vector_db"

    if any(keyword in text for keyword in ["chunk", "청크"]):
        return "chunk"

    if any(keyword in text for keyword in ["metadata", "메타데이터"]):
        return "metadata_filter"

    if any(keyword in text for keyword in ["reranker", "리랭커", "재정렬"]):
        return "reranker"

    if any(keyword in text for keyword in ["fine-tuning", "파인튜닝", "fine tuning"]):
        return "fine_tuning"

    if any(keyword in text for keyword in ["agent", "에이전트"]):
        return "agent"

    if any(keyword in text for keyword in ["tool calling", "function calling", "도구 호출", "함수 호출"]):
        return "tool_calling"

    if any(keyword in text for keyword in ["precision", "정밀도"]):
        return "precision"

    if any(keyword in text for keyword in ["recall", "재현율"]):
        return "recall"

    if any(keyword in text for keyword in ["accuracy", "정확도"]):
        return "accuracy"

    if any(keyword in text for keyword in ["overfitting", "과적합"]):
        return "overfitting"

    if any(keyword in text for keyword in ["data leakage", "데이터 누수", "target leakage"]):
        return "data_leakage"

    if any(keyword in text for keyword in ["train/test", "train test", "학습 테스트"]):
        return "train_test_split"

    if any(keyword in text for keyword in ["cnn", "합성곱"]):
        return "cnn"

    if any(keyword in text for keyword in ["epoch", "에폭"]):
        return "epoch"

    if any(keyword in text for keyword in ["loss", "손실 함수"]):
        return "loss_function"

    if any(keyword in text for keyword in ["dropout", "드롭아웃"]):
        return "dropout"

    if any(keyword in text for keyword in ["transfer learning", "전이학습"]):
        return "transfer_learning"

    if any(keyword in text for keyword in ["serving", "서빙"]):
        return "model_serving"

    if any(keyword in text for keyword in ["latency", "지연 시간", "응답 시간"]):
        return "latency"

    if any(keyword in text for keyword in ["drift", "드리프트"]):
        return "drift"

    if any(keyword in text for keyword in ["monitoring", "모니터링"]):
        return "monitoring"

    return "__unknown__"

def is_broad_ai_beginner_topic(topic: str) -> bool:
    text = topic.strip().lower()
    return _contains_any(text, BEGINNER_BASIC_RANDOM_KEYWORDS)

def _build_ai_beginner_evidence(
    *,
    topic_key: str,
    question_format: str,
) -> tuple[list[str], list[str], list[str], str | None, dict | None, str | None, str]:
    preset = AI_BEGINNER_TOPIC_PRESETS[topic_key]

    definition = preset["definition"]
    purpose = preset["purpose"]
    role = preset["role"]
    wrong_points = preset["wrong_points"]
    concepts = preset["concepts"]
    normalized_topic = preset["normalized_topic"]

    scenario = None
    log_or_metric = None
    body_context = None

    if question_format == "ai_basic_concept_find_correct":
        correct_points = [
            definition,
            role,
        ]
        incorrect_points = wrong_points

    elif question_format == "ai_basic_concept_find_incorrect":
        # find_incorrect에서는 correct_points가
        # '정답이 될 틀린 설명'의 근거가 된다.
        # wrong_points 전체를 넘기면 틀린 선택지가 여러 개 생길 수 있으므로
        # 틀린 설명은 1개만 사용한다.
        incorrect_answer_point = random.choice(wrong_points)

        correct_points = [
            incorrect_answer_point,
        ]

        incorrect_points = [
            definition,
            purpose,
            role,
        ]

        compare = preset.get("compare")
        if compare and compare.get("point"):
            incorrect_points.append(compare["point"])

        incorrect_points = incorrect_points[:4]

    elif question_format == "ai_purpose_find_correct":
        correct_points = [
            purpose,
            role,
        ]
        incorrect_points = wrong_points

    elif question_format == "ai_concept_compare_basic":
        compare = preset.get("compare") or {}
        target = compare.get("target", "관련 개념")
        point = compare.get("point", definition)

        correct_points = [
            point,
        ]
        incorrect_points = [
            f"{normalized_topic}과 {target}은 목적과 사용 방식이 완전히 같습니다.",
            f"{target}은 {normalized_topic}과 동일한 역할만 수행합니다.",
            *wrong_points[:2],
        ]

    elif question_format == "ai_term_role_match":
        term_role = preset.get("term_role", role)

        correct_points = [
            term_role,
        ]
        incorrect_points = wrong_points

    else:
        correct_points = [
            definition,
            purpose,
        ]
        incorrect_points = wrong_points

    return (
        correct_points,
        incorrect_points,
        concepts,
        scenario,
        log_or_metric,
        body_context,
        normalized_topic,
    )

def _build_ai_beginner_compare_evidence_by_key(
    *,
    compare_key: str,
) -> tuple[str, list[str], list[str], list[str], str | None, dict | None, str | None]:
    preset = AI_BEGINNER_COMPARE_PRESETS[compare_key]

    concept_a = preset.get("concept_a", "개념 A")
    concept_b = preset.get("concept_b", "개념 B")

    correct_points = [
        *preset["correct_points"],
        f"{concept_a}와 {concept_b}는 목적과 사용 방식이 서로 다릅니다.",
    ]

    wrong_points = [
        *preset["wrong_points"],
        f"{concept_a}와 {concept_b}는 목적과 사용 방식이 완전히 같습니다.",
        f"{concept_a}와 {concept_b}의 역할을 서로 반대로 설명합니다.",
    ]

    return (
        preset["normalized_topic"],
        preset["concepts"],
        correct_points,
        wrong_points,
        None,
        None,
        None,
    )


def build_beginner_evidence_pack_from_slot(
    *,
    slot: dict[str, str | None],
    difficulty: str,
    plan: QuestionFormatPlan,
) -> EvidencePack:
    if difficulty != "초급":
        raise ValueError("slot 기반 evidence는 초급에서만 사용할 수 있습니다.")

    raw_slot = slot.get("raw_slot") or ""
    slot_type = slot.get("slot_type")

    if slot_type == "compare":
        compare_key = slot.get("compare_key")
        if not compare_key:
            raise ValueError(f"compare slot에 compare_key가 없습니다: {slot}")

        (
            normalized_topic,
            concepts,
            correct_points,
            wrong_points,
            scenario,
            log_or_metric,
            body_context,
        ) = _build_ai_beginner_compare_evidence_by_key(compare_key=compare_key)

    else:
        topic_key = slot.get("topic_key")
        if not topic_key:
            raise ValueError(f"topic slot에 topic_key가 없습니다: {slot}")

        (
            correct_points,
            wrong_points,
            concepts,
            scenario,
            log_or_metric,
            body_context,
            normalized_topic,
        ) = _build_ai_beginner_evidence(
            topic_key=topic_key,
            question_format=plan.question_format,
        )

    return EvidencePack(
        topic=raw_slot,
        normalized_topic=normalized_topic,
        difficulty=difficulty,
        question_format=plan.question_format,
        answer_style=plan.answer_style,
        focus=plan.focus,
        concepts=concepts,
        correct_points=correct_points,
        wrong_points=wrong_points,
        scenario=scenario,
        log_or_metric=log_or_metric,
        body_context=body_context,
    )

def build_evidence_pack(
    *,
    topic: str,
    difficulty: str,
    plan: QuestionFormatPlan,
) -> EvidencePack:
    if difficulty == "초급":
        if plan.question_format == "ai_concept_compare_basic":
            compare_key = normalize_ai_beginner_compare(topic)

            if compare_key:
                (
                    normalized_topic,
                    concepts,
                    correct_points,
                    wrong_points,
                    scenario,
                    log_or_metric,
                    body_context,
                ) = _build_ai_beginner_compare_evidence(topic=topic)
            else:
                topic_key = normalize_ai_beginner_topic(topic)

                if topic_key == "__unknown__":
                    raise ValueError(f"지원하지 않는 AI 초급 topic입니다: {topic}")

                (
                    correct_points,
                    wrong_points,
                    concepts,
                    scenario,
                    log_or_metric,
                    body_context,
                    normalized_topic,
                ) = _build_ai_beginner_evidence(
                    topic_key=topic_key,
                    question_format=plan.question_format,
                )
        else:
            topic_key = normalize_ai_beginner_topic(topic)

            if topic_key == "__unknown__":
                raise ValueError(f"지원하지 않는 AI 초급 topic입니다: {topic}")

            (
                correct_points,
                wrong_points,
                concepts,
                scenario,
                log_or_metric,
                body_context,
                normalized_topic,
            ) = _build_ai_beginner_evidence(
                topic_key=topic_key,
                question_format=plan.question_format,
            )

        return EvidencePack(
            topic=topic,
            normalized_topic=normalized_topic,
            difficulty=difficulty,
            question_format=plan.question_format,
            answer_style=plan.answer_style,
            focus=plan.focus,
            concepts=concepts,
            correct_points=correct_points,
            wrong_points=wrong_points,
            scenario=scenario,
            log_or_metric=log_or_metric,
            body_context=body_context,
        )

    topic_key = normalize_ai_topic(topic)
    preset = AI_TOPIC_PRESETS[topic_key]

    scenario = preset.get("scenario") if difficulty == "중급" else None
    log_or_metric = None

    if difficulty == "중급" and plan.question_format == "ai_log_or_metric_interpretation":
        log_or_metric = preset.get("log_or_metric")

    correct_points = preset["correct_points"]
    wrong_points = preset["wrong_points"]

    if difficulty == "중급" and topic_key in AI_INTERMEDIATE_VARIANT_POOLS:
        correct_points, wrong_points, scenario, log_or_metric = _build_ai_intermediate_variant_evidence(
            topic_key=topic_key,
            question_format=plan.question_format,
            correct_points=correct_points,
            wrong_points=wrong_points,
            scenario=scenario,
            log_or_metric=log_or_metric,
        )
    elif difficulty == "중급":
        correct_points, wrong_points, scenario, log_or_metric = _refine_intermediate_evidence_by_format(
            topic_key=topic_key,
            question_format=plan.question_format,
            correct_points=correct_points,
            wrong_points=wrong_points,
            scenario=scenario,
            log_or_metric=log_or_metric,
        )

    body_context = None

    if difficulty == "중급" and plan.question_format == "ai_log_or_metric_interpretation":
        body_context = _build_body_context_for_log_or_metric(log_or_metric)

    return EvidencePack(
        topic=topic,
        normalized_topic=preset["normalized_topic"],
        difficulty=difficulty,
        question_format=plan.question_format,
        answer_style=plan.answer_style,
        focus=plan.focus,
        concepts=preset["concepts"],
        correct_points=correct_points,
        wrong_points=wrong_points,
        scenario=scenario,
        log_or_metric=log_or_metric,
        body_context=body_context,
    )

def _build_body_context_for_log_or_metric(log_or_metric: dict | None) -> str | None:
    if not log_or_metric:
        return None

    if "query" in log_or_metric:
        result_lines = []
        for item in log_or_metric.get("result_summary", []):
            result_lines.append(
                f"- chunk: {item.get('chunk')}, similarity: {item.get('similarity')}, category: {item.get('category')}"
            )

        return (
            "[검색 로그]\n"
            f"query: {log_or_metric.get('query')}\n"
            f"top_k: {log_or_metric.get('top_k')}\n"
            "검색 결과:\n"
            + "\n".join(result_lines)
            + f"\n문제 상황: {log_or_metric.get('issue')}"
        )

    if (
        "p95_latency_ms" in log_or_metric
        or "drift_score" in log_or_metric
        or "weekly_accuracy" in log_or_metric
        or "recent_deploy" in log_or_metric
    ):
        metric_lines = []

        for key in [
            "recent_deploy",
            "avg_latency_ms",
            "p95_latency_ms",
            "timeout_rate",
            "error_rate",
            "accuracy",
            "previous_accuracy",
            "weekly_accuracy",
            "baseline_accuracy",
            "drift_score",
            "rollback_available",
            "monitoring_enabled",
            "real_time_required",
            "refresh_interval",
            "inference_cost",
        ]:
            if key in log_or_metric:
                metric_lines.append(f"{key}: {log_or_metric.get(key)}")

        return (
            "[ModelOps 운영 지표]\n"
            + "\n".join(metric_lines)
            + f"\n문제 상황: {log_or_metric.get('issue')}"
        )

    if (
        "schema_provided" in log_or_metric
        or "parse_error_rate" in log_or_metric
        or "expected_format" in log_or_metric
        or "observed_outputs" in log_or_metric
        or "required_fields" in log_or_metric
    ):
        metric_lines = []

        for key in [
            "prompt",
            "schema_provided",
            "json_only_required",
            "expected_format",
            "required_fields",
            "parse_error_rate",
            "observed_output",
            "observed_outputs",
        ]:
            if key in log_or_metric:
                metric_lines.append(f"{key}: {log_or_metric.get(key)}")

        return (
            "[응답 형식 로그]\n"
            + "\n".join(metric_lines)
            + f"\n문제 상황: {log_or_metric.get('issue')}"
        )

    if "temperature" in log_or_metric:
        return (
            "[응답 설정 로그]\n"
            f"prompt: {log_or_metric.get('prompt')}\n"
            f"context_provided: {log_or_metric.get('context_provided')}\n"
            f"source_count: {log_or_metric.get('source_count')}\n"
            f"temperature: {log_or_metric.get('temperature')}\n"
            f"문제 상황: {log_or_metric.get('issue')}"
        )

    if any(
        key in log_or_metric
        for key in [
            "validation_loss",
            "validation_accuracy",
            "learning_rate",
            "loss_pattern",
            "loss_values",
            "batch_size",
            "gpu_memory_error",
            "input_resolution",
            "model_type",
            "best_validation_epoch",
            "current_epoch",
            "dataset_size",
            "pretrained_model_available",
            "sequence_order_required",
            "window_size",
        ]
    ):
        metric_lines = []

        for key in [
            "epoch",
            "current_epoch",
            "best_validation_epoch",
            "train_loss",
            "validation_loss",
            "train_accuracy",
            "validation_accuracy",
            "learning_rate",
            "loss_pattern",
            "loss_values",
            "batch_size",
            "gpu_memory_error",
            "input_resolution",
            "model_type",
            "dataset_size",
            "pretrained_model_available",
            "sequence_order_required",
            "window_size",
        ]:
            if key in log_or_metric:
                metric_lines.append(f"{key}: {log_or_metric.get(key)}")

        return (
            "[DL 학습 지표]\n"
            + "\n".join(metric_lines)
            + f"\n문제 상황: {log_or_metric.get('issue')}"
        )

    if any(
        key in log_or_metric
        for key in [
            "train_accuracy",
            "test_accuracy",
            "holdout_accuracy",
            "validation_accuracy",
            "accuracy",
            "precision",
            "recall",
            "threshold",
            "positive_class_ratio",
            "top_k_precision",
            "top_k_recall",
            "lift",
            "leakage_signal",
            "split_method",
            "preprocessing_order",
            "feature_name",
            "available_at_prediction_time",
            "targeting_ratio",
            "false_negative_cost",
            "retrain_available_now",
        ]
    ):
        metric_lines = []

        for key in [
            "train_accuracy",
            "test_accuracy",
            "holdout_accuracy",
            "validation_accuracy",
            "train_loss",
            "test_loss",
            "accuracy",
            "precision",
            "recall",
            "threshold",
            "positive_class_ratio",
            "top_k_precision",
            "top_k_recall",
            "lift",
            "split_method",
            "preprocessing_order",
            "feature_name",
            "available_at_prediction_time",
            "leakage_signal",
            "targeting_ratio",
            "false_negative_cost",
            "retrain_available_now",
        ]:
            if key in log_or_metric:
                metric_lines.append(f"{key}: {log_or_metric.get(key)}")

        return (
            "[ML 평가 지표]\n"
            + "\n".join(metric_lines)
            + f"\n문제 상황: {log_or_metric.get('issue')}"
        )

    if "train_loss" in log_or_metric:
        return (
            "[학습 지표]\n"
            f"epoch: {log_or_metric.get('epoch')}\n"
            f"train_loss: {log_or_metric.get('train_loss')}\n"
            f"validation_loss: {log_or_metric.get('validation_loss')}\n"
            f"문제 상황: {log_or_metric.get('issue')}"
        )

    if "avg_latency_ms" in log_or_metric:
        return (
            "[운영 로그]\n"
            f"avg_latency_ms: {log_or_metric.get('avg_latency_ms')}\n"
            f"timeout_rate: {log_or_metric.get('timeout_rate')}\n"
            f"recent_deploy: {log_or_metric.get('recent_deploy')}\n"
            f"문제 상황: {log_or_metric.get('issue')}"
        )

    return f"[로그/지표]\n{log_or_metric}"

def _refine_intermediate_evidence_by_format(
    *,
    topic_key: str,
    question_format: str,
    correct_points: list[str],
    wrong_points: list[str],
    scenario: str | None,
    log_or_metric: dict | None,
) -> tuple[list[str], list[str], str | None, dict | None]:
    if topic_key == "modelops":
        if question_format in ["ai_scenario_best_action", "ai_method_compare_decision"]:
            scenario = (
                "모델 API 배포 후 평균 응답 시간이 증가하고 일부 요청에서 timeout이 발생하고 있습니다. "
                "최근 새 모델 버전이 배포되었고, 운영 로그에서 latency 증가가 확인되었습니다."
            )
            correct_points = [
                "배포 이후 latency와 timeout이 증가했다면 서빙 로그, 리소스 사용량, 최근 배포 버전을 함께 점검해야 합니다.",
                "최근 배포 이후 문제가 발생했다면 모델 버전 관리와 롤백 가능성을 검토할 수 있습니다.",
            ]
            wrong_points = [
                "학습 데이터 분포만 분석하고 서빙 지연과 timeout 로그는 확인하지 않습니다.",
                "모델 정확도 지표만 다시 계산하고 API latency와 timeout은 점검하지 않습니다.",
                "모니터링 없이 새 모델을 계속 배포합니다.",
                "데이터 drift를 서버 재부팅만으로 해결하려고 합니다.",
            ]

        elif question_format == "ai_quality_issue_diagnosis":
            scenario = (
                "모델 API 배포 직후 평균 응답 시간이 증가하고 timeout 비율이 높아졌습니다. "
                "입력 데이터 분포 변화보다는 최근 배포 이후 서빙 지연이 두드러지고 있습니다."
            )
            correct_points = [
                "최근 배포 이후 latency와 timeout이 증가했다면 새 모델 버전의 추론 비용 증가나 서빙 인프라 병목을 원인으로 의심할 수 있습니다."
            ]
            wrong_points = [
                "데이터 drift만 원인으로 판단하고 latency와 timeout 로그는 확인하지 않습니다.",
                "모델의 학습 정확도만 확인하고 운영 지표는 확인하지 않습니다.",
                "프롬프트 표현만 수정해 API timeout을 해결하려고 합니다.",
                "모델 버전과 배포 시점을 확인하지 않습니다.",
            ]

        elif question_format == "ai_log_or_metric_interpretation":
            correct_points = [
                "recent_deploy가 True이고 latency와 timeout이 증가했다면 최근 배포 버전, 서빙 리소스, 롤백 가능성을 우선 점검해야 합니다."
            ]
            wrong_points = [
                "latency 문제를 무시하고 학습 정확도만 다시 계산합니다.",
                "서버를 재부팅하면 데이터 drift가 항상 해결된다고 판단합니다.",
                "모델 버전 관리를 하지 않고 새 모델을 계속 덮어씁니다.",
                "timeout 비율이 증가했는데도 운영 모니터링을 중단합니다.",
            ]

    if topic_key == "llm":
        if question_format in ["ai_scenario_best_action", "ai_method_compare_decision"]:
            scenario = (
                "사용자 질문에 대해 LLM이 그럴듯하지만 근거가 부족한 답변을 생성하고 있습니다. "
                "질문은 최신 정책과 관련되어 있고, 현재 별도의 참고 문서나 검색 결과가 제공되지 않았습니다."
            )
            correct_points = [
                "최신 정보나 근거가 필요한 질문에는 관련 문서 검색 결과를 context로 제공하거나 RAG를 적용하는 것이 적절합니다.",
                "프롬프트를 구체화하더라도 근거 문서가 없으면 최신 사실 검증에는 한계가 있습니다.",
            ]
            wrong_points = [
                "temperature를 높여 더 창의적인 답변을 생성합니다.",
                "근거 검증 없이 LLM 답변을 그대로 사용합니다.",
                "최신 정보를 LLM이 항상 자동으로 알고 있다고 가정합니다.",
                "서버 응답 시간을 줄이면 hallucination이 해결된다고 판단합니다.",
            ]

        elif question_format == "ai_quality_issue_diagnosis":
            scenario = (
                "LLM이 최신 정책에 대해 답변했지만, 참고 문서가 제공되지 않아 근거가 불명확합니다."
            )
            correct_points = [
                "근거 문서나 검색 결과가 제공되지 않은 상태에서 최신 사실을 묻는 질문에 답변하면 hallucination 위험이 커질 수 있습니다."
            ]
            wrong_points = [
                "temperature가 낮으면 외부 근거 없이도 항상 최신 사실을 정확히 답합니다.",
                "프롬프트 형식만 바꾸면 최신 정보 부족 문제가 항상 해결됩니다.",
                "hallucination은 서버 지연 시간만을 의미합니다.",
                "system prompt가 있으면 별도 근거 검증은 필요 없습니다.",
            ]

        elif question_format == "ai_log_or_metric_interpretation":
            correct_points = [
                "context_provided가 False이고 temperature가 높은 상황에서는 관련 근거 문서를 제공하고 무작위성을 낮추는 방향을 검토해야 합니다."
            ]
            wrong_points = [
                "temperature를 더 높여 근거 없는 답변을 더 다양하게 생성합니다.",
                "최신 정보를 자동으로 알고 있다고 보고 외부 검색을 생략합니다.",
                "hallucination을 서버 교체만으로 해결하려고 합니다.",
                "모델 파라미터를 직접 수정하는 것을 즉시 우선합니다.",
            ]
    if topic_key == "rag":
        if question_format == "ai_scenario_best_action":
            scenario = (
                "사내 문서 기반 QA 시스템에서 사용자가 '보안 정책'을 질문했지만, "
                "검색 결과에 보안 문서와 프론트엔드 문서가 함께 포함되고 있습니다. "
                "문서에는 category metadata가 저장되어 있지만, 검색 요청에는 category 조건이 적용되지 않았습니다."
            )
            correct_points = [
                "metadata filter를 적용해 검색 대상 category를 보안 문서로 제한합니다."
            ]
            wrong_points = [
                "query rewrite를 적용해 사용자의 질문 표현을 더 구체화합니다.",
                "reranker를 적용해 검색된 후보 문서의 상위 순서를 재정렬합니다.",
                "chunk size와 overlap을 조정해 문서 분리 단위를 다시 구성합니다.",
                "top_k 값을 조정해 검색 후보 문서의 분포 변화를 비교합니다.",
            ]

        elif question_format == "ai_scenario_find_incorrect_action":
            scenario = (
                "RAG 기반 QA 시스템에서 검색 품질을 개선하려고 합니다. "
                "검색 결과에는 관련 문서도 포함되지만, 일부 질의에서는 관련성이 낮은 문서가 함께 섞입니다. "
                "팀은 검색 범위, 순위, chunk 품질, 질의 표현, 후보 수를 함께 검토하고 있습니다."
            )
            correct_points = [
                "top_k를 먼저 확대해 더 많은 검색 후보가 포함되는지 확인합니다."
            ]
            wrong_points = [
                "metadata filter를 검토해 검색 대상 문서의 범위를 제한합니다.",
                "reranker를 검토해 관련 문서가 상위에 오도록 재정렬합니다.",
                "chunk 분리 기준을 점검해 의미 단위가 깨지는지 확인합니다.",
                "query rewrite를 검토해 검색 질의의 의도를 더 명확히 합니다.",
            ]

        elif question_format == "ai_quality_issue_diagnosis":
            scenario = (
                "RAG 검색 결과의 similarity는 일부 높게 나오지만, 상위 chunk에는 질문의 핵심 개념보다 "
                "문서 안내 문구, 준비물 설명, 부가 설명이 자주 포함됩니다. "
                "검색된 문서의 category는 대체로 맞지만, chunk 내용의 밀도가 낮은 상태입니다."
            )
            correct_points = [
                "chunk 분리와 문서 전처리 과정에서 불필요한 내용이 포함되었는지 점검합니다."
            ]
            wrong_points = [
                "metadata filter 설정이 누락되어 다른 category 문서가 섞였는지 점검합니다.",
                "reranker 부재로 관련 chunk가 하위 순위에 머무르는지 점검합니다.",
                "keyword search 부재로 핵심 용어 포함 문서가 누락되는지 점검합니다.",
                "top_k 설정이 작아 충분한 후보 문서가 확보되지 않았는지 점검합니다.",
            ]

        elif question_format == "ai_method_compare_decision":
            scenario = (
                "RAG 시스템에서 관련 문서는 검색 결과 후보에 포함되지만, 핵심 근거가 되는 chunk가 자주 3~5위에 위치합니다. "
                "검색 범위는 적절하고 category 혼입은 크지 않지만, 최종 context에는 1~2위 결과가 주로 사용되고 있습니다."
            )
            correct_points = [
                "reranker를 적용해 후보 chunk의 관련도를 다시 평가하고 상위 순서를 조정합니다."
            ]
            wrong_points = [
                "metadata filter를 강화해 검색 대상 category 범위를 더 좁힙니다.",
                "chunk size를 줄여 각 chunk의 주제 밀도와 분리 단위를 조정합니다.",
                "query rewrite를 적용해 검색 질의를 더 구체적인 표현으로 바꿉니다.",
                "top_k를 늘려 검색 후보 문서를 더 많이 확보하도록 조정합니다.",
            ]

        elif question_format == "ai_log_or_metric_interpretation":
            correct_points = [
                "metadata filter를 적용해 검색 결과에서 다른 category 문서가 제외되도록 제한합니다."
            ]
            wrong_points = [
                "reranker를 적용해 현재 검색 결과의 similarity 순서를 다시 정렬합니다.",
                "chunk size를 조정해 검색된 문서 조각의 길이와 밀도를 개선합니다.",
                "query rewrite를 적용해 검색어를 더 구체적인 표현으로 변경합니다.",
                "top_k를 늘려 같은 질의에서 더 많은 후보 문서를 확인합니다.",
            ]
    return correct_points, wrong_points, scenario, log_or_metric

def _build_ai_intermediate_variant_evidence(
    *,
    topic_key: str,
    question_format: str,
    correct_points: list[str],
    wrong_points: list[str],
    scenario: str | None,
    log_or_metric: dict | None,
) -> tuple[list[str], list[str], str | None, dict | None]:
    variant_pool = AI_INTERMEDIATE_VARIANT_POOLS.get(topic_key)

    if not variant_pool:
        return correct_points, wrong_points, scenario, log_or_metric

    variants = variant_pool.get(question_format)

    if not variants:
        return correct_points, wrong_points, scenario, log_or_metric

    variant = _select_variant(variants)

    return (
        variant.get("correct_points", correct_points),
        variant.get("wrong_points", wrong_points),
        variant.get("scenario", scenario),
        variant.get("log_or_metric", log_or_metric),
    )

def _select_variant(
    variants: List[Dict[str, Any]],
    *,
    seed: Optional[int] = None,
    used_variant_ids: Optional[set[str]] = None,
) -> Dict[str, Any]:
    """
    같은 format 안에서도 다양한 evidence를 만들기 위한 variant 선택 함수.
    used_variant_ids가 있으면 같은 batch 안에서 중복 variant를 최대한 피한다.
    """
    if not variants:
        raise ValueError("variant list is empty")

    candidates = variants

    if used_variant_ids:
        filtered = [v for v in variants if v.get("variant_id") not in used_variant_ids]
        if filtered:
            candidates = filtered

    rng = random.Random(seed) if seed is not None else random
    return rng.choice(candidates)

