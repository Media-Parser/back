# app/routes/documents.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Form,Response
from app.services.hwpx_extractor import extract_text_from_hwpx
from app.services.hwp_extractor import extract_text_from_hwp
from app.services.document_service import upload_file
from app.services.document_service import get_documents
from app.services.document_service import download_file
from app.services.document_service import delete_file
from app.models.document_model import Doc
import uuid
from fastapi import Query
import traceback
from fastapi import Response
from urllib.parse import quote

router = APIRouter()

# 문서 업로드 API (hwpx)
@router.post("/documents/upload/hwpx")
async def documents_upload(file: UploadFile = File(...), user_id: str = Form(...)):
    if not file.filename.endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="Only .hwpx files are allowed.")

    contents = await file.read()
    try:
        text = extract_text_from_hwpx(contents)
        doc = Doc(
            doc_id=str(uuid.uuid4()),
            user_id=user_id,
            title=file.filename.rsplit(".", 1)[0],
            contents=text,
            file_type="hwpx"
        )
        result = await upload_file(doc)
        return {"text": text, "db_result": result}
    except Exception as e:
        print("업로드 실패:", e) 
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 문서 업로드 API (hwp)
@router.post("/documents/upload/hwp")
async def documents_upload(file: UploadFile = File(...), user_id: str = Form(...)):
    if not file.filename.endswith(".hwp"):
        raise HTTPException(status_code=400, detail="Only .hwp files are allowed.")

    contents = await file.read()
    try:
        text = extract_text_from_hwp(contents)
        doc = Doc(
            doc_id=str(uuid.uuid4()),
            user_id=user_id,
            title=file.filename.rsplit(".", 1)[0],
            contents=text,
            file_type="hwp"
        )
        result = await upload_file(doc)
        return {"text": text, "db_result": result}
    except Exception as e:
        print("업로드 실패:", e) 
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 문서 조회 API
@router.get("/documents")
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
@router.get("/documents/download/{doc_id}")
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
@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    try:
        await delete_file(doc_id)
        return {"message": "Document deleted successfully"}
    except Exception as e:
        print("문서삭제 에러:", e)
        raise HTTPException(status_code=500, detail=str(e))
