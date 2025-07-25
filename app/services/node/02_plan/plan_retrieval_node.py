# 파일: 1_plan_retrieval_node.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from typing import List, Optional, Literal
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from graph_state import GraphState

# 환경 변수 로드
load_dotenv()

# --- 정당명 타입 정의 ---
PartyType = Literal["더불어민주당", "국민의힘", "개혁신당", "조국혁신당"]

# --- Pydantic 모델 정의 ---
class Parameters(BaseModel):
    k: Optional[int] = Field(10, description="표준 검색 시 사용할 문서 개수")
    k_per_side: Optional[int] = Field(5, description="균형 검색 시 각 입장에서 검색할 문서 개수")

class Filters(BaseModel):
    startdate: Optional[str] = Field(None, description="YYYY-MM-DD 형식의 검색 시작 날짜")
    enddate: Optional[str] = Field(None, description="YYYY-MM-DD 형식의 검색 종료 날짜")
    party: Optional[List[PartyType]] = Field(
        None,
        description="정당 기준 필터. 가능한 값: '더불어민주당', '국민의힘', '개혁신당', '조국혁신당'"
    )

class RetrievalPlan(BaseModel):
    """사용자의 질문을 분석하여 최적의 문서 검색 전략을 담는 데이터 스키마입니다."""
    strategy: str = Field(
        description="사용할 검색 전략. 'standard_retrieval', 'balanced_retrieval', 'no_retrieval', 'title_generation','no_generate' 중 하나여야 함"
    )
    data_type: List[str] = Field(
        description="검색에 필요한 데이터 유형. '사설','논평', '기사' 중 하나 이상을 포함하는 리스트. 검색이 필요 없으면 빈 리스트."
    )
    rewritten_question: Optional[str] = Field(
        description="검색에 용이하도록 키워드 위주 재구성. strategy가 no_retrieval 혹은 title_generation이면 None. 시간에 대한 내용은 제외."
    )
    filters: Filters = Field(
        description="검색에 적용할 메타데이터 필터"
    )
    parameters: Parameters = Field(
        None, description="선택된 전략에 필요한 파라미터"
    )
    generation_required: bool = Field(
        description=(
            "검색 후 요약 등의 응답 생성을 수행해야 하면 True, "
            "추천 등 단순히 검색 결과만 보여주면 되는 경우는 False"
        )
    )
    apply_body_required: Optional[bool] = Field(
        description="선택된 문서 부분에 대한 문장 조각 교체가 필요한 경우 True, 그렇지 않으면 False"
    )

# --- 노드 함수 ---
def plan_retrieval_node(state: GraphState) -> GraphState:
    """LLM의 Tool Calling 기능을 사용하여 구조화된 검색 전략을 계획합니다."""
    print("--- 노드 실행: 1. plan_retrieval (bind_tools 방식 적용) ---")

    planner_prompt_template = """
    You are a 'retrieval strategist' tasked with analyzing the user's question to determine the optimal document search strategy.
    Consider the intent behind the question, the type of information requested (factual, opinion-based, generative), and any temporal context.
    You must respond by calling the `RetrievalPlan` tool.

    ---

    ### [Guidelines for Analysis]

    #### 1. strategy (Search Strategy)
    Choose one of the following strategies based on the user's intent:

    - `"standard_retrieval"`: For simple fact-based or information-seeking queries.
    - `"balanced_retrieval"`: When the user requests a comparison of differing political views (e.g., across parties).
    - `"title_generation"`: Use only when the user explicitly asks to generate a title based on content.
    - `"no_retrieval"`: When the question can be answered directly without document lookup.
    - `"no_generate"`: Use only for inappropriate, mocking, or offensive content.

    #### 2. data_type (Required Data Types)
    Choose from:
    - `"editorial"`: 해석/관점 중심
    - `"opinion"`: 정당 입장/논평
    - `"news"`: 팩트 기반 보도

    #### 3. rewritten_question (Rewritten Query)
    Simplify question to core keywords (e.g., selected_text).
    Omit time phrases or generative intent.

    #### 4. filters (Date & Party)
    - Extract startdate/enddate if mentioned.
    - If no date: startdate = 1 year ago, enddate = today
    - If comparing political views, include:
      ```json
      "party": ["더불어민주당", "국민의힘"]
      ```

    Valid party values:
    - "더불어민주당"
    - "국민의힘"
    - "개혁신당"
    - "조국혁신당"

    #### 5. generation_required
    - True: if summarization, rewording, explanation, or editorialization is expected
    - False: if just retrieval is needed

    #### 6. apply_body_required
    - True: if user asks to fix or rewrite part of a document
    - False: if user just wants opinions, summaries, or context

    ### [Input]
    - Today's Date: {today}
    - User Question: {question}
    - selected text: {selected_text}
    ---
    """

    planner_prompt = ChatPromptTemplate.from_template(planner_prompt_template)
    planner_llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
    llm_with_tool = planner_llm.bind_tools([RetrievalPlan])
    parser = PydanticToolsParser(tools=[RetrievalPlan])

    planner_chain = planner_prompt | llm_with_tool | parser

    plan_objects = planner_chain.invoke({
        "question": state["question"],
        "today": datetime.now().strftime('%Y-%m-%d'),
        "selected_text": state.get("selected_text", "")
    })

    plan_dict = plan_objects[0].model_dump()
    if state.get("use_full_document", False):
        plan_dict["apply_body_required"] = False    
    return {**state, "plan": plan_dict}
