# app/services/chat_service.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Optional, List
from app.models.chat_model import ChatSendRequest
import re

ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']
collection = db['chat_qas']

async def get_next_chat_id():
    # chat_qas 컬렉션에서 chat_id 필드 기준으로 가장 큰 값을 찾기
    latest_chat = await collection.find_one(
        {"chat_id": {"$regex": "^chat_\\d{8}$"}},
        sort=[("chat_id", -1)]
    )

    if latest_chat and "chat_id" in latest_chat:
        match = re.search(r"chat_(\d{8})", latest_chat["chat_id"])
        if match:
            next_number = int(match.group(1)) + 1
        else:
            next_number = 1
    else:
        next_number = 1

    return f"chat_{next_number:08d}"

def convert_chat_qa(doc: dict) -> dict:
    result = {}
    for key, value in doc.items():
        if key == "_id":
            continue
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

# 채팅 QA 저장
async def save_chat_qa(question: ChatSendRequest, answer: str, suggestion: Optional[str] = None) -> dict:
    chat_id = await get_next_chat_id()  # 순차적 chat_id
    qa = {
        "chat_id": chat_id,
        "doc_id": question.doc_id,
        "question": question.dict(),
        "selection": question.selected_text if question.selected_text else None,
        "answer": answer,
        "suggestion": suggestion,
        "created_dt": datetime.now(),
    }
    await collection.insert_one(qa)
    return convert_chat_qa(qa)

# 문서별 QA 히스토리 불러오기 (최신순, 최대 100개)
async def get_chat_history(doc_id: str) -> List[dict]:
    try:
        cursor = collection.find({"doc_id": doc_id}).sort("created_dt", 1)
        docs_raw = await cursor.to_list(length=100)
        return [convert_chat_qa(doc) for doc in docs_raw]
    except Exception as e:
        print("get_chat_history error:", e)
        return []

# 문서별 QA 전체 삭제
async def delete_chat_history(doc_id: str) -> int:
    try:
        result = await collection.delete_many({"doc_id": doc_id})
        return result.deleted_count
    except Exception as e:
        print("delete_chat_history error:", e)
        return 0