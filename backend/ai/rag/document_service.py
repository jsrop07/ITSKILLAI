# ai/rag/document_service.py

import time
import logging
from sqlalchemy import text
from ai.embedding_service import create_embedding
from ai.vector_store import search_similar_chunks
from ai.vector_store import add_chunk_to_vector_store

logger = logging.getLogger("uvicorn.info")



def get_document_by_id(db, document_id: int):
    sql = text("""
        SELECT 
            document_id,
            title,
            file_name,
            file_path,
            source_type,
            category,
            description,
            uploaded_by,
            created_at,
            embedding_status,
            embedding_error
        FROM ai_documents
        WHERE document_id = :document_id
    """)

    result = db.execute(sql, {"document_id": document_id}).mappings().first()
    return result


def get_chunks_by_document_id(db, document_id: int):
    sql = text("""
        SELECT 
            chunk_id,
            document_id,
            chunk_index,
            content
        FROM ai_document_chunks
        WHERE document_id = :document_id
        ORDER BY chunk_index ASC
    """)

    result = db.execute(sql, {"document_id": document_id}).mappings().all()
    return result


def update_document_embedding_status(
    db,
    document_id: int,
    status: str,
    error: str | None = None
):
    sql = text("""
        UPDATE ai_documents
        SET 
            embedding_status = :status,
            embedding_error = :error
        WHERE document_id = :document_id
    """)

    db.execute(
        sql,
        {
            "status": status,
            "error": error,
            "document_id": document_id,
        }
    )
    db.commit()


def embed_document_chunks(db, document_id: int):
    start_time = time.time()
    logger.info(f"RAG Pipeline [Embed]: 문서 임베딩 시작 (document_id: {document_id})")
    document = get_document_by_id(db, document_id)

    if not document:
        logger.warning(f"RAG Pipeline [Embed]: 문서를 찾을 수 없습니다 (document_id: {document_id})")
        raise ValueError("문서를 찾을 수 없습니다.")

    chunks = get_chunks_by_document_id(db, document_id)

    if not chunks:
        logger.warning(f"RAG Pipeline [Embed]: 문서 chunk가 없습니다 (document_id: {document_id})")
        raise ValueError("문서 chunk가 없습니다.")

    try:
        update_document_embedding_status(db, document_id, "processing")

        embedded_count = 0

        for chunk in chunks:
            content = chunk["content"]

            if not content or not content.strip():
                continue

            embedding = create_embedding(content)

            vector_id = f"doc_{document_id}_chunk_{chunk['chunk_id']}"

            metadata = {
                "document_id": int(document_id),
                "chunk_id": int(chunk["chunk_id"]),
                "chunk_index": int(chunk["chunk_index"]),
                "file_name": document["file_name"],
                "title": document["title"],
                "category": document["category"],
                "source_type": document["source_type"],
            }

            add_chunk_to_vector_store(
                vector_id=vector_id,
                content=content,
                embedding=embedding,
                metadata=metadata,
            )

            embedded_count += 1

        update_document_embedding_status(db, document_id, "completed")

        elapsed_time = time.time() - start_time
        logger.info(f"RAG Pipeline [Embed]: 문서 임베딩 성공 (document_id: {document_id}, chunks: {embedded_count}, 소요 시간: {elapsed_time:.3f}초)")

        return {
            "document_id": document_id,
            "file_name": document["file_name"],
            "embedded_count": embedded_count,
            "embedding_status": "completed",
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"RAG Pipeline [Embed]: 문서 임베딩 실패 (document_id: {document_id}, 소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}")
        update_document_embedding_status(db, document_id, "failed", str(e))
        raise e

def search_document_chunks(query: str, top_k: int = 5, category: str | None = None):
    start_time = time.time()
    logger.info(f"RAG Pipeline [Search]: 문서 검색 시작 (query: '{query}', top_k: {top_k}, category: {category})")
    
    if not query or not query.strip():
        logger.warning("RAG Pipeline [Search]: 검색어가 비어 있습니다.")
        raise ValueError("검색어를 입력해주세요.")

    try:
        query_embedding = create_embedding(query)

        results = search_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
            category=category,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        search_results = []

        for i in range(len(documents)):
            distance = distances[i] if i < len(distances) else None
            similarity = None

            if distance is not None:
                similarity = 1 / (1 + distance)

            metadata = metadatas[i] if i < len(metadatas) else {}

            search_results.append({
                "content": documents[i],
                "metadata": metadata,
                "distance": distance,
                "similarity": similarity,
            })

        elapsed_time = time.time() - start_time
        logger.info(f"RAG Pipeline [Search]: 문서 검색 성공 (찾은 청크 수: {len(search_results)}, 소요 시간: {elapsed_time:.3f}초)")

        return {
            "query": query,
            "top_k": top_k,
            "category": category,
            "results": search_results,
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"RAG Pipeline [Search]: 문서 검색 실패 (소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}")
        raise

def build_context_from_search_results(
    query: str,
    top_k: int = 5,
    category: str | None = None,
) -> str:
    search_data = search_document_chunks(
        query=query,
        top_k=top_k,
        category=category,
    )

    results = search_data.get("results", [])

    if not results:
        raise ValueError("관련 문서 내용을 찾을 수 없습니다.")

    context_parts = []

    for idx, item in enumerate(results, start=1):
        content = item.get("content", "")
        metadata = item.get("metadata", {})

        file_name = metadata.get("file_name", "unknown")
        chunk_index = metadata.get("chunk_index", "")
        title = metadata.get("title", "")
        category_value = metadata.get("category", "")

        context_parts.append(
            f"[문서 {idx} | title={title} | category={category_value} | file={file_name} | chunk={chunk_index}]\n{content}"
        )

    return "\n\n".join(context_parts)