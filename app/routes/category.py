# app/routes/category.py
from fastapi import APIRouter, HTTPException
from app.services.category_service import (
    get_categories,
    add_category,
    delete_category,
    update_category
)

router = APIRouter()

# 카테고리 목록 조회
@router.get("/categories")
async def fetch_categories(user_id: str):
    return await get_categories(user_id)

# 카테고리 추가
@router.post("/categories")
async def create_category(data: dict):
    user_id = data.get("user_id")
    label = data.get("label")
    if not user_id or not label:
        raise HTTPException(status_code=400, detail="user_id와 label은 필수입니다.")
    return await add_category(user_id, label)

# 카테고리 삭제
@router.delete("/categories/{category_id}")
async def remove_category(category_id: str):
    deleted = await delete_category(category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="해당 카테고리를 찾을 수 없습니다.")
    return {"success": True}

# 카테고리 수정
@router.put("/categories/{category_id}")
async def edit_category(category_id: str, data: dict):
    label = data.get("label")
    if not label:
        raise HTTPException(status_code=400, detail="label은 필수입니다.")
    updated_category = await update_category(category_id, label) # 수정된 카테고리 객체를 받음
    if not updated_category:
        raise HTTPException(status_code=404, detail="수정 대상 없음")
    return updated_category # 업데이트된 카테고리 객체 반환
