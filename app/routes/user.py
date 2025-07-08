# 📁 app/routes/user.py
from fastapi import APIRouter, HTTPException, Depends
from app.services import user_service
from app.models.user_model import UserInDB
from app.services.user_service import delete_user_and_related
from app.core.jwt import get_current_user
router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(get_current_user)])

# 사용자 조회
@router.get("/{user_id}", response_model=UserInDB)
async def get_user_info(user_id: str):
    if not user_id.startswith("user_"):
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    user = await user_service.find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# 사용자 및 관련 데이터 삭제
@router.delete("/{user_id}")
async def delete_user(user_id: str):
    try:
        result = await delete_user_and_related(user_id)
        return result
    except Exception as e:
        print("유저 삭제 에러:", e)
        raise HTTPException(status_code=500, detail="사용자 삭제 중 오류 발생")

