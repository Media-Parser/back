# app/services/user_service.py
from app.models.user_model import UserInDB
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
import re

ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)

db = client['uploadedbyusers']
collection = db['users']

async def get_next_user_id():
    # user_id 필드가 있는 가장 마지막 사용자 찾기
    latest_user = await collection.find_one(
        {"user_id": {"$regex": "^user_\\d{8}$"}},  # user_00000001 형식
        sort=[("user_id", -1)]
    )

    if latest_user and "user_id" in latest_user:
        match = re.search(r"user_(\d{8})", latest_user["user_id"])
        if match:
            next_number = int(match.group(1)) + 1
        else:
            next_number = 1
    else:
        # 컬렉션이 비어있거나 user_id가 없는 경우
        next_number = 1

    return f"user_{next_number:08d}"

async def find_or_create_user(user_name, user_email, provider):
    user = await collection.find_one({"user_email": user_email, "provider": provider})
    if user:
        return UserInDB(**user)

    new_user_id = await get_next_user_id()

    doc = {
        "user_id": new_user_id,
        "user_name": user_name,
        "user_email": user_email,
        "provider": provider,
        "create_dt": datetime.utcnow()
    }

    result = await collection.insert_one(doc)
    return UserInDB(**doc)

async def find_user_by_email_provider(user_email, provider):
    user = await collection.find_one({"user_email": user_email, "provider": provider})
    if user:
        return UserInDB(**user)
    return None

async def find_user_by_id(user_id: str):
    user = await collection.find_one({"user_id": user_id})
    if user:
        user.pop("_id", None)
        return UserInDB(**user)
    return None
