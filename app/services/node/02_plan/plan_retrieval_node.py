# 파일: 1_plan_retrieval_node.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
# 'bind_tools'와 함께 사용할 새로운 파서
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from graph_state import GraphState
import json

# OpenAI API 키 로드를 위해 .env 파일 사용
load_dotenv()

# --- Pydantic 모델 정의 (변경 없음) ---
# 이 모델 자체가 LLM이 호출할 '도구(Tool)'의 스키마가 됩니다.
class Parameters(BaseModel):
    k: Optional[int] = Field(10, description="표준 검색 시 사용할 문서 개수")
    k_per_side: Optional[int] = Field(5, description="균형 검색 시 각 입장에서 검색할 문서 개수")

class Filters(BaseModel):
    startdate: Optional[str] = Field(None, description="YYYY-MM-DD 형식의 검색 시작 날짜")
    enddate: Optional[str] = Field(None, description="YYYY-MM-DD 형식의 검색 종료 날짜")

class RetrievalPlan(BaseModel):
    """사용자의 질문을 분석하여 최적의 문서 검색 전략을 담는 데이터 스키마입니다."""
    strategy: str = Field(description="사용할 검색 전략. 'standard_retrieval', 'balanced_retrieval', 'no_retrieval', 'title_generation','no_generate' 중 하나여야 함")
    data_type: List[str] = Field(description="검색에 필요한 데이터 유형. '사설','논평', '기사' 중 하나 이상을 포함하는 리스트. 검색이 필요 없으면 빈 리스트.")
    rewritten_question: Optional[str] = Field(description="검색에 용이하도록 키워드 위주 재구성. strategy가 no_retrieval 혹은 title_generation이면 None. 시간에 대한 내용은 제외.")
    filters: Filters = Field(description="검색에 적용할 메타데이터 필터")
    parameters: Parameters = Field(None, description="선택된 전략에 필요한 파라미터")
    generation_required: bool = Field(
        description=(
            "검색 후 응답 생성을 수행해야 하면 True, "
            "단순히 검색 결과만 보여주면 되는 경우는 False"
        )
    )
# --- 노드 함수 (bind_tools 방식으로 리팩토링) ---
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
    - `"title_generation"`: When the user asks for a title to be generated based on an article or opinion.
    - `"no_retrieval"`: When the question can be answered directly without any need for document retrieval.
    - `"no_generate"`: Select this strategy **only if** the user's request includes highly offensive content, such as profanity, mockery, or personal attacks.  
    ❗ However, if the user is asking to soften or rephrase an existing statement in a more polite or less aggressive tone, this **does not** count as offensive.  
    Do **not** use `"no_generate"` in such cases.

    #### 2. data_type (Required Data Types)
    Choose one or more of the following depending on what kind of information the user is looking for:

    - `"editorial"`: When perspectives or interpretations on a topic are needed.
    - `"opinion"`: When political positions or party-based viewpoints are relevant.
    - `"news"`: For factual or event-based reporting.

    If no retrieval is needed, return an empty list `[]`.

    #### 3. rewritten_question (Rewritten Query)
    Rewrite the question using only the core keywords to optimize for search.
    Remove greetings, general commentary, and generative intent.
    Also, exclude any time-related expressions from the rewritten question.

    #### 4. filters (Date Filters)
    If the user's question includes a temporal reference, extract and format the `startdate` and `enddate` as `YYYY-MM-DD`.

    If no explicit time expression is present, use the following defaults:
    - `startdate`: 1 year ago from today
    - `enddate`: today

    📌 Examples:
    - “Around this time last year” → `startdate`: today - 1 year - 7 days, `enddate`: today - 1 year + 7 days
    - “Last week” → `startdate`: last Monday, `enddate`: last Sunday
    - “May 10” → `startdate`: May 10, `enddate`: May 10

    📌 Date Validation Rules:
    - `enddate` cannot be earlier than `startdate`
    - `enddate` cannot be in the future
    - `startdate` must not be before March 1, 2024
    - If `strategy` is `"no_generate"`, both `startdate` and `enddate` should be set to `null`

    #### 5. generation_required: 
    - Set to true if the user is asking for any kind of response, rewriting, summarization, or editing based on retrieved content.
    - Set to false if the user only wants to see related documents, opinions, or facts — not a generated response.
    ---

    ### [Input]
    - Today's Date: {today}
    - User Question: {question}
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
    })

    plan_dict = plan_objects[0].model_dump()
    return {**state, "plan": plan_dict}
