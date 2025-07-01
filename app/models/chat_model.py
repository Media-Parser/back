# app/models/chat_model.py
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# Front에서 보내는 request body 
class ChatSendRequest(BaseModel):
    doc_id: str
    message: str  # 사용자 질문
    selected_yn: bool = False # 참조해서 (드래그된) 답변할 내용이 있는지
    selected_text: Optional[str] = None # 참조할 내용
    start_index: Optional[int] = -1 # 참조할 내용의 위치 (시작)
    end_index: Optional[int] = -1 # 참조할 내용의 위치 (끝)

# AI 서버와 호환되는 요청 모델 (내부 사용)
class AIRequest(BaseModel):
    doc_id: str
    message: str
    content: Optional[str] = None
    contain: Optional[bool] = False

# AI 서버와 호환되는 응답 모델 (내부 사용)
class AIResponse(BaseModel):
    chatbot_response: str
    article_content: Optional[str] = None
    key_points: Optional[List[str]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat() + "Z")

# 질문-답변 pair
# 질문-답변 한 사이클 돌았을 때 생성 및 저장
class ChatQA(BaseModel):
    chat_id: str
    doc_id: str
    question: ChatSendRequest
    selection: Optional[str] = None
    answer: str
    suggestion: Optional[str] = None
    created_dt: datetime

# chatQA 생성시 list 에 추가
class ChatHistory(BaseModel):
    session_id: str
    doc_id: str
    chatQAs: list[ChatQA] = []