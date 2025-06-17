# 📁 app/routes/user.py
from fastapi import APIRouter, HTTPException
from app.services import user_service
from app.models.user_model import UserInDB
from bson import ObjectId, errors as bson_errors

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{user_id}", response_model=UserInDB)
async def get_user_info(user_id: str):
    if not user_id.startswith("user_"):
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    user = await user_service.find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

