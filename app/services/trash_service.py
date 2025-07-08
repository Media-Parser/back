# app/services/trash_service.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
import traceback
from bson import ObjectId
from datetime import datetime

ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)

db = client['uploadedbyusers']
collection = db['docs']

# ======================== 휴지통 ========================
# MongoDB 문서에서 ObjectId, datetime 등을 문자열로 변환
def convert_mongo_document(doc: dict) -> dict:
    """MongoDB 문서에서 ObjectId, datetime, bytes 등을 문자열로 변환"""
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, bytes):  # ★ 여기를 추가!
            try:
                result[key] = value.decode("utf-8")
            except UnicodeDecodeError:
                result[key] = value.decode("utf-8", errors="replace")  # 깨진 부분은 �로 대체
        else:
            result[key] = value
    return result

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