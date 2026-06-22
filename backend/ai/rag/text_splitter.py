import re

def _token_unique_ratio(text: str) -> float:
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", text)
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def _is_bad_chunk(chunk: str) -> bool:
    text = (chunk or "").strip()

    if len(text) < 120:
        return True

    # 실제로 문제가 됐던 반복 패턴 방지
    if text.count("인공지") >= 8:
        return True

    if text.count("생성형 AI엔지니") >= 3:
        return True

    if text.count("교육훈련과정") >= 3:
        return True

    # 중복 토큰 비율이 낮으면 목차/깨진 추출일 가능성이 큼
    if _token_unique_ratio(text) < 0.35:
        return True

    evidence_terms = [
        "정의", "개념", "특징", "목적", "역할", "방법", "절차", "기준",
        "조건", "원인", "해결", "비교", "장점", "단점", "분석", "검증",
        "평가", "요구사항", "성능", "보안", "RAG", "검색", "임베딩",
        "metadata", "vector", "keyword", "hybrid", "LLM", "프롬프트",
    ]

    has_evidence_term = any(term in text for term in evidence_terms)
    has_sentence_ending = bool(
        re.search(r"(다\.|한다\.|된다\.|이다\.|있다\.|없다\.|해야 한다\.|필요하다\.)", text)
    )

    if not has_evidence_term and not has_sentence_ending:
        return True

    return False

def split_text_into_chunks(text: str, chunk_size: int = 700, overlap: int = 120):
    text = (text or "").strip()

    if not text:
        return []

    # 줄 단위 정리
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 너무 짧은 라인은 앞뒤 문맥에 도움이 안 되므로 제거
    cleaned_lines = []
    for line in lines:
        if len(line) < 5:
            continue
        cleaned_lines.append(line)

    # 페이지/제목/문단 단위가 최대한 유지되도록 문단 후보 생성
    paragraphs = []
    buffer = ""

    for line in cleaned_lines:
        is_heading = (
            line.startswith("[페이지")
            or re.match(r"^\d+[\.\)]\s+", line)
            or line.startswith("#")
            or "수행준거" in line
            or "필요 지식" in line
            or "필요 기술" in line
            or line == "지식"
            or line == "기술"
            or line == "태도"
        )

        if is_heading and buffer:
            paragraphs.append(buffer.strip())
            buffer = line
        else:
            buffer = f"{buffer}\n{line}".strip()

        if len(buffer) >= chunk_size:
            paragraphs.append(buffer.strip())
            buffer = ""

    if buffer:
        paragraphs.append(buffer.strip())

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            # 긴 문단은 문장 기준으로 한 번 더 분리
            sentences = re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s+", paragraph)
        else:
            sentences = [paragraph]

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current) + len(sentence) + 1 <= chunk_size:
                current = f"{current}\n{sentence}".strip()
            else:
                if current:
                    chunks.append(current)

                if overlap > 0 and chunks:
                    prev_tail = chunks[-1][-overlap:]
                    current = f"{prev_tail}\n{sentence}".strip()
                else:
                    current = sentence

    if current:
        chunks.append(current)

    # 너무 짧거나 반복/목차성 chunk 제거
    return [chunk for chunk in chunks if not _is_bad_chunk(chunk)]