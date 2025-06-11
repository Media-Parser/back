# app/routes/documents.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.hwpx_extractor import extract_text_from_hwpx
from app.services.document_service import create_file
from app.models.document_model import Doc
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/documents/upload/hwpx")
async def documents_upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="Only .hwpx files are allowed.")

    contents = await file.read()
    try:
        text = extract_text_from_hwpx(contents)
        doc = Doc(
            doc_id=str(uuid.uuid4()),
            user_id="xxx",  # 실제 서비스에서는 인증 유저의 id로 변경!
            title=file.filename.rsplit(".", 1)[0],
            contents=text,
            file_type="hwpx"
        )
        result = create_file(doc)
        return {"text": text, "db_result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
