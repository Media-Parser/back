# # app/services/ai_service.py
# import os
# from openai import OpenAI
# from typing import Optional
# from datetime import datetime
# from motor.motor_asyncio import AsyncIOMotorClient
# from app.core.config import settings

# ATLAS_URI = settings.ATLAS_URI
# client = AsyncIOMotorClient(ATLAS_URI)
# db = client['uploadedbyusers']

# # OpenAI client 초기화
# openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# async def get_document_content(doc_id: str) -> Optional[str]:
#     """문서 내용을 가져오는 함수"""
#     # temp_docs에서 먼저 찾기
#     temp_doc = await db["temp_docs"].find_one({"doc_id": doc_id})
#     if temp_doc:
#         return temp_doc.get("contents", "")
    
#     # temp_docs에 없으면 docs에서 찾기
#     doc = await db["docs"].find_one({"doc_id": doc_id})
#     if doc:
#         return doc.get("contents", "")
    
#     return None

# async def generate_ai_response(
#     message: str,
#     doc_id: str,
#     selected_text: Optional[str] = None,
#     use_full_document: bool = False
# ) -> tuple[str, Optional[str]]:
#     """
#     AI 응답을 생성하는 함수
    
#     Args:
#         message: 사용자 질문
#         doc_id: 문서 ID
#         selected_text: 선택된 텍스트 (있는 경우)
#         use_full_document: 전체 문서 내용 사용 여부
    
#     Returns:
#         tuple: (AI 응답, 추천 질문)
#     """
#     try:
#         # 프롬프트 구성
#         prompt = f"{message}\n\n"
        
#         # 선택된 텍스트가 있는 경우
#         if selected_text:
#             prompt += f"다음은 참조할 텍스트입니다:\n{selected_text}\n\n"
        
#         # 전체 문서 내용을 사용하는 경우
#         if use_full_document:
#             doc_content = await get_document_content(doc_id)
#             if doc_content:
#                 prompt += f"다음은 전체 문서 내용입니다:\n{doc_content}\n\n"
#             prompt += "전체 문서 내용을 참고하여 답변해 주세요.\n"
        
#         # OpenAI API 호출
#         completion = openai_client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.7,
#             max_tokens=600
#         )
        
#         answer = completion.choices[0].message.content
        
#         # 간단한 추천 질문 생성 (실제로는 더 정교하게 구현 가능)
#         suggestion = None
#         if "?" not in message:  # 질문이 아닌 경우에만 추천 질문 제공
#             suggestion = "이 내용에 대해 더 자세히 알고 싶으신가요?"
        
#         return answer, suggestion
        
#     except Exception as e:
#         error_message = f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}"
#         return error_message, None
import os
from openai import OpenAI
from typing import Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

ATLAS_URI = settings.ATLAS_URI
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def get_document_content(doc_id: str) -> Optional[str]:
    temp_doc = await db["temp_docs"].find_one({"doc_id": doc_id})
    if temp_doc:
        return temp_doc.get("contents", "")
    doc = await db["docs"].find_one({"doc_id": doc_id})
    if doc:
        return doc.get("contents", "")
    return None

def build_prompt(
    user_message: str,
    selected_text: Optional[str],
    doc_content: Optional[str]
) -> str:
    system_prompt = (
        "당신은 기사 작성, 기사 요약, 기사 제목 추천 등 미디어 작업에 특화된 AI 어시스턴트입니다.\n"
        "항상 사용자의 요청에 친절하고 구체적으로 답변하세요.\n"
        "가능하다면 명확한 근거와 이유를 제시하고, 너무 짧게만 답하지 마세요.\n"
    )
    prompt = f"{system_prompt}\n"
    prompt += f"사용자 질문: {user_message}\n"
    if selected_text:
        prompt += f"\n참고해야 할 문서 일부:\n'''{selected_text}'''\n"
    if doc_content:
        prompt += f"\n전체 기사 본문:\n'''{doc_content}'''\n"
    prompt += "\n문서와 질문 내용을 반영해서 알맞은 답변을 제공하세요."
    return prompt

async def generate_ai_response(
    message: str,
    doc_id: str,
    selected_text: Optional[str] = None,
    use_full_document: bool = False
) -> tuple[str, Optional[str]]:
    try:
        doc_content = None
        if use_full_document or not selected_text:
            doc_content = await get_document_content(doc_id)

        prompt = build_prompt(message, selected_text, doc_content)

        # (선택) 프롬프트 디버깅용 출력
        # print("=== AI PROMPT ===\n", prompt)

        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 친절한 기사 AI 비서입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=700
        )

        answer = completion.choices[0].message.content

        # "추천 질문"은 상황에 맞춰서 다양하게
        suggestion = None
        if not any(q in message for q in "??!"):
            suggestion = "이 기사에 대한 요약이나, 논조 비평도 요청해 보실래요?"

        return answer, suggestion

    except Exception as e:
        error_message = f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}"
        return error_message, None