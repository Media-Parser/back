# app/services/document_service.py

import os
import re
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.document_model import Doc
from app.services.hwp_extractor import extract_text_from_hwp
from app.services.hwpx_extractor import extract_text_from_hwpx
from app.services.doc_topic import embed_openai
# ====== 설정 ======
ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']
collection = db['docs']
temp_collection = db['temp_docs']

DELETE_YES = "y"
DELETE_NO = "n"
tz_kst = timezone(timedelta(hours=9))


# ====== [공통 유틸 함수] ======

def to_kst(dt: Optional[datetime]) -> Optional[str]:
    if dt:
        return dt.astimezone(tz_kst).isoformat()
    return None

def serialize_doc(doc):
    return {
        "doc_id": str(doc.get("doc_id")),
        "user_id": doc["user_id"],
        "title": doc["title"],
        "contents": doc["contents"],
        "created_dt": to_kst(doc.get("created_dt")),
        "updated_dt": to_kst(doc.get("updated_dt")),
        "file_type": doc["file_type"],
        "category_id": doc.get("category_id", ""),
        "delete_yn": doc.get("delete_yn", DELETE_NO),
    }

def build_next_doc_id(current_id: Optional[str]) -> str:
    if current_id:
        match = re.search(r"doc_(\d{8})", current_id)
        next_number = int(match.group(1)) + 1 if match else 1
    else:
        next_number = 1
    return f"doc_{next_number:08d}"

async def get_next_doc_id():
    latest_doc = await collection.find_one(
        {"doc_id": {"$regex": "^doc_\\d{8}$"}},
        sort=[("doc_id", -1)]
    )
    current_id = latest_doc["doc_id"] if latest_doc else None
    return build_next_doc_id(current_id)


# ======================== 대시보드 ========================

async def get_documents(user_id: str, category_id: Optional[str] = None):
    query = {"user_id": user_id, "delete_yn": DELETE_NO}
    if category_id:
        query["category_id"] = category_id

    docs = await collection.find(query).to_list(length=None)
    return [serialize_doc(doc) for doc in docs]

async def update_document_title(doc_id: str, user_id: str, new_title: str) -> bool:
    result = await collection.update_one(
        {"doc_id": doc_id, "user_id": user_id},
        {"$set": {"title": new_title, "updated_dt": datetime.now(tz=tz_kst)}}
    )
    return result.modified_count > 0

async def download_file(doc_id: str, user_id: str):
    doc = await temp_collection.find_one({"doc_id": doc_id, "user_id": user_id}) or \
          await collection.find_one({"doc_id": doc_id, "user_id": user_id})
    if doc:
        doc.pop("_id", None)
    return doc

async def delete_file(doc_id: str, user_id: str):
    result = await collection.update_one(
        {"doc_id": doc_id, "user_id": user_id},
        {"$set": {"delete_yn": DELETE_YES}}
    )
    await temp_collection.delete_one({"doc_id": doc_id, "user_id": user_id})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Document not found or you don't have permission.")
    return True

async def upload_file(file: Doc):
    file_dict = file.model_dump()
    contents = ""
    try:
        if file.file_type == "hwp":
            contents = extract_text_from_hwp(file.file_blob)
        elif file.file_type == "hwpx":
            contents = extract_text_from_hwpx(file.file_blob)
    except Exception as e:
        print(f"[upload_file] 파일 파싱 실패: {e}")
    file_dict["contents"] = contents
    result = await collection.insert_one(file_dict)
    if result.inserted_id:
        return {"message": "Doc registered successfully", "doc_id": file_dict["doc_id"]}
    return {"message": "Failed to register doc"}


# ======================== 챗봇/에디터 ========================

async def has_temp_doc(doc_id: str, user_id: str) -> bool:
    return await temp_collection.find_one({"doc_id": doc_id, "user_id": user_id}) is not None

async def get_temp_doc(doc_id: str, user_id: str):
    doc = await temp_collection.find_one({"doc_id": doc_id, "user_id": user_id})
    if doc:
        doc.pop("_id", None)
    return doc

async def get_doc(doc_id: str, user_id: str):
    doc = await collection.find_one({"doc_id": doc_id, "user_id": user_id})
    if doc:
        doc.pop("_id", None)
    return doc

async def delete_temp_doc(doc_id: str, user_id: str):
    await temp_collection.delete_one({"doc_id": doc_id, "user_id": user_id})

async def update_temp_doc(doc_id: str, user_id: str, update_data: dict):
    now = datetime.now(tz=tz_kst)
    update_data["updated_dt"] = now
    doc = await temp_collection.find_one({"doc_id": doc_id, "user_id": user_id})
    if not doc:
        origin = await collection.find_one({"doc_id": doc_id, "user_id": user_id})
        if not origin:
            return None
        base_doc = {
            "doc_id": origin.get("doc_id"),
            "user_id": origin.get("user_id"),
            "title": origin.get("title"),
            "contents": origin.get("contents"),
            "file_type": origin.get("file_type"),
            "created_dt": origin.get("created_dt"),
            "updated_dt": now,
        }
        base_doc.update(update_data)
        await temp_collection.insert_one(base_doc)
        return {"message": "Temp doc created"}
    await temp_collection.update_one({"doc_id": doc_id, "user_id": user_id}, {"$set": update_data})
    return {"message": "Temp doc updated"}

async def finalize_temp_doc(doc_id: str, user_id: str):
    # 1. 임시 저장된 문서를 가져옵니다.
    temp_doc = await temp_collection.find_one({"doc_id": doc_id, "user_id": user_id})
    if not temp_doc:
        # 임시 저장된 내용이 없으면 저장할 것도 없으므로 종료합니다.
        return {"success": True, "message": "No temporary document to finalize."}

    # 2. 원본 문서를 가져옵니다.
    origin_doc = await collection.find_one({"doc_id": doc_id, "user_id": user_id})
    if not origin_doc:
        # 원본이 없는 비정상적인 경우
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this document.")

    # 3. 원본과 임시 저장된 문서의 제목과 내용을 비교합니다.
    title_changed = temp_doc.get("title") != origin_doc.get("title")
    contents_changed = temp_doc.get("contents") != origin_doc.get("contents")

    # 4. 변경된 내용이 있을 경우에만 원본 문서를 업데이트합니다.
    if title_changed or contents_changed:
        print(f"[LOG] Document {doc_id} has changes. Finalizing...")
        now = datetime.now(tz=tz_kst)
        result = await collection.update_one(
            {"doc_id": doc_id, "user_id": user_id},
            {"$set": {
                "title": temp_doc.get("title"),
                "contents": temp_doc.get("contents"),
                "updated_dt": now,
            }}
        )
        message = "Document finalized successfully."
        updated_count = result.modified_count
    else:
        # 변경된 내용이 없으면 업데이트를 수행하지 않습니다.
        print(f"[LOG] Document {doc_id} has no changes. Skipping update.")
        message = "No changes to save."
        updated_count = 0

    # 5. 작업이 끝나면 임시 문서를 삭제합니다.
    await temp_collection.delete_one({"doc_id": doc_id, "user_id": user_id})
    
    return {"success": True, "message": message, "updated": updated_count}