# app/services/ai_service.py
import re
from openai import OpenAI
from typing import Optional, List, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import Settings 
from langgraph.graph import StateGraph, END
from app.services.node import (
    GraphState,
    detect_injection,
    analyze_sentiment_bias,
    plan_retrieval_node,
    standard_retrieval_node,
    balanced_retrieval_node,
    grade_and_filter_node,
    generate_response_node,
    generate_titles_node,
    generate_suggestion_node,
)

ATLAS_URI = Settings.ATLAS_URI
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']
openai_client = OpenAI(api_key=Settings.OPENAI_API_KEY)

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

# 종속성 문제 없으면 03_context 쪽으로 이동 예정
async def retrieve_document_node(state: GraphState) -> dict:
    print("--- 노드 실행: retrieve_document_node ---")
    doc_id = state.get("doc_id")
    if not doc_id:
        return {"context": ""}
    doc_to_process = await db["temp_docs"].find_one({"doc_id": doc_id}) \
        or await db["docs"].find_one({"doc_id": doc_id})
    if doc_to_process:
        formatted_context = f"[문서 제목]\n{doc_to_process.get('title', '')}\n\n[문서 내용]\n{doc_to_process.get('contents', '')}"
        return {"context": formatted_context}
    return {"context": "오류: 해당 ID의 문서를 찾을 수 없습니다."}

async def should_retrieve_conditionally(state: GraphState) -> str:
    strategy = state.get("plan", {}).get("strategy", "no_retrieval")
    return {
        "standard_retrieval": "standard_retriever",
        "balanced_retrieval": "balanced_retriever",
        "title_generation": "generate_titles",
        "no_retrieval": "generate"
    }.get(strategy, "__end__")
    
def guardrails_node(state: GraphState) -> GraphState:
    print("--- 노드 실행: guardrails ---")
    question = state["question"]
    if "위험" in detect_injection(question):
        return {**state, "generation": "오류: 부적절한 질문입니다 (프롬프트 인젝션)."}
    bias_result = analyze_sentiment_bias(question)
    if any(k in bias_result for k in ["공격", "비난", "혐오"]):
        return {**state, "generation": f"오류: 부적절한 질문입니다 (감지된 편향: {bias_result})."}
    return state

def check_guardrails(state: GraphState) -> str:
    return "__end__" if state.get("generation", "").startswith("오류") else "plan_retrieval"


# 대화 흐름을 위한 메시지 생성
# def build_messages_with_history(
#     chat_history: List[dict],  # [{question: {...}, answer: "..."}]
#     user_message: str,
#     selected_text: Optional[str] = None,
#     doc_content: Optional[dict] = None
# ):
#     system_prompt = {
#             "role": "system",
#             "content": """
#         당신은 기사 작성, 기사 요약, 기사 제목 추천 등 미디어 작업에 특화된 AI 어시스턴트입니다. 사용자의 추가 질문을 유도하는 열린 태도로, 맥락을 잘 이해해서 친절하게 답하세요.

#         - **모든 답변은 마크다운(Markdown) 형식**으로, 단락별로 빈 줄을 충분히 넣어 가독성 있게 작성하세요.
#         - 예시, 리스트, 표, 인용구 등 다양한 표현 방식을 적극적으로 활용하세요.
#         - 항상 사실에 근거한 답변을 제공하고, 불확실하거나 추정이 필요한 내용은 명확히 표시하세요.
#         - 민감하거나 논란 소지가 있는 이슈는 반드시 중립적인 시각을 유지하세요.
#         - 개인정보, 과도한 추측, 너무 주관적 평가는 삼가세요.
#         - 질문이 영어면 영어, 한글이면 한글로 답변하세요.

#         ---

#         **기사 제목 추천, 변경, 요약, 제목과 관련된 답변은 반드시 다음 중 하나의 라벨을 한 줄에 사용하여 추천 제목만을 큰따옴표("...")로 감싸 한 줄에 써 주세요.**

#         - **반드시 라벨을 아래 중 하나로 써주세요**  
#             - `변경 제목 제안:`
#             - `추천 제목:`
#             - `제안하는 기사 제목:`
#             - `기사 제목 추천:`
#         - **반드시 아래처럼 한 줄에만!**
#             - 예시: 변경 제목 제안: "미래 산업을 이끄는 인공지능의 힘"
#             - 예시: 추천 제목: "AI 혁신, 산업을 바꾸다"
#         - **여러 개 추천 시 반드시 1. ... 2. ...** 형식으로 한 줄씩 써주세요.

#         ---

#         **문장/문단/본문/내용 추천도 반드시 라벨로 표시해 주세요.**
#         - 적용할 문장: "..."
#         - 추천 문장: "..."
#         - 변경 문장 제안: "..."

#         ---

#         **"수정", "추천", "변경", "다듬기" 요청이 포함된 질문에 답할 땐 반드시 아래 형식을 따르세요.**

#         🔄 **수정 제안**

#         **Before:**  
#         (수정 전 문장)

#         **After:**  
#         (수정 후 문장 — 바뀐 부분을 **굵게** 혹은 ==밑줄==로 강조)

#         > 변경 이유: (자연스럽게 설명. 반드시 After와 한 블록에 포함)

#         ---

#         **포맷을 어기면 사용자가 적용/복사를 할 수 없습니다. 반드시 포맷을 지키세요!**

#         **단, 기타 설명/분석/비평/요약 등은 기존 마크다운 규칙을 지키세요.**

#         """
#     }
#     messages = [system_prompt]
#     for qa in chat_history:
#         q = qa.get("question", {})
#         q_txt = q.get("message") if isinstance(q, dict) else str(q)
#         # selection 보여주고 싶으면 추가
#         if q.get("selected_text"):
#             q_txt += f"\n\n{q['selected_text']}"
#         messages.append({"role": "user", "content": q_txt})
#         messages.append({"role": "assistant", "content": qa.get("answer", "")})
#     # 마지막: 현재 질문 추가
#     new_q = user_message
#     if selected_text:
#         new_q += f"\n\n{selected_text}"
#     if doc_content and isinstance(doc_content, dict):
#         title = doc_content.get("title", "")
#         contents = doc_content.get("contents", "")
#         new_q += (
#             f"\n\n[문서 제목]\n{title}\n\n"
#             f"[문서 내용]\n{contents}\n"
#         )
#     elif doc_content:
#         new_q += f"\n\n(전체 기사 내용: {doc_content})"
#     messages.append({"role": "user", "content": new_q})
#     return messages

# # 후속 질문 생성
# async def generate_suggestion(answer: str, user_message: str) -> str:
#     """
#     AI 답변과 사용자의 질문을 참고하여 후속으로 할 만한 질문을 만들어줌
#     """
#     prompt = (
#         f"아래는 기사 관련 AI가 사용자의 질문에 답변한 내용입니다.\n\n"
#         f"질문: {user_message}\n"
#         f"답변: {answer}\n\n"
#         "만약 사용자가 이어서 궁금해할 만한 다음 질문을 한 문장으로 만들어 주세요. "
#         "실제 사용자의 입장에서, 답변을 보고 자연스럽게 이어질만한 추가 질문을 예시로 작성해 주세요. "
#         "질문문 끝에는 반드시 '?'를 붙여주세요."
#     )
#     completion = openai_client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": "너는 기사 관련 AI 대화의 흐름을 자연스럽게 이어주는 어시스턴트야."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.5,
#         max_tokens=500
#     )
#     print("=== AI SUGGESTION ===\n",completion.choices[0].message.content)
#     suggestion = completion.choices[0].message.content.strip()
#     suggestion = re.sub(r"^(후속 질문:|Q:|질문:)\s*", "", suggestion)
#     return suggestion

# AI 응답 생성
async def generate_ai_response(
    message: str,
    doc_id: str,
    selected_text: Optional[str] = None,
    use_full_document: bool = False
) -> Tuple[str, Optional[str]]:
    """
    LangGraph 파이프라인을 실제로 실행하여 답변과 추천질문을 생성하는 함수
    """
    try:
        graph_inputs = {
            "question": message,
            "original_question": message,
            "doc_id": doc_id,
            "selected_text": selected_text,
            "documents": [],
            "generation": "",
            "context": "",
            "retries": 0,
            "plan": None,
            "suggestion": None,
            "value_type": None,
            "apply_value": None,
        }
        final_state = await graph_app.ainvoke(graph_inputs)
        answer = final_state.get("generation", "")
        suggestion = final_state.get("suggestion", "")
        return answer, suggestion
    except Exception as e:
        return f"AI 응답 생성 중 오류: {str(e)}", None
    
    # try:
    #     # 1. 최근 [limit]개 대화 내역 불러오기
    #     from app.services.chat_service import get_chat_history_for_prompt
    #     chat_history = await get_chat_history_for_prompt(doc_id, limit=3)

    #     # 2. 전체 문서 내용 필요 시
    #     doc_content = None
    #     if use_full_document or not selected_text:
    #         doc_content = await get_document_content(doc_id)

    #     # 3. messages 구성
    #     messages = build_messages_with_history(
    #         chat_history=chat_history,
    #         user_message=message,
    #         selected_text=selected_text,
    #         doc_content=doc_content
    #     )

    #     # 4. OpenAI 호출
    #     completion = openai_client.chat.completions.create(
    #         model="gpt-3.5-turbo",
    #         messages=messages,
    #         temperature=0.7,
    #         max_tokens=2000
    #     )
    #     answer = (completion.choices[0].message.content or "").strip()

    #     # 5. 추천질문 생성
    #     suggestion = await generate_suggestion(answer, message)
    #     return answer, suggestion

    # except Exception as e:
    #     error_message = f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}"
    #     return error_message, None
    
    
    # --- LangGraph 정의 ---
graph_builder = StateGraph(GraphState)
graph_builder.add_node("retrieve_document", retrieve_document_node)
graph_builder.add_node("guardrails", guardrails_node)
graph_builder.add_node("plan_retrieval", plan_retrieval_node)
graph_builder.add_node("standard_retriever", standard_retrieval_node)
graph_builder.add_node("balanced_retriever", balanced_retrieval_node)
graph_builder.add_node("grade_and_filter", grade_and_filter_node)
graph_builder.add_node("generate", generate_response_node)
graph_builder.add_node("generate_titles", generate_titles_node)
graph_builder.add_node("generate_suggestion_node", generate_suggestion_node)

# --- 엣지 연결 ---
graph_builder.set_entry_point("retrieve_document")
graph_builder.add_edge("retrieve_document", "guardrails")
graph_builder.add_conditional_edges("guardrails", check_guardrails, {"plan_retrieval": "plan_retrieval", "__end__": END})
graph_builder.add_conditional_edges("plan_retrieval", should_retrieve_conditionally, {
    "standard_retriever": "standard_retriever",
    "balanced_retriever": "balanced_retriever",
    "generate_titles": "generate_titles",
    "generate": "generate",
    "__end__": END
})
graph_builder.add_edge("standard_retriever", "grade_and_filter")
graph_builder.add_edge("balanced_retriever", "grade_and_filter")

# rewrite 로직 일단 필요 없음
graph_builder.add_edge("grade_and_filter", "generate") 
# graph_builder.add_conditional_edges("grade_and_filter", decide_to_generate_or_rewrite, {
#     "generate": "generate",
#     "rewrite_query": "rewrite_query"
# })
# graph_builder.add_edge("rewrite_query", "generate")

graph_builder.add_edge("generate", END)
graph_builder.add_edge("generate_titles", END)

# 컴파일
graph_app = graph_builder.compile()


if __name__ == "__main__":
    import asyncio

    async def main():
        print("\n--- LangGraph RAG 애플리케이션 시작 ---")
        print("질문을 입력하세요. 종료하려면 'exit' 또는 'quit'을 입력하세요.")

        while True:
            question = input("\n질문: ")
            if question.lower() in ["exit", "quit"]:
                print("애플리케이션을 종료합니다.")
                break
            
            inputs = {"question": question, "documents": [], "value_type": "content"}
            final_state = await graph_app.ainvoke(inputs)
            
            generation = final_state.get("generation")
            if not generation:
                print("\n[AI 답변]\n죄송하지만, 제공된 정보만으로는 답변하기 어렵습니다.")
            else:
                print("\n[AI 답변]")
                print(generation)
            print(final_state)
    
    asyncio.run(main())