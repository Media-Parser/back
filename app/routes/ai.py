# app/routes/ai.py
from fastapi import APIRouter, HTTPException
from app.services.ai_service import generate_ai_response, get_document_content
from app.models.chat_model import AIRequest, AIResponse
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["AI"])

@router.post("/send", response_model=AIResponse)
async def ai_chat_endpoint(req: AIRequest):
    """
    Original AI server compatible endpoint
    Maintains backward compatibility with the previous AI server interface
    """
    try:
        # Determine if we should use full document content
        use_full_document = req.contain if req.contain is not None else False
        selected_text = req.content if req.content else None
        
        # Generate AI response
        ai_answer, _ = await generate_ai_response(
            message=req.message,
            doc_id=req.doc_id,
            selected_text=selected_text,
            use_full_document=use_full_document
        )
        
        # Return in the format expected by the original AI server
        return AIResponse(
            chatbot_response="",
            article_content=ai_answer,
            key_points=[],
            timestamp=datetime.now().isoformat() + "Z"
        )
        
    except Exception as e:
        return AIResponse(
            chatbot_response=f"오류가 발생했습니다: {str(e)}",
            article_content="",
            key_points=[],
            timestamp=datetime.now().isoformat() + "Z"
        )
