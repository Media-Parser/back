from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.hwpx_extractor import extract_text_from_hwpx
from app.services.load_doc_by_user import create_file


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
        text = extract_text_from_hwpx(contents)  # 파일명 인자 제거
        create_file({
            "user_id": "xxx",
            "title": "문서 제목",
            "contents": text,
            "file_type": "hwpx"
        })
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))