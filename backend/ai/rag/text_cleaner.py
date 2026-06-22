# backend/ai/rag/text_cleaner.py

import re


REMOVE_LINE_KEYWORDS = [
    "교수·학습 방법",
    "교수학습 방법",
    "수행 tip",
    "수행 Tip",
    "자료·자료",
    "자료 및 준비물",
    "기기(장비·공구)",
    "안전·유의사항",
    "안전 유의사항",
    "학습모듈의 내용체계",
    "자기진단",
    "평가지",
    "평가자 체크리스트",
    "훈련기준",
    "직업기초능력",
    "교수 방법",
    "학습 방법",
]

def _is_toc_or_repeated_line(line: str) -> bool:
    """
    PDF 추출 과정에서 생기는 목차/헤더/푸터/반복 라인을 제거한다.
    예: '인공지 01. 인공지 02. 인공지 03...' 같은 라인
    """
    if not line:
        return True

    # 이전에 실제로 나온 문제 패턴
    if line.count("인공지") >= 4:
        return True

    if line.count("생성형 AI엔지니") >= 2:
        return True

    if line.count("교육훈련과정") >= 2:
        return True

    # 숫자 목차가 과도하게 반복되는 라인
    number_tokens = re.findall(r"\b\d{1,2}\b", line)
    if len(number_tokens) >= 8 and len(line) < 250:
        return True

    # 같은 짧은 토큰이 과도하게 반복되는 라인
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", line)
    if len(tokens) >= 12:
        unique_ratio = len(set(tokens)) / max(len(tokens), 1)
        if unique_ratio < 0.35:
            return True

    # 목차 점선 형태
    if re.search(r"\.{3,}\s*\d+$", line):
        return True

    return False


def _normalize_cleaned_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

def clean_pdf_text_for_rag(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)

    lines = text.splitlines()
    cleaned_lines = []

    skip_block = False

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        # 단독 페이지 번호 제거
        if re.fullmatch(r"\d+", line):
            continue

        # 너무 짧은 줄 제거
        if len(line) < 5:
            continue

        # 점선/구분선 제거
        if re.fullmatch(r"[\.\-\_\=\s]+", line):
            continue

        # NCS PDF에서 출제와 관련이 낮은 안내성 줄 제거
        if any(keyword in line for keyword in REMOVE_LINE_KEYWORDS):
            continue

        # 목차성 라인 일부 제거
        if re.match(r"^\d+\.\s*$", line):
            continue

        # 반복 목차/헤더/깨진 PDF 추출 라인 제거
        if _is_toc_or_repeated_line(line):
            continue

        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)
    return _normalize_cleaned_text(cleaned_text)