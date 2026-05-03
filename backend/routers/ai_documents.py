import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import AIDocument, AIDocumentChunk, Admin
from schemas import AIDocumentRead
from routers.auth import get_current_admin
from schemas import AIDocumentSearchRequest
from ai.rag.document_loader import load_text_from_file
from ai.rag.text_splitter import split_text_into_chunks
from ai.rag.document_service import embed_document_chunks
from ai.rag.document_service import search_document_chunks
from ai.services.competency_config import normalize_competency_type, get_competency_label

router = APIRouter(prefix="/api/ai/documents", tags=["AI Documents"])

UPLOAD_DIR = "uploads/ai_docs"


@router.post("/upload")
def upload_ai_document(
    title: str = Form(...),
    source_type: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # current_admin: Admin = Depends(get_current_admin),
):
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in [".pdf", ".docx", ".txt", ".md"]:
            raise HTTPException(status_code=400, detail="PDF, DOCX, TXT, MD 파일만 업로드할 수 있습니다.")

        saved_file_name = f"{title}_{file.filename}"
        saved_file_path = os.path.join(UPLOAD_DIR, saved_file_name)

        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        text = load_text_from_file(saved_file_path)

        if not text.strip():
            raise HTTPException(status_code=400, detail="문서에서 텍스트를 추출할 수 없습니다.")

        chunks = split_text_into_chunks(text)

        if not chunks:
            raise HTTPException(status_code=400, detail="문서 chunk 생성에 실패했습니다.")

        normalized_category = normalize_competency_type(category)

        ai_document = AIDocument(
            title=title,
            file_name=file.filename,
            file_path=saved_file_path,
            source_type=source_type,
            category=normalized_category,
            description=description,
            uploaded_by=None,
            embedding_status="pending",
            embedding_error=None,
        )

        db.add(ai_document)
        db.flush()

        saved_chunks = []
        category_label = get_competency_label(normalized_category)

        for index, chunk in enumerate(chunks):
            chunk_content = f"""
[역량유형: {category_label}]
[문서제목: {title}]
[출처유형: {source_type or "unknown"}]

{chunk}
""".strip()

            document_chunk = AIDocumentChunk(
                document_id=ai_document.document_id,
                chunk_index=index,
                content=chunk_content,
                page_no=None,
                vector_id=None,
            )
            db.add(document_chunk)
            db.flush()

            saved_chunks.append({
                "chunk_id": document_chunk.chunk_id,
                "chunk_index": document_chunk.chunk_index,
                "content_preview": chunk_content[:100],
            })

        db.commit()
        db.refresh(ai_document)

        return {
            "message": "문서 업로드 및 chunk 저장이 완료되었습니다.",
            "document": {
                "document_id": ai_document.document_id,
                "title": ai_document.title,
                "file_name": ai_document.file_name,
                "source_type": ai_document.source_type,
                "category": ai_document.category,
                "chunk_count": len(saved_chunks),
            },
            "chunks": saved_chunks,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[AIDocumentRead])
def list_ai_documents(
    db: Session = Depends(get_db),
):
    return db.query(AIDocument).order_by(AIDocument.created_at.desc()).all()


@router.post("/{document_id}/embed")
def embed_document(document_id: int, conn=Depends(get_db)):
    try:
        result = embed_document_chunks(conn, document_id)
        return {
            "message": "문서 embedding 저장이 완료되었습니다.",
            "data": result,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"문서 embedding 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/search")
def search_documents(
    request: AIDocumentSearchRequest,
):
    try:
        result = search_document_chunks(
            query=request.query,
            top_k=request.top_k or 5,
            category=request.category,
        )

        return {
            "message": "문서 검색이 완료되었습니다.",
            "data": result,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"문서 검색 중 오류가 발생했습니다: {str(e)}"
        )