# app/services/chat_service.py

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from motor.motor_asyncio import AsyncIOMotorClient
from app.models.chat_model import ChatSendRequest
from app.core.config import Settings

# MongoDB 설정
ATLAS_URI = Settings.ATLAS_URI
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']
collection = db['chat_qas']

# 시간대 설정
tz_kst = timezone(timedelta(hours=9))


# ===== 공통 유틸 =====

async def get_curr_chat_id(doc_id: str):
    latest = await collection.find_one(
        {"doc_id": doc_id, "chat_id": {"$regex": "^chat_\\d{8}$"}},
        sort=[("chat_id", -1)]
    )
    if latest and "chat_id" in latest:
        return latest["chat_id"]
    return -1  # 👈 없으면 -1


async def get_next_chat_id(doc_id: str):
    # 해당 doc_id에서 chat_id 중 가장 큰 값을 찾음
    latest = await collection.find_one(
        {"doc_id": doc_id, "chat_id": {"$regex": "^chat_\\d{8}$"}},
        sort=[("chat_id", -1)]
    )
    if latest and "chat_id" in latest:
        match = re.search(r"chat_(\d{8})", latest["chat_id"])
        next_number = int(match.group(1)) + 1 if match else 1
    else:
        next_number = 1
    return f"chat_{next_number:08d}"


def convert_chat_qa(doc: dict) -> dict:
    result = {}
    for key, value in doc.items():
        if key == "_id":
            continue
        if isinstance(value, datetime):
            result[key] = value.astimezone(tz_kst).isoformat()
        else:
            result[key] = value
    return result

# 채팅 QA 저장
async def save_chat_qa(
    question: ChatSendRequest,
    answer: str,
    suggestion: Optional[str] = None,
    value_type: Optional[str] =None,
    apply_title: Optional[str] =None,
    apply_body: Optional[str] =None, 
) -> dict:
    chat_id = await get_next_chat_id(question.doc_id)

    print(value_type)
    print(collection)

    qa = {
        "chat_id": chat_id,
        "doc_id": question.doc_id,
        "question": question.model_dump(),
        "selection": question.selected_text if question.selected_text else None,
        "answer": answer,
        "suggestion": suggestion,
        "apply_title": apply_title,
        "apply_body": apply_body,
        "type": value_type,
        "created_dt": datetime.now(tz=tz_kst),
    }
    await collection.insert_one(qa)
    return convert_chat_qa(qa)

# 히스토리 조회
async def get_chat_history(doc_id: str) -> List[dict]:
    try:
        cursor = collection.find({"doc_id": doc_id}).sort("created_dt", 1)
        docs_raw = await cursor.to_list(length=100)
        return [convert_chat_qa(doc) for doc in docs_raw]
    except Exception as e:
        print("❌ get_chat_history error:", e)
        return []

# 히스토리 삭제
async def delete_chat_history(doc_id: str) -> int:
    try:
        result = await collection.delete_many({"doc_id": doc_id})
        return result.deleted_count
    except Exception as e:
        print("❌ delete_chat_history error:", e)
        return 0

# 최신 QA → 프롬프트용 제한된 기록
async def get_chat_history_for_prompt(doc_id: str, limit: int = 10):
    cursor = collection.find({"doc_id": doc_id}).sort("created_dt", -1)
    docs_raw = await cursor.to_list(length=limit)
    return list(reversed(docs_raw))