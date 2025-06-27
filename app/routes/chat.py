from fastapi import APIRouter, HTTPException
from app.services.chat_service import save_chat_qa, get_chat_history, delete_chat_history
from app.services.ai_service import generate_ai_response
from app.models.chat_model import ChatSendRequest, ChatQA
from typing import List

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