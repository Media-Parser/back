# app/services/document_service.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.document_model import Doc
from datetime import datetime
import re
from typing import Optional
from fastapi import HTTPException

ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)

db = client['uploadedbyusers']
collection = db['docs']
temp_collection = db['temp_docs']

# ====== [공통 유틸 함수] ======

# MongoDB 문서에서 ObjectId, datetime 등을 문자열로 변환
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

# 문서 ID 생성   
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

# ======================== 대시보드 ========================

# 유저별 문서 조회
async def get_documents(user_id: str, category_id: Optional[str] = None):
    query = {"user_id": user_id,"delete_yn": "n"}
    if category_id:
        query["category_id"] = category_id

    docs = await collection.find(query).to_list(length=None)
    return [serialize_doc(doc) for doc in docs]

# 문서 제목 변경
async def update_document_title(doc_id: str, new_title: str) -> bool:
    from datetime import datetime
    result = await collection.update_one(
        {"doc_id": doc_id},
        {"$set": {"title": new_title, "updated_dt": datetime.now()}}
    )
    return result.modified_count > 0

# 문서 다운로드
async def download_file(document_id: str):
    # 1. temp_docs에 우선 검색
    doc = await temp_collection.find_one({"doc_id": document_id})
    if doc:
        doc.pop("_id", None)
        return doc
    # 2. temp에 없으면 원본 docs에서 검색
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
    await temp_collection.delete_one({"doc_id": document_id})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return True

# 문서 업로드
async def upload_file(file: Doc):
    file_dict = file.model_dump()
    result = await collection.insert_one(file_dict)

    if result.inserted_id:
        return {"message": "Doc registered successfully", "doc_id": file_dict["doc_id"]}
    else:
        return {"message": "Failed to register doc"}

# ======================== 챗봇 ========================

# temp_docs 임시저장본 존재 여부 확인
async def has_temp_doc(doc_id: str) -> bool:
    doc = await temp_collection.find_one({"doc_id": doc_id})
    return doc is not None

# temp_docs 조회 (존재 시에만)
async def get_temp_doc(doc_id: str):
    doc = await temp_collection.find_one({"doc_id": doc_id})
    if doc: doc.pop("_id", None)
    return doc

# docs 조회 (존재 시에만)
async def get_doc(doc_id: str):
    doc = await collection.find_one({"doc_id": doc_id})
    if doc: doc.pop("_id", None)
    return doc

# temp_docs 삭제
async def delete_temp_doc(doc_id: str):
    await temp_collection.delete_one({"doc_id": doc_id})

# temp_docs 업데이트
async def update_temp_doc(doc_id: str, update_data: dict):
    update_data["updated_dt"] = datetime.now()
    doc = await temp_collection.find_one({"doc_id": doc_id})
    if not doc:
        # 최초 편집시 원본 복사 후 변경
        origin = await collection.find_one({"doc_id": doc_id})
        if not origin:
            return None
        base_doc = {
            "doc_id": origin.get("doc_id"),
            "user_id": origin.get("user_id"),
            "title": origin.get("title"),
            "contents": origin.get("contents"),
            "file_type": origin.get("file_type"),
            "created_dt": origin.get("created_dt"),
            "updated_dt": datetime.now(),
        }
        base_doc.update(update_data)
        await temp_collection.insert_one(base_doc)
        return {"message": "Temp doc created"}
    else:
        await temp_collection.update_one({"doc_id": doc_id}, {"$set": update_data})
        return {"message": "Temp doc updated"}

# temp_docs -> docs 최종저장
async def finalize_temp_doc(doc_id: str):
    temp_doc = await temp_collection.find_one({"doc_id": doc_id})
    if not temp_doc:
        return {"success": False, "message": "No temp doc found"}
    temp_doc.pop('_id', None)
    result = await collection.update_one(
        {"doc_id": doc_id},
        {"$set": {
            "title": temp_doc.get("title"),
            "contents": temp_doc.get("contents"),
            "updated_dt": datetime.now(),
            "file_type": temp_doc.get("file_type"),
        }}
    )
    await temp_collection.delete_one({"doc_id": doc_id})
    return {"success": True, "message": "Doc finalized", "updated": result.modified_count}