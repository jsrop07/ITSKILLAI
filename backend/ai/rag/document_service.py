# ai/rag/document_service.py

import re
import time
import logging
from sqlalchemy import text
from ai.rag.embedding_service import create_embedding
from ai.rag.vector_store import (
    search_similar_chunks,
    add_chunk_to_vector_store,
    delete_document_vectors,
)

logger = logging.getLogger("uvicorn.info")

# ─────────────────────────────────────────────
# RAG Search Config
# ─────────────────────────────────────────────
MIN_CONTEXT_SIMILARITY = 0.42
MIN_CONTENT_LENGTH = 120
DEFAULT_RAG_CANDIDATE_K = 20


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

def delete_document_with_chunks(db, document_id: int):
    """
    문서 삭제:
    1. 문서 존재 확인
    2. ChromaDB vector 삭제
    3. ai_document_chunks 삭제
    4. ai_documents 삭제
    """
    document = get_document_by_id(db, document_id)

    if not document:
        raise ValueError("문서를 찾을 수 없습니다.")

    file_path = document.get("file_path")

    try:
        # 1) ChromaDB vector 삭제
        delete_document_vectors(document_id)

        # 2) DB chunk 삭제
        db.execute(
            text("""
                DELETE FROM ai_document_chunks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id}
        )

        # 3) DB document 삭제
        db.execute(
            text("""
                DELETE FROM ai_documents
                WHERE document_id = :document_id
            """),
            {"document_id": document_id}
        )

        db.commit()

        return {
            "document_id": document_id,
            "file_path": file_path,
            "deleted": True,
            "message": "문서와 관련 chunk/vector가 삭제되었습니다.",
        }

    except Exception:
        db.rollback()
        raise

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
            candidate_k = max(top_k * 4, DEFAULT_RAG_CANDIDATE_K)

            vector_results = search_vector_chunks(
                query=query,
                top_k=candidate_k,
                category=category,
            )

            keyword_results = search_keyword_chunks(
                db=db,
                query=query,
                top_k=candidate_k,
                category=category,
            )

            search_results = merge_hybrid_search_results(
                vector_results=vector_results,
                keyword_results=keyword_results,
                top_k=candidate_k,
            )
            logger.info(
                "Hybrid RAG [Merge]: "
                f"vector_results={len(vector_results)}, "
                f"keyword_results={len(keyword_results)}, "
                f"merged_results={len(search_results)}, "
                f"candidate_k={candidate_k}, "
                f"final_top_k={top_k}"
            )
        for item in search_results:
            _calculate_context_quality(item)

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

def _normalize_context_text(content: str) -> str:
    if not content:
        return ""

    text_value = str(content)

    lines = []
    for line in text_value.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        # 내부 메타 헤더는 품질 판단에서 제외
        if stripped.startswith("[역량유형:"):
            continue
        if stripped.startswith("[문서제목:"):
            continue
        if stripped.startswith("[출처유형:"):
            continue

        lines.append(stripped)

    return " ".join(lines)


def _score_noise_signals(content: str) -> int:
    text_value = _normalize_context_text(content)

    noise_keywords = [
        "교수자",
        "학습자",
        "교수·학습 방법",
        "교수학습 방법",
        "교수 방법",
        "학습 방법",
        "학습 활동",
        "평가자 질문",
        "평가자 체크리스트",
        "자기진단",
        "체크리스트",
        "평가지",
        "수업",
        "실습 시",
        "자료 및 준비물",
        "기기(장비·공구)",
        "안전·유의사항",
        "안전 유의사항",
    ]

    return sum(1 for keyword in noise_keywords if keyword in text_value)


def _score_evidence_signals(content: str) -> int:
    text_value = _normalize_context_text(content)

    evidence_keywords = [
        "정의",
        "개념",
        "특징",
        "목적",
        "역할",
        "절차",
        "방법",
        "기준",
        "조건",
        "비교",
        "차이",
        "장점",
        "단점",
        "원인",
        "해결",
        "분석",
        "검증",
        "평가",
        "요구사항",
        "기능 요구사항",
        "비기능",
        "품질",
        "성능",
        "보안",
        "가용성",
        "유지보수",
        "추적성",
        "인터페이스",
        "제약사항",
        "응답 시간",
        "처리량",
        "RAG",
        "검색",
        "임베딩",
        "embedding",
        "chunk",
        "metadata",
        "reranker",
        "RRF",
        "vector",
        "keyword",
        "hybrid",
        "LLM",
        "프롬프트",
        "schema",
        "tool calling",
    ]

    return sum(1 for keyword in evidence_keywords if keyword in text_value)


def _score_structure_signals(content: str) -> int:
    text_value = _normalize_context_text(content)

    score = 0

    structure_patterns = [
        "다음과 같다",
        "예를 들어",
        "따라서",
        "때문에",
        "반면",
        "그러나",
        "즉,",
        "첫째",
        "둘째",
        "셋째",
        "1.",
        "2.",
        "3.",
    ]

    score += sum(1 for pattern in structure_patterns if pattern in text_value)

    if "장점" in text_value and "단점" in text_value:
        score += 2

    if "원인" in text_value and ("해결" in text_value or "대응" in text_value):
        score += 2

    if "기준" in text_value and ("판단" in text_value or "평가" in text_value):
        score += 2

    return score


def _calculate_context_quality(item: dict) -> dict:
    content = item.get("content", "")
    metadata = item.get("metadata", {})

    text_value = _normalize_context_text(content)

    noise_score = _score_noise_signals(content)
    evidence_score = _score_evidence_signals(content)
    structure_score = _score_structure_signals(content)

    vector_score = float(item.get("vector_score") or item.get("similarity") or 0.0)
    keyword_score = float(item.get("keyword_score") or 0.0)
    hybrid_score = float(item.get("hybrid_score") or 0.0)

    search_source = item.get("search_source") or ""
    source_bonus = 0.0

    if search_source == "hybrid":
        source_bonus = 0.08
    elif search_source == "vector":
        source_bonus = 0.03
    elif search_source == "keyword":
        source_bonus = 0.03

    length_bonus = 0.0
    content_length = len(text_value)

    if 250 <= content_length <= 1200:
        length_bonus = 0.04
    elif content_length > 1200:
        length_bonus = -0.03

    quality_score = (
        hybrid_score
        + 0.04 * evidence_score
        + 0.03 * structure_score
        + source_bonus
        + length_bonus
        - 0.05 * noise_score
    )

    quality = {
        "noise_score": noise_score,
        "evidence_score": evidence_score,
        "structure_score": structure_score,
        "quality_score": round(quality_score, 6),
        "content_length": content_length,
    }

    item["quality"] = quality
    item["noise_score"] = noise_score
    item["evidence_score"] = evidence_score
    item["structure_score"] = structure_score
    item["quality_score"] = round(quality_score, 6)

    return quality


def _matches_category(item: dict, category: str | None) -> bool:
    if not category:
        return True

    metadata = item.get("metadata", {})
    item_category = metadata.get("category") or item.get("category")

    return item_category == category


def _is_low_quality_context(item: dict) -> bool:
    content = item.get("content", "")
    text_value = _normalize_context_text(content)

    if not text_value or len(text_value) < MIN_CONTENT_LENGTH:
        return True

    quality = item.get("quality") or _calculate_context_quality(item)

    noise_score = quality["noise_score"]
    evidence_score = quality["evidence_score"]
    structure_score = quality["structure_score"]

    # 안내성 문구가 많고, 실제 근거 신호가 거의 없으면 제외
    if noise_score >= 3 and evidence_score <= 1:
        return True

    # 안내성 문구가 매우 많고 구조적 설명도 없으면 제외
    if noise_score >= 5 and structure_score == 0:
        return True

    # 근거 신호와 구조 신호가 모두 없으면 문제 생성 근거로 부적합
    if evidence_score == 0 and structure_score == 0:
        return True

    return False


def _is_valid_context_item(
    item: dict,
    search_mode: str,
    category: str | None = None,
) -> bool:
    if not _matches_category(item, category):
        return False

    content = item.get("content", "")

    if not content:
        return False

    _calculate_context_quality(item)

    if _is_low_quality_context(item):
        return False

    if search_mode == "vector":
        return (item.get("similarity") or 0.0) >= MIN_CONTEXT_SIMILARITY

    if search_mode == "keyword":
        return (item.get("keyword_score") or 0.0) > 0

    # hybrid는 RRF 점수 절대값보다 품질 점수와 최종 정렬에 맡긴다.
    return True

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
        if _is_valid_context_item(item, search_mode, category)
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

def _extract_page_hint(content: str) -> str | None:
    if not content:
        return None

    match = re.search(r"\[페이지\s*(\d+)\]", str(content))
    if not match:
        return None

    return match.group(1)

def _build_content_preview(content: str, max_length: int = 300) -> str:
    if not content:
        return ""

    text_value = str(content)

    # RAG chunk 앞에 붙인 내부 메타 header 제거
    lines = []
    for line in text_value.splitlines():
        stripped = line.strip()

        if stripped.startswith("[역량유형:"):
            continue
        if stripped.startswith("[문서제목:"):
            continue
        if stripped.startswith("[출처유형:"):
            continue
        if stripped.startswith("[페이지"):
            continue

        lines.append(stripped)

    preview = " ".join(line for line in lines if line)
    preview = preview.replace("\\n", " ")
    preview = " ".join(preview.split())

    return preview[:max_length]
    
def build_context_and_evidence_from_search_results(
    db,
    query: str,
    top_k: int = 5,
    category: str | None = None,
    search_mode: str = "hybrid",
) -> dict:
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

    valid_results = []

    for item in results:
        if _is_valid_context_item(item, search_mode, category):
            valid_results.append(item)

    valid_results.sort(
        key=lambda x: (
            x.get("quality_score") or 0.0,
            x.get("hybrid_score") or 0.0,
            x.get("vector_score") or 0.0,
            x.get("keyword_score") or 0.0,
        ),
        reverse=True,
    )

    filtered_results = valid_results[:top_k]

    logger.info(
        "RAG Context [Filter]: "
        f"before={len(results)}, "
        f"valid={len(valid_results)}, "
        f"after={len(filtered_results)}, "
        f"search_mode={search_mode}, "
        f"category={category}"
    )

    if not filtered_results:
        raise ValueError("관련 문서 내용의 검색 점수가 너무 낮습니다.")

    context_parts = []
    evidence_documents = []

    for idx, item in enumerate(filtered_results, start=1):
        content = item.get("content", "")
        metadata = item.get("metadata", {})

        file_name = metadata.get("file_name", "unknown")
        chunk_id = metadata.get("chunk_id")
        chunk_index = metadata.get("chunk_index", "")
        title = metadata.get("title", "")
        category_value = metadata.get("category", "")
        source_type = metadata.get("source_type", "")

        vector_score = item.get("vector_score")
        keyword_score = item.get("keyword_score")
        hybrid_score = item.get("hybrid_score")
        rrf_score = item.get("rrf_score")
        vector_rank = item.get("vector_rank")
        keyword_rank = item.get("keyword_rank")
        search_source = item.get("search_source")

        content_preview = _build_content_preview(content)
        page_hint = _extract_page_hint(content)
        quality = item.get("quality") or _calculate_context_quality(item)
        
        context_parts.append(
            f"[문서 {idx} | title={title} | category={category_value} | "
            f"file={file_name} | chunk={chunk_index} | source={search_source} | "
            f"vector_score={vector_score} | keyword_score={keyword_score} | hybrid_score={hybrid_score}]\n"
            f"{content}"
        )



        evidence_documents.append({
            "title": title,
            "file_name": file_name,
            "category": category_value,
            "source_type": source_type,
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "page_hint": page_hint,
            "search_source": search_source,
            "vector_score": vector_score,
            "keyword_score": keyword_score,
            "hybrid_score": hybrid_score,
            "rrf_score": rrf_score,
            "vector_rank": vector_rank,
            "keyword_rank": keyword_rank,
            "noise_score": quality.get("noise_score"),
            "evidence_score": quality.get("evidence_score"),
            "structure_score": quality.get("structure_score"),
            "quality_score": quality.get("quality_score"),
            "content_length": quality.get("content_length"),
            "content_preview": content_preview,
        })

    return {
        "context": "\n\n".join(context_parts),
        "evidence": {
            "search_query": query,
            "search_mode": search_mode,
            "top_k": top_k,
            "category": category,
            "documents": evidence_documents,
        },
    }