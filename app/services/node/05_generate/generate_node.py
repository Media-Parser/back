# service/node/05_generate/generate_node.py
import os
from pprint import pprint
from typing import List, Optional, Union, Dict, Any, TypedDict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda

# --- 1. 설정: API 키 로드 ---
# .env 파일에서 환경 변수를 로드합니다.
# 이 스크립트와 같은 위치에 .env 파일을 만들고 아래와 같이 키를 추가하세요.
# OPENAI_API_KEY="your_api_key_here"
load_dotenv()
# --- 그래프 상태 정의 ---
class GraphState(TypedDict):
    question: str # 이제 이 노드에서는 사용되지 않지만, 상태 유지를 위해 남겨둠
    answer: str   # 이 노드의 핵심 입력값
    suggestion: Optional[str]

# --- 2. 시스템 프롬프트 및 템플릿 정의 ---

# 시스템 프롬프트 (제목 관련 내용 제외)
SYSTEM_PROMPT_WITHOUT_TITLES = """
당신은 기사 작성, 기사 요약 등 미디어 작업에 특화된 AI 어시스턴트입니다. 항상 맥락을 이해하고 친절하게 답하세요.
항상 사실에 근거하여 답변하세요. 사실 확인이 어려운 내용은 반드시 “추정”임을 명시해 주세요.
요약, 추천, 분석, 비평 등 요청 유형에 따라 적절한 형식으로 답변을 제시하세요.
문어체를 유지하며, 너무 딱딱하지 않게 자연스럽고 읽기 쉬운 문장을 사용하세요.

기사 요약 시 핵심 내용을 빠뜨리지 말고, 불필요한 군더더기는 줄여주세요.
기사 비평을 요청받으면 논리적 근거와 기사 내 인용구를 활용해 비평해 주세요.

표, 리스트, 인용구 등 다양한 표현 방식을 적절히 활용해 주세요.
답변은 마크다운(Markdown) 형식을 사용하여, 단락 구분이 명확하게 보이도록 적당히 줄바꿈(Enter)을 활용하세요.
"""

# LangChain 프롬프트 템플릿 생성
prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_WITHOUT_TITLES),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{user_input}")
])


# --- 3. 메시지 생성 및 실행을 위한 함수 ---

def create_prompt_messages(
    chat_history: List[Dict[str, Any]],  # [{question: {...}, answer: "..."}]
    user_message: str,
    selected_text: Optional[str] = None,
    doc_content: Optional[Union[str, Dict[str, str]]] = None
) -> List[Union[HumanMessage, AIMessage]]:
    """
    LangChain 프롬프트 템플릿을 사용하여 LLM에 전달할 메시지 리스트를 생성합니다.
    """
    # 1. 이전 대화 기록을 LangChain 메시지 형식으로 변환
    history_messages = []
    for qa in chat_history:
        q = qa.get("question", {})
        q_text = q.get("message", "") if isinstance(q, dict) else str(q)
        if q.get("selected_text"):
            q_text += f"\n\n(참고한 부분: {q['selected_text']})"
        
        history_messages.append(HumanMessage(content=q_text))
        history_messages.append(AIMessage(content=qa.get("answer", "")))

    # 2. 현재 사용자 입력을 구성
    current_input = user_message
    if selected_text:
        current_input += f"\n\n(참고한 부분: {selected_text})"
    
    if isinstance(doc_content, dict):
        contents = doc_content.get("contents", "")
        current_input += f"\n\n[문서 내용]\n{contents}\n"
    elif isinstance(doc_content, str):
        current_input += f"\n\n(전체 기사 내용: {doc_content})"

    # 3. 템플릿을 사용하여 최종 메시지 포맷팅
    return prompt_template.format_messages(
        chat_history=history_messages,
        user_input=current_input
    )



def build_messages_with_history(chat_history: List[dict], user_message: str, selected_text: Optional[str] = None, doc_content: Optional[dict] = None):
    system_prompt = create_prompt_messages(chat_history, user_message, selected_text, doc_content)
    messages = [system_prompt]
    for qa in chat_history:
        q = qa.get("question", {})
        q_txt = q.get("message") if isinstance(q, dict) else str(q)
        if q.get("selected_text"):
            q_txt += f"\n\n(참고한 부분: {q['selected_text']})"
        messages.append({"role": "user", "content": q_txt})
        messages.append({"role": "assistant", "content": qa.get("answer", "")})
    new_q = user_message + (f"\n\n(참고한 부분: {selected_text})" if selected_text else "")
    if doc_content and isinstance(doc_content, dict):
        new_q += f"\n\n[문서 제목]\n{doc_content.get('title', '')}\n\n[문서 내용]\n{doc_content.get('contents', '')}"
    messages.append({"role": "user", "content": new_q})
    return messages


def generate_response_node(state: GraphState) -> dict:
        # LLM 모델 초기화
    try:
        llm = ChatOpenAI(model="gpt-3.5-turbo")
    except Exception as e:
        raise e
        
    print("--- 노드 실행: generate_response_node ---")
    chat_history = state.get("chat_history", [])
    user_message = state.get("original_question", "")
    selected_text = state.get("selected_text")
    doc_content = state.get("doc_content")

    messages = build_messages_with_history(
        chat_history=chat_history,
        user_message=user_message,
        selected_text=selected_text,
        doc_content=doc_content
    )

    final_messages = create_prompt_messages(
        chat_history=chat_history,
        user_message=user_message,
        doc_content=doc_content,
        selected_text=selected_text 
    )
    
    print("--------------------")

    print("\n[2] LangChain 체인을 통해 LLM을 호출합니다...")
    # LLM 호출
    response = llm.invoke(final_messages).content
    return {"generation": response}




# --- 4. 스크립트 메인 실행 부분 ---

if __name__ == "__main__":
    # 이 스크립트를 직접 실행할 때 아래 코드가 동작합니다.
    
    print("--- 미디어 어시스턴트 노드 테스트 시작 ---")