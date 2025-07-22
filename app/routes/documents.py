from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Response, Query, Body, Depends
from app.services.hwpx_extractor import extract_text_from_hwpx
from app.services.hwp_extractor import extract_text_from_hwp
from app.services.document_service import (
    upload_file, get_next_doc_id, get_documents, download_file, delete_file,
    update_document_title, has_temp_doc, get_temp_doc, get_doc, update_temp_doc, finalize_temp_doc,delete_temp_doc
)
from app.models.document_model import Doc
from typing import List, Optional, Dict
from urllib.parse import quote
from app.core.jwt import get_current_user

# [보안] 모든 라우터에 JWT 인증 의존성 추가
router = APIRouter(prefix="/documents", tags=["Documents"], dependencies=[Depends(get_current_user)])

# ======================== 대시보드 ========================

@router.get("/")
async def list_documents(user_id: str = Query(...), current_user_id: str = Depends(get_current_user)):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You can only access your own documents.")
    try:
        docs = await get_documents(user_id)
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/title/{doc_id}")
async def update_document_title_api(doc_id: str, data: dict = Body(...), current_user_id: str = Depends(get_current_user)):
    new_title = data.get("title")
    if not new_title or not new_title.strip():
        raise HTTPException(status_code=400, detail="제목이 비어 있습니다.")
    ok = await update_document_title(doc_id, current_user_id, new_title.strip())
    if not ok:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없거나 수정되지 않았습니다.")
    return {"message": "Document title updated successfully"}

@router.get("/download/{doc_id}")
async def download_document(doc_id: str, current_user_id: str = Depends(get_current_user)):
    try:
        doc = await download_file(doc_id, current_user_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found or you don't have permission.")
        
        title = doc.get('title', 'document')
        ext = doc.get('file_type', '')
        filename = f"{title}.{ext}" if ext else f"{title}.hwpx"
        quoted_filename = quote(filename)
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}"}
        return Response(content=doc.get("file_blob") or doc.get("contents"), media_type="application/octet-stream", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{doc_id}")
async def delete_document_api(doc_id: str, current_user_id: str = Depends(get_current_user)):
    try:
        await delete_file(doc_id, current_user_id)
        return {"message": "Document deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload/hwpx")
async def documents_upload_hwpx(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    category_id: Optional[str] = Form(None),
    current_user_id: str = Depends(get_current_user)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You can only upload to your own account.")
    if not file.filename.lower().endswith('.hwpx'):
        raise HTTPException(status_code=400, detail="Only .hwpx files are allowed.")
    contents = await file.read()
    text = ""
    try:
        text = extract_text_from_hwpx(contents)
    except Exception as e:
        print(f"본문 추출 실패: {e}")
    doc = Doc(
        doc_id=await get_next_doc_id(), user_id=user_id, title=file.filename.rsplit(".", 1)[0],
        contents=text, file_type="hwpx", file_blob=contents, category_id=category_id or ""
    )
    return await upload_file(doc)

@router.post("/upload/hwp")
async def documents_upload_hwp(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    category_id: Optional[str] = Form(None),
    current_user_id: str = Depends(get_current_user)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You can only upload to your own account.")
    if not file.filename.lower().endswith('.hwp'):
        raise HTTPException(status_code=400, detail="Only .hwp files are allowed.")
    contents = await file.read()
    text = ""
    try:
        text = extract_text_from_hwp(contents)
    except Exception as e:
        print(f"본문 추출 실패: {e}")
    doc = Doc(
        doc_id=await get_next_doc_id(), user_id=user_id, title=file.filename.rsplit(".", 1)[0],
        contents=text, file_type="hwp", file_blob=contents, category_id=category_id or ""
    )
    return await upload_file(doc)

# ======================== 챗봇/에디터 ========================

@router.get("/temp/exists/{doc_id}")
async def check_temp_doc_exists(doc_id: str, current_user_id: str = Depends(get_current_user)):
    exists = await has_temp_doc(doc_id, current_user_id)
    return {"exists": exists}

@router.get("/temp/{doc_id}")
async def get_temp_doc_route(doc_id: str, current_user_id: str = Depends(get_current_user)):
    doc = await get_temp_doc(doc_id, current_user_id)
    if not doc:
        raise HTTPException(404, "임시저장 문서가 없습니다")
    
    # [수정] file_blob 필드를 응답에서 제외
    doc.pop("file_blob", None)
    return doc

@router.delete("/temp/{doc_id}")
async def delete_temp_doc_route(doc_id: str, current_user_id: str = Depends(get_current_user)):
    await delete_temp_doc(doc_id, current_user_id)
    return {"message": "임시저장 삭제 완료"}

@router.get("/{doc_id}")
async def get_doc_route(doc_id: str, current_user_id: str = Depends(get_current_user)):
    doc = await get_doc(doc_id, current_user_id)
    if not doc:
        raise HTTPException(404, "문서가 없거나 접근 권한이 없습니다.")
    
    contents = doc.get("contents")
    if isinstance(contents, bytes):
        try:
            contents = contents.decode('utf-8')
        except UnicodeDecodeError:
            try:
                contents = contents.decode('cp949')
            except Exception:
                contents = ""
    doc["contents"] = contents
    topic_id = doc.get("topic_id", 11)
    hashtag = doc.get("hashtag", ["언니메롱","언니안녕","야호"])
    # [수정] file_blob 필드를 응답에서 제외
    doc.pop("file_blob", None)
    return {**doc, "topic_id": topic_id, "hashtag":hashtag}

@router.patch("/temp/{doc_id}")
async def patch_temp_doc_route(doc_id: str, update_data: dict = Body(...), current_user_id: str = Depends(get_current_user)):
    result = await update_temp_doc(doc_id, current_user_id, update_data)
    if not result:
        raise HTTPException(404, "원본 문서가 없거나 접근 권한이 없습니다.")
    return result

@router.post("/finalize/{doc_id}")
async def finalize_document_route(doc_id: str, current_user_id: str = Depends(get_current_user)):
    result = await finalize_temp_doc(doc_id, current_user_id)
    return result
