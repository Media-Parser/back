from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.hwpx_extractor import extract_text_from_hwpx
from app.services.load_doc_by_user import create_file, Doc
from datetime import datetime
import uuid


router = APIRouter()
@router.get("/")
def read_root():
    return {"message": "Hello, Jinoh!"} # JSON 형식으로 반환
    

@router.post("/documents/upload/hwpx")
async def documents_upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="Only .hwpx files are allowed.")
    
    

    contents = await file.read()
    try:
        text = extract_text_from_hwpx(contents)
        doc = Doc(
            doc_id=str(uuid.uuid4()),
            user_id="xxx",
            title=file.filename.rsplit(".", 1)[0],
            contents=text, # file.filename.rsplit(".", 1)[1],
            file_type="hwpx"
        )
        result = create_file(doc)
        return {"text": text, "db_result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))