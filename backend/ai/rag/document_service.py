# ai/rag/document_service.py

import time
import logging
from sqlalchemy import text
from ai.embedding_service import create_embedding
from ai.vector_store import search_similar_chunks
from ai.vector_store import add_chunk_to_vector_store

logger = logging.getLogger("uvicorn.info")

# ─────────────────────────────────────────────
# RAG Search Config
# ─────────────────────────────────────────────
MIN_CONTEXT_SIMILARITY = 0.42
MIN_HYBRID_SCORE = 0.35

DEFAULT_VECTOR_WEIGHT = 0.7
DEFAULT_KEYWORD_WEIGHT = 0.3

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

def search_vector_chunks(
    query: str,
    top_k: int = 5,
    category: str | None = None,
):
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
        vector_score = None

        if distance is not None:
            vector_score = 1 / (1 + distance)

        metadata = metadatas[i] if i < len(metadatas) else {}

        search_results.append({
            "content": documents[i],
            "metadata": metadata,
            "distance": distance,
            "similarity": vector_score,
            "vector_score": vector_score,
            "keyword_score": 0.0,
            "hybrid_score": vector_score or 0.0,
            "search_source": "vector",
        })

    return search_results

def _extract_keywords(query: str) -> list[str]:
    keywords = []

    for token in query.replace(",", " ").split():
        token = token.strip()
        if len(token) >= 2:
            keywords.append(token)

    return list(dict.fromkeys(keywords))[:8]

def search_keyword_chunks(
    db,
    query: str,
    top_k: int = 5,
    category: str | None = None,
):
    keywords = _extract_keywords(query)

    if not keywords:
        return []

    where_clauses = []
    params = {
        "limit": top_k,
    }

    keyword_conditions = []

    for idx, keyword in enumerate(keywords):
        param_name = f"kw_{idx}"
        params[param_name] = f"%{keyword}%"

        keyword_conditions.append(
            f"""(
                c.content LIKE :{param_name}
                OR d.title LIKE :{param_name}
                OR d.source_type LIKE :{param_name}
                OR d.description LIKE :{param_name}
            )"""
        )

    where_clauses.append("(" + " OR ".join(keyword_conditions) + ")")

    if category:
        where_clauses.append("d.category = :category")
        params["category"] = category

    where_sql = " AND ".join(where_clauses)

    score_expr_parts = []

    for idx, keyword in enumerate(keywords):
        param_name = f"kw_{idx}"
        score_expr_parts.append(f"""
            CASE
                WHEN c.content LIKE :{param_name} THEN 1
                ELSE 0
            END
        """)

    score_expr = " + ".join(score_expr_parts)

    sql = text(f"""
        SELECT
            c.chunk_id,
            c.document_id,
            c.chunk_index,
            c.content,
            d.title,
            d.file_name,
            d.category,
            d.source_type,
            ({score_expr}) AS raw_keyword_score
        FROM ai_document_chunks c
        JOIN ai_documents d ON c.document_id = d.document_id
        WHERE {where_sql}
        ORDER BY raw_keyword_score DESC, c.chunk_id ASC
        LIMIT :limit
    """)

    rows = db.execute(sql, params).mappings().all()

    max_score = max([row["raw_keyword_score"] for row in rows], default=1)

    results = []

    for row in rows:
        raw_score = row["raw_keyword_score"] or 0
        keyword_score = raw_score / max_score if max_score else 0.0

        metadata = {
            "document_id": int(row["document_id"]),
            "chunk_id": int(row["chunk_id"]),
            "chunk_index": int(row["chunk_index"]),
            "file_name": row["file_name"],
            "title": row["title"],
            "category": row["category"],
            "source_type": row["source_type"],
        }

        results.append({
            "content": row["content"],
            "metadata": metadata,
            "distance": None,
            "similarity": None,
            "vector_score": 0.0,
            "keyword_score": keyword_score,
            "hybrid_score": keyword_score,
            "search_source": "keyword",
        })

    return results

def merge_hybrid_search_results(
    vector_results: list[dict],
    keyword_results: list[dict],
    top_k: int = 5,
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
):
    merged = {}

    def get_key(item: dict):
        metadata = item.get("metadata", {})
        chunk_id = metadata.get("chunk_id")

        if chunk_id is not None:
            return f"chunk:{chunk_id}"

        document_id = metadata.get("document_id")
        chunk_index = metadata.get("chunk_index")

        return f"doc:{document_id}:chunk_index:{chunk_index}"

    for item in vector_results:
        key = get_key(item)
        merged[key] = {
            **item,
            "vector_score": item.get("vector_score") or item.get("similarity") or 0.0,
            "keyword_score": 0.0,
            "search_source": "vector",
        }

    for item in keyword_results:
        key = get_key(item)

        if key in merged:
            merged[key]["keyword_score"] = item.get("keyword_score") or 0.0
            merged[key]["search_source"] = "hybrid"
        else:
            merged[key] = {
                **item,
                "vector_score": 0.0,
                "keyword_score": item.get("keyword_score") or 0.0,
                "search_source": "keyword",
            }

    results = []

    for item in merged.values():
        vector_score = item.get("vector_score") or 0.0
        keyword_score = item.get("keyword_score") or 0.0

        hybrid_score = (
            vector_score * vector_weight
            + keyword_score * keyword_weight
        )

        item["hybrid_score"] = hybrid_score
        results.append(item)

    results.sort(
        key=lambda x: (
            x.get("hybrid_score") or 0.0,
            x.get("vector_score") or 0.0,
            x.get("keyword_score") or 0.0,
        ),
        reverse=True,
    )

    return results[:top_k]

def search_document_chunks(
    db,
    query: str,
    top_k: int = 5,
    category: str | None = None,
    search_mode: str = "hybrid",
):
    start_time = time.time()
    logger.info(
        f"RAG Pipeline [Search]: 문서 검색 시작 "
        f"(query: '{query}', top_k: {top_k}, category: {category}, search_mode: {search_mode})"
    )

    if not query or not query.strip():
        logger.warning("RAG Pipeline [Search]: 검색어가 비어 있습니다.")
        raise ValueError("검색어를 입력해주세요.")

    if search_mode not in ["vector", "keyword", "hybrid"]:
        raise ValueError("search_mode는 vector, keyword, hybrid 중 하나여야 합니다.")

    try:
        if search_mode == "vector":
            search_results = search_vector_chunks(
                query=query,
                top_k=top_k,
                category=category,
            )

        elif search_mode == "keyword":
            search_results = search_keyword_chunks(
                db=db,
                query=query,
                top_k=top_k,
                category=category,
            )

        else:
            vector_results = search_vector_chunks(
                query=query,
                top_k=max(top_k * 2, 10),
                category=category,
            )

            keyword_results = search_keyword_chunks(
                db=db,
                query=query,
                top_k=max(top_k * 2, 10),
                category=category,
            )

            search_results = merge_hybrid_search_results(
                vector_results=vector_results,
                keyword_results=keyword_results,
                top_k=top_k,
            )

        elapsed_time = time.time() - start_time
        logger.info(
            f"RAG Pipeline [Search]: 문서 검색 성공 "
            f"(mode={search_mode}, 찾은 청크 수: {len(search_results)}, 소요 시간: {elapsed_time:.3f}초)"
        )

        return {
            "query": query,
            "top_k": top_k,
            "category": category,
            "search_mode": search_mode,
            "results": search_results,
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(
            f"RAG Pipeline [Search]: 문서 검색 실패 "
            f"(mode={search_mode}, 소요 시간: {elapsed_time:.3f}초) - 에러: {str(e)}"
        )
        raise

def _is_valid_context_item(item: dict, search_mode: str) -> bool:
    content = item.get("content", "")

    if not content or len(content.strip()) < 80:
        return False

    if search_mode == "vector":
        return (item.get("similarity") or 0.0) >= MIN_CONTEXT_SIMILARITY

    if search_mode == "keyword":
        return (item.get("keyword_score") or 0.0) > 0

    return (item.get("hybrid_score") or 0.0) >= MIN_HYBRID_SCORE

def build_context_from_search_results(
    db,
    query: str,
    top_k: int = 5,
    category: str | None = None,
    search_mode: str = "hybrid",
) -> str:
    search_data = search_document_chunks(
        db=db,
        query=query,
        top_k=top_k,
        category=category,
        search_mode=search_mode,
    )

    results = search_data.get("results", [])

    if not results:
        raise ValueError("관련 문서 내용을 찾을 수 없습니다.")

    filtered_results = [
        item for item in results
        if _is_valid_context_item(item, search_mode)
    ]

    if not filtered_results:
        raise ValueError("관련 문서 내용의 검색 점수가 너무 낮습니다.")

    context_parts = []

    for idx, item in enumerate(filtered_results, start=1):
        content = item.get("content", "")
        metadata = item.get("metadata", {})

        file_name = metadata.get("file_name", "unknown")
        chunk_index = metadata.get("chunk_index", "")
        title = metadata.get("title", "")
        category_value = metadata.get("category", "")

        vector_score = item.get("vector_score")
        keyword_score = item.get("keyword_score")
        hybrid_score = item.get("hybrid_score")
        search_source = item.get("search_source")

        context_parts.append(
            f"[문서 {idx} | title={title} | category={category_value} | "
            f"file={file_name} | chunk={chunk_index} | source={search_source} | "
            f"vector_score={vector_score} | keyword_score={keyword_score} | hybrid_score={hybrid_score}]\n"
            f"{content}"
        )

    return "\n\n".join(context_parts)