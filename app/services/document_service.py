# app/services/document_service.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.document_model import Doc
from bson import ObjectId
from datetime import datetime

ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)

db = client['uploadedbyusers']
collection = db['docs']

# MongoDB 문서에서 ObjectId, datetime 등을 문자열로 변환
def convert_mongo_document(doc: dict) -> dict:
    """MongoDB 문서에서 ObjectId, datetime 등을 문자열로 변환"""
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()  # "2025-06-14T16:11:00"
        else:
            result[key] = value
    return result


# 유저별 문서 조회
async def get_documents(user_id: str):
    docs = []
    cursor = collection.find({"user_id": user_id, "delete_Yn": {"$ne": "y"}})
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs

# 문서 업로드
async def upload_file(file: Doc):
    file_dict = file.model_dump()

    result = await collection.insert_one(file_dict)
    if result.inserted_id:
        return {"message": "Doc registered successfully", "doc_id": file_dict["doc_id"]}
    else:
        return {"message": "Failed to register doc"}

# 문서 다운로드
async def download_file(document_id: str):
    doc = await collection.find_one({"doc_id": document_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

# 문서 삭제
async def delete_file(document_id: str):
    result = await collection.update_one(
        {"doc_id": document_id},
        {"$set": {"delete_Yn": "y"}}
    )
    if result.modified_count > 0:
        return True
    else:
        return False

# 휴지통 목록 조회 (delete_Yn = 'y')
async def get_deleted_documents(user_id: str):
    try:
        docs_cursor = collection.find({"user_id": user_id, "delete_Yn": "y"})
        docs_raw = await docs_cursor.to_list(length=100)
        docs = [convert_mongo_document(doc) for doc in docs_raw]
        return docs
    except Exception as e:
        print("get_deleted_documents error:", e)
        return []

# 문서 복원 처리 (delete_Yn = 'n'으로 변경)
async def restore_document(document_id: str) -> bool:
    try:
        result = await collection.update_one(
            {"_id": ObjectId(document_id), "delete_Yn": "y"},
            {"$set": {"delete_Yn": "n"}}
        )
        return result.modified_count > 0
    except Exception as e:
        print("restore_document error:", e)
        return False

# 휴지통에서 개별 문서 영구 삭제
async def delete_document_permanently(document_id: str) -> bool:
    try:
        result = await collection.delete_one({"_id": ObjectId(document_id), "delete_Yn": "y"})
        return result.deleted_count > 0
    except Exception as e:
        print("delete_document_permanently error:", e)
        return False

# 휴지통 전체 문서 영구 삭제
async def delete_all_deleted_documents() -> int:
    try:
        result = await collection.delete_many({"delete_Yn": "y"})
        return result.deleted_count
    except Exception as e:
        print("delete_all_deleted_documents error:", e)
        return 0



