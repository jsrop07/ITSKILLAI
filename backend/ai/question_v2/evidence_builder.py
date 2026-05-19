
import random 
from typing import Any, Dict, List, Optional
from ai.question_v2.models import EvidencePack, QuestionFormatPlan

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
        "aliases": ["ml", "ML", "머신러닝", "모델 학습", "모델 평가"],
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

def normalize_ai_topic(topic: str) -> str:
    text = topic.strip().lower()

    for key, preset in AI_TOPIC_PRESETS.items():
        for alias in preset["aliases"]:
            if alias.lower() in text:
                return key

    # 사용자가 애매하게 입력하면 기본은 RAG로 두지 말고 LLM 일반 주제로 처리
    return "llm"


def build_evidence_pack(
    *,
    topic: str,
    difficulty: str,
    plan: QuestionFormatPlan,
) -> EvidencePack:
    topic_key = normalize_ai_topic(topic)
    preset = AI_TOPIC_PRESETS[topic_key]

    scenario = preset.get("scenario") if difficulty == "중급" else None
    log_or_metric = None

    if difficulty == "중급" and plan.question_format == "ai_log_or_metric_interpretation":
        log_or_metric = preset.get("log_or_metric")

    correct_points = preset["correct_points"]
    wrong_points = preset["wrong_points"]

    if difficulty == "중급" and topic_key == "rag":
        correct_points, wrong_points, scenario, log_or_metric = _build_rag_intermediate_variant_evidence(
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

    if "train_accuracy" in log_or_metric:
        return (
            "[평가 지표]\n"
            f"train_accuracy: {log_or_metric.get('train_accuracy')}\n"
            f"test_accuracy: {log_or_metric.get('test_accuracy')}\n"
            f"문제 상황: {log_or_metric.get('issue')}"
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

    if "temperature" in log_or_metric:
        return (
            "[응답 설정 로그]\n"
            f"prompt: {log_or_metric.get('prompt')}\n"
            f"context_provided: {log_or_metric.get('context_provided')}\n"
            f"temperature: {log_or_metric.get('temperature')}\n"
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

def _build_rag_intermediate_variant_evidence(
    *,
    question_format: str,
    correct_points: list[str],
    wrong_points: list[str],
    scenario: str | None,
    log_or_metric: dict | None,
) -> tuple[list[str], list[str], str | None, dict | None]:
    variants = RAG_INTERMEDIATE_VARIANTS.get(question_format)

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