# app/services/chat_service.py

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

def normalize_text(text: str) -> str:
    text = re.sub(r'\s+', '', text)
    text = text.replace('\u200b', '').replace('\xa0', '').replace(' ', '')
    return text.strip()

def find_substring_index(full: str, sub: str) -> int:
    norm_full = normalize_text(full)
    norm_sub = normalize_text(sub)
    idx = norm_full.find(norm_sub)
    return idx if idx >= 0 else -1

def split_apply_value(apply_value: Optional[str]):
    if not apply_value:
        return None, None
    title, body = None, None
    m_title_after = re.search(r'\[문서 제목\][\s\n]*([^\n\[\]]+)', apply_value)
    if m_title_after:
        title = m_title_after.group(1).strip()
    if not title:
        m_title = re.search(
            r'(?:변경 제목 제안|추천 제목|제목 추천|제안하는 기사 제목)\s*[:：]\s*["“]([^"”]+)["”]', 
            apply_value
        )
        if m_title:
            title = m_title.group(1).strip()
    return title, body

def extract_apply_info(answer: str, question: ChatSendRequest, doc_contents: str):
    md_titles = re.findall(r'-\s*([^\n]+)', answer)
    if md_titles:
        return md_titles[0].strip(), "title"

    lines = [line.strip() for line in answer.split('\n') if line.strip()]
    titles = [line for line in lines if not line.startswith("추천 기사 제목은") and len(line) > 3]
    if titles:
        return titles[0], "title"

    m = re.findall(r'-\s*([^\n]+)', answer)
    if m:
        return m[0].strip(), "title", None, None

    selected_text = getattr(question, "selected_text", None)
    if selected_text and doc_contents:
        idx = doc_contents.find(selected_text)
        if idx >= 0:
            return selected_text, "body", idx, idx + len(selected_text)

    if titles:
        return titles[0], "title", None, None

    return None, None


# ===== 주요 기능 =====

# 채팅 QA 저장
async def save_chat_qa(
    question: ChatSendRequest,
    answer: str,
    suggestion: Optional[str] = None,
    doc_contents: Optional[str] = None,
) -> dict:
    chat_id = await get_next_chat_id(question.doc_id)
    apply_value, value_type = extract_apply_info(
        answer, question, doc_contents or ""
    )
    apply_title, apply_body = split_apply_value(apply_value)

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
