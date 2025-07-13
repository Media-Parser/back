# app/services/category_service.py

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB 설정
MONGO_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["uploadedbyusers"]
collection = db["categories"]
doc_collection = db["docs"]

# 시간대 설정
tz_kst = timezone(timedelta(hours=9))


# ===== 유틸 =====

def build_next_category_id(current_id: Optional[str]) -> str:
    if current_id:
        match = re.search(r"category_(\d{8})", current_id)
        next_number = int(match.group(1)) + 1 if match else 1
    else:
        next_number = 1
    return f"category_{next_number:08d}"

def create_path(label: str) -> str:
    return f"/dashboard/{label.lower()}"


# ===== 기능 =====

# 카테고리 ID 생성
async def get_next_category_id():
    latest = await collection.find_one(
        {"category_id": {"$regex": "^category_\\d{8}$"}},
        sort=[("category_id", -1)]
    )
    current_id = latest["category_id"] if latest else None
    return build_next_category_id(current_id)

# 카테고리 조회
async def get_categories(user_id: str):
    docs = await collection.find({"user_id": user_id}).to_list(length=None)
    return [
        {
            "category_id": str(doc["category_id"]),
            "user_id": doc["user_id"],
            "label": doc["label"],
            "path": doc["path"],
            "created_dt": doc.get("created_dt").astimezone(tz_kst).isoformat() if doc.get("created_dt") else None,
            "updated_dt": doc.get("updated_dt").astimezone(tz_kst).isoformat() if doc.get("updated_dt") else None
        } for doc in docs
    ]

# 카테고리 추가
async def add_category(user_id: str, label: str, path: Optional[str] = None):
    category_id = await get_next_category_id()
    now = datetime.now(tz=tz_kst)
    final_path = path or create_path(label)

    doc = {
        "category_id": category_id,
        "user_id": user_id,
        "label": label,
        "path": final_path,
        "created_dt": now,
    }
    await collection.insert_one(doc)

    return {
        "category_id": category_id,
        "user_id": user_id,
        "label": label,
        "path": final_path,
        "created_dt": now.isoformat()
    }

# 카테고리 삭제
async def delete_category(category_id: str):
    result = await collection.delete_one({"category_id": category_id})
    await doc_collection.update_many(
        {"category_id": category_id},
        {"$set": {"category_id": ""}}
    )
    return result.deleted_count

# 카테고리 수정
async def update_category(category_id: str, label: str):
    path = create_path(label)
    now = datetime.now(tz=tz_kst)
    updated_doc = await collection.find_one_and_update(
        {"category_id": category_id},
        {
            "$set": {
                "label": label,
                "path": path,
                "updated_dt": now
            }
        },
        return_document=True
    )

    if updated_doc:
        return {
            "category_id": str(updated_doc["category_id"]),
            "user_id": updated_doc["user_id"],
            "label": updated_doc["label"],
            "path": updated_doc["path"],
            "created_dt": updated_doc.get("created_dt").astimezone(tz_kst).isoformat() if updated_doc.get("created_dt") else None,
            "updated_dt": now.isoformat()
        }
    return None

# 문서 카테고리 이동
async def move_document(doc_id: str, category_id: str):
    now = datetime.now(tz=tz_kst)
    await doc_collection.update_one(
        {"doc_id": doc_id},
        {"$set": {
            "category_id": category_id,
            "updated_dt": now
        }}
    )
