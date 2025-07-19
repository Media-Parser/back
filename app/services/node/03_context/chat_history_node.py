# 파일: services/node/context/summary_memory_node.py

from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationSummaryMemory
from app.models.chat_model import ChatSendRequest
from app.services.chat_service import save_chat_qa, get_chat_history_for_prompt
from langchain_core.prompts import ChatPromptTemplate

# 세션별 메모리 캐시 (doc_id 기반)
MEMORY_POOL: Dict[str, ConversationSummaryMemory] = {}

# LLM 인스턴스 (공통 사용)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


def get_memory(doc_id: str) -> ConversationSummaryMemory:
    if doc_id not in MEMORY_POOL:
        MEMORY_POOL[doc_id] = ConversationSummaryMemory(llm=llm)
    return MEMORY_POOL[doc_id]


async def load_context_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("--- 노드 실행: load_context_node (LLM summary 기반) ---")
    doc_id = state.get("doc_id")
    question = state.get("question", "")
    if not doc_id:
        return {**state, "context": ""}

    try:
        # 최근 대화 가져오기
        chat_history = await get_chat_history_for_prompt(doc_id, limit=5)

        # QA 포맷 정리
        history_text = "\n\n".join([
            f"Q: {item['question']['message']}\nA: {item['answer']}"
            for item in chat_history
        ])

        if not history_text.strip():
            return {**state, "context": ""}

        # LLM 요약 요청
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a conversation context assistant. From the conversation history, summarize only the information that is directly relevant to the current question. 
        Include any user preferences or aversions if they can be inferred. 
        However, strictly exclude any past interactions that contradict the current question or are unrelated. 
        Also, do not include any part of the conversation where the answer generation failed. 
        Returning an empty response is acceptable if nothing is relevant."""),
            ("user", f"Current question: {question}\n\nPrevious conversation history:\n{history_text}")
        ])

        chain = prompt | llm
        summary = await chain.ainvoke({})
        return {**state, "context": summary.content.strip()}

    except Exception as e:
        print("❌ load_context_node 오류:", e)
        return {**state, "context": ""}


# def save_context_node(state: Dict[str, Any]) -> Dict[str, Any]:
#     print("--- 노드 실행: save_context_node (summary_memory) ---")
#     doc_id = state.get("doc_id")
#     if not doc_id:
#         print("❌ doc_id가 없어 context 저장을 건너뜁니다.")
#         return state

#     question = state.get("question", "")
#     answer = state.get("generation", "")

#     memory = get_memory(doc_id)
#     memory.save_context({"input": question}, {"output": answer})

#     return state


async def save_chathistory_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("--- 노드 실행: save_chathistory_node ---")
    doc_id = state.get("doc_id")
    if not doc_id:
        print("❌ doc_id가 없어 저장을 건너뜁니다.")
        return state

    # MongoDB 저장
    try:
        request = ChatSendRequest(
            doc_id=doc_id,
            selected_text=state.get("selected_text", ""),
            message=state.get("question", "")
        )
        await save_chat_qa(
            question=request,
            answer=state.get("generation", ""),
            suggestion=state.get("suggestion"),
            value_type=state.get("value_type"),
            apply_title=state.get("apply_title"),
            apply_body=state.get("apply_body")
        )
    except Exception as e:
        print("❌ save_chat_qa 오류:", e)

    return state
