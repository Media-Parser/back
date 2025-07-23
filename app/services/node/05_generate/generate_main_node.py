from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from graph_state import GraphState

load_dotenv()

# === LLM이 반환할 JSON 형식 정의 ===
class GenMainOutput(BaseModel):
    generation: str = Field(..., description="응답 또는 수정 이유 설명")
    suggestion: Optional[str] = Field(None, description="후속 제안 또는 질문")
    apply_body: Optional[str] = Field(None, description="선택된 문서를 대체할 수정안 (선택된 경우에만)")

# === 공통 SYSTEM 프롬프트 ===
SYSTEM_PROMPT = """
당신은 언론 어시스턴트입니다.

[작업 조건]
- 사용자의 질문과 제공된 문서를 바탕으로 응답(generation)과 후속 제안(suggestion)을 생성하세요.
사용자가 선택한 텍스트는 문서의 일부분(어절 또는 구)일 수 있으며, `apply_body`에는 해당 텍스트를 정확히 대체할 수 있는 말을 적당한 길이로 작성해야 합니다.

`apply_body` 작성시 다음 기준을 반드시 지키세요:
- 선택된 텍스트를 **해당 위치에 그대로 치환할 수 있도록** 작성해야 합니다.
- 문장 전체로 확장하지 마세요. 오직 **문장 내에서 대체 가능한 조각**만 생성하세요.
- 의미는 유지하면서도 문법적으로 더 자연스럽고 명확하게 다듬어야 합니다.
- 주변 문맥과의 연결성을 고려하여 올바른 조사를 선택하세요.

[출력 형식]
반드시 다음 필드를 포함한 JSON 객체로 응답하세요:
- generation: 응답
- suggestion: 후속 제안
- apply_body: 선택된 문서 부분에 대한 수정
"""

# === USER 프롬프트 ===
USER_TEMPLATE_WITH_APPLY = """
질문:
{question}

이전까지의 대화 내용 요약:
{context}

선택된 문서 부분:
{selected_text}

출력 예시:
{{
  "generation": "문체가 지나치게 구어체여서 편집했습니다.",
  "suggestion": "'이 문단의 정책적 배경을 더 설명해 드릴까요?'",
  "apply_body": "대한민국은 민주공화국입니다."
}}
"""

USER_TEMPLATE_SIMPLE = """
질문:
{question}

이전까지의 대화 내용 요약:
{context}

선택된 문서 부분:
{selected_text}
"""

def generate_main_node(state: GraphState) -> GraphState:
    print("--- 노드 실행: generate_main_node ---")

    question = state.get("question", "")
    selected_text = state.get("selected_text", "")
    context = state.get("context", "")
    apply_body_required = state.get("plan", {}).get("apply_body_required", False)

    # 문서 연결
    document_context = ""
    if "documents" in state:
        documents = state["documents"]
        if isinstance(documents, list) and documents:
            document_context = "\n\n".join(
                [f"[문서 {i+1}]\n{doc.page_content}" for i, doc in enumerate(documents)]
            )

    # 프롬프트 설정
    if apply_body_required:
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", USER_TEMPLATE_WITH_APPLY + (
                f"\n아래 문서는 외부 문서입니다. 이중 질문과 관련된 내용만 요약하거나 인용해서 사용하세요:\n\n{document_context}" if document_context else ""
            ))
        ])

        llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(
            [GenMainOutput], tool_choice="GenMainOutput"
        )
        chain = prompt | llm | PydanticToolsParser(tools=[GenMainOutput])

        result: GenMainOutput = chain.invoke({
            "question": question,
            "context": context,
            "selected_text": selected_text or ""
        })[0]

        return {
            **state,
            "generation": result.generation,
            "suggestion": result.suggestion,
            "apply_body": result.apply_body or "",
        }

    else:
        # apply_body가 필요 없는 경우
        prompt = ChatPromptTemplate.from_messages([
            ("system", "당신은 언론 어시스턴트입니다.\n문서를 바탕으로 질문에 응답하고 후속 제안을 생성하세요."),
            ("user", USER_TEMPLATE_SIMPLE + (
                f"\n아래 문서는 외부 문서입니다. 이중 질문과 관련된 내용만 요약하거나 인용해서 사용하세요:\n\n{document_context}" if document_context else ""
            ))
        ])

        llm = ChatOpenAI(model="gpt-4o-mini")
        chain = prompt | llm
        result = chain.invoke({
            "question": question,
            "context": context,
            "selected_text": selected_text
        })

        return {
            **state,
            "generation": result.content.strip(),
            "suggestion": None,
            "apply_body": "",
        }