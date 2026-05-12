# ai/rag/vector_store.py

import os
import time
import logging
import chromadb
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("uvicorn.info")

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "ai_question_documents"
)

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

collection = client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME
)


def add_chunk_to_vector_store(
    vector_id: str,
    content: str,
    embedding: list[float],
    metadata: dict
):
    start_time = time.time()
    logger.info(f"Vector Store [Upsert]: 청크 추가 시작 (ID: {vector_id})")
    try:
        collection.upsert(
            ids=[vector_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata]
        )
        elapsed_time = time.time() - start_time
        logger.info(f"Vector Store [Upsert]: 청크 추가 성공 (ID: {vector_id}, 소요 시간: {elapsed_time:.3f}초)")
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Vector Store [Upsert]: 청크 추가 실패 (ID: {vector_id}, 소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}")
        raise


def search_similar_chunks(
    query_embedding: list[float],
    top_k: int = 5,
    category: str | None = None
):
    start_time = time.time()
    logger.info(f"Vector Store [Search]: 유사도 검색 시작 (top_k={top_k}, category={category})")

    try:
        where = None

        if category:
            where = {"category": category}

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        elapsed_time = time.time() - start_time
        logger.info(f"Vector Store [Search]: 유사도 검색 성공 (소요 시간: {elapsed_time:.3f}초)")
        return results

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Vector Store [Search]: 유사도 검색 실패 (소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}")
        raise