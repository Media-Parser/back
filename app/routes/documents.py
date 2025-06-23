# app/routes/documents.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Response, Query, Body
from app.services.hwpx_extractor import extract_text_from_hwpx
from app.services.hwp_extractor import extract_text_from_hwp
from app.services.document_service import (
    upload_file, get_next_doc_id, get_documents, download_file, delete_file,
    update_document_title, has_temp_doc,get_temp_doc, get_doc,update_temp_doc,finalize_temp_doc
)
from app.models.document_model import Doc
from typing import Optional
import traceback
from urllib.parse import quote


router = APIRouter(prefix="/documents", tags=["Documents"])

# ======================== 대시보드 ========================
# 문서 조회 API
@router.get("/")
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
        
        print("title:", title)
        print("ext:", ext)

        filename = f"{title}.{ext}" if ext else title + ".hwpx"
        print("filename:", filename)
        quoted_filename = quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}"
        }
        return Response(
            content=doc["contents"],
            media_type="application/octet-stream",
            headers=headers
        )
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
async def documents_upload(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    category_id: Optional[str] = Form(None)
):

    if not file.filename.endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="Only .hwpx files are allowed.")

    contents = await file.read()
    try:
        text = extract_text_from_hwpx(contents)
        doc = Doc(
        doc_id=await get_next_doc_id(),
        user_id=user_id,
        title=file.filename.rsplit(".", 1)[0],
        contents=text,
        file_type="hwpx",
        category_id=category_id or ""
        )
        result = await upload_file(doc)
        doc_id = result.get("doc_id")
        if not doc_id:
            raise HTTPException(status_code=500, detail="문서 ID 생성 실패")
        return {"doc_id": doc_id}
    except Exception as e:
        print("업로드 실패:", e) 
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 문서 업로드 API (hwp)
@router.post("/upload/hwp")
async def documents_upload(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    category_id: Optional[str] = Form(None)
):
    if not file.filename.endswith(".hwp"):
        raise HTTPException(status_code=400, detail="Only .hwp files are allowed.")

    contents = await file.read()
    try:
        text = extract_text_from_hwp(contents)
        doc = Doc(
        doc_id=await get_next_doc_id(),
        user_id=user_id,
        title=file.filename.rsplit(".", 1)[0],
        contents=text,
        file_type="hwp",
        category_id=category_id or ""
        )
        result = await upload_file(doc)
        doc_id = result.get("doc_id")
        if not doc_id:
            raise HTTPException(status_code=500, detail="문서 ID 생성 실패")
        return {"doc_id": doc_id}
    except Exception as e:
        print("업로드 실패:", e) 
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ======================== 챗봇 ========================
# @router.get("/{documentId}")
# async def get_temp_document(documentId: str):
#     try:
#         doc = await get_or_create_temp_doc(documentId)  # ← 기존 get_one_temp_doc → get_or_create_temp_doc
#         if not doc:
#             raise HTTPException(status_code=404, detail="Document not found")
#         return doc
#     except Exception as e:
#         print("임시문서 조회 에러:", e)
#         raise HTTPException(status_code=500, detail=str(e))

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

# docs 문서 조회
@router.get("/{doc_id}")
async def get_doc_route(doc_id: str):
    doc = await get_doc(doc_id)
    if not doc:
        raise HTTPException(404, "문서가 없습니다")
    return doc

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