# app/services/user_service.py

import os
import re
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from app.models.user_model import UserInDB

# ===== 설정 =====
ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']

collection = db['users']
docs_collection = db['docs']
temp_docs_collection = db['temp_docs']
categories_collection = db['categories']

tz_kst = timezone(timedelta(hours=9))


# ===== 공통 유틸 =====

def build_next_user_id(current_id: str = None) -> str:
    if current_id:
        match = re.search(r"user_(\d{8})", current_id)
        next_number = int(match.group(1)) + 1 if match else 1
    else:
        next_number = 1
    return f"user_{next_number:08d}"


# ===== 사용자 관련 기능 =====

# 사용자 ID 생성
async def get_next_user_id():
    latest_user = await collection.find_one(
        {"user_id": {"$regex": "^user_\\d{8}$"}},
        sort=[("user_id", -1)]
    )
    current_id = latest_user["user_id"] if latest_user else None
    return build_next_user_id(current_id)

# 사용자 생성 또는 조회
async def find_or_create_user(user_name: str, user_email: str, provider: str):
    user = await collection.find_one({"user_email": user_email, "provider": provider})
    if user:
        user.pop("_id", None)
        return UserInDB(**user)

    new_user_id = await get_next_user_id()

    doc = {
        "user_id": new_user_id,
        "user_name": user_name,
        "user_email": user_email,
        "provider": provider,
        "create_dt": datetime.now(tz=tz_kst),
    }

    await collection.insert_one(doc)
    return UserInDB(**doc)

# 이메일 + provider 기준 사용자 조회
async def find_user_by_email_provider(user_email: str, provider: str):
    user = await collection.find_one({"user_email": user_email, "provider": provider})
    if user:
        user.pop("_id", None)
        return UserInDB(**user)
    return None

# ID 기준 사용자 조회
async def find_user_by_id(user_id: str):
    user = await collection.find_one({"user_id": user_id})
    if user:
        user.pop("_id", None)
        return UserInDB(**user)
    return None

# 사용자 및 연관 데이터 삭제
async def delete_user_and_related(user_id: str):
    await docs_collection.delete_many({"user_id": user_id})
    await temp_docs_collection.delete_many({"user_id": user_id})
    await categories_collection.delete_many({"user_id": user_id})
    await collection.delete_one({"user_id": user_id})
    return {"message": "사용자 및 관련 데이터 모두 삭제 완료"}
