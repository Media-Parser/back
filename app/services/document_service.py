# app/services/document_service.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.document_model import Doc
from bson import ObjectId
from datetime import datetime
import re
from typing import Optional
import traceback

ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)

db = client['uploadedbyusers']
collection = db['docs']
temp_collection = db['temp_docs']

def serialize_doc(doc):
    return {
        "doc_id": str(doc.get("doc_id")),
        "user_id": doc["user_id"],
        "title": doc["title"],
        "contents": doc["contents"],
        "created_dt": doc["created_dt"],
        "updated_dt": doc.get("updated_dt"),
        "file_type": doc["file_type"],
        "category_id": doc.get("category_id", ""),  # 새 필드 사용 시
        "delete_yn": doc.get("delete_yn", "n"),
    }
    
async def get_next_doc_id():
    latest_doc = await collection.find_one(
        {"doc_id": {"$regex": "^doc_\\d{8}$"}},
        sort=[("doc_id", -1)]
    )

    if latest_doc and "doc_id" in latest_doc:
        match = re.search(r"doc_(\d{8})", latest_doc["doc_id"])
        if match:
            next_number = int(match.group(1)) + 1
        else:
            next_number = 1
    else:
        next_number = 1

    return f"doc_{next_number:08d}"

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
async def get_documents(user_id: str, category_id: Optional[str] = None):
    query = {"user_id": user_id,"delete_yn": "n"}
    if category_id:
        query["category_id"] = category_id

    docs = await collection.find(query).to_list(length=None)
    return [serialize_doc(doc) for doc in docs]


# 문서 업로드
async def upload_file(file: Doc):
    file_dict = file.model_dump()
    result = await collection.insert_one(file_dict)
    # temp_collection에도 insert
    await temp_collection.insert_one(file_dict)

    if result.inserted_id:
        return {"message": "Doc registered successfully", "doc_id": file_dict["doc_id"]}
    else:
        return {"message": "Failed to register doc"}

# 문서 다운로드
async def download_file(document_id: str):
    doc = await collection.find_one({"doc_id": document_id})
    if doc:
        doc.pop("_id", None)
    return doc

# 문서 삭제
async def delete_file(document_id: str):
    result = await collection.update_one(
        {"doc_id": document_id},
        {"$set": {"delete_yn": "y"}}
    )
    if result.modified_count > 0:
        return True
    else:
        return False

# 휴지통 목록 조회 (delete_yn = 'y')
async def get_deleted_documents(user_id: str):
    try:
        docs_cursor = collection.find({"user_id": user_id, "delete_yn": "y"})
        docs_raw = await docs_cursor.to_list(length=100)
        docs = [convert_mongo_document(doc) for doc in docs_raw]
        return docs
    except Exception as e:
        print("get_deleted_documents error:", e)
        return []

# 문서 복원 처리 (delete_yn = 'n'으로 변경)
async def restore_document(document_id: str) -> bool:
    try:
        result = await collection.update_one(
            {"doc_id": document_id, "delete_yn": "y"},
            {"$set": {"delete_yn": "n"}}
        )
        return result.modified_count > 0
    except Exception as e:
        print("restore_document error:", e)
        return False

# 휴지통에서 개별 문서 영구 삭제
async def delete_document_permanently(document_id: str) -> bool:
    try:
        result = await collection.delete_one({"doc_id": document_id, "delete_yn": "y"})
        print(f"[삭제 요청] doc_id={document_id} / matched={result.raw_result.get('n')} / deleted={result.deleted_count}")
        return result.deleted_count > 0
    except Exception as e:
        print("delete_document_permanently error:", e)
        traceback.print_exc()
        return False

# 휴지통 전체 문서 영구 삭제
async def delete_all_deleted_documents() -> int:
    try:
        result = await collection.delete_many({"delete_yn": "y"})
        return result.deleted_count
    except Exception as e:
        print("❌ delete_all_deleted_documents error:", e)
        traceback.print_exc()  # 추가
        raise  # FastAPI에 에러 전달

# 문서편집-AI: doc_id로 TEMP_COLLECTION 에서 문서 조회
async def get_one_temp_doc(doc_id: str):
    doc = await temp_collection.find_one({"doc_id": doc_id, "delete_Yn": {"$ne": "y"}})
    if doc:
        doc = convert_mongo_document(doc)
    return doc

# 문서 임시 수정
async def update_temp_doc(doc_id: str, update_data: dict):
    try:
        # _id로 찾기 (ObjectId 사용)
        result = await temp_collection.update_one(
            {"doc_id": doc_id, "delete_Yn": {"$ne": "y"}},
            {"$set": update_data}
        )
        if result.modified_count > 0:
            return {"message": "Document updated successfully"}
        else:
            return {"message": "No document updated"}
    except Exception as e:
        print("update_document error:", e)
        return {"message": "Failed to update document"}