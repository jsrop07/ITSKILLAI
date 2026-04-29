import re


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

    # 너무 짧은 chunk 제거
    return [chunk for chunk in chunks if len(chunk.strip()) >= 80]