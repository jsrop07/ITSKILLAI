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
MIN_HYBRID_SCORE = 0.0


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
            db.execute(
                text("""
                    UPDATE ai_document_chunks
                    SET vector_id = :vector_id
                    WHERE chunk_id = :chunk_id
                """),
                {
                    "vector_id": vector_id,
                    "chunk_id": chunk["chunk_id"],
                }
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

def _build_fulltext_query(query: str) -> str:
    """
    MariaDB FULLTEXT BOOLEAN MODE용 query를 만든다.
    - 너무 짧은 토큰은 제외한다.
    - 각 토큰 뒤에 *를 붙여 prefix matching을 허용한다.
    - 예: "비기능 요구사항 추적성" -> "+비기능* +요구사항* +추적성*"
    """
    keywords = _extract_keywords(query)

    if not keywords:
        return ""

    boolean_terms = []

    for keyword in keywords:
        cleaned = (
            keyword.strip()
            .replace("+", "")
            .replace("-", "")
            .replace("@", "")
            .replace("~", "")
            .replace("*", "")
            .replace('"', "")
            .replace("'", "")
            .replace("(", "")
            .replace(")", "")
        )

        if len(cleaned) >= 2:
            boolean_terms.append(f"{cleaned}*")

    return " ".join(boolean_terms)


def search_keyword_chunks(
    db,
    query: str,
    top_k: int = 5,
    category: str | None = None,
):
    """
    MariaDB FULLTEXT 기반 keyword search.

    기존 LIKE 검색이 아니라 MATCH(content) AGAINST(...)를 사용한다.
    이 단계부터는 단순 문자열 포함 검색이 아니라 DB의 전문 검색 점수를 사용한다.
    """
    fulltext_query = _build_fulltext_query(query)

    if not fulltext_query:
        return []

    params = {
        "query": fulltext_query,
        "limit": top_k,
    }

    category_sql = ""

    if category:
        category_sql = "AND d.category = :category"
        params["category"] = category

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
            MATCH(c.content) AGAINST (:query IN BOOLEAN MODE) AS raw_keyword_score
        FROM ai_document_chunks c
        JOIN ai_documents d ON c.document_id = d.document_id
        WHERE MATCH(c.content) AGAINST (:query IN BOOLEAN MODE)
        {category_sql}
        ORDER BY raw_keyword_score DESC, c.chunk_id ASC
        LIMIT :limit
    """)

    rows = db.execute(sql, params).mappings().all()

    max_score = max(
        [float(row["raw_keyword_score"] or 0.0) for row in rows],
        default=1.0,
    )

    results = []

    for rank, row in enumerate(rows, start=1):
        raw_score = float(row["raw_keyword_score"] or 0.0)
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
            "keyword_raw_score": raw_score,
            "keyword_rank": rank,
            "hybrid_score": keyword_score,
            "search_source": "keyword",
        })

    return results

def merge_hybrid_search_results(
    vector_results: list[dict],
    keyword_results: list[dict],
    top_k: int = 5,
    rrf_k: int = 60,
):
    """
    Vector 결과와 FULLTEXT keyword 결과를 RRF로 병합한다.

    RRF 장점:
    - vector_score와 keyword_score의 스케일 차이를 직접 섞지 않는다.
    - 각 검색기의 순위를 기준으로 병합한다.
    - vector와 keyword 양쪽에 모두 등장한 chunk는 상위로 올라간다.
    """
    merged: dict[str, dict] = {}

    def get_key(item: dict) -> str:
        metadata = item.get("metadata", {})
        chunk_id = metadata.get("chunk_id")

        if chunk_id is not None:
            return f"chunk:{chunk_id}"

        document_id = metadata.get("document_id")
        chunk_index = metadata.get("chunk_index")
        return f"doc:{document_id}:chunk_index:{chunk_index}"

    def add_ranked_results(results: list[dict], source_name: str):
        for rank, item in enumerate(results, start=1):
            key = get_key(item)
            rrf_score = 1 / (rrf_k + rank)

            if key not in merged:
                merged[key] = {
                    **item,
                    "vector_score": 0.0,
                    "keyword_score": 0.0,
                    "vector_rank": None,
                    "keyword_rank": None,
                    "rrf_score": 0.0,
                    "search_sources": [],
                }

            merged[key]["rrf_score"] += rrf_score

            if source_name not in merged[key]["search_sources"]:
                merged[key]["search_sources"].append(source_name)

            if source_name == "vector":
                merged[key]["vector_score"] = item.get("vector_score") or item.get("similarity") or 0.0
                merged[key]["vector_rank"] = rank

            if source_name == "keyword":
                merged[key]["keyword_score"] = item.get("keyword_score") or 0.0
                merged[key]["keyword_rank"] = rank

    add_ranked_results(vector_results, "vector")
    add_ranked_results(keyword_results, "keyword")

    results = []

    for item in merged.values():
        sources = item.get("search_sources", [])

        if "vector" in sources and "keyword" in sources:
            item["search_source"] = "hybrid"
        elif "vector" in sources:
            item["search_source"] = "vector"
        else:
            item["search_source"] = "keyword"

        item["hybrid_score"] = item.get("rrf_score") or 0.0
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
            logger.info(
                "Hybrid RAG [Merge]: "
                f"vector_results={len(vector_results)}, "
                f"keyword_results={len(keyword_results)}, "
                f"merged_results={len(search_results)}, "
                f"top_k={top_k}"
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

def _is_noise_context(content: str) -> bool:
    """
    문제 생성 근거로 부적합한 교수·학습 안내성 chunk를 필터링한다.
    NCS PDF에는 교수자 안내, 학습 활동, 평가자 질문 등이 섞여 있어
    검색 점수가 높아도 문제 생성 근거로는 부적절할 수 있다.
    """
    if not content:
        return True

    text_value = str(content)

    noise_keywords = [
        "교수자",
        "학습자",
        "학습한다",
        "수업",
        "실습 시",
        "평가자 질문",
        "평가 방법",
        "평가지",
        "자기진단",
        "체크리스트",
        "학습 내용",
        "학습 목표",
        "교수·학습 방법",
        "교수 방법",
        "학습 방법",
        "UML 저작도구",
        "라이선스에 유의",
        "파워포인트 자료",
    ]

    evidence_keywords = [
        "요구사항",
        "비기능",
        "기능 요구사항",
        "품질",
        "성능",
        "가용성",
        "보안성",
        "유지보수",
        "검증",
        "타당성",
        "분석",
        "인터페이스",
        "제약사항",
        "응답 시간",
        "처리량",
    ]

    noise_count = sum(1 for keyword in noise_keywords if keyword in text_value)
    evidence_count = sum(1 for keyword in evidence_keywords if keyword in text_value)

    # 안내성 문구가 많고, 출제 근거 키워드가 적으면 제외
    if noise_count >= 2 and evidence_count <= 1:
        return True

    # 평가/학습 안내 페이지 성격이 강한 chunk 제외
    if noise_count >= 4:
        return True

    return False


def _is_valid_context_item(item: dict, search_mode: str) -> bool:
    content = item.get("content", "")

    if not content or len(content.strip()) < 80:
        return False

    if _is_noise_context(content):
        return False

    if search_mode == "vector":
        return (item.get("similarity") or 0.0) >= MIN_CONTEXT_SIMILARITY

    if search_mode == "keyword":
        return (item.get("keyword_score") or 0.0) > 0

    return (item.get("hybrid_score") or 0.0) > MIN_HYBRID_SCORE

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

    logger.info(
        "RAG Context [Filter]: "
        f"before={len(results)}, "
        f"after={len(filtered_results)}, "
        f"search_mode={search_mode}, "
        f"category={category}"
    )

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