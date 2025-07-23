# app/services/node/03_context/chat_history_node.py
"""
03_context/context_nodes.py

이 모듈은 LangGraph 기반 RAG 챗봇에서 대화 기록을 불러오고 저장하는 노드를 정의합니다. 이를 통해 챗봇은 다음과 같은 기능을 수행할 수 있습니다:

    • 여러 턴의 세션에서 이전 대화를 기억 (단기 기억)
    • MongoDB에 메시지를 저장하여 서버 재시작 후에도 대화 유지
    • 오래된 메시지를 요약하고 최근 N개의 메시지를 그대로 남겨 프롬프트 길이를 줄임 (윈도우 기반 요약 버퍼)


LangGraph 통합
-----------------
이 모듈을 임포트한 후 다음과 같이 두 개의 노드를 그래프에 추가하세요:

    from context_nodes import load_context_node, save_context_node

    graph_builder.add_node("load_context", load_context_node)
    graph_builder.add_node("save_context", save_context_node)

그래프에서 다음과 같은 구조로 연결합니다:

    START  ➜  load_context  ➜  ... (기존 노드들) ... ➜  save_context ➜ END

`load_context_node`는 이전 대화 요약 + 최근 대화를 합친 `"context"` 문자열을 `GraphState`에 주입합니다.
이 `"context"`는 프롬프트에서 `{context}` 형태로 사용할 수 있습니다.

응답이 생성된 이후, `save_context_node`는 최신 질문/응답 쌍을 MongoDB에 저장하고 요약 상태를 업데이트합니다.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

from dotenv import load_dotenv
from langchain_mongodb import MongoDBChatMessageHistory
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI
from chat_service import get_chat_history, save_chat_qa
from app.models.chat_model import ChatSendRequest, ChatQA, ChatHistory
from typing import Dict, Optional, Any, Literal

from dotenv import load_dotenv
from langchain_mongodb import MongoDBChatMessageHistory
from langchain.memory import ConversationSummaryBufferMemory, ConversationBufferMemory
from langchain_openai import ChatOpenAI

# .env에서 Mongo URI 로드
load_dotenv()

# ---------------------------------------------------------------------------
# 환경 변수 로딩
# ---------------------------------------------------------------------------

def _mongo_uri() -> str:
    return os.getenv("ATLAS_URI_BACK")


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(temperature=0)


# ---------------------------------------------------------------------------
# ContextManager: 메모리 + 체크포인트 관리 전용
# ---------------------------------------------------------------------------

class ContextManager:
    """
    LangChain memory (buffer or summary) 및 checkpointing 기능 제공

    저장(save_chat_qa)은 별도로 백엔드에서 처리하며,
    이 클래스는 대화 context 유지에만 집중.
    """

    def __init__(
        self,
        session_id: str,
        memory_type: Literal["summary", "buffer"] = "summary",
        llm: Optional[ChatOpenAI] = None,
        max_token_limit: int = 1200,
    ) -> None:
        self.session_id = session_id
        self.memory_type = memory_type

        # Mongo 기반 메시지 저장소 (메모리 용도)
        self.chat_history = MongoDBChatMessageHistory(
            connection_string=_mongo_uri(),
            session_id=session_id,
            database_name="chat_history",
            collection_name="message_store",
        )

        # 메모리 타입 선택
        if memory_type == "summary":
            self.memory = ConversationSummaryBufferMemory(
                llm=llm or _get_llm(),
                max_token_limit=max_token_limit,
                return_messages=True,
                chat_memory=self.chat_history,
            )
        elif memory_type == "buffer":
            self.memory = ConversationBufferMemory(
                return_messages=True,
                chat_memory=self.chat_history,
            )
        else:
            raise ValueError(f"Unsupported memory_type: {memory_type}")

    def get_context_str(self) -> str:
        """요약 또는 버퍼된 대화 내용을 문자열로 반환"""
        return self.memory.load_memory_variables({})["history"]

    def append_turn(self, human: str, ai: str) -> None:
        """메모리에만 저장 (DB 저장은 backend에서 별도로 처리)"""
        self.memory.save_context({"input": human}, {"output": ai})

    def get_context_state(self) -> Dict[str, Any]:
        """현재 memory 상태를 checkpoint 형태로 반환"""
        return self.memory.dict()  # memory 내부 상태를 그대로 반환

    def load_context_from_state(self, state: Dict[str, Any]):
        """외부에서 복원된 memory state를 메모리에 반영"""
        self.memory.load_memory_variables(state)