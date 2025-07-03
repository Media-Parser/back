from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Response, Query, Body, Depends
from app.services.hwpx_extractor import extract_text_from_hwpx
from app.services.hwp_extractor import extract_text_from_hwp
from app.services.document_service import (
    upload_file, get_next_doc_id, get_documents, download_file, delete_file,
    update_document_title, has_temp_doc, get_temp_doc, get_doc, update_temp_doc, finalize_temp_doc
)
from app.models.document_model import Doc
from app.models.temp_model import TempDoc
from typing import List, Optional
import traceback
from urllib.parse import quote
import magic
import tempfile
import os
from app.core.jwt import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"], dependencies=[Depends(get_current_user)])

# ======================== 대시보드 ========================

# 문서 목록 조회 API
@router.get("/")    # ★ response_model=List[Doc] 제거
async def list_documents(user_id: str = Query(...)):
    try:
        docs = await get_documents(user_id)
        if not isinstance(docs, list):
            return []
        return docs
    except Exception as e:
        print("문서조회 에러:", e)
        return []

# 문서 제목 변경 API
@router.patch("/title/{doc_id}")
async def update_document_title_api(
    doc_id: str,
    data: dict = Body(...)
):
    new_title = data.get("title")
    if not new_title or not new_title.strip():
        raise HTTPException(status_code=400, detail="제목이 비어 있습니다.")
    ok = await update_document_title(doc_id, new_title.strip())
    if not ok:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없거나 수정되지 않았습니다.")
    return {"message": "Document title updated successfully"}

# 문서 다운로드 API
@router.get("/download/{doc_id}")
async def download_document(doc_id: str):
    try:
        doc = await download_file(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        title = doc.get('title', 'document')
        ext = doc.get('file_type', '')
        filename = f"{title}.{ext}" if ext else f"{title}.hwpx"
        quoted_filename = quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}"
        }
        return Response(
            content=doc.get("file_blob") or doc.get("contents"),
            media_type="application/octet-stream",
            headers=headers
        )
    except HTTPException as e:
        raise
    except Exception as e:
        print("문서다운로드 에러:", e)
        raise HTTPException(status_code=500, detail=str(e))

# 문서 삭제 API
@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    try:
        await delete_file(doc_id)
        return {"message": "Document deleted successfully"}
    except Exception as e:
        print("문서삭제 에러:", e)
        raise HTTPException(status_code=500, detail=str(e))

# 문서 업로드 API (hwpx)
@router.post("/upload/hwpx")
async def documents_upload_hwpx(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    category_id: Optional[str] = Form(None)
):
    if not file.filename.lower().endswith('.hwpx'):
        raise HTTPException(status_code=400, detail="Only .hwpx files are allowed.")
    contents = await file.read()
    parse_error_msg = None
    text = ""
    try:
        text = extract_text_from_hwpx(contents)
        print("본문 추출 결과:", text)
    except Exception as e:
        parse_error_msg = "본문 추출 실패: " + str(e)
        text = ""
    doc = Doc(
        doc_id=await get_next_doc_id(),
        user_id=user_id,
        title=file.filename.rsplit(".", 1)[0],
        contents=text,
        file_type="hwpx",
        file_blob=contents,
        category_id=category_id or ""
    )
    result = await upload_file(doc)
    doc_id = result.get("doc_id")
    return {"doc_id": doc_id, "parse_error": parse_error_msg}

# 문서 업로드 API (hwp)
@router.post("/upload/hwp")
async def documents_upload_hwp(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    category_id: Optional[str] = Form(None)
):
    if not file.filename.lower().endswith('.hwp'):
        raise HTTPException(status_code=400, detail="Only .hwp files are allowed.")
    contents = await file.read()
    parse_error_msg = None
    text = ""
    try:
        # 여기서 임시파일 만들지 말고 바로 넘김!
        text = extract_text_from_hwp(contents)
        print("본문 추출 결과:", text)
    except Exception as e:
        parse_error_msg = "본문 추출 실패: " + str(e)
        text = ""
    doc = Doc(
        doc_id=await get_next_doc_id(),
        user_id=user_id,
        title=file.filename.rsplit(".", 1)[0],
        contents=text,
        file_type="hwp",
        file_blob=contents,
        category_id=category_id or ""
    )
    result = await upload_file(doc)
    doc_id = result.get("doc_id")
    return {"doc_id": doc_id, "parse_error": parse_error_msg}

# ======================== 챗봇 ========================

# temp_docs 임시저장본 존재 여부
@router.get("/temp/exists/{doc_id}")
async def check_temp_doc_exists(doc_id: str):
    exists = await has_temp_doc(doc_id)
    return {"exists": exists}

# temp_docs 임시저장본 조회 (존재 시에만)
@router.get("/temp/{doc_id}")
async def get_temp_doc_route(doc_id: str):
    doc = await get_temp_doc(doc_id)
    if not doc:
        raise HTTPException(404, "임시저장 문서가 없습니다")
    return doc

# temp_docs 임시저장본 삭제
@router.delete("/temp/{doc_id}")
async def delete_temp_doc(doc_id: str):
    from app.services.document_service import delete_temp_doc
    await delete_temp_doc(doc_id)
    return {"message": "임시저장 삭제 완료"}

# docs 문서 조회
@router.get("/{doc_id}")
async def get_doc_route(doc_id: str):
    doc = await get_doc(doc_id)
    if not doc:
        raise HTTPException(404, "문서가 없습니다")
    # contents가 str이면 포함, 아니면 제외
    contents = doc.get("contents")
    if isinstance(contents, bytes):
        try:
            contents = contents.decode('utf-8')
        except Exception:
            contents = ""
    return {
        "doc_id": doc["doc_id"],
        "user_id": doc["user_id"],
        "title": doc["title"],
        "contents": contents,
        "file_type": doc.get("file_type"),
        "category_id": doc.get("category_id"),
        "created_dt": doc.get("created_dt"),
        "updated_dt": doc.get("updated_dt"),
        "delete_yn": doc.get("delete_yn"),
        # "file_blob": None  # 절대 포함 X
    }

# 임시저장(처음이면 insert, 있으면 patch)
@router.patch("/temp/{doc_id}")
async def patch_temp_doc_route(doc_id: str, update_data: dict = Body(...)):
    result = await update_temp_doc(doc_id, update_data)
    if not result:
        raise HTTPException(404, "원본 문서가 없습니다")
    return result

# 최종 저장
@router.post("/finalize/{doc_id}")
async def finalize_document_route(doc_id: str):
    result = await finalize_temp_doc(doc_id)
    return result
