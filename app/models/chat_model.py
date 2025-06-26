# app/models/chat_model.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class ChatQA(BaseModel):
    chat_id: str
    doc_id: str
    question: str
    answer: str
    suggestion: Optional[str] = None
    created_dt: datetime

class ChatSendRequest(BaseModel):
    doc_id: str
    message: str  # 사용자 질문
    article_content: Optional[str] = None