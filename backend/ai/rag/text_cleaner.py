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

        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)

    # 반복 공백/줄바꿈 정리
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    cleaned_text = re.sub(r"[ \t]{2,}", " ", cleaned_text)

    return cleaned_text.strip()