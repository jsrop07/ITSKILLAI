import re
from typing import Any
from ai.questions.models import EvidencePack, QuestionFormatPlan

def _strip_rag_context_headers(text: str) -> str:
    if not text:
        return ""

    cleaned_lines = []

    for line in str(text).splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("[문서 "):
            continue
        if stripped.startswith("[역량유형:"):
            continue
        if stripped.startswith("[문서제목:"):
            continue
        if stripped.startswith("[출처유형:"):
            continue
        if stripped.startswith("[페이지"):
            continue

        cleaned_lines.append(stripped)

    cleaned = " ".join(cleaned_lines)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def _split_sentences(text: str) -> list[str]:
    if not text:
        return []

    parts = re.split(
        r"(?<=다\.)\s+|(?<=요\.)\s+|(?<=[.!?])\s+",
        text
    )

    sentences = []

    for part in parts:
        sentence = part.strip()

        if len(sentence) < 25:
            continue

        if len(sentence) > 280:
            sentence = sentence[:280].strip()

        sentences.append(sentence)

    return sentences

def _extract_rag_evidence_sentences(rag_context: str, limit: int = 5) -> list[str]:
    cleaned = _strip_rag_context_headers(rag_context)
    sentences = _split_sentences(cleaned)

    if not sentences and cleaned:
        return [cleaned[:300]]

    evidence_keywords = [
        "정의", "특징", "목적", "역할", "절차", "방법", "기준", "조건",
        "비교", "차이", "원인", "해결", "검증", "평가", "분석",
        "요구사항", "성능", "보안", "품질", "추적성",
        "RAG", "검색", "임베딩", "chunk", "metadata", "reranker",
        "RRF", "vector", "keyword", "hybrid", "LLM", "schema", "tool calling",
    ]

    scored = []

    for sentence in sentences:
        score = sum(1 for keyword in evidence_keywords if keyword in sentence)
        scored.append((score, sentence))

    scored.sort(key=lambda item: item[0], reverse=True)

    selected = [sentence for score, sentence in scored if score > 0]

    if not selected:
        selected = [sentence for _, sentence in scored]

    return selected[:limit]

CLAIM_SIGNAL_KEYWORDS = [
    "정의", "특징", "목적", "역할", "방법", "기준", "조건", "절차",
    "필요", "중요", "사용", "활용", "적용", "검증", "평가", "비교",
    "개선", "완화", "방지", "확인", "고려", "반영", "조정",
    "is", "are", "used", "use", "requires", "should", "can", "helps",
]

LOW_VALUE_CLAIM_KEYWORDS = [
    "교수자", "학습자", "평가자 질문", "학습 내용", "학습 목표",
    "수업", "평가지", "체크리스트", "자기진단", "라이선스",
    "파워포인트", "목차", "참고자료",

    # 추가
    "검색 결과 로그",
    "source chunk id",
    "similarity score",
    "retrieved_context_saved",
    "validation/reject",
    "parametric memory",
    "non-parametric memory",
    "RAG-Sequence",
    "RAG-Token",
    "retriever / generator",
]
EASY_HINT_PATTERNS = [
    "만 ",
    "항상",
    "무조건",
    "반드시 제거",
    "필요 없다",
    "필요 없습니다",
    "무시",
    "생략",
    "확인하지 않고",
    "검토하지 않고",
    "이해합니다",
    "검색합니다",
]

FOCUS_KEYWORDS = {
    "fine_tuning": ["fine-tuning", "fine tuning", "finetuning", "파인튜닝", "사전학습", "추가 학습", "도메인", "작업"],
    "transfer_learning": ["transfer learning", "전이학습", "pretrained", "사전학습", "feature reuse"],
    "deep_learning_overfitting": ["overfitting", "과적합", "validation loss", "train loss", "dropout", "regularization", "early stopping"],
    "rrf_merge": ["rrf", "rank", "순위", "병합", "vector rank", "keyword rank"],
    "hybrid_search": ["hybrid", "vector", "keyword", "fulltext", "하이브리드", "벡터", "키워드"],
    "metadata_filter": ["metadata", "category", "메타데이터", "카테고리", "문서 범위", "출처"],
    "context_filter": ["chunk", "context", "noise", "노이즈", "청크", "품질"],
    "reranker": ["reranker", "rank", "재정렬", "상위", "후보"],
    "structured_output": ["structured output", "json schema", "required", "enum", "schema", "검증"],
    "tool_calling": ["tool calling", "function calling", "arguments", "tool name", "schema"],
    "llm_grounding": ["grounding", "hallucination", "근거", "출처", "context"],
}
RAG_FOCUS_VARIANTS = {
    "rrf_merge": [
        {
            "variant_id": "rrf_rank_merge_basic",
            "body_context": [
                "Hybrid RAG에서는 vector 검색과 keyword 검색의 순위가 다르게 나타날 수 있습니다.",
                "RRF는 서로 다른 검색 결과의 rank를 함께 반영해 최종 근거 우선순위를 정하는 데 사용됩니다.",
            ],
            "scenario": (
                "문서 검색 로그에서 vector search와 keyword search의 상위 결과가 서로 다르게 나타났습니다. "
                "팀은 두 검색 결과를 어떻게 결합해야 문제 생성에 사용할 근거 chunk의 우선순위를 안정적으로 정할 수 있을지 판단하려고 합니다."
            ),
            "correct": "vector rank와 keyword rank를 함께 반영해 최종 근거 우선순위를 정합니다.",
            "wrong": [
                "검색 후보 수를 늘린 뒤 상위 chunk의 출처와 중복 여부를 검토합니다.",
                "vector similarity가 높은 결과를 우선 보고 keyword 결과를 보조로 비교합니다.",
                "keyword raw score와 vector similarity를 정규화해 하나의 점수로 비교합니다.",
                "reranker로 이미 검색된 후보의 문맥 관련성을 다시 평가합니다.",
            ],
        },
        {
            "variant_id": "rrf_score_scale_mismatch",
            "body_context": [
                "vector similarity와 keyword raw score는 계산 기준과 점수 범위가 다를 수 있습니다.",
                "RRF는 원점수 합산 대신 각 검색기의 rank를 기준으로 결과를 병합합니다.",
            ],
            "scenario": (
                "팀은 hybrid search 결과를 만들기 위해 vector similarity와 keyword raw score를 그대로 더하려고 합니다. "
                "하지만 두 점수의 스케일이 달라 특정 검색 방식의 점수가 과도하게 반영될 수 있습니다."
            ),
            "correct": "원점수 합산 대신 각 검색기의 rank를 기준으로 RRF 점수를 계산합니다.",
            "wrong": [
                "vector similarity가 높은 chunk를 중심으로 최종 context를 구성합니다.",
                "keyword raw score가 높은 chunk를 우선 사용하고 vector 결과를 참고합니다.",
                "검색 후보 수를 늘려 점수 스케일 차이의 영향을 줄입니다.",
                "reranker로 후보의 문맥 관련성만 다시 평가합니다.",
            ],
        },
        {
            "variant_id": "rrf_dual_retriever_overlap",
            "body_context": [
                "두 검색 방식에 함께 등장한 chunk는 여러 기준에서 관련성이 확인된 후보일 수 있습니다.",
                "RRF는 각 검색 결과의 순위를 누적해 공통으로 강한 후보를 상위에 배치할 수 있습니다.",
            ],
            "scenario": (
                "검색 결과에서 한 chunk는 vector search와 keyword search 양쪽에 모두 포함되었고, "
                "다른 chunk들은 한쪽 검색 결과에만 나타났습니다. 팀은 어떤 chunk를 우선 근거로 볼지 판단해야 합니다."
            ),
            "correct": "두 검색 결과에 함께 등장한 chunk의 rank를 누적해 우선순위를 판단합니다.",
            "wrong": [
                "vector 결과에만 있는 chunk를 의미 유사도 기준으로 우선 검토합니다.",
                "keyword 결과에만 있는 chunk를 용어 일치 기준으로 우선 검토합니다.",
                "검색 후보 수를 늘려 양쪽 검색 결과의 공통 후보를 더 확인합니다.",
                "reranker로 후보 chunk의 문맥 관련성을 다시 비교합니다.",
            ],
        },
    ],
    "metadata_filter": [
        {
            "variant_id": "metadata_category_scope",
            "body_context": [
                "RAG 검색에서는 문서의 category와 출처 조건이 검색 범위 제한에 사용될 수 있습니다.",
                "metadata filter가 누락되면 요청 범위와 다른 문서가 함께 검색될 수 있습니다.",
            ],
            "scenario": (
                "사내 QA 시스템에서 사용자는 인사 규정에 대해 질문했지만, 검색 결과에는 개발 문서와 보안 문서가 함께 포함되었습니다. "
                "문서에는 category metadata가 저장되어 있으며, 팀은 요청 범위에 맞는 근거만 사용하려고 합니다."
            ),
            "correct": "문서 category 조건을 적용해 요청 범위에 맞는 검색 결과를 사용합니다.",
            "wrong": [
                "query rewrite로 사용자의 질문 표현을 더 구체화합니다.",
                "reranker로 검색 후보의 문맥 관련성을 다시 평가합니다.",
                "검색 후보 수를 늘려 관련 문서 누락 가능성을 줄입니다.",
                "chunk 크기와 overlap을 조정해 문맥 단절을 줄입니다.",
            ],
        },
        {
            "variant_id": "metadata_source_type_filter",
            "body_context": [
                "문서 출처와 source_type은 검색 결과의 신뢰도와 사용 범위를 판단하는 기준이 될 수 있습니다.",
                "검색 조건에 출처 제한이 없으면 목적과 다른 문서가 근거로 섞일 수 있습니다.",
            ],
            "scenario": (
                "문제 생성 시스템이 공식 가이드 문서를 기준으로 문제를 만들도록 설정되었지만, 검색 결과에는 실험용 메모와 임시 정리 문서가 함께 포함되었습니다. "
                "팀은 검수 가능한 근거 문서만 문제 생성에 사용하려고 합니다."
            ),
            "correct": "source_type과 문서 출처 조건을 적용해 검수 가능한 근거만 사용합니다.",
            "wrong": [
                "vector similarity가 높은 chunk를 우선 사용하고 출처는 검수 단계에서 확인합니다.",
                "검색 후보 수를 늘려 공식 문서가 포함될 가능성을 높입니다.",
                "LLM 프롬프트에 공식 문서 중심으로 답하라고 추가합니다.",
                "reranker로 후보 문서의 문맥 관련성만 다시 평가합니다.",
            ],
        },
        {
            "variant_id": "metadata_mixed_competency",
            "body_context": [
                "문제 생성용 RAG에서는 역량 유형과 문서 category가 문제 범위와 일치해야 합니다.",
                "다른 역량 문서가 섞이면 선택지와 해설이 현재 출제 범위에서 벗어날 수 있습니다.",
            ],
            "scenario": (
                "AI 문제를 생성하는 과정에서 검색 결과에 SQL과 정보보안 문서가 함께 포함되었습니다. "
                "검색된 chunk의 similarity는 높지만, 일부 문서는 현재 출제 역량과 category가 다릅니다."
            ),
            "correct": "competency와 category metadata를 확인해 현재 출제 범위의 문서만 사용합니다.",
            "wrong": [
                "similarity가 높은 chunk를 모두 사용해 문제 소재를 다양화합니다.",
                "query rewrite로 검색어를 더 길게 만들어 관련 문서를 다시 찾습니다.",
                "검색 top_k를 늘려 더 많은 후보 chunk를 확보합니다.",
                "선택지 생성 prompt에 AI 용어를 더 많이 포함하도록 지시합니다.",
            ],
        },
    ],
    "context_filter": [
        {
            "variant_id": "context_noise_chunk",
            "body_context": [
                "검색 결과에는 문제 근거로 쓰기 어려운 안내문, 목차, 평가 문구가 포함될 수 있습니다.",
                "context filter는 근거로 적합한 chunk를 선별해 생성 품질을 높이는 데 사용됩니다.",
            ],
            "scenario": (
                "문서 검색 결과에 관련 개념 설명도 있지만, 일부 chunk에는 목차와 교수자 안내 문구가 포함되어 있습니다. "
                "팀은 문제 생성에 사용할 근거 context를 선별해야 합니다."
            ),
            "correct": "chunk의 내용과 출처를 검토해 문제 근거로 적합한 context만 사용합니다.",
            "wrong": [
                "query rewrite로 검색어 표현을 더 명확하게 조정합니다.",
                "metadata 조건을 적용해 문서 범위 혼입을 줄입니다.",
                "검색 top_k를 늘려 더 많은 chunk를 context에 포함합니다.",
                "reranker로 후보 chunk의 순서를 다시 평가합니다.",
            ],
        },
        {
            "variant_id": "context_too_many_chunks",
            "body_context": [
                "검색 결과가 너무 많거나 서로 다른 주제가 섞이면 generator가 핵심 근거를 혼동할 수 있습니다.",
                "문제 생성에는 관련성과 품질이 높은 context를 제한적으로 제공하는 것이 중요합니다.",
            ],
            "scenario": (
                "RAG 문제 생성에서 top_k를 크게 설정한 뒤, LLM이 서로 다른 문서의 내용을 섞어 선택지를 만들었습니다. "
                "팀은 생성에 사용할 context 수와 품질을 조정하려고 합니다."
            ),
            "correct": "quality_score와 근거 적합성을 기준으로 사용할 context를 선별합니다.",
            "wrong": [
                "검색 후보 수를 더 늘려 LLM이 다양한 근거를 참고하게 합니다.",
                "프롬프트에 선택지를 더 구체적으로 쓰라고 지시합니다.",
                "metadata filter로 문서 범위를 먼저 좁히는 방안을 검토합니다.",
                "reranker로 후보 chunk의 문맥 관련성을 다시 평가합니다.",
            ],
        },
        {
            "variant_id": "context_low_evidence_score",
            "body_context": [
                "근거 신호가 약한 chunk는 문제의 정답과 해설을 뒷받침하기 어렵습니다.",
                "evidence_score와 structure_score는 문제 생성에 적합한 context를 고르는 데 활용될 수 있습니다.",
            ],
            "scenario": (
                "검색된 chunk의 similarity는 높지만, 실제 내용은 짧은 용어 나열과 안내 문장 위주입니다. "
                "팀은 해당 chunk를 문제 생성 근거로 사용할지 판단해야 합니다."
            ),
            "correct": "evidence_score와 structure_score를 함께 확인해 근거성이 낮은 chunk를 제외합니다.",
            "wrong": [
                "similarity가 높으므로 해당 chunk를 우선 문제 근거로 사용합니다.",
                "keyword score가 낮은 chunk만 제외하고 나머지는 모두 유지합니다.",
                "검색 query를 길게 바꿔 동일 문서를 다시 검색합니다.",
                "LLM 해설에서 부족한 근거를 자연어로 보완하게 합니다.",
            ],
        },
    ],
    "reranker": [
        {
            "variant_id": "reranker_relevant_but_low_rank",
            "body_context": [
                "관련 문서가 검색 후보에 포함되어도 최종 상위 context에 배치되지 않을 수 있습니다.",
                "reranker는 검색 후보의 문맥 관련성을 다시 평가해 순서를 조정하는 데 사용됩니다.",
            ],
            "scenario": (
                "사용자 질문과 직접 관련된 chunk가 검색 후보에는 포함되었지만, 최종 상위 context에는 덜 관련된 chunk가 먼저 배치되었습니다. "
                "팀은 후보 문서의 순서를 다시 조정하려고 합니다."
            ),
            "correct": "reranker로 후보 chunk의 문맥 관련성을 재평가해 상위 순서를 조정합니다.",
            "wrong": [
                "metadata filter로 요청 범위와 다른 category 문서를 줄입니다.",
                "query rewrite로 사용자 질문의 표현을 더 구체화합니다.",
                "검색 top_k를 늘려 더 많은 후보 chunk를 확보합니다.",
                "chunk 전처리 기준을 조정해 문맥 단절을 줄입니다.",
            ],
        },
        {
            "variant_id": "reranker_semantic_tie_break",
            "body_context": [
                "vector similarity가 비슷한 후보들이 있을 때는 문맥 적합도를 추가로 비교해야 할 수 있습니다.",
                "reranker는 후보 간 의미적 우선순위를 더 세밀하게 조정하는 데 활용됩니다.",
            ],
            "scenario": (
                "검색 결과 상위 chunk들의 similarity가 비슷하지만, 일부는 질문의 핵심 조건과 직접 연결되지 않습니다. "
                "팀은 어떤 후보를 최종 context로 우선 사용할지 판단해야 합니다."
            ),
            "correct": "reranker로 질문 조건과 후보 chunk의 문맥 일치도를 다시 비교합니다.",
            "wrong": [
                "similarity 소수점 차이가 가장 큰 chunk를 최종 근거로 선택합니다.",
                "keyword raw score가 있는 chunk만 우선 context로 사용합니다.",
                "metadata filter로 문서 category만 다시 확인합니다.",
                "검색 후보 수를 늘려 상위 결과의 다양성을 확보합니다.",
            ],
        },
        {
            "variant_id": "reranker_after_hybrid",
            "body_context": [
                "Hybrid search는 후보를 넓게 찾는 데 유리하지만, 최종 순서가 항상 최적이라는 보장은 없습니다.",
                "RRF 이후에도 후보 간 문맥 적합도를 다시 평가할 수 있습니다.",
            ],
            "scenario": (
                "Hybrid RAG와 RRF 병합으로 후보 chunk를 확보했지만, 최종 상위 결과에 질문 조건과 덜 맞는 문서가 포함되었습니다. "
                "팀은 최종 context 순서를 한 번 더 정교화하려고 합니다."
            ),
            "correct": "RRF로 병합한 후보를 reranker로 재평가해 최종 context 순서를 조정합니다.",
            "wrong": [
                "vector search 결과만 남기고 keyword search 결과는 제외합니다.",
                "keyword raw score와 vector similarity를 단순 합산합니다.",
                "metadata 조건을 제거해 더 많은 후보를 확보합니다.",
                "chunk 길이가 긴 문서를 우선 context로 사용합니다.",
            ],
        },
    ],
    "hybrid_search": [
        {
            "variant_id": "hybrid_semantic_and_keyword",
            "body_context": [
                "vector search는 의미적으로 유사한 문서를 찾는 데 강점이 있습니다.",
                "keyword search는 정확한 용어와 식별자가 포함된 문서를 찾는 데 유리합니다.",
            ],
            "scenario": (
                "사용자 질문에는 자연어 표현과 정확한 기술 용어가 함께 포함되어 있습니다. "
                "하나의 검색 방식만 사용하면 일부 근거 문서가 누락될 수 있습니다."
            ),
            "correct": "vector search와 keyword search를 함께 사용해 의미와 용어 일치를 모두 반영합니다.",
            "wrong": [
                "query rewrite로 질문 표현을 더 구체화합니다.",
                "reranker로 검색 후보의 문맥 적합도를 다시 평가합니다.",
                "metadata 조건을 적용해 문서 범위 혼입을 줄입니다.",
                "검색 후보 수를 늘려 더 많은 chunk를 검토합니다.",
            ],
        },
        {
            "variant_id": "hybrid_exact_term_recall",
            "body_context": [
                "정확한 기술 용어가 중요한 질문에서는 keyword search가 근거 누락을 줄이는 데 도움이 됩니다.",
                "의미 유사도만으로는 약어, 함수명, 설정값 같은 표현을 놓칠 수 있습니다.",
            ],
            "scenario": (
                "사용자가 특정 설정값과 기술 용어가 포함된 질문을 했지만, vector search 결과는 의미적으로 비슷한 일반 설명 위주로 검색되었습니다. "
                "팀은 정확한 용어가 포함된 문서도 함께 찾으려고 합니다."
            ),
            "correct": "keyword search를 함께 적용해 정확한 용어가 포함된 문서를 후보에 포함합니다.",
            "wrong": [
                "vector similarity 기준을 낮춰 더 많은 의미 유사 문서를 가져옵니다.",
                "reranker로 이미 검색된 후보의 순서만 다시 조정합니다.",
                "metadata filter로 문서 category 범위를 제한합니다.",
                "chunk overlap을 늘려 문맥 단절 가능성을 줄입니다.",
            ],
        },
        {
            "variant_id": "hybrid_semantic_recall",
            "body_context": [
                "사용자 표현이 문서의 정확한 용어와 다를 때는 vector search가 의미 기반 검색에 도움이 됩니다.",
                "keyword search만 사용하면 같은 의미의 다른 표현을 놓칠 수 있습니다.",
            ],
            "scenario": (
                "사용자는 쉬운 표현으로 질문했지만 문서에는 다른 기술 용어로 설명되어 있습니다. "
                "keyword search 결과는 부족하고, 팀은 의미적으로 가까운 근거 문서까지 찾으려고 합니다."
            ),
            "correct": "vector search를 함께 적용해 표현이 달라도 의미가 가까운 문서를 후보에 포함합니다.",
            "wrong": [
                "keyword query에 더 많은 동의어를 직접 추가합니다.",
                "metadata filter로 문서 범위를 먼저 제한합니다.",
                "검색 후보 수를 늘려 keyword 결과를 더 많이 확보합니다.",
                "reranker로 keyword search 후보의 순서만 다시 평가합니다.",
            ],
        },
    ],
}

RAG_FOCUS_VARIANTS.update({
    # ─────────────────────────────────────
    # LLM 계열
    # ─────────────────────────────────────
    "structured_output": [
        {
            "variant_id": "structured_output_required_fields",
            "body_context": [
                "Structured Output은 LLM 응답이 정해진 JSON Schema와 필수 필드 조건을 따르도록 제한하는 방식입니다.",
                "JSON 형식으로 파싱되더라도 required 필드, enum 값, answer 범위 같은 비즈니스 규칙 검증이 필요합니다.",
            ],
            "scenario": (
                "AI 문제 생성 API에서 LLM 응답이 JSON 형식으로 파싱되었지만, "
                "일부 필수 필드가 누락되고 answer 값의 범위도 검증되지 않은 상태입니다. "
                "팀은 저장 전에 응답 구조의 정합성을 확인하려고 합니다."
            ),
            "correct": "required 필드, enum 값, answer 범위를 서버 측 schema로 검증합니다.",
            "wrong": [
                "프롬프트에 JSON 형식을 더 명확히 요청해 출력 형식을 유도합니다.",
                "temperature를 낮춰 응답 형식의 변동성을 줄입니다.",
                "few-shot 예시를 추가해 원하는 응답 구조를 보여줍니다.",
                "파서에서 누락 필드를 기본값으로 보정하는 규칙을 추가합니다.",
            ],
        },
        {
            "variant_id": "structured_output_business_rule",
            "body_context": [
                "Structured Output에서는 JSON 파싱 성공 여부와 비즈니스 규칙 검증을 분리해서 확인해야 합니다.",
                "문제 생성 결과는 choices 개수, answer 매핑, explanation 정합성 같은 서비스 규칙도 만족해야 합니다.",
            ],
            "scenario": (
                "LLM이 문제 JSON을 반환했고 파싱도 성공했습니다. "
                "그러나 choices는 4개만 생성되었고, explanation은 answer와 다른 정답 번호를 설명하고 있습니다. "
                "팀은 이 응답을 저장할지 판단해야 합니다."
            ),
            "correct": "JSON 파싱 이후 choices 개수와 answer-explanation 정합성을 추가 검증합니다.",
            "wrong": [
                "JSON 파싱이 성공했으므로 저장 단계로 바로 전달합니다.",
                "프롬프트에 객관식 형식을 다시 설명해 다음 응답 품질을 개선합니다.",
                "answer 번호를 임의로 수정해 저장 가능한 형태로 맞춥니다.",
                "LLM 응답 원문을 로그에 남기고 검수자가 나중에 확인하게 합니다.",
            ],
        },
        {
            "variant_id": "structured_output_retry_repair",
            "body_context": [
                "LLM 응답이 schema를 만족하지 않으면 저장하지 않고 retry 또는 repair 대상으로 분리해야 합니다.",
                "자동 보정은 가능한 범위를 제한하고, 핵심 정답 정합성은 검증 기준으로 판단해야 합니다.",
            ],
            "scenario": (
                "문제 생성 결과에서 title과 body는 정상으로 보이지만 answer 값이 6으로 생성되었습니다. "
                "선택지는 5개뿐이므로 저장하면 채점 오류가 발생할 수 있습니다."
            ),
            "correct": "answer 범위 오류를 검증 실패로 처리하고 retry 또는 repair 흐름으로 보냅니다.",
            "wrong": [
                "answer 값을 가장 가까운 선택지 번호로 자동 변경해 저장합니다.",
                "문제 본문이 자연스러우면 answer 범위 오류는 검수 단계로 넘깁니다.",
                "프롬프트 예시를 늘려 다음 생성 결과의 형식을 개선합니다.",
                "temperature를 낮춰 이후 응답의 형식 변동성을 줄입니다.",
            ],
        },
    ],

    "tool_calling": [
        {
            "variant_id": "tool_calling_arguments_schema",
            "body_context": [
                "Tool calling에서는 LLM이 반환한 tool name과 arguments를 실행 전에 검증해야 합니다.",
                "arguments의 타입, 필수 값, 허용 범위를 서버 측 schema 기준으로 확인해야 합니다.",
            ],
            "scenario": (
                "LLM이 외부 검색 도구를 호출하겠다고 응답했지만, arguments에 허용되지 않은 필드와 잘못된 타입의 값이 포함되어 있습니다. "
                "팀은 도구 실행 전에 안전한 검증 흐름을 적용하려고 합니다."
            ),
            "correct": "tool name과 arguments를 서버 측 schema와 허용 규칙으로 검증합니다.",
            "wrong": [
                "프롬프트에 올바른 tool 호출 예시를 추가해 다음 응답을 유도합니다.",
                "tool 호출 실패 로그를 수집해 반복 오류 패턴을 분석합니다.",
                "사용자 질문 intent를 다시 분류해 필요한 도구를 재확인합니다.",
                "응답 JSON을 파싱한 뒤 누락 필드를 기본값으로 보완합니다.",
            ],
        },
        {
            "variant_id": "tool_calling_allowed_tool",
            "body_context": [
                "Tool calling 결과는 모델이 제안한 도구 이름을 그대로 실행하지 않고 허용 목록과 비교해야 합니다.",
                "허용되지 않은 도구나 위험한 arguments는 실행 전에 차단해야 합니다.",
            ],
            "scenario": (
                "LLM이 사용자의 요청을 처리하면서 내부 관리자 전용 tool을 호출하려고 합니다. "
                "응답 형식은 올바르지만, 해당 tool은 일반 사용자 요청에서 허용되지 않은 기능입니다."
            ),
            "correct": "허용된 tool 목록과 권한 규칙을 확인한 뒤 실행 여부를 결정합니다.",
            "wrong": [
                "tool name이 JSON에 포함되어 있으므로 그대로 실행합니다.",
                "tool 호출 예시를 프롬프트에 추가해 다음 응답을 안정화합니다.",
                "arguments 타입만 맞으면 tool 권한 검사는 검수 단계로 넘깁니다.",
                "도구 실행 결과를 보고 문제가 있으면 사후에 차단합니다.",
            ],
        },
        {
            "variant_id": "tool_calling_failure_handling",
            "body_context": [
                "Tool calling 실패 시에는 원인 로그를 남기고 안전한 fallback 응답을 제공해야 합니다.",
                "외부 도구 오류를 사용자에게 그대로 노출하면 보안 정보나 내부 구조가 드러날 수 있습니다.",
            ],
            "scenario": (
                "LLM이 외부 API tool을 호출했지만 timeout이 발생했습니다. "
                "현재 시스템은 원본 오류 메시지와 내부 endpoint 정보를 사용자에게 그대로 반환하려고 합니다."
            ),
            "correct": "tool 실패 원인을 로그로 남기고 사용자에게는 안전한 fallback 응답을 제공합니다.",
            "wrong": [
                "외부 API endpoint와 원본 오류를 그대로 사용자에게 전달합니다.",
                "tool 호출을 중단하고 모든 요청을 일반 LLM 답변으로 처리합니다.",
                "temperature를 낮춰 tool 호출 실패 가능성을 줄입니다.",
                "프롬프트에 오류를 친절하게 설명하라는 문장을 추가합니다.",
            ],
        },
    ],

    "llm_grounding": [
        {
            "variant_id": "grounding_missing_context",
            "body_context": [
                "근거가 중요한 질문에서는 관련 context와 출처를 함께 제공해야 hallucination 위험을 줄일 수 있습니다.",
                "LLM 답변이 자연스럽더라도 근거 문서가 없으면 최신성이나 사실성을 보장하기 어렵습니다.",
            ],
            "scenario": (
                "사내 챗봇이 최신 보안 정책 질문에 자연스럽게 답변했지만, "
                "참고 문서나 검색 결과가 제공되지 않았고 답변 출처도 남아 있지 않습니다."
            ),
            "correct": "관련 정책 문서를 context로 제공하고 답변에 사용된 출처를 함께 기록합니다.",
            "wrong": [
                "temperature를 낮춰 답변 표현의 변동성을 줄입니다.",
                "system prompt에 친절하고 단정적으로 답하라는 지시를 추가합니다.",
                "few-shot 예시를 추가해 답변 형식을 더 안정화합니다.",
                "모델 응답 시간이 길어지지 않도록 검색 단계를 줄입니다.",
            ],
        },
        {
            "variant_id": "grounding_context_answer_mismatch",
            "body_context": [
                "RAG 답변은 제공된 context와 생성된 답변 내용이 일치하는지 확인해야 합니다.",
                "검색된 근거와 다른 내용을 답하면 출처를 제공하더라도 신뢰성이 낮아질 수 있습니다.",
            ],
            "scenario": (
                "LLM이 검색된 문서를 참고해 답변했지만, 답변 내용 일부가 제공된 context와 다르게 생성되었습니다. "
                "팀은 근거 기반 응답의 신뢰성을 높이려고 합니다."
            ),
            "correct": "답변 내용이 제공된 context와 일치하는지 검증하고 불일치 시 재생성합니다.",
            "wrong": [
                "답변에 출처 링크가 있으므로 내용 불일치는 허용합니다.",
                "검색 top_k를 늘려 더 많은 문서를 LLM에 전달합니다.",
                "프롬프트에 더 확신 있게 답하라는 지시를 추가합니다.",
                "temperature를 낮춰 문장 표현의 변동성을 줄입니다.",
            ],
        },
        {
            "variant_id": "grounding_source_trace",
            "body_context": [
                "근거 추적이 필요한 서비스에서는 어떤 chunk가 답변 생성에 사용되었는지 저장해야 합니다.",
                "source chunk를 남기면 검수자가 답변의 근거와 생성 결과를 비교할 수 있습니다.",
            ],
            "scenario": (
                "문서 기반 답변은 생성되었지만, 어떤 문서와 chunk를 근거로 사용했는지 저장되지 않았습니다. "
                "운영자는 검수 화면에서 답변의 근거를 확인할 수 없는 상태입니다."
            ),
            "correct": "답변 생성에 사용된 문서명, chunk_id, score, content_preview를 함께 저장합니다.",
            "wrong": [
                "답변 문장이 자연스러우면 별도 근거 추적 없이 저장합니다.",
                "검색 query만 저장하고 실제 사용된 chunk 정보는 생략합니다.",
                "LLM에게 출처를 자연어로 쓰게 하고 서버 저장은 줄입니다.",
                "검수자가 필요할 때 같은 query로 다시 검색하도록 안내합니다.",
            ],
        },
    ],

    # ─────────────────────────────────────
    # ModelOps 계열
    # ─────────────────────────────────────
    "modelops_serving": [
        {
            "variant_id": "serving_latency_after_deploy",
            "body_context": [
                "모델 운영에서는 정확도뿐 아니라 latency, timeout, 리소스 사용량을 함께 확인해야 합니다.",
                "배포 직후 지연이 증가하면 모델 버전과 serving 설정 변화를 함께 점검해야 합니다.",
            ],
            "scenario": (
                "모델 API를 새 버전으로 배포한 뒤 운영 로그에서 avg latency 420ms→980ms, "
                "p95 latency 1.2s→3.8s, timeout 비율 1%→7%로 증가했습니다. "
                "입력 데이터 분포 변화는 아직 뚜렷하지 않으며, 사용자는 응답 지연을 경험하고 있습니다."
            ),
            "correct": "배포 버전별 latency, timeout 로그, 서빙 리소스 사용량을 함께 확인합니다.",
            "wrong": [
                "운영 데이터의 입력 분포 변화를 drift 기준으로 먼저 비교합니다.",
                "학습 데이터셋을 확장해 다음 모델 재학습 계획을 세웁니다.",
                "프롬프트 예시를 추가해 응답 형식 안정성을 개선합니다.",
                "threshold를 조정해 positive 예측 비율의 변화를 확인합니다.",
            ],
        },
        {
            "variant_id": "serving_cost_latency_tradeoff",
            "body_context": [
                "모델 서빙에서는 응답 품질, latency, 비용 사이의 trade-off를 함께 고려해야 합니다.",
                "모델 크기나 추론 설정이 바뀌면 비용과 지연 시간이 함께 변할 수 있습니다.",
            ],
            "scenario": (
                "팀은 더 큰 모델로 교체한 뒤 답변 품질은 좋아졌지만 p95 latency와 GPU 비용이 크게 증가한 것을 확인했습니다. "
                "운영 환경에서 계속 사용할 수 있는지 판단해야 합니다."
            ),
            "correct": "품질 개선 폭과 p95 latency, GPU 비용을 함께 비교해 서빙 전략을 조정합니다.",
            "wrong": [
                "정확도 지표가 좋아졌으므로 비용과 latency 검토를 배포 이후로 미룹니다.",
                "입력 데이터 drift를 먼저 분석해 성능 저하 여부를 확인합니다.",
                "검색 context 품질을 높여 모델 크기 증가 문제를 보완합니다.",
                "프롬프트 문장을 줄여 모델 비용 증가 문제를 모두 해결합니다.",
            ],
        },
        {
            "variant_id": "serving_rollback_decision",
            "body_context": [
                "배포 후 장애 지표가 증가하면 원인 확인과 함께 롤백 가능성을 검토해야 합니다.",
                "모델 버전, API 오류율, timeout 비율은 운영 안정성 판단에 중요한 지표입니다.",
            ],
            "scenario": (
                "새 모델 배포 후 특정 시간대에 timeout 비율과 5xx 오류가 증가했습니다. "
                "비즈니스 영향이 커지고 있어 팀은 즉시 대응 방안을 정해야 합니다."
            ),
            "correct": "배포 버전과 장애 로그를 확인하고 필요하면 이전 안정 버전으로 롤백합니다.",
            "wrong": [
                "장애 시간대의 요청량과 오류 로그를 함께 확인합니다.",
                "영향을 받은 API endpoint와 모델 버전을 비교합니다.",
                "사용자 영향 범위를 확인해 임시 우회 안내를 검토합니다.",
                "모니터링 지표를 기준으로 롤백 여부를 운영팀과 공유합니다.",
            ],
        },
    ],

    "modelops_monitoring": [
        {
            "variant_id": "monitoring_data_drift",
            "body_context": [
                "운영 데이터 분포가 학습 시점과 달라지면 model quality가 저하될 수 있습니다.",
                "data drift는 입력 분포 변화와 성능 하락을 함께 확인해 판단해야 합니다.",
            ],
            "scenario": (
                "운영 중인 예측 모델의 최근 성능이 하락했고, 입력 feature 분포가 학습 시점과 달라졌다는 신호가 관찰되었습니다. "
                "팀은 성능 저하 원인을 확인하려고 합니다."
            ),
            "correct": "운영 입력 데이터와 학습 데이터의 분포 차이를 drift 기준으로 분석합니다.",
            "wrong": [
                "서빙 latency가 안정적이면 모델 품질 문제는 아니라고 판단합니다.",
                "프롬프트 예시를 추가해 모델 출력 형식을 안정화합니다.",
                "검색 context 품질을 점검해 답변 근거 누락을 줄입니다.",
                "GPU 리소스를 늘려 추론 처리량을 먼저 개선합니다.",
            ],
        },
        {
            "variant_id": "monitoring_segment_quality_drop",
            "body_context": [
                "전체 성능 평균이 안정적이어도 특정 사용자군이나 데이터 세그먼트에서 품질이 하락할 수 있습니다.",
                "운영 모니터링은 전체 지표와 세그먼트별 지표를 함께 확인해야 합니다.",
            ],
            "scenario": (
                "전체 모델 정확도는 큰 변화가 없지만 특정 지역 사용자 데이터에서 오류율이 증가했습니다. "
                "팀은 운영 품질 저하가 일부 세그먼트에 집중되는지 확인하려고 합니다."
            ),
            "correct": "전체 지표와 세그먼트별 오류율을 함께 비교해 품질 저하 범위를 확인합니다.",
            "wrong": [
                "전체 accuracy가 유지되므로 세그먼트별 오류율은 검토하지 않습니다.",
                "서빙 리소스를 늘려 모든 사용자 요청의 처리량을 개선합니다.",
                "학습 epoch를 늘려 다음 모델의 train accuracy를 높입니다.",
                "검색 query를 구체화해 관련 문서 누락 가능성을 줄입니다.",
            ],
        },
        {
            "variant_id": "monitoring_feedback_loop",
            "body_context": [
                "운영 환경에서는 사용자 피드백과 예측 결과 로그를 함께 수집해 품질 개선에 활용할 수 있습니다.",
                "모니터링은 단순 지표 확인을 넘어 재학습 또는 개선 판단의 근거가 됩니다.",
            ],
            "scenario": (
                "운영 중인 모델에 대해 사용자 불만이 증가하고 있지만, 현재 시스템은 예측 로그와 피드백을 연결해 저장하지 않습니다. "
                "팀은 개선 대상을 구체적으로 파악하려고 합니다."
            ),
            "correct": "예측 로그와 사용자 피드백을 함께 수집해 오류 유형과 개선 대상을 분석합니다.",
            "wrong": [
                "모델 응답 시간을 줄이기 위해 serving 리소스를 먼저 증설합니다.",
                "학습 데이터 전체를 무작위로 늘려 다음 모델을 재학습합니다.",
                "프롬프트 문장을 수정해 사용자 불만을 자연어로 완화합니다.",
                "정확도 평균이 유지되는 동안 세부 오류 분석은 보류합니다.",
            ],
        },
    ],

    # ─────────────────────────────────────
    # ML 계열
    # ─────────────────────────────────────
    "model_evaluation": [
        {
            "variant_id": "evaluation_accuracy_vs_recall",
            "body_context": [
                "분류 모델은 accuracy만으로 평가하면 목적에 맞지 않는 결정을 할 수 있습니다.",
                "소수 클래스 탐지가 중요한 문제에서는 recall과 precision을 함께 확인해야 합니다.",
            ],
            "scenario": (
                "불량 탐지 모델의 전체 accuracy는 0.96으로 높지만 실제 불량 클래스 recall은 0.28에 머물고 있습니다. "
                "팀은 운영 목적에 맞는 평가 기준을 다시 정하려고 합니다."
            ),
            "correct": "불량 클래스 recall과 precision을 함께 확인해 모델 개선 방향을 판단합니다.",
            "wrong": [
                "전체 accuracy가 높으므로 현재 모델을 운영 기준으로 선택합니다.",
                "feature importance를 확인해 주요 입력 변수만 해석합니다.",
                "교차 검증 fold별 accuracy 변동을 비교합니다.",
                "학습 데이터 수를 늘려 전체 표본 규모를 확장합니다.",
            ],
        },
        {
            "variant_id": "evaluation_precision_recall_tradeoff",
            "body_context": [
                "precision과 recall은 모델 목적에 따라 trade-off를 고려해야 하는 지표입니다.",
                "오탐과 미탐의 비용이 다르면 threshold별 지표 변화를 비교해야 합니다.",
            ],
            "scenario": (
                "스팸 탐지 모델에서 threshold를 낮추면 recall은 높아지지만 정상 메일 오탐도 증가합니다. "
                "팀은 서비스 목적에 맞는 threshold를 선택하려고 합니다."
            ),
            "correct": "threshold별 precision과 recall 변화를 비교해 허용 가능한 균형점을 찾습니다.",
            "wrong": [
                "accuracy가 가장 높은 threshold를 항상 최종 기준으로 선택합니다.",
                "feature importance를 기준으로 threshold 값을 직접 결정합니다.",
                "학습 데이터 크기를 늘린 뒤 현재 threshold를 유지합니다.",
                "교차 검증 fold 수를 늘려 평가 표본을 더 세분화합니다.",
            ],
        },
        {
            "variant_id": "evaluation_metric_by_business_goal",
            "body_context": [
                "평가 지표는 모델이 해결하려는 비즈니스 목표와 오류 비용에 맞게 선택해야 합니다.",
                "같은 모델이라도 목적에 따라 중요하게 볼 지표가 달라질 수 있습니다.",
            ],
            "scenario": (
                "고객 이탈 예측 모델을 운영하면서 마케팅 팀은 상위 위험 고객을 우선 선별하려고 합니다. "
                "전체 정답률보다 실제 캠페인 대상 선정 품질이 중요한 상황입니다."
            ),
            "correct": "상위 위험군 precision과 lift를 함께 확인해 타겟팅 품질을 평가합니다.",
            "wrong": [
                "전체 accuracy만 기준으로 모델 버전을 선택합니다.",
                "전체 고객의 평균 예측 확률만 비교해 성능을 판단합니다.",
                "학습 loss가 낮은 모델을 우선 배포 대상으로 정합니다.",
                "feature 수가 많은 모델을 더 정교한 모델로 판단합니다.",
            ],
        },
    ],

    "class_imbalance": [
        {
            "variant_id": "imbalance_minority_recall",
            "body_context": [
                "클래스 불균형 상황에서는 전체 accuracy가 높아도 소수 클래스 탐지 성능이 낮을 수 있습니다.",
                "소수 클래스가 중요한 문제에서는 recall, precision, class weight 등을 함께 검토해야 합니다.",
            ],
            "scenario": (
                "사기 거래 탐지 모델에서 정상 거래가 대부분이라 전체 accuracy는 높지만 사기 거래 recall이 낮습니다. "
                "팀은 소수 클래스 탐지를 개선하려고 합니다."
            ),
            "correct": "소수 클래스 recall과 precision을 확인하고 class weight나 threshold 조정을 검토합니다.",
            "wrong": [
                "전체 accuracy가 높으므로 현재 모델 성능이 충분하다고 판단합니다.",
                "정상 클래스 precision만 확인해 모델 안정성을 평가합니다.",
                "feature importance를 기준으로 입력 변수 해석을 먼저 진행합니다.",
                "학습 epoch를 늘려 train accuracy를 더 높입니다.",
            ],
        },
        {
            "variant_id": "imbalance_threshold_tuning",
            "body_context": [
                "불균형 데이터에서는 threshold 조정에 따라 소수 클래스 recall과 오탐률이 크게 달라질 수 있습니다.",
                "운영 목적에 맞게 threshold별 성능 변화를 비교해야 합니다.",
            ],
            "scenario": (
                "희귀 질환 예측 모델에서 기본 threshold를 사용하면 양성 환자 탐지율이 낮게 나타납니다. "
                "팀은 미탐을 줄이면서 오탐 증가도 관리하려고 합니다."
            ),
            "correct": "threshold별 recall과 false positive 변화를 비교해 운영 기준을 정합니다.",
            "wrong": [
                "전체 accuracy가 가장 높은 threshold를 그대로 사용합니다.",
                "데이터를 무작위로 섞어 train/test split만 다시 수행합니다.",
                "모델 구조를 크게 바꿔 파라미터 수를 늘립니다.",
                "feature importance 상위 변수만 남겨 모델을 단순화합니다.",
            ],
        },
        {
            "variant_id": "imbalance_sampling_strategy",
            "body_context": [
                "불균형 데이터에서는 sampling 전략이 학습 데이터 분포와 평가 결과에 영향을 줄 수 있습니다.",
                "oversampling이나 undersampling은 검증 데이터와 분리해 신중히 적용해야 합니다.",
            ],
            "scenario": (
                "팀은 소수 클래스 샘플을 늘리기 위해 oversampling을 적용하려고 합니다. "
                "하지만 train/test split 이전에 전체 데이터에 oversampling을 적용하면 평가가 왜곡될 수 있습니다."
            ),
            "correct": "train 데이터에만 sampling을 적용하고 분리된 검증 데이터로 성능을 확인합니다.",
            "wrong": [
                "전체 데이터에 oversampling을 먼저 적용한 뒤 train/test를 나눕니다.",
                "소수 클래스 수가 늘어나면 별도 검증 없이 모델을 선택합니다.",
                "threshold를 기본값으로 유지하고 accuracy만 비교합니다.",
                "feature importance가 낮은 변수를 제거해 불균형을 해결합니다.",
            ],
        },
    ],

    "data_leakage": [
        {
            "variant_id": "leakage_future_feature",
            "body_context": [
                "데이터 누수는 예측 시점에 사용할 수 없는 정보가 학습 feature에 포함될 때 발생할 수 있습니다.",
                "검증 성능이 비정상적으로 높으면 feature 생성 시점과 사용 가능 여부를 확인해야 합니다.",
            ],
            "scenario": (
                "이탈 예측 모델의 검증 성능이 비정상적으로 높게 나왔습니다. "
                "확인해보니 예측 시점 이후에만 알 수 있는 해지 처리 결과가 feature에 포함되어 있었습니다."
            ),
            "correct": "예측 시점에 사용할 수 없는 feature를 제거하고 평가를 다시 수행합니다.",
            "wrong": [
                "성능이 높으므로 해당 feature를 유지하고 운영 배포를 진행합니다.",
                "threshold를 조정해 positive 예측 비율만 안정화합니다.",
                "class weight를 적용해 클래스 불균형을 먼저 완화합니다.",
                "교차 검증 fold 수를 늘려 평가 결과의 평균을 안정화합니다.",
            ],
        },
        {
            "variant_id": "leakage_preprocessing_before_split",
            "body_context": [
                "train/test split 이전에 전체 데이터 통계를 사용해 전처리하면 평가 데이터 정보가 학습에 새어 들어갈 수 있습니다.",
                "전처리 기준은 학습 데이터에서 fit하고 평가 데이터에는 transform만 적용해야 합니다.",
            ],
            "scenario": (
                "팀은 전체 데이터의 평균과 표준편차를 사용해 scaling을 수행한 뒤 train/test split을 진행했습니다. "
                "이후 검증 성능이 실제 운영보다 높게 나타났습니다."
            ),
            "correct": "train 데이터에서 전처리 기준을 fit하고 test 데이터에는 transform만 적용합니다.",
            "wrong": [
                "전체 데이터를 사용한 scaling이므로 더 안정적인 기준이라고 판단합니다.",
                "평가 지표를 accuracy 대신 F1-score로 바꿔 성능을 다시 봅니다.",
                "학습 데이터를 늘려 scaling 기준의 분산을 줄입니다.",
                "feature importance를 확인해 영향이 큰 변수를 해석합니다.",
            ],
        },
        {
            "variant_id": "leakage_target_encoded_variable",
            "body_context": [
                "target과 직접 연결된 파생변수는 모델 평가를 실제보다 좋게 만들 수 있습니다.",
                "feature가 운영 시점에 사용 가능한 정보인지 확인해야 합니다.",
            ],
            "scenario": (
                "분류 모델에서 target 값을 집계해 만든 파생변수가 feature로 포함되어 있습니다. "
                "검증 성능은 높지만 실제 운영에서는 같은 정보를 사용할 수 없는 상황입니다."
            ),
            "correct": "target 정보를 직접 반영한 파생변수를 제거하고 운영 시점 기준 feature를 재구성합니다.",
            "wrong": [
                "검증 성능이 높으므로 해당 파생변수를 주요 feature로 유지합니다.",
                "threshold를 조정해 예측 분포를 운영 환경에 맞춥니다.",
                "소수 클래스 recall을 높이기 위해 class weight를 적용합니다.",
                "교차 검증을 반복해 성능 평균의 신뢰도를 높입니다.",
            ],
        },
    ],

    # ─────────────────────────────────────
    # DL 계열
    # ─────────────────────────────────────
    "deep_learning_overfitting": [
        {
            "variant_id": "dl_overfitting_loss_gap",
            "body_context": [
                "train loss는 감소하지만 validation loss가 증가하면 과적합 가능성을 점검해야 합니다.",
                "일반화 성능을 높이려면 validation 기준으로 regularization이나 early stopping을 검토할 수 있습니다.",
            ],
            "scenario": (
                "딥러닝 모델 학습에서 train loss는 계속 낮아지지만 validation loss는 일정 시점 이후 증가하고 있습니다. "
                "팀은 모델의 일반화 성능 저하를 완화하려고 합니다."
            ),
            "correct": "validation loss 변화를 기준으로 과적합을 확인하고 early stopping을 검토합니다.",
            "wrong": [
                "GPU 메모리 사용량을 줄이기 위해 batch size를 조정합니다.",
                "learning rate를 낮춰 학습 속도 안정성을 먼저 확인합니다.",
                "모델 서빙 latency를 비교해 운영 비용을 검토합니다.",
                "입력 데이터 파이프라인 오류 여부를 우선 점검합니다.",
            ],
        },
        {
            "variant_id": "dl_overfitting_accuracy_gap",
            "body_context": [
                "train accuracy와 validation accuracy의 차이가 커지면 학습 데이터에 과도하게 맞춰졌을 가능성이 있습니다.",
                "dropout, data augmentation, regularization은 과적합 완화에 활용될 수 있습니다.",
            ],
            "scenario": (
                "이미지 분류 모델에서 train accuracy는 높지만 validation accuracy는 낮게 유지되고 있습니다. "
                "팀은 학습 데이터에만 맞춰진 모델을 개선하려고 합니다."
            ),
            "correct": "train-validation 성능 차이를 확인하고 dropout과 data augmentation을 검토합니다.",
            "wrong": [
                "batch size를 줄여 GPU 메모리 부족 가능성을 먼저 해결합니다.",
                "입력 이미지 크기를 줄여 추론 latency를 개선합니다.",
                "class label 이름을 정리해 출력 해석 가능성을 높입니다.",
                "서빙 리소스를 늘려 validation accuracy를 개선합니다.",
            ],
        },
        {
            "variant_id": "dl_overfitting_checkpoint",
            "body_context": [
                "epoch가 증가해도 validation 성능이 악화되면 최적 시점의 checkpoint를 선택해야 할 수 있습니다.",
                "early stopping은 validation 지표를 기준으로 학습 중단 시점을 결정하는 방법입니다.",
            ],
            "scenario": (
                "모델 학습 초반에는 validation score가 개선되었지만, 이후 epoch가 늘어날수록 validation score가 낮아졌습니다. "
                "팀은 어떤 학습 결과를 최종 모델로 선택할지 판단해야 합니다."
            ),
            "correct": "validation 성능이 가장 좋은 checkpoint를 기준으로 모델을 선택합니다.",
            "wrong": [
                "가장 마지막 epoch의 모델을 최종 모델로 선택합니다.",
                "train loss가 가장 낮은 시점의 모델을 우선 배포합니다.",
                "GPU 사용량이 가장 낮은 epoch의 모델을 선택합니다.",
                "모델 파라미터 수가 가장 많은 구조를 최종 모델로 정합니다.",
            ],
        },
    ],

    "fine_tuning": [
        {
            "variant_id": "fine_tuning_domain_adaptation",
            "body_context": [
                "Fine-tuning은 사전학습 모델을 특정 도메인 데이터와 작업 목적에 맞게 추가 학습하는 방법입니다.",
                "도메인 용어와 업무 표현이 중요한 경우 fine-tuning으로 모델 동작을 조정할 수 있습니다.",
            ],
            "scenario": (
                "사전학습 모델을 사내 질의응답 업무에 적용했지만 도메인 용어와 업무 표현을 충분히 반영하지 못하고 있습니다. "
                "팀은 모델을 업무 환경에 맞게 조정하려고 합니다."
            ),
            "correct": "도메인 데이터로 모델을 추가 학습해 업무 표현 반영을 개선합니다.",
            "wrong": [
                "프롬프트 예시를 늘려 출력 형식 안정성을 개선합니다.",
                "추론 temperature를 낮춰 응답 변동성을 줄입니다.",
                "외부 검색 context를 추가해 답변 근거 제공을 강화합니다.",
                "모델 서빙 리소스를 늘려 응답 지연을 줄입니다.",
            ],
        },
        {
            "variant_id": "fine_tuning_validation_check",
            "body_context": [
                "Fine-tuning 결과는 학습 데이터 성능만으로 판단하지 않고 분리된 검증 데이터로 확인해야 합니다.",
                "도메인 적합성과 일반화 성능을 함께 확인해야 운영 품질을 판단할 수 있습니다.",
            ],
            "scenario": (
                "팀은 도메인 데이터로 모델을 추가 학습한 뒤 train 성능이 좋아진 것을 확인했습니다. "
                "하지만 운영 데이터에서 같은 성능이 유지될지 아직 검증하지 않았습니다."
            ),
            "correct": "분리된 검증 데이터로 fine-tuning 이후 성능 변화를 확인합니다.",
            "wrong": [
                "train 성능이 좋아졌으므로 추가 검증 없이 배포를 진행합니다.",
                "프롬프트 예시를 늘려 출력 형식의 일관성을 보완합니다.",
                "temperature를 낮춰 응답의 표현 변동성을 줄입니다.",
                "서빙 리소스를 늘려 추론 지연 문제를 먼저 개선합니다.",
            ],
        },
        {
            "variant_id": "fine_tuning_vs_rag",
            "body_context": [
                "Fine-tuning은 모델 가중치를 조정하는 방법이고, RAG는 외부 문서를 검색해 context로 제공하는 방법입니다.",
                "도메인 지식 반영 방식에 따라 fine-tuning과 RAG의 적용 목적이 달라집니다.",
            ],
            "scenario": (
                "팀은 모델이 특정 업무 표현을 일관되게 이해하도록 만들고 싶어 합니다. "
                "현재 문제는 최신 문서 검색보다 도메인 표현 자체의 모델 반영 부족에 가깝습니다."
            ),
            "correct": "도메인 표현을 반영하도록 fine-tuning으로 모델 동작을 조정합니다.",
            "wrong": [
                "검색 top_k를 늘려 더 많은 외부 문서를 context로 제공합니다.",
                "metadata filter를 적용해 문서 검색 범위를 제한합니다.",
                "reranker로 검색 후보의 문맥 관련성을 다시 평가합니다.",
                "system prompt에 친절한 답변 톤을 추가합니다.",
            ],
        },
    ],

    "transfer_learning": [
        {
            "variant_id": "transfer_learning_small_dataset",
            "body_context": [
                "전이학습은 사전학습 모델의 표현을 새 작업에 활용해 적은 데이터에서도 학습 효율을 높이는 방법입니다.",
                "새 작업의 데이터가 부족할 때 전체 모델을 처음부터 학습하는 것보다 효율적일 수 있습니다.",
            ],
            "scenario": (
                "새로운 이미지 분류 업무를 시작했지만 라벨링된 데이터가 충분하지 않습니다. "
                "팀은 제한된 데이터로도 안정적인 모델을 만들 방법을 검토하고 있습니다."
            ),
            "correct": "사전학습 모델의 표현을 활용하고 필요한 부분만 새 작업에 맞게 조정합니다.",
            "wrong": [
                "데이터가 적어도 전체 모델을 처음부터 깊게 학습합니다.",
                "검색 context를 추가해 이미지 특징 추출 문제를 보완합니다.",
                "서빙 리소스를 늘려 학습 데이터 부족 문제를 해결합니다.",
                "threshold를 조정해 학습 데이터 수의 한계를 보완합니다.",
            ],
        },
        {
            "variant_id": "transfer_learning_freeze_layers",
            "body_context": [
                "전이학습에서는 사전학습된 하위 표현을 활용하고 일부 layer만 조정할 수 있습니다.",
                "모든 layer를 무조건 학습하기보다 데이터 양과 작업 차이를 고려해야 합니다.",
            ],
            "scenario": (
                "사전학습 이미지 모델을 유사한 도메인의 새 분류 작업에 적용하려고 합니다. "
                "데이터가 많지 않아 전체 layer를 모두 학습하면 과적합 위험이 있습니다."
            ),
            "correct": "초기 layer 표현을 활용하고 필요한 상위 layer 중심으로 fine-tuning합니다.",
            "wrong": [
                "모든 layer를 처음부터 동일한 learning rate로 학습합니다.",
                "검증 성능을 보지 않고 train accuracy만 기준으로 선택합니다.",
                "batch size를 줄여 데이터 부족 문제를 직접 해결합니다.",
                "모델 서빙 latency를 비교해 학습 전략을 결정합니다.",
            ],
        },
        {
            "variant_id": "transfer_learning_domain_gap",
            "body_context": [
                "사전학습 모델과 새 작업의 도메인 차이가 크면 추가 학습 범위를 더 넓게 검토해야 합니다.",
                "전이학습은 기존 표현 재사용과 새 도메인 적응 사이의 균형을 고려합니다.",
            ],
            "scenario": (
                "사전학습 모델은 일반 이미지로 학습되었지만 새 작업은 의료 영상 분류입니다. "
                "팀은 기존 표현을 어느 정도 활용하면서 도메인 차이를 반영하려고 합니다."
            ),
            "correct": "사전학습 표현을 활용하되 도메인 차이에 맞춰 추가 fine-tuning 범위를 조정합니다.",
            "wrong": [
                "도메인이 달라도 classifier head만 바꾸면 충분하다고 판단합니다.",
                "외부 검색 문서를 추가해 이미지 도메인 차이를 보완합니다.",
                "서빙 GPU를 늘려 도메인 적응 문제를 해결합니다.",
                "threshold만 조정해 의료 영상 특성 반영을 대체합니다.",
            ],
        },
    ],
})

def _select_focus_variant(
    *,
    focus: str,
    index: int,
) -> dict[str, Any] | None:
    variants = RAG_FOCUS_VARIANTS.get(focus)

    if not variants:
        return None

    safe_index = max(index, 0)
    return variants[safe_index % len(variants)]
def _has_easy_hint(text: str) -> bool:
    return any(pattern in text for pattern in EASY_HINT_PATTERNS)


def _is_low_value_claim(sentence: str) -> bool:
    text = sentence.lower()

    low_value_patterns = [
        "검색 결과 로그",
        "source chunk",
        "similarity score",
        "top_k",
        "retrieved_context",
        "validation/reject",
        "parametric memory",
        "non-parametric memory",
        "retriever / generator",
    ]

    if any(pattern.lower() in text for pattern in low_value_patterns):
        return True

    return any(keyword in sentence for keyword in LOW_VALUE_CLAIM_KEYWORDS)


def _score_document_claim(sentence: str, focus: str) -> int:
    lower = sentence.lower()
    score = 0

    for keyword in CLAIM_SIGNAL_KEYWORDS:
        if keyword.lower() in lower:
            score += 1

    for keyword in FOCUS_KEYWORDS.get(focus, []):
        if keyword.lower() in lower:
            score += 3

    if 45 <= len(sentence) <= 220:
        score += 2

    if "?" in sentence:
        score -= 2

    if _is_low_value_claim(sentence):
        score -= 5

    return score


def _normalize_claim_sentence(sentence: str) -> str:
    value = re.sub(r"\s+", " ", sentence or "").strip()
    value = value.strip("-•· ")
    return value


def _extract_document_claims(
    rag_context: str,
    focus: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    cleaned = _strip_rag_context_headers(rag_context)
    sentences = _split_sentences(cleaned)

    candidates: list[tuple[int, str]] = []

    for sentence in sentences:
        claim = _normalize_claim_sentence(sentence)

        if len(claim) < 35:
            continue

        if _is_low_value_claim(claim):
            continue

        score = _score_document_claim(claim, focus)

        if score <= 0:
            continue

        candidates.append((score, claim))

    candidates.sort(key=lambda item: item[0], reverse=True)

    unique_claims = []
    seen = set()

    for score, claim in candidates:
        key = claim[:80]

        if key in seen:
            continue

        seen.add(key)
        unique_claims.append(
            {
                "claim": claim,
                "score": score,
                "focus": focus,
            }
        )

        if len(unique_claims) >= limit:
            break

    if not unique_claims and cleaned:
        fallback = cleaned[:260].strip()
        if fallback:
            unique_claims.append(
                {
                    "claim": fallback,
                    "score": 1,
                    "focus": focus,
                }
            )

    return unique_claims

def _build_claim_based_body_context(
    *,
    topic: str,
    focus: str,
    document_claims: list[dict[str, Any]],
    variant: dict[str, Any] | None = None,
    max_length: int = 520,
) -> str | None:
    if variant and variant.get("body_context"):
        lines = variant.get("body_context", [])[:2]
        body = "[문서 기반 판단 기준]\n" + "\n".join(
            f"- {line}" for line in lines
        )
        return body[:max_length]
    
    focus_context_map = {
        "fine_tuning": (
            "[문서 기반 판단 기준]\n"
            "- 사전학습 모델은 대상 도메인 데이터와 작업 목적에 맞게 추가 학습하여 조정할 수 있습니다.\n"
            "- 모델 조정 결과는 별도 검증 데이터로 확인해야 합니다."
        ),
        "rrf_merge": (
            "[문서 기반 판단 기준]\n"
            "- Hybrid RAG에서는 vector 검색과 keyword 검색의 순위가 다르게 나타날 수 있습니다.\n"
            "- RRF는 서로 다른 검색 결과의 rank를 함께 반영해 최종 근거 우선순위를 정하는 데 사용됩니다."
        ),
        "hybrid_search": (
            "[문서 기반 판단 기준]\n"
            "- vector search는 의미 유사도에 강점이 있고 keyword search는 정확한 용어 일치에 강점이 있습니다.\n"
            "- 두 검색 방식을 함께 사용하면 근거 누락을 줄일 수 있습니다."
        ),
        "metadata_filter": (
            "[문서 기반 판단 기준]\n"
            "- 검색 결과는 요청한 문서 범위와 category 조건에 맞게 제한되어야 합니다.\n"
            "- metadata 조건이 누락되면 다른 범위의 문서가 함께 검색될 수 있습니다."
        ),
        "context_filter": (
            "[문서 기반 판단 기준]\n"
            "- 검색된 chunk 중에는 문제 생성 근거로 약한 안내문이나 노이즈가 포함될 수 있습니다.\n"
            "- context 품질과 출처를 확인해 사용할 근거를 선별해야 합니다."
        ),
    }

    body = focus_context_map.get(focus)

    if body:
        return body[:max_length]

    if not document_claims:
        return None

    return (
        "[문서 기반 판단 기준]\n"
        "- 검색된 문서의 핵심 주장과 현재 상황의 목표를 함께 확인해야 합니다."
    )

def _build_claim_based_scenario(
    *,
    topic: str,
    focus: str,
    document_claims: list[dict[str, Any]],
    variant: dict[str, Any] | None = None,
) -> str:
    if variant and variant.get("scenario"):
        return variant["scenario"]

    if focus == "fine_tuning":
        return (
            "팀은 사전학습 모델을 사내 도메인 질의응답 업무에 적용하려고 합니다. "
            "기본 모델만으로는 도메인 용어와 업무 표현을 충분히 반영하지 못해, "
            "문서 근거를 바탕으로 모델 조정 방법을 판단해야 하는 상황입니다."
        )

    if focus == "rrf_merge":
        return (
            "문서 검색 로그에서 vector search와 keyword search의 상위 결과가 서로 다르게 나타났습니다. "
            "팀은 두 검색 결과를 어떻게 결합해야 문제 생성에 사용할 근거 chunk의 우선순위를 안정적으로 정할 수 있을지 판단하려고 합니다."
        )

    if focus == "hybrid_search":
        return (
            "사용자 질문에는 의미적으로 유사한 표현과 정확한 기술 용어가 함께 포함되어 있습니다. "
            "팀은 하나의 검색 방식만 사용할 때 근거 문서가 누락될 수 있는지 검토하고 있습니다."
        )

    if focus == "metadata_filter":
        return (
            "문서 검색 결과에 요청 범위와 다른 category의 문서가 함께 포함되고 있습니다. "
            "팀은 검색 결과가 사용자가 요청한 문서 범위와 일치하도록 조정하려고 합니다."
        )

    if focus == "context_filter":
        return (
            "검색 결과에는 관련 문서도 포함되어 있지만 일부 chunk에는 목차, 안내문, 일반 설명처럼 문제 근거로 약한 내용이 섞여 있습니다. "
            "팀은 문제 생성에 사용할 context를 선별하려고 합니다."
        )

    if focus == "reranker":
        return (
            "관련 문서가 검색 후보에는 포함되어 있지만 최종 context 상위에는 배치되지 않고 있습니다. "
            "팀은 후보 문서의 순서를 다시 평가해 더 직접적인 근거를 앞에 배치하려고 합니다."
        )

    if focus == "deep_learning_overfitting":
        return (
            "딥러닝 모델 학습에서 학습 데이터 성능은 좋아지지만 검증 데이터 성능은 더 이상 개선되지 않고 있습니다. "
            "팀은 문서 근거를 바탕으로 일반화 성능 관점의 대응을 판단해야 합니다."
        )

    return (
        f"팀은 '{topic}'와 관련된 문서 검색 결과를 바탕으로 실무 조치를 판단하려고 합니다. "
        "검색된 문서의 핵심 주장과 현재 상황의 목표를 함께 고려해야 하는 상황입니다."
    )

def _build_claim_based_correct_point(
    *,
    topic: str,
    focus: str,
    document_claims: list[dict[str, Any]],
    variant: dict[str, Any] | None = None,
) -> str:
    if variant and variant.get("correct"):
        return variant["correct"]

    if focus == "fine_tuning":
        return (
            "도메인 데이터로 모델을 추가 학습해 업무 표현 반영을 개선합니다."
        )

    if focus == "rrf_merge":
        return (
            "vector rank와 keyword rank를 함께 반영해 최종 근거 우선순위를 정합니다."
        )

    if focus == "hybrid_search":
        return (
            "vector search와 keyword search를 함께 사용해 의미 유사도와 용어 일치를 반영합니다."
        )

    if focus == "metadata_filter":
        return (
            "문서 category와 metadata 조건을 적용해 요청 범위에 맞는 검색 결과를 사용합니다."
        )

    if focus == "context_filter":
        return (
            "검색된 chunk의 출처와 내용을 검토해 문제 근거로 적합한 context를 선별합니다."
        )

    if focus == "reranker":
        return (
            "검색 후보의 문맥 관련성을 다시 평가해 관련 chunk를 상위에 배치합니다."
        )

    if focus == "deep_learning_overfitting":
        return (
            "검증 성능 변화를 기준으로 과적합을 확인하고 완화 조치를 적용합니다."
        )

    return (
        "검색된 문서의 출처와 핵심 내용을 확인해 현재 상황에 맞는 조치를 선택합니다."
    )

def _build_plausible_wrong_points(
    *,
    focus: str,
    document_claims: list[dict[str, Any]],
    variant: dict[str, Any] | None = None,
) -> list[str]:
    if variant and variant.get("wrong"):
        return variant["wrong"][:4]
    wrong_by_focus = {
        "fine_tuning": [
            "프롬프트 예시를 늘려 출력 형식 안정성을 개선합니다.",
            "추론 temperature를 낮춰 응답 변동성을 줄입니다.",
            "모델 서빙 리소스를 늘려 응답 지연을 줄입니다.",
            "외부 검색 context를 추가해 답변 근거 제공을 강화합니다.",
        ],
        "rrf_merge": [
            "검색 후보 수를 늘린 뒤 상위 chunk의 출처와 중복 여부를 검토합니다.",
            "vector similarity가 높은 결과를 우선 보고 keyword 결과를 보조로 비교합니다.",
            "keyword raw score와 vector similarity를 정규화해 하나의 점수로 비교합니다.",
            "reranker로 이미 검색된 후보의 문맥 관련성을 다시 평가합니다.",
        ],
        "hybrid_search": [
            "query rewrite로 사용자 질문 표현을 더 구체화합니다.",
            "검색 후보 수를 늘려 더 많은 chunk를 검토합니다.",
            "reranker로 검색 후보의 문맥 적합도를 다시 평가합니다.",
            "metadata 조건을 적용해 문서 범위 혼입을 줄입니다.",
        ],
        "metadata_filter": [
            "query rewrite로 질문 표현을 더 구체화합니다.",
            "reranker로 후보 chunk의 최종 순서를 다시 평가합니다.",
            "chunk 크기와 overlap을 조정해 문맥 단절을 줄입니다.",
            "검색 후보 수를 늘려 누락 가능성을 줄입니다.",
        ],
        "context_filter": [
            "query rewrite로 검색어 표현을 더 명확하게 조정합니다.",
            "metadata 조건을 적용해 문서 범위 혼입을 줄입니다.",
            "reranker로 후보 chunk의 순서를 다시 평가합니다.",
            "검색 top_k를 조정해 후보 다양성을 확보합니다.",
        ],
        "reranker": [
            "metadata filter로 요청 범위와 다른 category 문서를 줄입니다.",
            "query rewrite로 사용자 질문의 의도를 더 명확하게 표현합니다.",
            "chunk 전처리 기준을 조정해 문맥 단절을 줄입니다.",
            "hybrid search로 의미 유사도와 키워드 일치를 함께 반영합니다.",
        ],
        "deep_learning_overfitting": [
            "입력 데이터 파이프라인 오류 여부를 점검합니다.",
            "GPU 메모리 사용량을 줄이기 위해 batch size를 조정합니다.",
            "학습 속도 안정성을 보기 위해 learning rate를 비교합니다.",
            "모델 구조별 추론 latency를 비교해 운영 비용을 검토합니다.",
        ],
    }

    fallback = [
        "검색 조건을 조정해 후보 문서의 범위를 다시 확인합니다.",
        "후보 chunk의 순서를 재평가해 상위 context 구성을 비교합니다.",
        "문서 전처리와 chunk 분할 기준을 점검합니다.",
        "LLM 프롬프트의 출력 형식 제약을 보완합니다.",
    ]

    wrong_points = wrong_by_focus.get(focus, fallback)

    cleaned = []

    for point in wrong_points:
        if _has_easy_hint(point):
            continue
        cleaned.append(point)

    if len(cleaned) < 4:
        cleaned.extend([p for p in fallback if p not in cleaned])

    return cleaned[:4]

def _clean_evidence_point_for_choice_seed(text: str) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()

    forbidden_prefixes = [
        "문서 claim은",
        "문서 근거는",
        "정답은",
        "이 조치는",
    ]

    for prefix in forbidden_prefixes:
        if value.startswith(prefix):
            value = value.replace(prefix, "", 1).strip()

    value = value.replace("판단을 뒷받침합니다.", "").strip()
    value = value.replace("조치여야 합니다.", "조치입니다.").strip()

    return value

def _ensure_log_or_metric_scenario(
    *,
    scenario: str,
    focus: str,
    question_format: str,
) -> str:
    if question_format != "ai_log_or_metric_interpretation":
        return scenario

    # 이미 로그/지표 정보가 있으면 그대로 둔다.
    required_markers = [
        "로그", "지표", "latency", "timeout", "accuracy", "loss",
        "similarity", "top_k", "검색 결과", "운영 로그", "평가 지표"
    ]

    if any(marker in scenario for marker in required_markers):
        return scenario

    log_blocks = {
        "modelops_serving": (
            " 운영 로그에서는 p95 latency 증가, timeout 비율 상승, GPU 사용량 증가가 함께 관찰되고 있습니다."
        ),
        "modelops_monitoring": (
            " 운영 지표에서는 최근 accuracy 하락과 입력 데이터 분포 변화가 함께 관찰되고 있습니다."
        ),
        "model_evaluation": (
            " 평가 지표에서는 accuracy, precision, recall이 서로 다른 방향으로 나타나고 있습니다."
        ),
        "class_imbalance": (
            " 평가 지표에서는 전체 accuracy는 높지만 소수 클래스 recall이 낮게 나타나고 있습니다."
        ),
        "deep_learning_overfitting": (
            " 학습 지표에서는 train loss는 감소하지만 validation loss는 증가하고 있습니다."
        ),
        "rrf_merge": (
            " 검색 로그에는 vector_rank, keyword_rank, rrf_score가 함께 기록되어 있습니다."
        ),
        "metadata_filter": (
            " 검색 결과 로그에는 요청 category와 다른 문서가 함께 포함된 것으로 나타납니다."
        ),
        "context_filter": (
            " 검색 결과 로그에는 noise_score가 높은 chunk와 evidence_score가 낮은 chunk가 포함되어 있습니다."
        ),
        "reranker": (
            " 검색 로그에서는 관련 chunk가 후보에는 포함되었지만 상위 rank에 배치되지 않았습니다."
        ),
        "structured_output": (
            " 검증 로그에는 required 필드 누락과 answer 범위 오류가 함께 기록되어 있습니다."
        ),
        "tool_calling": (
            " tool 실행 로그에는 허용되지 않은 tool name과 arguments schema 오류가 기록되어 있습니다."
        ),
    }

    return scenario + log_blocks.get(
        focus,
        " 관련 로그와 지표를 함께 확인해 현재 상황의 원인을 판단해야 합니다."
    )

def _build_claim_based_evidence(
    *,
    topic: str,
    rag_context: str,
    focus: str,
    answer_style: str,
    question_format: str,
    document_claims: list[dict[str, Any]],
    variant: dict[str, Any] | None = None,
) -> tuple[list[str], str, list[str], list[str], dict[str, Any], str | None]:
    fallback_concepts, fallback_scenario, fallback_correct, fallback_wrong, fallback_log = (
        _build_rag_focus_evidence(
            topic=topic,
            rag_context=rag_context,
            focus=focus,
            answer_style=answer_style,
        )
    )

    concepts = fallback_concepts

    scenario = _build_claim_based_scenario(
        topic=topic,
        focus=focus,
        document_claims=document_claims,
        variant=variant,
    )

    scenario = _ensure_log_or_metric_scenario(
        scenario=scenario,
        focus=focus,
        question_format=question_format,
    )

    correct_points = [
        _clean_evidence_point_for_choice_seed(
            _build_claim_based_correct_point(
                topic=topic,
                focus=focus,
                document_claims=document_claims,
                variant=variant,
            )
        )
    ]

    wrong_points = [
        _clean_evidence_point_for_choice_seed(point)
        for point in _build_plausible_wrong_points(
            focus=focus,
            document_claims=document_claims,
            variant=variant,
        )
    ]

    body_context = _build_claim_based_body_context(
        topic=topic,
        focus=focus,
        document_claims=document_claims,
        variant=variant,
    )

    log_or_metric = {
        **fallback_log,
        "evidence_mode": "claim_based_rag",
        "document_claims": document_claims,
        "claim_count": len(document_claims),
        "claim_focus": focus,
        "variant_id": variant.get("variant_id") if variant else None,
        "choice_style_constraints": {
            "target_length": "35~55 Korean characters",
            "tone": "all choices must be action sentences ending with 합니다",
            "avoid": [
                "문서 claim은",
                "정답은",
                "판단을 뒷받침합니다",
                "것입니다",
                "방향입니다",
            ],
        },
    }

    return concepts, scenario, correct_points, wrong_points, log_or_metric, body_context

def _build_rag_body_context(
    rag_context: str,
    focus: str = "document_grounding",
    max_length: int = 650,
) -> str | None:
    sentences = _extract_rag_evidence_sentences(rag_context, limit=6)

    if not sentences:
        return None

    focus_evidence_map = {
        "fine_tuning": [
            "Fine-tuning은 사전학습된 모델을 특정 데이터나 작업에 맞게 추가 학습해 모델 동작을 조정하는 방법입니다."
        ],
        "transfer_learning": [
            "사전학습 모델이나 전이학습은 기존에 학습된 표현을 새 작업에 활용해 적은 데이터에서도 학습 효율을 높이는 데 사용됩니다."
        ],
        "deep_learning_overfitting": [
            "학습 손실은 낮아지지만 검증 손실이 증가하면 과적합 가능성을 점검하고 dropout, regularization, early stopping 같은 완화 방법을 검토해야 합니다."
        ],
        "cnn": [
            "CNN은 합성곱 연산을 통해 이미지의 지역적 특징을 추출하는 데 적합한 딥러닝 구조입니다."
        ],
        "dl_training_resource": [
            "딥러닝 학습 중 GPU 메모리 부족이 발생하면 batch size, 입력 크기, 모델 구조가 메모리 사용량에 미치는 영향을 함께 확인해야 합니다."
        ],
        "model_evaluation": [
            "분류 모델 평가는 accuracy만으로 판단하기보다 문제 목적에 따라 precision, recall, F1-score를 함께 확인해야 합니다."
        ],
        "class_imbalance": [
            "클래스 불균형 상황에서는 전체 accuracy가 높아도 소수 클래스 recall이 낮을 수 있으므로 탐지 목적에 맞는 지표를 함께 확인해야 합니다."
        ],
        "data_leakage": [
            "데이터 누수는 예측 시점에 사용할 수 없는 정보가 학습이나 평가에 포함되어 성능을 실제보다 높게 보이게 만드는 문제입니다."
        ],
        "train_test_split": [
            "모델의 일반화 성능을 확인하려면 학습 데이터와 평가 데이터를 목적과 예측 시점에 맞게 분리해야 합니다."
        ],
        "modelops_serving": [
            "모델 운영에서는 정확도뿐 아니라 latency, timeout, 서빙 리소스 사용량 같은 운영 지표를 함께 모니터링해야 합니다."
        ],
        "modelops_monitoring": [
            "운영 데이터 분포가 학습 시점과 달라지면 data drift로 인해 모델 성능이 저하될 수 있으므로 지속적인 모니터링이 필요합니다."
        ],
        "llm_grounding": [
            "LLM 답변 품질을 높이려면 근거 문서 제공 여부와 답변 출처를 함께 확인해 hallucination 위험을 줄여야 합니다."
        ],
        "structured_output": [
            "Structured Output은 LLM 응답이 지정한 JSON Schema와 필수 필드 조건을 따르도록 제한하고 검증하는 방식입니다."
        ],
        "tool_calling": [
            "Tool calling에서는 LLM이 반환한 tool name과 arguments를 실행 전에 서버 측 schema와 허용 규칙으로 검증해야 합니다."
        ],
        "ai_agent": [
            "AI agent는 목표를 해석하고 필요한 도구 호출이나 단계적 실행을 선택해 작업을 수행하는 구조입니다."
        ],
        "rrf_merge": [
            "Vector search와 keyword search의 결과가 다르게 나타날 수 있으므로, Hybrid RAG에서는 RRF 같은 방식으로 순위 병합 기준을 확인해야 합니다."
        ],
        "hybrid_search": [
            "Hybrid RAG는 vector search와 keyword search를 함께 사용해 의미 유사도와 정확한 용어 일치를 모두 반영하는 검색 방식입니다."
        ],
        "metadata_filter": [
            "RAG 검색 품질을 개선할 때는 문서의 category, 출처, 범위 같은 metadata 조건이 검색 결과에 제대로 반영되었는지 확인해야 합니다."
        ],
        "context_filter": [
            "검색 결과에 관련 없는 chunk나 품질이 낮은 context가 포함되면, context filter와 chunk 전처리 품질을 함께 점검해야 합니다."
        ],
        "reranker": [
            "관련 문서가 검색 후보에 있어도 상위에 오르지 못하면, rank와 reranker 적용 여부를 함께 검토해야 합니다."
        ],
    }

    evidence_lines = focus_evidence_map.get(focus)

    if not evidence_lines:
        evidence_lines = sentences[:3]

    unique_lines = []
    for line in evidence_lines:
        if line and line not in unique_lines:
            unique_lines.append(line)

    body = "[문서 근거]\n" + "\n".join(f"- {line}" for line in unique_lines[:4])

    if len(body) > max_length:
        body = body[:max_length].rstrip() + "..."

    return body

def _detect_rag_focus_from_topic(lower_topic: str) -> str | None:
    if any(k in lower_topic for k in ["metadata", "메타데이터", "category", "카테고리", "문서 범위", "범위"]):
        return "metadata_filter"

    if any(k in lower_topic for k in ["rrf", "rank", "순위", "병합", "결합"]):
        return "rrf_merge"

    if any(k in lower_topic for k in [
        "chunk", "청크", "context", "noise", "노이즈",
        "chunk 품질", "context 품질", "근거 품질", "노이즈 chunk"
    ]):
        return "context_filter"

    if any(k in lower_topic for k in ["reranker", "재정렬", "re-ranker"]):
        return "reranker"

    if any(k in lower_topic for k in ["hybrid", "vector", "keyword", "fulltext", "하이브리드", "벡터", "키워드"]):
        return "hybrid_search"

    return None

def _detect_rag_focus_from_context(combined: str) -> str | None:
    if any(k in combined for k in ["metadata", "category", "메타데이터", "카테고리", "문서 범위"]):
        return "metadata_filter"

    if any(k in combined for k in ["reranker", "재정렬", "re-ranker"]):
        return "reranker"

    if any(k in combined for k in [
        "chunk", "청크", "context", "noise", "노이즈",
        "chunk 품질", "context 품질", "근거 품질", "노이즈 chunk"
    ]):
        return "context_filter"

    if any(k in combined for k in ["rrf", "vector_rank", "keyword_rank", "순위 병합", "rank fusion"]):
        return "rrf_merge"

    if any(k in combined for k in ["hybrid", "vector search", "keyword search", "fulltext", "하이브리드", "벡터 검색", "키워드 검색"]):
        return "hybrid_search"

    return None

def _detect_ai_focus_from_topic(lower_topic: str) -> str | None:
    # ModelOps는 fine-tuning, LLM, ML 키워드보다 먼저 본다.
    if any(k in lower_topic for k in [
        "modelops", "model ops", "서빙", "serving", "latency", "timeout",
        "p95", "inference", "rollback", "롤백", "응답 시간", "타임아웃",
        "추론", "배포", "gpu 비용", "처리량", "throughput",
        "5xx", "오류율", "서빙 리소스", "모델 api", "운영 판단"
    ]):
        return "modelops_serving"

    if any(k in lower_topic for k in [
        "monitoring", "모니터링", "drift", "data drift", "드리프트",
        "distribution shift", "분포 변화", "운영 데이터",
        "세그먼트", "segment", "사용자 피드백", "feedback",
        "품질 하락", "성능 하락", "운영 로그"
    ]):
        return "modelops_monitoring"

    if any(k in lower_topic for k in [
        "structured output", "json schema", "required", "enum",
        "answer_range", "validation_error", "parse_error", "schema",
        "구조화 출력", "구조화된 출력", "필수 필드", "json 검증",
        "스키마 검증", "파싱 오류", "응답 형식", "형식 검증"
    ]):
        return "structured_output"

    if any(k in lower_topic for k in [
        "tool calling", "function calling", "tool arguments",
        "function schema", "tool name", "도구 호출", "함수 호출",
        "arguments", "argument", "도구 인자", "툴 호출",
        "허용된 도구", "tool 검증", "도구 실행"
    ]):
        return "tool_calling"

    if any(k in lower_topic for k in [
        "hallucination", "환각", "grounding", "근거", "출처",
        "source_count", "context_provided", "근거성", "답변 출처"
    ]):
        return "llm_grounding"

    if any(k in lower_topic for k in [
        "data leakage", "target leakage", "데이터 누수", "타깃 누수",
        "available at prediction time", "prediction time",
        "예측 시점", "미래 정보", "사후 정보", "전처리 누수",
        "전체 데이터 통계", "target encoding", "파생변수"
    ]):
        return "data_leakage"

    if any(k in lower_topic for k in [
        "class imbalance", "imbalanced", "불균형", "minority class",
        "positive class", "소수 클래스", "희귀", "사기 탐지",
        "양성 클래스", "oversampling", "undersampling", "class weight"
    ]):
        return "class_imbalance"

    if any(k in lower_topic for k in [
        "precision", "recall", "f1", "f1-score", "accuracy",
        "정밀도", "재현율", "정확도", "평가 지표", "classification metric",
        "lift", "auc", "roc", "false positive", "false negative",
        "오탐", "미탐", "threshold", "임계값", "타겟팅"
    ]):
        return "model_evaluation"

    if any(k in lower_topic for k in [
        "fine-tuning", "fine tuning", "finetuning", "파인튜닝",
        "도메인 데이터", "추가 학습", "도메인 적응"
    ]):
        return "fine_tuning"

    if any(k in lower_topic for k in [
        "transfer learning", "전이학습", "pretrained", "pre-trained",
        "사전학습", "사전 학습", "feature reuse"
    ]):
        return "transfer_learning"

    if any(k in lower_topic for k in [
        "overfitting", "과적합", "validation loss", "train loss",
        "training loss", "dropout", "regularization", "early stopping",
        "검증 손실", "학습 손실", "드롭아웃", "정규화",
        "train accuracy", "validation accuracy", "checkpoint",
        "일반화", "augmentation", "data augmentation"
    ]):
        return "deep_learning_overfitting"

    return None

def _detect_rag_focus(rag_context: str, topic: str = "") -> str:
    text = _strip_rag_context_headers(rag_context)
    lower_topic = (topic or "").lower()
    combined = f"{lower_topic}\n{text.lower()}"

    # 0. 명시적인 AI topic은 검색 context보다 먼저 본다.
    # 예: ModelOps topic인데 검색 결과에 fine-tuning 문서가 섞여도 modelops_serving으로 유지한다.
    topic_ai_focus = _detect_ai_focus_from_topic(lower_topic)
    if topic_ai_focus:
        return topic_ai_focus

    rag_topic_markers = [
        "rag", "검색", "인덱싱", "indexing", "retrieval",
        "chunk", "청크", "embedding", "임베딩",
        "vector", "keyword", "hybrid", "rrf", "metadata", "reranker",
        "메타데이터", "카테고리", "재정렬"
    ]

    is_rag_topic = any(k in lower_topic for k in rag_topic_markers)

    if is_rag_topic:
        topic_focus = _detect_rag_focus_from_topic(lower_topic)
        if topic_focus:
            return topic_focus

        context_focus = _detect_rag_focus_from_context(combined)
        if context_focus:
            return context_focus

        return "hybrid_search"

    # DL / fine-tuning 계열
    if any(k in combined for k in [
        "fine-tuning", "fine tuning", "finetuning", "파인튜닝"
    ]):
        return "fine_tuning"

    if any(k in combined for k in [
        "pretrained", "pre-trained", "pretraining", "pre-training",
        "사전학습", "사전 학습", "pretrained model", "transfer learning", "전이학습"
    ]):
        return "transfer_learning"

    if any(k in combined for k in [
        "overfitting", "과적합", "validation loss", "train loss",
        "training loss", "dropout", "regularization", "early stopping",
        "검증 손실", "학습 손실", "드롭아웃", "정규화",
        "train accuracy", "validation accuracy", "checkpoint",
        "일반화", "augmentation", "data augmentation"
    ]):
        return "deep_learning_overfitting"

    if any(k in combined for k in [
        "cnn", "convolution", "convolutional neural network",
        "합성곱", "이미지 분류", "image classification"
    ]):
        return "cnn"

    if any(k in combined for k in [
        "batch size", "gpu memory", "cuda out of memory", "메모리 부족", "gpu"
    ]):
        return "dl_training_resource"

    # ML 평가 / 데이터 문제
    if any(k in combined for k in [
        "data leakage", "target leakage", "데이터 누수", "타깃 누수",
        "available at prediction time", "prediction time",
        "예측 시점", "미래 정보", "사후 정보", "전처리 누수",
        "전체 데이터 통계", "target encoding", "파생변수"
    ]):
        return "data_leakage"

    if any(k in combined for k in [
        "class imbalance", "imbalanced", "불균형", "minority class",
        "positive class", "소수 클래스", "희귀", "사기 탐지",
        "양성 클래스", "oversampling", "undersampling", "class weight"
    ]):
        return "class_imbalance"

    if any(k in combined for k in [
        "precision", "recall", "f1", "f1-score", "accuracy",
        "정밀도", "재현율", "정확도", "평가 지표", "classification metric",
        "lift", "auc", "roc", "false positive", "false negative",
        "오탐", "미탐", "threshold", "임계값", "타겟팅"
    ]):
        return "model_evaluation"

    if any(k in combined for k in [
        "train/test", "train test", "train_test", "holdout",
        "random split", "time-based split", "교차 검증", "cross validation"
    ]):
        return "train_test_split"

    # ModelOps
    if any(k in combined for k in [
        "serving", "model serving", "latency", "timeout", "p95",
        "inference", "rollback", "서빙", "지연", "응답 시간", "타임아웃", "추론",
        "배포", "롤백", "gpu 비용", "비용", "처리량", "throughput",
        "5xx", "오류율", "서빙 리소스", "모델 api"
    ]):
        return "modelops_serving"

    if any(k in combined for k in [
        "drift", "data drift", "monitoring", "모니터링", "드리프트",
        "distribution shift", "분포 변화", "운영 데이터",
        "세그먼트", "segment", "사용자 피드백", "feedback",
        "품질 하락", "성능 하락", "운영 로그"
    ]):
        return "modelops_monitoring"

    # LLM / Agent
    if any(k in combined for k in [
        "hallucination", "환각", "grounding", "근거", "source_count", "context_provided"
    ]):
        return "llm_grounding"

    if any(k in combined for k in [
        "structured output", "json schema", "required", "enum",
        "answer_range", "validation_error", "parse_error", "schema",
        "구조화 출력", "구조화된 출력", "필수 필드", "json 검증",
        "스키마 검증", "파싱 오류", "응답 형식", "형식 검증"
    ]):
        return "structured_output"

    if any(k in combined for k in [
        "tool calling", "function calling", "tool arguments",
        "function schema", "tool name", "도구 호출", "함수 호출",
        "arguments", "argument", "도구 인자", "툴 호출",
        "허용된 도구", "tool 검증", "도구 실행"
    ]):
        return "tool_calling"

    if any(k in combined for k in [
        "agent", "ai agent", "에이전트", "mcp", "a2a", "langchain", "langgraph"
    ]):
        return "ai_agent"

    # topic은 RAG가 아니었지만 context가 RAG 문서인 경우 fallback
    context_focus = _detect_rag_focus_from_context(combined)
    if context_focus:
        return context_focus

    return "document_grounding"

def _build_rag_focus_evidence(
    *,
    topic: str,
    rag_context: str,
    focus: str,
    answer_style: str,
) -> tuple[list[str], str, list[str], list[str], dict]:
    compact_context = _compact_rag_context(rag_context)

    base_log = {
        "document_topic": topic,
        "rag_focus": focus,
        "rag_context_summary": compact_context,
    }
    if focus == "fine_tuning":
        concepts = ["fine-tuning", "pretrained model", "task adaptation", "model training"]
        scenario = (
            "사전학습 모델을 특정 도메인 작업에 적용하려고 합니다. "
            "문서에서는 fine-tuning이 기존 모델의 가중치를 특정 데이터와 작업에 맞게 추가 학습해 조정하는 방법이라고 설명합니다."
        )
        correct = [
            "사전학습 모델을 대상 작업 데이터로 추가 학습해 도메인이나 작업 요구사항에 맞게 조정합니다."
        ]
        wrong = [
            "외부 문서를 검색해 프롬프트에 붙이는 것만으로 모델 가중치가 조정된다고 판단합니다.",
            "fine-tuning을 temperature 조정처럼 추론 설정만 바꾸는 작업으로 이해합니다.",
            "사전학습 모델을 활용하지 않고 항상 처음부터 전체 모델을 학습합니다.",
            "검증 데이터 없이 학습 손실만 보고 fine-tuning 결과를 판단합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "transfer_learning":
        concepts = ["pretrained model", "transfer learning", "fine-tuning", "feature reuse"]
        scenario = (
            "새로운 이미지 분류 또는 예측 작업을 수행하려고 하지만 학습 데이터가 충분하지 않습니다. "
            "문서에서는 사전학습 모델의 표현을 활용해 새 작업에 맞게 조정하는 전이학습을 설명합니다."
        )
        correct = [
            "사전학습 모델의 기존 표현을 활용하고 필요한 부분을 fine-tuning해 새 작업에 맞게 적용합니다."
        ]
        wrong = [
            "데이터가 적어도 항상 처음부터 깊은 모델을 학습합니다.",
            "사전학습 모델은 추가 학습에 사용할 수 없다고 판단합니다.",
            "전이학습을 외부 문서 검색 방식인 RAG와 같은 개념으로 이해합니다.",
            "검증 성능을 확인하지 않고 train loss만 기준으로 모델을 선택합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "deep_learning_overfitting":
        concepts = ["overfitting", "validation loss", "dropout", "regularization", "early stopping"]
        scenario = (
            "딥러닝 모델 학습 중 train loss는 계속 낮아지지만 validation loss는 증가하고 있습니다. "
            "문서에서는 이런 경우 학습 데이터에 과도하게 맞춰진 과적합 가능성을 점검해야 한다고 설명합니다."
        )
        correct = [
            "validation loss 증가와 train/validation 성능 차이를 기준으로 과적합을 의심하고 dropout, regularization, early stopping을 검토합니다."
        ]
        wrong = [
            "train loss가 계속 낮아지므로 epoch 수만 늘려 학습을 계속합니다.",
            "validation loss는 무시하고 train accuracy만 기준으로 모델을 선택합니다.",
            "출력 클래스 수를 줄이면 과적합 원인이 자동으로 해결된다고 판단합니다.",
            "검증 성능을 보지 않고 학습 데이터 성능만으로 일반화 성능을 판단합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "cnn":
        concepts = ["CNN", "convolution", "image feature", "image classification"]
        scenario = (
            "이미지 데이터를 분류하기 위한 모델 구조를 선택하려고 합니다. "
            "문서에서는 CNN이 합성곱 연산을 통해 이미지의 지역적 특징을 추출하는 데 적합하다고 설명합니다."
        )
        correct = [
            "이미지의 지역적 패턴을 학습하기 위해 convolution layer를 사용하는 CNN 구조를 검토합니다."
        ]
        wrong = [
            "CNN을 문서 검색 결과를 재정렬하는 RAG 모듈로 이해합니다.",
            "이미지의 공간적 구조를 고려하지 않고 모든 픽셀을 독립적인 표 형태로만 처리합니다.",
            "합성곱 연산 없이 출력 클래스 수만 조정해 이미지 특징 추출 문제를 해결합니다.",
            "CNN을 API latency를 측정하는 운영 지표로 판단합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "dl_training_resource":
        concepts = ["batch size", "GPU memory", "training stability", "CNN training"]
        scenario = (
            "딥러닝 모델 학습 중 GPU 메모리 부족 오류가 반복적으로 발생합니다. "
            "문서에서는 batch size와 입력 크기, 모델 구조가 메모리 사용량에 영향을 줄 수 있다고 설명합니다."
        )
        correct = [
            "모델 구조와 입력 크기를 유지해야 한다면 batch size를 줄여 GPU 메모리 사용량을 낮춥니다."
        ]
        wrong = [
            "epoch 수를 늘려 메모리 부족 문제를 해결합니다.",
            "dropout 비율만 높여 GPU 메모리 오류를 해결합니다.",
            "validation split을 조정해 평가 데이터 비율만 바꿉니다.",
            "learning rate만 낮추면 메모리 사용량이 항상 줄어든다고 판단합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "model_evaluation":
        concepts = ["accuracy", "precision", "recall", "F1-score", "classification metric"]
        scenario = (
            "분류 모델의 성능을 평가하려고 합니다. "
            "문서에서는 accuracy만으로는 충분하지 않을 수 있으며, precision, recall, F1-score를 함께 고려해야 한다고 설명합니다."
        )
        correct = [
            "문제 목적과 데이터 특성에 맞게 accuracy뿐 아니라 precision, recall, F1-score를 함께 확인합니다."
        ]
        wrong = [
            "모든 분류 문제에서 accuracy만 가장 중요한 지표라고 판단합니다.",
            "positive class 탐지가 중요한 상황에서도 recall을 확인하지 않습니다.",
            "precision과 recall의 차이를 고려하지 않고 하나의 지표처럼 사용합니다.",
            "평가 지표를 보지 않고 학습 데이터 크기만 기준으로 모델을 선택합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "class_imbalance":
        concepts = ["class imbalance", "positive class", "recall", "precision", "threshold"]
        scenario = (
            "분류 모델의 전체 accuracy는 높지만 소수 클래스의 recall이 낮습니다. "
            "문서에서는 클래스 불균형 상황에서 전체 accuracy만으로 모델을 평가하기 어렵다고 설명합니다."
        )
        correct = [
            "소수 클래스 탐지가 중요한 경우 recall과 precision을 함께 보고 threshold나 class weight 같은 대응을 검토합니다."
        ]
        wrong = [
            "전체 accuracy가 높으므로 모델 품질이 충분하다고 판단합니다.",
            "소수 클래스 recall은 무시하고 평균 손실값만 비교합니다.",
            "불균형 데이터에서도 threshold 조정은 성능 판단과 무관하다고 봅니다.",
            "positive class 비율을 확인하지 않고 모델을 선택합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "data_leakage":
        concepts = ["data leakage", "target leakage", "prediction time", "evaluation reliability"]
        scenario = (
            "모델의 검증 성능이 비정상적으로 높게 나타났습니다. "
            "문서에서는 예측 시점에 사용할 수 없는 정보가 feature에 포함되면 data leakage로 평가가 왜곡될 수 있다고 설명합니다."
        )
        correct = [
            "예측 시점에 사용할 수 없는 feature가 학습이나 평가에 포함되었는지 확인하고 제거합니다."
        ]
        wrong = [
            "성능이 높으므로 feature 구성을 검토하지 않고 그대로 배포합니다.",
            "데이터 누수는 운영 성능과 무관하다고 판단합니다.",
            "누수 가능성을 보지 않고 threshold만 조정합니다.",
            "검증 성능이 높으면 test 절차를 생략해도 된다고 판단합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "train_test_split":
        concepts = ["train/test split", "generalization", "time-based split", "validation"]
        scenario = (
            "모델 평가 데이터를 구성하려고 합니다. "
            "문서에서는 학습 데이터와 평가 데이터를 적절히 분리해야 모델의 일반화 성능을 확인할 수 있다고 설명합니다."
        )
        correct = [
            "운영 환경과 예측 시점을 고려해 학습 데이터와 평가 데이터를 분리합니다."
        ]
        wrong = [
            "모든 데이터를 섞어 학습과 평가에 반복 사용합니다.",
            "평가 데이터로 모델을 반복 학습해 성능을 높입니다.",
            "시간 순서가 중요한 문제에서도 random split만 사용합니다.",
            "분리 기준 없이 전체 데이터 기준 전처리를 먼저 수행합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "modelops_serving":
        concepts = ["model serving", "latency", "timeout", "inference", "rollback"]
        scenario = (
            "모델 API 배포 후 latency와 timeout 비율이 증가했습니다. "
            "문서에서는 모델 운영에서 응답 시간, 오류율, 배포 버전, 리소스 사용량을 함께 모니터링해야 한다고 설명합니다."
        )
        correct = [
            "최근 배포 버전의 추론 시간, 서빙 리소스 사용량, timeout 로그를 확인하고 필요하면 롤백 가능성을 검토합니다."
        ]
        wrong = [
            "학습 데이터만 확장해 재학습 계획을 먼저 세웁니다.",
            "정확도 지표만 확인하고 latency와 timeout 로그는 보지 않습니다.",
            "데이터 drift만 원인으로 판단하고 배포 시점은 확인하지 않습니다.",
            "API 서버 상태를 보지 않고 프롬프트 문장만 수정합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "modelops_monitoring":
        concepts = ["monitoring", "data drift", "distribution shift", "model quality"]
        scenario = (
            "운영 중인 모델의 성능이 최근 하락했고, 입력 데이터 분포가 학습 시점과 달라졌습니다. "
            "문서에서는 data drift를 모니터링해 운영 품질 저하 원인을 확인해야 한다고 설명합니다."
        )
        correct = [
            "운영 입력 데이터와 학습 데이터의 분포 차이를 drift 기준으로 분석하고 성능 저하와의 관계를 확인합니다."
        ]
        wrong = [
            "서빙 latency가 안정적이면 모델 품질 저하는 발생하지 않는다고 판단합니다.",
            "입력 데이터 분포 변화는 무시하고 서버 증설만 진행합니다.",
            "최근 배포가 없으면 운영 데이터 변화도 확인하지 않습니다.",
            "정확도 하락을 프롬프트 표현 문제로만 해석합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "llm_grounding":
        concepts = ["LLM", "hallucination", "grounding", "context", "source"]
        scenario = (
            "LLM이 최신 정책이나 사실 질문에 대해 자연스러운 답변을 생성했지만, "
            "참고 문서나 출처가 제공되지 않았습니다. 문서에서는 근거 없는 답변이 hallucination으로 이어질 수 있다고 설명합니다."
        )
        correct = [
            "근거가 중요한 질문에는 관련 문서를 context로 제공하고 답변에 사용된 출처를 함께 남깁니다."
        ]
        wrong = [
            "temperature만 낮추면 최신 사실의 근거성이 자동으로 보장된다고 판단합니다.",
            "출처 문서가 없어도 모델이 항상 최신 정보를 알고 있다고 가정합니다.",
            "답변 문장이 자연스러우면 별도 검증이 필요 없다고 판단합니다.",
            "근거 부족 문제를 서버 응답 시간 문제로만 해석합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "ai_agent":
        concepts = ["AI agent", "tool use", "planning", "workflow", "agent communication"]
        scenario = (
            "AI 시스템이 단순 답변을 넘어 여러 단계의 작업을 수행해야 합니다. "
            "문서에서는 agent가 목표를 해석하고 필요한 도구 호출이나 단계적 실행을 선택할 수 있다고 설명합니다."
        )
        correct = [
            "작업 목표를 기준으로 필요한 도구와 실행 단계를 선택하는 agent workflow를 구성합니다."
        ]
        wrong = [
            "AI agent를 항상 단일 문장 답변만 생성하는 정적 모델로 이해합니다.",
            "도구 호출이나 상태 관리 없이 모든 작업을 한 번의 프롬프트로만 처리합니다.",
            "agent 간 작업 위임이나 외부 도구 연결을 모델 학습률 조정 문제로 해석합니다.",
            "workflow 상태와 실행 결과를 추적하지 않고 최종 답변만 저장합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "structured_output":
        concepts = ["structured output", "JSON schema", "required field", "enum validation", "answer range validation"]
        scenario = (
            "AI 문제 생성 API에서 LLM이 JSON 형식의 응답을 반환했지만, "
            "필수 필드, enum 값, answer 범위 같은 검증 조건을 만족하는지 확인해야 하는 상황입니다."
        )
        correct = ["응답 JSON을 저장하기 전에 required 필드, enum 값, answer 범위 같은 schema와 비즈니스 규칙을 검증합니다."]
        wrong = [
            "JSON 형태로 응답했다는 점만 보고 저장 단계로 넘깁니다.",
            "프롬프트에 JSON 작성을 요청했으므로 별도 schema 검증을 생략합니다.",
            "choices 개수만 맞으면 answer 범위 오류를 허용합니다.",
            "LLM이 의도한 의미가 맞다고 보고 enum 오류를 저장합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "tool_calling":
        concepts = ["tool calling", "function calling", "tool arguments", "server-side validation"]
        scenario = (
            "LLM이 tool calling 응답으로 외부 함수 이름과 arguments를 반환했습니다. "
            "실행 전에 tool name과 arguments가 허용된 schema와 규칙을 만족하는지 확인해야 하는 상황입니다."
        )
        correct = ["tool name과 arguments를 실행 전에 서버 측 schema와 허용 규칙으로 검증합니다."]
        wrong = [
            "LLM이 반환한 tool arguments를 검증 없이 바로 실행합니다.",
            "함수 이름만 맞으면 arguments의 타입과 허용 필드는 확인하지 않습니다.",
            "tool calling을 사용하면 prompt injection 위험은 없다고 판단합니다.",
            "도구 호출 실패 시 사용자에게 원본 오류를 그대로 노출합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "rrf_merge":
        concepts = ["RRF", "vector rank", "keyword rank", "hybrid search"]
        scenario = (
            "문서 검색 로그에서 vector search와 keyword search의 상위 결과가 서로 다르게 나타났습니다. "
            "두 검색 방식의 순위를 함께 반영해 최종 context 우선순위를 정해야 하는 상황입니다."
        )
        correct = [
            "vector rank와 keyword rank를 RRF로 병합해 의미 유사도와 키워드 일치를 함께 반영합니다."
        ]
        wrong = [
            "vector similarity를 주 지표로 두고 keyword rank는 참고값으로 처리합니다.",
            "keyword raw score와 vector similarity를 같은 척도로 보고 합산합니다.",
            "keyword search 결과를 별도 검토 단계로 분리하고 병합 순위에는 반영하지 않습니다.",
            "후보 수를 늘린 뒤 별도 병합 기준 없이 상위 검색 결과를 사용합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "hybrid_search":
        concepts = ["hybrid search", "vector search", "keyword search", "FULLTEXT search"]
        scenario = (
            "사용자 질문에 의미적으로 유사한 문서와 정확한 키워드가 포함된 문서가 모두 필요합니다. "
            "하나의 검색 방식만으로는 관련 근거가 누락될 수 있는 상황입니다."
        )
        correct = ["vector search와 keyword search를 함께 사용해 의미 유사도와 정확한 용어 일치를 모두 반영합니다."]
        wrong = [
            "vector search만 사용하면 항상 keyword search보다 정확하다고 판단합니다.",
            "keyword search는 RAG에서 필요 없으므로 제거합니다.",
            "검색된 후보의 출처와 내용을 보지 않고 첫 번째 결과만 사용합니다.",
            "top_k를 무조건 크게 늘리면 검색 품질이 항상 좋아진다고 판단합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "metadata_filter":
        concepts = ["metadata filter", "category", "document scope", "retrieval filter"]
        scenario = (
            "문서 검색 결과에 요청 범위와 다른 category의 문서가 함께 포함되고 있습니다. "
            "문서에는 category와 출처 같은 metadata가 저장되어 있으며, 검색 범위가 요청 조건과 일치하는지 확인해야 하는 상황입니다."
        )
        correct = ["검색 결과의 문서 category와 metadata 조건이 요청한 범위와 일치하는지 확인합니다."]
        wrong = [
            "문서 category 조건을 확인하지 않고 검색 결과 수만 늘립니다.",
            "metadata filter 대신 LLM 프롬프트만 수정합니다.",
            "검색 범위와 무관하게 similarity가 높은 chunk를 모두 사용합니다.",
            "출처가 다른 문서가 섞여도 문제 생성 결과만 보고 판단합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "context_filter":
        concepts = ["context filter", "chunk quality", "noise chunk", "evidence selection"]
        scenario = (
            "검색 결과에는 관련 문서도 포함되어 있지만, 일부 chunk는 목차, 안내문, 품질이 낮은 context를 포함하고 있습니다. "
            "문제 생성에 사용할 근거 chunk를 선별해야 하는 상황입니다."
        )
        correct = ["검색된 chunk의 출처와 내용을 검토해 문제 생성 근거로 적합한 context만 사용합니다."]
        wrong = [
            "근거 chunk의 품질을 확인하지 않고 LLM 프롬프트만 수정합니다.",
            "검색된 모든 chunk를 품질 검토 없이 context에 포함합니다.",
            "문서 출처와 chunk 내용을 확인하지 않고 모델 응답만 기준으로 판단합니다.",
            "noise chunk가 있어도 top_k만 늘리면 해결된다고 판단합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    if focus == "reranker":
        concepts = ["reranker", "rank", "retrieval ranking", "candidate reranking"]
        scenario = (
            "관련 문서가 검색 후보에는 포함되어 있지만 상위 context에 오르지 못하고 있습니다. "
            "검색 후보의 순서를 다시 평가해 관련 chunk를 상위에 배치해야 하는 상황입니다."
        )
        correct = ["관련 chunk가 후보에 있지만 상위에 오르지 못하는 경우 reranker나 rank 재정렬을 검토합니다."]
        wrong = [
            "관련 chunk가 하위에 있어도 첫 번째 검색 결과만 문제 생성 근거로 사용합니다.",
            "검색 후보의 순위를 확인하지 않고 프롬프트만 수정합니다.",
            "reranker는 검색 품질과 무관하다고 판단합니다.",
            "후보에 없는 문서를 reranker만으로 새로 검색할 수 있다고 판단합니다.",
        ]
        return concepts, scenario, correct, wrong, base_log

    concepts = [topic, "문서 근거", "검증 기준"]
    scenario = f"문서 검색 결과를 바탕으로 '{topic}'와 관련된 실무 상황을 판단하려고 합니다."
    correct = ["검색된 문서 근거의 출처, 내용, 검색 조건을 함께 확인해 판단합니다."]
    wrong = [
        "문서 근거 없이 일반적인 조치만 우선 적용합니다.",
        "검색된 근거를 확인하지 않고 모델 응답만 기준으로 판단합니다.",
        "문서 범위와 검색 조건을 확인하지 않은 채 결과 수만 늘립니다.",
        "근거 chunk의 품질을 보지 않고 모든 검색 결과를 동일하게 사용합니다.",
    ]
    return concepts, scenario, correct, wrong, base_log

def build_rag_evidence_pack(
    *,
    topic: str,
    difficulty: str,
    plan: QuestionFormatPlan,
    rag_context: str,
) -> EvidencePack:
    rag_focus = _detect_rag_focus(rag_context, topic=topic)

    variant = _select_focus_variant(
        focus=rag_focus,
        index=plan.index - 1,
    )

    document_claims = _extract_document_claims(
        rag_context=rag_context,
        focus=rag_focus,
        limit=3,
    )

    use_claim_based = difficulty == "중급" and bool(document_claims)

    if use_claim_based:
        (
            concepts,
            scenario,
            base_correct_points,
            base_wrong_points,
            log_or_metric,
            rag_body_context,
        ) = _build_claim_based_evidence(
            topic=topic,
            rag_context=rag_context,
            focus=rag_focus,
            answer_style=plan.answer_style,
            question_format=plan.question_format,
            document_claims=document_claims,
            variant=variant,
        )
    else:
        rag_body_context = _build_rag_body_context(rag_context, focus=rag_focus)

        (
            concepts,
            scenario,
            base_correct_points,
            base_wrong_points,
            log_or_metric,
        ) = _build_rag_focus_evidence(
            topic=topic,
            rag_context=rag_context,
            focus=rag_focus,
            answer_style=plan.answer_style,
        )

        log_or_metric = {
            **log_or_metric,
            "evidence_mode": "focus_template_fallback",
            "document_claims": document_claims,
            "claim_count": len(document_claims),
            "variant_id": variant.get("variant_id") if variant else None,
        }

    if plan.answer_style == "find_incorrect":
        correct_points = base_wrong_points[:1]
        wrong_points = base_correct_points + base_wrong_points[1:4]
    else:
        correct_points = base_correct_points[:1]
        wrong_points = base_wrong_points[:4]

    rag_normalized_topic = topic or "문서 기반 RAG 문제"

    return EvidencePack(
        topic=topic,
        normalized_topic=rag_normalized_topic,
        difficulty=difficulty,
        question_format=plan.question_format,
        answer_style=plan.answer_style,
        focus=rag_focus,
        concepts=concepts,
        correct_points=correct_points,
        wrong_points=wrong_points,
        scenario=scenario,
        log_or_metric=log_or_metric,
        body_context=rag_body_context,
    )

def _compact_rag_context(rag_context: str, max_chars: int = 1200) -> str:
    text = (rag_context or "").strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "\n\n[이하 문서 내용 생략]"