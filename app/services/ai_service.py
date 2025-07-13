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


# ===== LangGraph Nodes =====
async def retrieve_document_node(state: GraphState) -> dict:
    print("--- 노드 실행: retrieve_document_node ---")
    doc_id = state.get("doc_id")
    if not doc_id:
        return {"context": ""}

    doc = await db["temp_docs"].find_one({"doc_id": doc_id}) or await db["docs"].find_one({"doc_id": doc_id})
    if not doc:
        return {"context": "오류: 해당 ID의 문서를 찾을 수 없습니다."}

    context = f"[문서 제목]\n{doc.get('title', '')}\n\n[문서 내용]\n{doc.get('contents', '')}"
    return {"context": context}


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


async def should_retrieve_conditionally(state: GraphState) -> str:
    strategy = state.get("plan", {}).get("strategy", "no_retrieval")
    return {
        "standard_retrieval": "standard_retriever",
        "balanced_retrieval": "balanced_retriever",
        "title_generation": "generate_titles",
        "no_retrieval": "generate"
    }.get(strategy, "__end__")


# ===== LangGraph 실행 =====
async def generate_ai_response(
    message: str,
    doc_id: str,
    selected_text: Optional[str] = None,
    use_full_document: bool = False
) -> Tuple[str, Optional[str]]:
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
        return final_state.get("generation", ""), final_state.get("suggestion", "")
    except Exception as e:
        return f"AI 응답 생성 중 오류: {str(e)}", None


# ===== LangGraph 구성 =====
graph_builder = StateGraph(GraphState)

# 노드 등록
graph_builder.add_node("retrieve_document", retrieve_document_node)
graph_builder.add_node("guardrails", guardrails_node)
graph_builder.add_node("plan_retrieval", plan_retrieval_node)
graph_builder.add_node("standard_retriever", standard_retrieval_node)
graph_builder.add_node("balanced_retriever", balanced_retrieval_node)
graph_builder.add_node("grade_and_filter", grade_and_filter_node)
graph_builder.add_node("generate", generate_response_node)
graph_builder.add_node("generate_titles", generate_titles_node)
graph_builder.add_node("generate_suggestion_node", generate_suggestion_node)

# 엣지 연결
graph_builder.set_entry_point("retrieve_document")
graph_builder.add_edge("retrieve_document", "guardrails")
graph_builder.add_conditional_edges("guardrails", check_guardrails, {
    "plan_retrieval": "plan_retrieval",
    "__end__": END
})
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


# ===== CLI 테스트 실행 =====
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
            print("\n[AI 답변]" if generation else "\n[AI 답변 없음]")
            print(generation or "죄송하지만, 제공된 정보만으로는 답변하기 어렵습니다.")
            print(final_state)

    asyncio.run(main())
