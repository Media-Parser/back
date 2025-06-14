# 📁 app/routes/user.py
from fastapi import APIRouter, HTTPException
from app.services import user_service
from app.models.user import UserInDB

router = APIRouter()

@router.get("/users/{user_id}", response_model=UserInDB)
async def get_user_info(user_id: str):
    user = await user_service.find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
