# app/models/chat_model.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

# Front에서 보내는 request body 
class ChatSendRequest(BaseModel):
    doc_id: str
    message: str  # 사용자 질문
    selected_yn: bool # 참조해서 (드래그된) 답변할 내용이 있는지
    selected_text: Optional[str] # 참조할 내용
    start_index: Optional[int] = -1 # 참조할 내용의 위치 (시작)
    end_index: Optional[int] = -1 # 참조할 내용의 위치 (끝)

# 질문-답변 pair 
# 질문-답변 한 사이클 돌았을 때 생성 및 저장
class ChatQA(BaseModel):
    chat_id: str
    doc_id: str
    question: ChatSendRequest
    answer: str
    suggestion: Optional[str] = None
    created_dt: datetime

# chatQA 생성시 list 에 추가
class ChatHistory(BaseModel):
    session_id: str
    doc_id: str
    chatQAs: list[ChatQA] = []