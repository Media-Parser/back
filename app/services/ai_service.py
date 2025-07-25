# app/services/ai_service.py
from typing import Optional, Tuple
from datetime import timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from openai import OpenAI
from langgraph.graph import StateGraph, END
from app.core.config import Settings
import asyncio
from app.services.chat_service import get_curr_chat_id
from app.services.node import (
    GraphState,
    plan_retrieval_node,
    standard_retrieval_node,
    balanced_retrieval_node,
    grade_and_filter_node,
    generate_titles_node,
    generate_main_node,
    load_context_node,
    #save_context_node
 #   load_chathistory_node
)

# ===== 설정 =====
ATLAS_URI = Settings.ATLAS_URI
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']
openai_client = OpenAI(api_key=Settings.OPENAI_API_KEY)
tz_kst = timezone(timedelta(hours=9))

# ===== 문서 조회 노드 =====
async def retrieve_document_node(state: GraphState) -> dict:
    print("--- 노드 실행: retrieve_document_node ---")
    doc_id = state.get("doc_id")
    if not doc_id:
        return {**state, "selected_text": ""}

    async def fetch(coll):
        return await db[coll].find_one({"doc_id": doc_id})
    
    temp_doc, main_doc = await asyncio.gather(fetch("temp_docs"), fetch("docs"))
    doc = temp_doc or main_doc

    if not doc:
        return {**state}

    topic_id = doc.get("topic_id")
    if not isinstance(topic_id, int):
        topic_id = -1

    if "plan" in state and "filters" in state["plan"]:
        state["plan"]["filters"]["topic_id"] = topic_id
    return {**state, "selected_text": doc.get("contents", "")}

async def no_generate_node(state: GraphState) -> dict:
    print("--- 노드 실행: no_generate_node ---")
    generation_reason = "요청에 부적절한 표현이 포함되어 있어 응답 생성을 중단했습니다."
    return {**state, "generation": generation_reason}  # ✨ 여기에 이유를 명시


# ===== 조건 함수 =====
async def should_load_document(state: GraphState) -> str:
    return "retrieve_document" if state.get("use_full_document") else "plan_retrieval"


async def should_continue_after_retrieval(state: GraphState) -> str:
    if state.get("plan", {}).get("generation_required"):
        return "generate"
    return "__end__"


async def should_retrieve_conditionally(state: GraphState) -> str:
    strategy = state.get("plan", {}).get("strategy", "no_retrieval")
    return {
        "standard_retrieval": "standard_retriever",
        "balanced_retrieval": "balanced_retriever",
        "title_generation": "generate_titles",
        "no_retrieval": "generate",
        "generate": "generate",
        "no_generate": "no_generate"
    }.get(strategy, "__end__")

# ===== LangGraph 구성 =====
def build_graph() -> StateGraph:
    graph_builder = StateGraph(GraphState)

    # 노드 등록
    graph_builder.add_node("load_context", load_context_node)
    graph_builder.add_node("retrieve_document", retrieve_document_node)
    graph_builder.add_node("plan_retrieval", plan_retrieval_node)
    graph_builder.add_node("standard_retriever", standard_retrieval_node)
    graph_builder.add_node("balanced_retriever", balanced_retrieval_node)
    graph_builder.add_node("grade_and_filter", grade_and_filter_node)
    graph_builder.add_node("generate", generate_main_node)
    graph_builder.add_node("generate_titles", generate_titles_node)
    graph_builder.add_node("no_generate", no_generate_node)

    # 그래프 흐름 정의
    graph_builder.set_entry_point("load_context")
    graph_builder.add_conditional_edges("load_context", should_load_document, {
        "retrieve_document": "retrieve_document",
        "plan_retrieval": "plan_retrieval"
    })
    graph_builder.add_edge("retrieve_document", "plan_retrieval")
    graph_builder.add_conditional_edges("plan_retrieval", should_retrieve_conditionally, {
        "standard_retriever": "standard_retriever",
        "balanced_retriever": "balanced_retriever",
        "generate_titles": "generate_titles",
        "no_retrieval": "generate",
        "generate":"generate",
        "no_generate": "no_generate",
        "__end__": END
    })

    graph_builder.add_edge("standard_retriever", "grade_and_filter")
    graph_builder.add_edge("balanced_retriever", "grade_and_filter")
    graph_builder.add_conditional_edges("grade_and_filter", should_continue_after_retrieval, {
    "generate": "generate",
    "__end__": END
    })
    graph_builder.add_edge("generate", END)
    graph_builder.add_edge("generate_titles", END)

    return graph_builder.compile()

# 그래프 객체 전역 1회 생성
graph_app = build_graph()


# ===== LangGraph 실행 =====
async def generate_ai_response(
    message: str,
    doc_id: str,
    selected_text: Optional[str] = None,
    use_full_document: bool = False
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]:

    try:
        chat_id = await get_curr_chat_id(doc_id)
        print(f"chat_id:{chat_id}")
        if not chat_id:
            chat_id = "chat_00000001"
        inputs = {
            "question": message,
            "doc_id": doc_id,
            "chat_id": chat_id,
            "selected_text": selected_text,
            "use_full_document": use_full_document,
        }

        config = {"configurable": {"run_id": f"run_{doc_id}_{chat_id}"}}
        final_state = await graph_app.ainvoke(inputs, config=config)

        return (
            final_state.get("generation", "답변 생성 실패"),
            final_state.get("suggestion"),
            final_state.get("apply_title"),
            final_state.get("apply_body")
        )

    except Exception as e:
        print(f"AI 응답 생성 중 오류: {str(e)}")
        return f"AI 응답 생성 중 오류가 발생했습니다", None, None, None
