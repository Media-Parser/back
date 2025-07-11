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

# 채팅 QA 저장
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

# 텍스트 정규화
def normalize_text(text):
    text = re.sub(r'\s+', '', text)      # 모든 공백 제거
    text = text.replace('\u200b', '')    # zero width space 제거
    text = text.replace('\xa0', '')      # nbsp 제거
    text = text.replace(' ', '')         # 일반 공백
    text = text.strip()
    return text

# 전체 문서에서 부분문장 찾기
def find_substring_index(full, sub):
    norm_full = normalize_text(full)
    norm_sub = normalize_text(sub)
    idx = norm_full.find(norm_sub)
    if idx < 0:
        return -1
    # full에서 norm_sub와 가장 비슷한 실제 위치 찾기
    # 대충 매칭: norm_full에서 idx만큼의 길이의 substring이 full에서 어디에 위치하는지 찾아주는 매핑 로직 필요
    # 아니면 difflib로 가장 비슷한 위치를 반환해도 됨
    # 여기선 대충 first match만 (문장이 길지 않으니 대부분 ok)
    return idx

# 답변에서 추천 기사 제목 추출
def extract_apply_info(answer: str, question: ChatSendRequest, doc_contents: str):
    # 1. 마크다운 리스트(- 제목) 우선
    md_titles = re.findall(r'-\s*([^\n]+)', answer)
    if md_titles:
        # 첫 번째만 대표값으로 apply_value로 반환
        first_title = md_titles[0].strip()
        return first_title, "title", None, None

    # 2. 마크다운 없이 줄바꿈만 있을 때
    lines = [line.strip() for line in answer.split('\n') if line.strip()]
    # 안내 문구, 3글자 이하 등 제외
    titles = [line for line in lines if not line.startswith("추천 기사 제목은") and len(line) > 3]
    if titles:
        first_title = titles[0]
        return first_title, "title", None, None

    # 3. 리스트 첫 번째 추천 등
    m = re.findall(r'-\s*([^\n]+)', answer)
    if m:
        # 맨 앞 제목만 apply_value로, 나머지는 그대로 둠
        first_title = m[0].strip()
        return first_title, "title", None, None

    # 4. 선택된 부분 있으면, 그 위치 반환
    selected_text = getattr(question, "selected_text", None)
    if selected_text and doc_contents:
        idx = doc_contents.find(selected_text)
        if idx >= 0:
            return selected_text, "body", idx, idx + len(selected_text)
        
    # 5. 줄바꿈만으로 나눠진 경우(마크다운 리스트 없이)
    lines = [line.strip() for line in answer.split('\n') if line.strip()]
    # 안내 문구 등 제외
    titles = [line for line in lines if not line.startswith("추천 기사 제목은") and len(line) > 3]
    if titles:
        first_title = titles[0]
        return first_title, "title", None, None

    return None, None, None, None


# 채팅 QA 저장
async def save_chat_qa(
    question: ChatSendRequest,
    answer: str,
    suggestion: Optional[str] = None,
    doc_contents: Optional[str] = None,
) -> dict:
    chat_id = await get_next_chat_id()
    apply_value, value_type, apply_start_index, apply_end_index = extract_apply_info(
        answer, question, doc_contents or ""
    )

    # === 여기서 분리 ===
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
        "start_index": apply_start_index,
        "end_index": apply_end_index,
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

# 문서별 QA 히스토리 불러오기 (최신순, 최대 10개)
async def get_chat_history_for_prompt(doc_id: str, limit: int = 10):
    cursor = collection.find({"doc_id": doc_id}).sort("created_dt", -1)
    docs_raw = await cursor.to_list(length=limit)
    return list(reversed(docs_raw))  # 최신순 → 대화 흐름순으로

# apply_value 분리
def split_apply_value(apply_value: Optional[str]):
    title, body = None, None
    if not apply_value:
        return None, None
    # [문서 제목] ... 만 딱 잡기
    m_title_after = re.search(r'\[문서 제목\][\s\n]*([^\n\[\]]+)', apply_value)
    if m_title_after:
        title = m_title_after.group(1).strip()
    # 기존 로직도 fallback으로 유지 + "제안하는 기사 제목"도 추가
    if not title:
        m_title = re.search(
            r'(?:변경 제목 제안|추천 제목|제목 추천|제안하는 기사 제목)\s*[:：]\s*["“]([^"”]+)["”]', 
            apply_value
        )
        if m_title:
            title = m_title.group(1).strip()
    return title, body