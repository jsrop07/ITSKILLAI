import os
import time
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("uvicorn.info")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"


def create_embedding(text: str) -> list[float]:
    """
    입력 텍스트를 OpenAI embedding vector로 변환한다.
    """
    if not text or not text.strip():
        logger.error("Embedding 실패: 텍스트가 비어 있습니다.")
        raise ValueError("Embedding할 텍스트가 비어 있습니다.")

    start_time = time.time()
    logger.info("LLM Pipeline [Embedding]: OpenAI 임베딩 생성 시작")
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        elapsed_time = time.time() - start_time
        logger.info(f"LLM Pipeline [Embedding]: 임베딩 생성 성공 (소요 시간: {elapsed_time:.3f}초)")
        return response.data[0].embedding
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"LLM Pipeline [Embedding]: 임베딩 생성 실패 (소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}")
        raise