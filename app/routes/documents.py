# 📁 app/routes/auth.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.hwpx_extractor import extract_text_from_hwpx


router = APIRouter()

@router.post("/documents/upload")
async def extract_hwpx_text(file: UploadFile = File(...)):
    if not file.filename.endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="Only .hwpx files are allowed.")

    contents = await file.read()
    try:
        text = extract_text_from_hwpx(file.filename, contents)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
