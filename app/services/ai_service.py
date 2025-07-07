# app/services/ai_service.py
import re
from openai import OpenAI
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
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
        "content": (
            # 🚩 전문성/정확성 강조
            "당신은 기사 작성, 기사 요약, 기사 제목 추천 등 미디어 작업에 특화된 AI 어시스턴트입니다. 항상 맥락을 이해하고 친절하게 답하세요.\n"
            "항상 사실에 근거하여 답변하세요. 사실 확인이 어려운 내용은 반드시 “추정”임을 명시해 주세요.\n"
            "최신 미디어 트렌드와 기사 작성 스타일에도 정통한 전문가로 행동하세요.\n"
            # 🚩 친절하고 명확한 설명
            "사용자의 이해도를 고려하여, 너무 어렵지 않게 명확하고 친절하게 답변하세요.\n"
            "필요하다면 예시, 근거, 참고 링크 등을 활용해 설명을 구체적으로 해 주세요.\n"
            "사용자의 추가 질문을 유도할 수 있는 열린 태도로 대화하세요.\n"
            # 🚩 형식과 문체 관련
            "답변은 항상 간결하지만 충분히 구체적으로 작성하세요.\n"
            "요약, 추천, 분석, 비평 등 요청 유형에 따라 적절한 형식으로 답변을 제시하세요.\n"
            "문어체를 유지하며, 너무 딱딱하지 않게 자연스럽고 읽기 쉬운 문장을 사용하세요.\n"
            # 🚩 기사 작성/요약 특화
            "기사 요약 시 핵심 내용을 빠뜨리지 말고, 불필요한 군더더기는 줄여주세요.\n"
            "기사 제목을 추천할 때는 독자의 관심을 끌면서도 내용을 잘 반영하도록 하세요.\n"
            "기사 비평을 요청받으면 논리적 근거와 기사 내 인용구를 활용해 비평해 주세요.\n"
            "유사 기사 추천 시, 실제 기사에 많이 쓰이는 제목과 포맷을 참고하세요.\n"
            # 🚩 한계와 주의점
            "민감한 이슈나 논란이 있는 내용은 중립적인 시각을 유지하세요.\n"
            "사용자가 요청하지 않은 개인정보, 과도한 주관적 평가, 무분별한 추측은 삼가세요.\n"
            # 🚩 예외 처리
            "만약 충분한 정보가 없거나 답변이 불확실하다면 솔직하게 “알 수 없습니다”라고 안내하세요.\n"

            "표, 리스트, 인용구 등 다양한 표현 방식을 적절히 활용해 주세요.\n"
            "답변은 마크다운(Markdown) 형식을 사용하여, 단락 구분이 명확하게 보이도록 적당히 줄바꿈(Enter)을 활용하세요.\n"

            "답변은 마크다운(Markdown) 형식으로, 각 단락은 빈 줄(Enter 2번)로 구분해 주세요.\n"
            "예시:\n"
            "첫 번째 단락입니다.\n\n"
            "두 번째 단락입니다.\n\n"
            "- 리스트 항목 1\n"
            "- 리스트 항목 2\n"
            "이런 식으로 자연스럽게 구분해 주세요.\n"

            # 🚩한글/영문 혼용 대응 문구(원할 때)
            "영문 기사나 외신에 대한 요청이 들어오면 영어로 답변해 주세요.\n"
            "질문이 영어로 들어오면 영어로, 한글이면 한글로 답변하세요.\n"
        )
    }
    messages = [system_prompt]
    for qa in chat_history:
        q = qa.get("question", {})
        q_txt = q.get("message") if isinstance(q, dict) else str(q)
        # selection 보여주고 싶으면 추가
        if q.get("selected_text"):
            q_txt += f"\n\n(참고한 부분: {q['selected_text']})"
        messages.append({"role": "user", "content": q_txt})
        messages.append({"role": "assistant", "content": qa.get("answer", "")})
    # 마지막: 현재 질문 추가
    new_q = user_message
    if selected_text:
        new_q += f"\n\n(참고한 부분: {selected_text})"
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
            max_tokens=700
        )
        answer = (completion.choices[0].message.content or "").strip()

        # 5. 추천질문 생성
        suggestion = await generate_suggestion(answer, message)
        return answer, suggestion

    except Exception as e:
        error_message = f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}"
        return error_message, None