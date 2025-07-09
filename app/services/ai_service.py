# app/services/ai_service.py
import re
from openai import OpenAI
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic.types import T
from app.core.config import settings

ATLAS_URI = settings.ATLAS_URI
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# 문서 내용 가져오기
async def get_document_content(doc_id: str) -> Optional[dict]:
    temp_doc = await db["temp_docs"].find_one({"doc_id": doc_id})
    if temp_doc:
        return {
            "title": temp_doc.get("title", ""),
            "contents": temp_doc.get("contents", "")
        }
    doc = await db["docs"].find_one({"doc_id": doc_id})
    if doc:
        return {
            "title": doc.get("title", ""),
            "contents": doc.get("contents", "")
        }
    return None

# 대화 흐름을 위한 메시지 생성
def build_messages_with_history(
    chat_history: List[dict],  # [{question: {...}, answer: "..."}]
    user_message: str,
    selected_text: Optional[str] = None,
    doc_content: Optional[dict] = None
):
    system_prompt = {
            "role": "system",
            "content": """
        당신은 기사 작성, 기사 요약, 기사 제목 추천 등 미디어 작업에 특화된 AI 어시스턴트입니다. 사용자의 추가 질문을 유도하는 열린 태도로, 맥락을 잘 이해해서 친절하게 답하세요.

        - **모든 답변은 마크다운(Markdown) 형식**으로, 단락별로 빈 줄을 충분히 넣어 가독성 있게 작성하세요.
        - 예시, 리스트, 표, 인용구 등 다양한 표현 방식을 적극적으로 활용하세요.
        - 항상 사실에 근거한 답변을 제공하고, 불확실하거나 추정이 필요한 내용은 명확히 표시하세요.
        - 민감하거나 논란 소지가 있는 이슈는 반드시 중립적인 시각을 유지하세요.
        - 개인정보, 과도한 추측, 너무 주관적 평가는 삼가세요.
        - 질문이 영어면 영어, 한글이면 한글로 답변하세요.

        ---

        **기사 제목 추천, 변경, 요약, 제목과 관련된 답변은 반드시 다음 중 하나의 라벨을 한 줄에 사용하여 추천 제목만을 큰따옴표("...")로 감싸 한 줄에 써 주세요.**

        - **반드시 라벨을 아래 중 하나로 써주세요**  
            - `변경 제목 제안:`
            - `추천 제목:`
            - `제안하는 기사 제목:`
            - `기사 제목 추천:`
        - **반드시 아래처럼 한 줄에만!**
            - 예시: 변경 제목 제안: "미래 산업을 이끄는 인공지능의 힘"
            - 예시: 추천 제목: "AI 혁신, 산업을 바꾸다"
        - **여러 개 추천 시 반드시 1. ... 2. ...** 형식으로 한 줄씩 써주세요.

        ---

        **문장/문단/본문/내용 추천도 반드시 라벨로 표시해 주세요.**
        - 적용할 문장: "..."
        - 추천 문장: "..."
        - 변경 문장 제안: "..."

        ---

        **"수정", "추천", "변경", "다듬기" 요청이 포함된 질문에 답할 땐 반드시 아래 형식을 따르세요.**

        🔄 **수정 제안**

        **Before:**  
        (수정 전 문장)

        **After:**  
        (수정 후 문장 — 바뀐 부분을 **굵게** 혹은 ==밑줄==로 강조)

        > 변경 이유: (자연스럽게 설명. 반드시 After와 한 블록에 포함)

        ---

        **포맷을 어기면 사용자가 적용/복사를 할 수 없습니다. 반드시 포맷을 지키세요!**

        **단, 기타 설명/분석/비평/요약 등은 기존 마크다운 규칙을 지키세요.**

        """
    }
    messages = [system_prompt]
    for qa in chat_history:
        q = qa.get("question", {})
        q_txt = q.get("message") if isinstance(q, dict) else str(q)
        # selection 보여주고 싶으면 추가
        if q.get("selected_text"):
            q_txt += f"\n\n{q['selected_text']}"
        messages.append({"role": "user", "content": q_txt})
        messages.append({"role": "assistant", "content": qa.get("answer", "")})
    # 마지막: 현재 질문 추가
    new_q = user_message
    if selected_text:
        new_q += f"\n\n{selected_text}"
    if doc_content and isinstance(doc_content, dict):
        title = doc_content.get("title", "")
        contents = doc_content.get("contents", "")
        new_q += (
            f"\n\n[문서 제목]\n{title}\n\n"
            f"[문서 내용]\n{contents}\n"
        )
    elif doc_content:
        new_q += f"\n\n(전체 기사 내용: {doc_content})"
    messages.append({"role": "user", "content": new_q})
    return messages

# 후속 질문 생성
async def generate_suggestion(answer: str, user_message: str) -> str:
    """
    AI 답변과 사용자의 질문을 참고하여 후속으로 할 만한 질문을 만들어줌
    """
    prompt = (
        f"아래는 기사 관련 AI가 사용자의 질문에 답변한 내용입니다.\n\n"
        f"질문: {user_message}\n"
        f"답변: {answer}\n\n"
        "만약 사용자가 이어서 궁금해할 만한 다음 질문을 한 문장으로 만들어 주세요. "
        "실제 사용자의 입장에서, 답변을 보고 자연스럽게 이어질만한 추가 질문을 예시로 작성해 주세요. "
        "질문문 끝에는 반드시 '?'를 붙여주세요."
    )
    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "너는 기사 관련 AI 대화의 흐름을 자연스럽게 이어주는 어시스턴트야."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=500
    )
    print("=== AI SUGGESTION ===\n",completion.choices[0].message.content)
    suggestion = completion.choices[0].message.content.strip()
    suggestion = re.sub(r"^(후속 질문:|Q:|질문:)\s*", "", suggestion)
    return suggestion

# AI 응답 생성
async def generate_ai_response(
    message: str,
    doc_id: str,
    selected_text: Optional[str] = None,
    use_full_document: bool = False
) -> tuple[str, Optional[str]]:
    try:
        # 1. 최근 [limit]개 대화 내역 불러오기
        from app.services.chat_service import get_chat_history_for_prompt
        chat_history = await get_chat_history_for_prompt(doc_id, limit=3)

        # 2. 전체 문서 내용 필요 시
        doc_content = None
        if use_full_document or not selected_text:
            doc_content = await get_document_content(doc_id)

        # 3. messages 구성
        messages = build_messages_with_history(
            chat_history=chat_history,
            user_message=message,
            selected_text=selected_text,
            doc_content=doc_content
        )

        # 4. OpenAI 호출
        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        answer = (completion.choices[0].message.content or "").strip()

        # 5. 추천질문 생성
        suggestion = await generate_suggestion(answer, message)
        return answer, suggestion

    except Exception as e:
        error_message = f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}"
        return error_message, None