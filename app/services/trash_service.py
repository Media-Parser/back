# app/services/trash_service.py

import os
import traceback
from bson import ObjectId
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB 연결 설정
ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']
collection = db['docs']

# 상수
DELETE_YES = "y"
DELETE_NO = "n"
tz_kst = timezone(timedelta(hours=9))

# ===== 유틸 =====

def convert_mongo_document(doc: dict) -> dict:
    """MongoDB 문서에서 ObjectId, datetime, bytes 등을 문자열로 변환"""
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.astimezone(tz_kst).isoformat()
        elif isinstance(value, bytes):
            try:
                result[key] = value.decode("utf-8")
            except UnicodeDecodeError:
                result[key] = value.decode("utf-8", errors="replace")
        else:
            result[key] = value
    return result


# ===== 휴지통 기능 =====

# 휴지통 목록 조회 (delete_yn = 'y')
async def get_deleted_documents(user_id: str):
    try:
        docs_cursor = collection.find({"user_id": user_id, "delete_yn": DELETE_YES})
        docs_raw = await docs_cursor.to_list(length=100)
        return [convert_mongo_document(doc) for doc in docs_raw]
    except Exception as e:
        print("❌ get_deleted_documents error:", e)
        traceback.print_exc()
        return []

# 문서 복원 처리
async def restore_document(document_id: str) -> bool:
    try:
        result = await collection.update_one(
            {"doc_id": document_id, "delete_yn": DELETE_YES},
            {"$set": {"delete_yn": DELETE_NO}}
        )
        return result.modified_count > 0
    except Exception as e:
        print("❌ restore_document error:", e)
        traceback.print_exc()
        return False

# 휴지통에서 개별 문서 영구 삭제
async def delete_document_permanently(document_id: str) -> bool:
    try:
        result = await collection.delete_one(
            {"doc_id": document_id, "delete_yn": DELETE_YES}
        )
        print(f"[삭제 요청] doc_id={document_id} | matched={result.raw_result.get('n')} | deleted={result.deleted_count}")
        return result.deleted_count > 0
    except Exception as e:
        print("❌ delete_document_permanently error:", e)
        traceback.print_exc()
        return False

# 휴지통 전체 문서 영구 삭제
async def delete_all_deleted_documents() -> int:
    try:
        result = await collection.delete_many({"delete_yn": DELETE_YES})
        print(f"[전체 삭제] deleted_count={result.deleted_count}")
        return result.deleted_count
    except Exception as e:
        print("❌ delete_all_deleted_documents error:", e)
        traceback.print_exc()
        raise
