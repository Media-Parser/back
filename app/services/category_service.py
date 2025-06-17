# app/services/category_service.py
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime
from typing import Optional
import os
import re

MONGO_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["uploadedbyusers"]
collection = db["categories"]

async def get_next_category_id():
    latest_category = await collection.find_one(
        {"category_id": {"$regex": "^category_\\d{8}$"}},
        sort=[("category_id", -1)]
    )

    if latest_category and "category_id" in latest_category:
        match = re.search(r"category_(\d{8})", latest_category["category_id"])
        if match:
            next_number = int(match.group(1)) + 1
        else:
            next_number = 1
    else:
        next_number = 1

    return f"category_{next_number:08d}"

def create_path(label: str) -> str:
    return f"/dashboard/{label.lower()}"


async def get_categories(user_id: str):
    docs = await collection.find({"user_id": user_id}).to_list(length=None)
    return [
        {
            "category_id": str(doc["category_id"]),
            "user_id": doc["user_id"],
            "label": doc["label"],
            "path": doc["path"],
            "created_dt": doc.get("created_dt"),
            "updated_dt": doc.get("updated_dt")
        } for doc in docs
    ]


async def add_category(user_id: str, label: str, path: Optional[str] = None):
    category_id = await get_next_category_id()
    path = path or f"/dashboard/{label.lower()}"
    doc = {
        "category_id": category_id,
        "user_id": user_id,
        "label": label,
        "path": create_path(label),
        "created_dt": datetime.now(),
    }
    result = await collection.insert_one(doc)
    
    return {
        "category_id": category_id,
        "user_id": user_id,
        "label": label,
        "path": doc["path"],
        "created_dt": doc["created_dt"],
    }

async def delete_category(category_id: str):
    result = await collection.delete_one({"category_id": category_id})
    doc_collection = db["docs"]

    await doc_collection.update_many(
        {"category_id": category_id},
        {"$set": {"category_id": ""}}
    )
    return result.deleted_count

async def update_category(category_id: str, label: str):
    path = create_path(label) # path 생성 로직은 동일
    updated_doc = await collection.find_one_and_update( # find_one_and_update 사용
        {"category_id": category_id},
        {
            "$set": {
                "label": label,
                "path": path,
                "updated_dt": datetime.now()
            }
        },
        return_document=True # 업데이트된 문서를 반환하도록 설정
    )
    if updated_doc:
        return {
            "category_id": str(updated_doc["category_id"]),
            "user_id": updated_doc["user_id"],
            "label": updated_doc["label"],
            "path": updated_doc["path"],
            "created_dt": updated_doc.get("created_dt"),
            "updated_dt": updated_doc.get("updated_dt")
        }
    return None # 업데이트 실패 시 None 반환
