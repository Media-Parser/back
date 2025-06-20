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

docs_collection = db['docs']
temp_docs_collection = db['temp_docs']
categories_collection = db['categories']

# 사용자 ID 생성
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

# 사용자 생성
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

# 사용자 조회
async def find_user_by_email_provider(user_email, provider):
    user = await collection.find_one({"user_email": user_email, "provider": provider})
    if user:
        return UserInDB(**user)
    return None

# 사용자 조회
async def find_user_by_id(user_id: str):
    user = await collection.find_one({"user_id": user_id})
    if user:
        user.pop("_id", None)
        return UserInDB(**user)
    return None

# 사용자 및 관련 데이터 삭제
async def delete_user_and_related(user_id: str):
    # 1. docs 삭제
    await docs_collection.delete_many({"user_id": user_id})
    # 2. temp_docs 삭제
    await temp_docs_collection.delete_many({"user_id": user_id})
    # 3. categories 삭제
    await categories_collection.delete_many({"user_id": user_id})
    # 4. user 자체 삭제 (users 컬렉션 예시)
    await db['users'].delete_one({"user_id": user_id})
    return {"message": "사용자 및 관련 데이터 모두 삭제 완료"}