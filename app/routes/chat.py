# 📁 app/routes/chat.py
from fastapi import APIRouter, HTTPException
from app.services.chat_service import save_chat_qa, get_chat_history, delete_chat_history
from app.services.ai_service import generate_ai_response
from app.models.chat_model import ChatSendRequest, ChatQA
from typing import List
import httpx
import os

AI_SERVER_URL = os.getenv("AI_SERVER_URL")

router = APIRouter(prefix="/chat", tags=["Chatbot"])

# 질문 저장 (AI inference 후 값 입력)
@router.post("/send", response_model=ChatQA)
async def chat_send(req: ChatSendRequest):
    # AI 서비스를 통해 응답 생성
    ai_answer, ai_suggestion = await generate_ai_response(
        message=req.message,
        doc_id=req.doc_id,
        selected_text=req.selected_text if req.selected_yn else None,
        use_full_document=not req.selected_yn  # 선택된 텍스트가 없으면 전체 문서 사용
    )
    
    # 채팅 QA 저장
    chat_qa = await save_chat_qa(req, ai_answer, ai_suggestion)
    return chat_qa

# 문서별 QA 히스토리
@router.get("/history/{doc_id}", response_model=List[ChatQA])
async def chat_history(doc_id: str):
    qas = await get_chat_history(doc_id)
    return qas

# 전체 삭제
@router.delete("/history/{doc_id}")
async def delete_history(doc_id: str):
    deleted = await delete_chat_history(doc_id)
    return {"deleted_count": deleted}

async def your_ai_inference(message, article_content):
    async with httpx.AsyncClient() as client:
        payload = {
            "message": message,
            "article_content": article_content
        }
        # AI inference 서버로 POST 요청
        resp = await client.post(f"{AI_SERVER_URL}/chat/send", json=payload)
        resp.raise_for_status()
        data = resp.json()
        # AI 응답 형태에 맞춰 값 추출 (키 이름은 실제 응답 참고)
        answer = data.get("chatbot_response") or data.get("article_content")
        suggestion = data.get("suggestion")
        return answer, suggestion
