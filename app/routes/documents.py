# app/routes/documents.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Response, Query, Body
from app.services.hwpx_extractor import extract_text_from_hwpx
from app.services.hwp_extractor import extract_text_from_hwp
from app.services.document_service import upload_file, get_next_doc_id
from app.services.document_service import get_documents
from app.services.document_service import download_file
from app.services.document_service import delete_file
from app.models.document_model import Doc
from fastapi import Query
from app.services.document_service import get_one_temp_doc, update_temp_doc, get_or_create_temp_doc
import traceback
from urllib.parse import quote
from typing import Optional

router = APIRouter(prefix="/documents", tags=["Documents"])

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
        return {"text": text, "db_result": result}
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
        return {"text": text, "db_result": result}
    except Exception as e:
        print("업로드 실패:", e) 
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get("/{documentId}")
async def get_temp_document(documentId: str):
    try:
        doc = await get_or_create_temp_doc(documentId)  # ← 기존 get_one_temp_doc → get_or_create_temp_doc
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc
    except Exception as e:
        print("임시문서 조회 에러:", e)
        raise HTTPException(status_code=500, detail=str(e))

# # 문서편집-AI: GET temp 문서 
# @router.get("/{documentId}")
# async def get_temp_document(documentId: str):
#     try:
#         doc = await get_one_temp_doc(documentId)
#         if not doc:
#             raise HTTPException(status_code=404, detail="Document not found")
#         return doc
#     except Exception as e:
#         print("임시문서 조회 에러:", e)
#         raise HTTPException(status_code=500, detail=str(e))
    

# 문서 임시저장: temp 문서 수정
@router.patch("/{documentId}")
async def autosave_document(documentId: str, update_data: dict = Body(...)):
    try:
        doc = await update_temp_doc(documentId, update_data)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc
    except Exception as e:
        print("임시문서 수정 에러:", e)
        raise HTTPException(status_code=500, detail=str(e))
