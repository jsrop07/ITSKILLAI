import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"


def create_embedding(text: str) -> list[float]:
    """
    입력 텍스트를 OpenAI embedding vector로 변환한다.
    """
    if not text or not text.strip():
        raise ValueError("Embedding할 텍스트가 비어 있습니다.")

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )

    return response.data[0].embedding