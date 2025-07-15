# app/services/ai_service.py

import re
from typing import Optional, List, Tuple
from datetime import timedelta, timezone

from openai import OpenAI
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import Settings
from langgraph.graph import StateGraph, END
from app.services.node import (
    GraphState,
    plan_retrieval_node,
    standard_retrieval_node,
    balanced_retrieval_node,
    grade_and_filter_node,
    generate_response_node,
    generate_titles_node,
    generate_suggestion_node,
)

# ===== 설정 =====
ATLAS_URI = Settings.ATLAS_URI
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']
openai_client = OpenAI(api_key=Settings.OPENAI_API_KEY)
tz_kst = timezone(timedelta(hours=9))


# ===== 문서 조회 =====
async def get_document_content(doc_id: str) -> Optional[dict]:
    for coll in ["temp_docs", "docs"]:
        doc = await db[coll].find_one({"doc_id": doc_id})
        if doc:
            return {
                "title": doc.get("title", ""),
                "contents": doc.get("contents", "")
            }
    return None


async def retrieve_document_node(state: GraphState) -> dict:
    print("--- 노드 실행: retrieve_document_node ---")
    doc_id = state.get("doc_id")
    if not doc_id:
        return {**state, "context": ""}

    doc = await db["temp_docs"].find_one({"doc_id": doc_id}) or await db["docs"].find_one({"doc_id": doc_id})
    if not doc:
        return {**state, "context": "오류: 해당 ID의 문서를 찾을 수 없습니다."}

    context = f"[문서 제목]\n{doc.get('title', '')}\n\n[문서 내용]\n{doc.get('contents', '')}"
    print(context)
    return {**state, "context": context}



async def should_retrieve_conditionally(state: GraphState) -> str:
    strategy = state.get("plan", {}).get("strategy", "no_retrieval")
    return {
        "standard_retrieval": "standard_retriever",
        "balanced_retrieval": "balanced_retriever",
        "title_generation": "generate_titles",
        "no_retrieval": "generate"
    }.get(strategy, "__end__")


# ===== LangGraph 실행 =====
# 히스토리 반영 안됨, content 제대로 안들어감
async def generate_ai_response(message: str, doc_id: str, selected_text: Optional[str] = None, use_full_document: bool = False) -> Tuple[str, Optional[str]]:
    try:
        from chat_service import get_chat_history_for_prompt
        chat_history = await get_chat_history_for_prompt(doc_id, limit=3)
        doc_content = await get_document_content(doc_id) if use_full_document or not selected_text else None

        inputs = {"question": message, "original_question": message, "documents": [], "doc_id": doc_id}
        config = {"configurable": {"run_id": f"run_{doc_id}"}}
        final_state = await graph_app.ainvoke(inputs, config=config)
        print(final_state)
        answer = final_state.get("generation", "답변 생성 실패")
        suggestion = generate_suggestion_node({"question": message}).get("suggestion")
        return answer, suggestion
    except Exception as e:
        return f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}", None


# ===== LangGraph 구성 =====
graph_builder = StateGraph(GraphState)

# 노드 등록
graph_builder.add_node("retrieve_document", retrieve_document_node)
graph_builder.add_node("plan_retrieval", plan_retrieval_node)
graph_builder.add_node("standard_retriever", standard_retrieval_node)
graph_builder.add_node("balanced_retriever", balanced_retrieval_node)
graph_builder.add_node("grade_and_filter", grade_and_filter_node)
graph_builder.add_node("generate", generate_response_node)
graph_builder.add_node("generate_titles", generate_titles_node)
graph_builder.add_node("generate_suggestion_node", generate_suggestion_node)

# 엣지 연결
graph_builder.set_entry_point("retrieve_document")
graph_builder.add_edge("retrieve_document", "plan_retrieval")
graph_builder.add_conditional_edges("plan_retrieval", should_retrieve_conditionally, {
    "standard_retriever": "standard_retriever",
    "balanced_retriever": "balanced_retriever",
    "generate_titles": "generate_titles",
    "generate": "generate",
    "__end__": END
})
graph_builder.add_edge("standard_retriever", "grade_and_filter")
graph_builder.add_edge("balanced_retriever", "grade_and_filter")
graph_builder.add_edge("grade_and_filter", "generate")
graph_builder.add_edge("generate", END)
graph_builder.add_edge("generate_titles", END)

# 그래프 컴파일
graph_app = graph_builder.compile()