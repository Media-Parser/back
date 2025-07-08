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

def normalize_text(text):
    text = re.sub(r'\s+', '', text)      # 모든 공백 제거
    text = text.replace('\u200b', '')    # zero width space 제거
    text = text.replace('\xa0', '')      # nbsp 제거
    text = text.replace(' ', '')         # 일반 공백
    text = text.strip()
    return text


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

def extract_apply_info(answer: str, question: ChatSendRequest, doc_contents: str):
    # 1. After 블록 전체 추출 (여러 줄도 포함)
    after_match = re.search(
        r'\*\*After:\*\*\s*([\s\S]+?)(?:\n\s*>\s*변경 이유:|\n\s*\*\*|\Z)', answer)
    if after_match:
        after = after_match.group(1)
        # 블록 전체 앞뒤 쓸데없는 따옴표, 괄호 등 한 번만 정리
        after = after.strip()
        after = re.sub(r'^[\(\["“]+', '', after)
        after = re.sub(r'[\)"”]+$', '', after)
        # 비어있지 않으면 반환
        if after.strip():
            # before 도 똑같이 잡아서 위치 매칭
            before_match = re.search(
                r'\*\*Before:\*\*\s*([\s\S]+?)(?:\n\s*\*\*After:|\n\s*\*\*|\Z)', answer)
            if before_match:
                before = before_match.group(1).strip()
                before = re.sub(r'^[\(\["“]+', '', before)
                before = re.sub(r'[\)"”]+$', '', before)
                # 위치 매칭
                idx = doc_contents.find(before)
                if idx < 0:
                    norm_full = normalize_text(doc_contents)
                    norm_before = normalize_text(before)
                    idx = norm_full.find(norm_before)
                    # 정확 매핑 어렵다면 idx만 반환(대부분 문단이면 충분)
                if idx >= 0:
                    return after, "body", idx, idx + len(before)
            # Before 매칭 실패하면 그냥 After 전체 반환(위치 지정 X)
            return after, "body", None, None

    # 2. 라벨(적용할 문장, 추천 문장 등) 패턴도 여전히 지원
    m = re.search(r'(적용할 문장|추천 문장|수정 문장|변경 제목 제안)\s*[:：]\s*["“]([\s\S]{2,}?)["”]', answer)
    if m:
        label = m.group(1)
        txt = m.group(2).strip()
        # 사용자의 질문이 '제목'이 아닌 '부분/내용' 수정이면 apply_body로!
        if "제목" not in (question.message or ""):
            return txt, "body", None, None
        vtype = "title" if label == "변경 제목 제안" else "body"
        return txt, vtype, None, None

    # 3. 리스트 첫 번째 추천 등
    m = re.search(r'\d+\.\s*["“]([^"”]{2,})["”]', answer)
    if m:
        return m.group(1).strip(), "body", None, None

    # 4. 선택된 부분 있으면, 그 위치 반환
    selected_text = getattr(question, "selected_text", None)
    if selected_text and doc_contents:
        idx = doc_contents.find(selected_text)
        if idx >= 0:
            return selected_text, "body", idx, idx + len(selected_text)

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