from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import PageContent
from schemas import PageContentCreate, PageContentUpdate, PageContentRead

router = APIRouter(prefix="/api/page-contents", tags=["page-contents"])


@router.get("", response_model=List[PageContentRead])
def list_page_contents(
    page_key: Optional[str] = Query(None),
    user_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(PageContent)
    if page_key:
        query = query.filter(PageContent.page_key == page_key)
    if user_type:
        query = query.filter(PageContent.user_type == user_type)
    if is_active is not None:
        query = query.filter(PageContent.is_active == is_active)
    return query.order_by(PageContent.page_key, PageContent.section_key).all()


@router.get("/by-key")
def get_content_by_key(
    page_key: str = Query(...),
    section_key: Optional[str] = Query(None),
    content_key: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """프론트엔드에서 특정 키로 컨텐츠 조회"""
    query = db.query(PageContent).filter(
        PageContent.page_key == page_key,
        PageContent.is_active == True,
    )
    if section_key:
        query = query.filter(PageContent.section_key == section_key)
    if content_key:
        query = query.filter(PageContent.content_key == content_key)

    results = query.all()
    # dict 형태로 변환
    result_map = {}
    for item in results:
        key = f"{item.section_key}.{item.content_key}"
        result_map[key] = {
            "content_id": item.content_id,
            "title": item.title,
            "body": item.body,
            "extra_json": item.extra_json,
        }
    return result_map


@router.post("", response_model=PageContentRead)
def create_page_content(data: PageContentCreate, db: Session = Depends(get_db)):
    content = PageContent(**data.model_dump())
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


@router.get("/{content_id}", response_model=PageContentRead)
def get_page_content(content_id: int, db: Session = Depends(get_db)):
    content = db.query(PageContent).filter(PageContent.content_id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="컨텐츠를 찾을 수 없습니다.")
    return content


@router.put("/{content_id}", response_model=PageContentRead)
def update_page_content(
    content_id: int, data: PageContentUpdate, db: Session = Depends(get_db)
):
    content = db.query(PageContent).filter(PageContent.content_id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="컨텐츠를 찾을 수 없습니다.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(content, key, value)
    db.commit()
    db.refresh(content)
    return content


@router.delete("/{content_id}")
def delete_page_content(content_id: int, db: Session = Depends(get_db)):
    content = db.query(PageContent).filter(PageContent.content_id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="컨텐츠를 찾을 수 없습니다.")
    db.delete(content)
    db.commit()
    return {"message": "삭제되었습니다."}
