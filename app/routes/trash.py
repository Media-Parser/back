# 📁 app/routes/trash.py
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from app.services.trash_service import (
    get_deleted_documents,
    restore_document,
    delete_document_permanently,
    delete_all_deleted_documents
)
from app.models.document_model import Doc
from typing import List
from app.core.jwt import get_current_user

router = APIRouter(prefix="/trash", tags=["Trash"], dependencies=[Depends(get_current_user)])

# 1. 휴지통 문서 목록 조회
@router.get("/", response_model=List[Doc])
async def get_trash_documents(user_id: str = Query(...)):
    try:
        docs = await get_deleted_documents(user_id)
        return docs
    except Exception as e:
        print("휴지통 문서 조회 에러:", e)
        raise HTTPException(status_code=500, detail=str(e))

# 2. 휴지통 문서 복원
@router.post("/restore/{document_id}")
async def restore_trash_document(document_id: str):
    try:
        success = await restore_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"success": True, "message": "Document restored"}
    except Exception as e:
        print("휴지통 문서 복원 에러:", e)
        raise HTTPException(status_code=500, detail=str(e))

# 3. 휴지통 문서 전체 삭제
@router.delete("/all")
async def delete_all_trash_documents():
    try:
        deleted_count = await delete_all_deleted_documents()
        return {"success": True, "message": f"{deleted_count} documents permanently deleted"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# 4. 휴지통 문서 개별 삭제
@router.delete("/{document_id}")
async def delete_trash_document(document_id: str):
    try:
        success = await delete_document_permanently(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found or already deleted")
        return {"success": True, "message": "Document permanently deleted"}
    except Exception as e:
        print("휴지통 문서 개별 삭제 에러:", e)
        raise HTTPException(status_code=500, detail=str(e))
