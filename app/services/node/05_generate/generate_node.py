# service/node/05_generate/generate_node.py

import os
from typing import List, Optional, Union, Dict, Any, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

# --- 1. 설정: API 키 로드 ---
load_dotenv()

# --- 2. LangGraph 상태 정의 ---
class GraphState(TypedDict):
    question: str                  # 이전 질문
    answer: str                    # 이전 답변
    suggestion: Optional[str]      # 대안 제안 등


# --- 3. 시스템 프롬프트 템플릿 정의 ---
SYSTEM_PROMPT = """
당신은 기사 작성, 요약, 비평에 특화된 미디어 어시스턴트입니다.

- 항상 문맥을 고려하여 친절하고 정확하게 답하세요.
- 근거가 명확하지 않으면 “추정”임을 분명히 밝혀 주세요.
- 요약 시 핵심을 빠뜨리지 말고 불필요한 표현은 줄이세요.
- 문어체를 유지하되 너무 딱딱하지 않도록 자연스럽게 표현하세요.
- 표, 리스트, 인용 등을 적절히 활용하세요.
- 답변은 마크다운 형식으로 단락을 구분해 주세요.
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{user_input}")
])


# --- 4. LLM 메시지 생성 함수 ---
def create_prompt_messages(
    chat_history: List[Dict[str, Any]],
    user_message: str,
    selected_text: Optional[str] = None,
    doc_content: Optional[Union[str, Dict[str, str]]] = None
) -> List[Union[HumanMessage, AIMessage]]:
    """
    LangChain 메시지 포맷으로 변환 + 사용자 질문 구성
    """
    history_messages = []
    for qa in chat_history:
        q = qa.get("question", {})
        q_text = q.get("message", "") if isinstance(q, dict) else str(q)
        if q.get("selected_text"):
            q_text += f"\n\n(참고한 부분: {q['selected_text']})"

        history_messages.append(HumanMessage(content=q_text))
        history_messages.append(AIMessage(content=qa.get("answer", "")))

    # 현재 질문 구성
    current_input = user_message
    if selected_text:
        current_input += f"\n\n(참고한 부분: {selected_text})"

    if isinstance(doc_content, dict):
        title = doc_content.get("title", "")
        contents = doc_content.get("contents", "")
        current_input += f"\n\n[문서 제목]\n{title}\n\n[문서 내용]\n{contents}"
    elif isinstance(doc_content, str):
        current_input += f"\n\n(전체 기사 내용: {doc_content})"

    return prompt_template.format_messages(
        chat_history=history_messages,
        user_input=current_input
    )


# --- 5. 노드 정의 ---
def generate_response_node(state: GraphState) -> dict:
    """
    LangGraph용 LLM 응답 생성 노드
    """
    print("--- 노드 실행: generate_response_node ---")

    chat_history = state.get("chat_history", [])       # 전체 QA 기록
    user_message = state.get("original_question", "")  # 현재 질문
    selected_text = state.get("selected_text")         # 강조 문장 등
    doc_content = state.get("doc_content")             # 문서 전문

    # 메시지 생성
    messages = create_prompt_messages(
        chat_history=chat_history,
        user_message=user_message,
        selected_text=selected_text,
        doc_content=doc_content,
    )

    print("[2] LangChain 체인을 통해 LLM 호출 시작...")

    llm = ChatOpenAI(model="gpt-4o-mini")
    response = llm.invoke(messages).content

    return {"generation": response}


# --- 6. 테스트 실행 (직접 실행 시) ---
if __name__ == "__main__":
    print("--- 미디어 어시스턴트 노드 테스트 시작 ---")