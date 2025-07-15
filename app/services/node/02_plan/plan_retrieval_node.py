# service/node/02_plan/plan_retrieval_node.py

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
    k: Optional[int] = Field(None, description="표준 검색 시 사용할 문서 개수")
    k_per_side: Optional[int] = Field(None, description="균형 검색 시 각 입장에서 검색할 문서 개수")

class Filters(BaseModel):
    startdate: Optional[str] = Field(None, description="YYYY-MM-DD 형식의 검색 시작 날짜")
    enddate: Optional[str] = Field(None, description="YYYY-MM-DD 형식의 검색 종료 날짜")

class RetrievalPlan(BaseModel):
    """사용자의 질문을 분석하여 최적의 문서 검색 전략을 담는 데이터 스키마입니다."""
    strategy: str = Field(description="사용할 검색 전략. 'standard_retrieval', 'balanced_retrieval', 'no_retrieval', 'chathistory_retrieve' 중 하나여야 함")
    data_type: List[str] = Field(description="검색에 필요한 데이터 유형. '사설','논평', '기사' 중 하나 이상을 포함하는 리스트. 검색이 필요 없으면 빈 리스트.")
    rewritten_question: str = Field(description="검색에 더 용이하도록 재구성된 질문. 검색이 필요 없으면 원래 질문을 그대로 반환. 시간에 대한 내용은 제외.")
    filters: Filters = Field(description="검색에 적용할 메타데이터 필터")
    parameters: Parameters = Field(None, description="선택된 전략에 필요한 파라미터")

# --- 노드 함수 (bind_tools 방식으로 리팩토링) ---
def plan_retrieval_node(state: GraphState) -> GraphState:
    """LLM의 Tool Calling 기능을 사용하여 구조화된 검색 전략을 계획합니다."""
    print("--- 노드 실행: 1. plan_retrieval (bind_tools 방식 적용) ---")

    planner_prompt_template = """
    당신은 사용자의 질문을 분석하여 최적의 문서 검색 전략을 수립하는 '검색 전략가'입니다.
    질문의 의도, 정보의 종류(사실, 의견, 생성), 시간적 맥락을 종합적으로 고려하여,
    반드시 `RetrievalPlan` 도구를 호출하여 응답하세요.
    ---
    ### [분석 가이드라인]

#### 1. strategy (검색 전략)
질문의 의도에 따라 아래 중 하나를 고르세요:

- `"standard_retrieval"`: 단순 정보 검색
- `"balanced_retrieval"`: 서로 다른 입장(예: 여야, 찬반 등)의 비교가 필요함
- `"title_generation"`: 기사/의견을 기반으로 생성(요약, 제목 생성 등)을 요구함
- `"chathistory_retrieve"`: 이전 대화 맥락 기반 검색이 필요한 경우
    전략 분류 예시:
    - "여야의 입장 차이를 보여줘" → `balanced_retrieval`
    - "기사 제목을 만들어줘" → `title_generation`
    - "최신 AI 동향은?" → `standard_retrieval`
    - "안녕하세요, 좋은 하루 되세요!" → `no_retrieval`

    #### 2. data_type (필요한 데이터 유형)
    - `"사설"`: 특정 주제에 대한 시각, 관점이 필요할 때
    - `"논평"`: 정치적 입장, 정당별 의견이 필요할 때
    - `"기사"`: 사건, 사실 기반 정보가 필요할 때

    복수 선택 가능. 검색이 불필요하면 빈 리스트 (`[]`)로 두세요.

    #### 3. rewritten_question (질문 재작성)
    - 검색에 용이하도록 핵심 키워드만 남기고 시간 표현은 제거하세요.
    - 인삿말, 설명적 문장, 생성형 표현은 제거하세요.
    - 예:  
    - "작년 이맘때 발표된 부동산 정책에 대한 여야의 입장은 어때?"  
        → `"부동산 정책 여야 입장"`

    #### 4. filters (날짜 필터)
    - 질문 내 시간 표현이 있다면, `startdate`, `enddate`를 `YYYY-MM-DD` 형식으로 계산하여 지정하세요.
    - 시간 표현이 없으면 다음을 기본값으로 사용하세요:
        - `startdate`: 오늘 기준 1년 전
        - `enddate`: 오늘

    📌 기간 계산 예시:
    - "작년 이맘때" → `startdate`: 작년 오늘 - 7일, `enddate`: 작년 오늘 + 7일
    - "지난주" → `startdate`: 지난주 월요일, `enddate`: 지난주 일요일
    - "5월 10일" → `startdate`, `enddate`: 5월 10일

    📌 날짜 유효성 검사:
    - `enddate`는 `startdate`보다 과거일 수 없습니다.
    - `enddate`는 오늘보다 미래일 수 없습니다.
    - `startdate`는 2024년 3월 1일보다 과거일 수 없습니다.
    - `no_generate`인 경우, `startdate`와 `enddate`는 `null`로 설정하세요.

    ---
    ### [입력 값]
    - 오늘 날짜: {today}
    - 사용자 질문: {question}
    ---
    """

    planner_prompt = ChatPromptTemplate.from_template(planner_prompt_template)
    
    # 🎯 2. LLM에 Pydantic 모델(Tool)을 바인딩
    planner_llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
    llm_with_plan_tool = planner_llm.bind_tools([RetrievalPlan])

    # 🎯 3. Tool 출력을 파싱하기 위한 파서 정의
    parser = PydanticToolsParser(tools=[RetrievalPlan])

    # 🎯 4. 새로운 체인 구성
    planner_chain = planner_prompt | llm_with_plan_tool | parser

    today = datetime.now()
    
    # 체인 실행. 더 이상 format_instructions를 전달할 필요가 없습니다.
    plan_objects = planner_chain.invoke({
        "question": state["question"],
        "today": today.strftime('%Y-%m-%d'),
    })
    
    # 파서는 호출된 도구의 리스트를 반환하므로 첫 번째 항목을 사용합니다.
    plan_object = plan_objects[0]
    
    plan_dict = plan_object.model_dump()
    # print(f"✅ 검색 계획 수립 완료: {json.dumps(plan_dict, indent=2, ensure_ascii=False)}")
    print(state)
    print(plan_dict)
    return {
        **state,
        "plan": plan_dict
    }


# --- 이 노드를 단독으로 실행하기 위한 코드 (변경 없음) ---
if __name__ == '__main__':
    test_cases = [
        # {"question": "작년 이맘때에 발표된 부동산 정책에 대한 여야의 입장은 어때?"},
        # {"question": "최신 AI 기술 동향에 대해 알려줘."},
        # {"question": "안녕하세요, 오늘 하루도 좋은 하루 되세요!"},
        # {"question": "양자컴퓨터의 원리가 뭐야?"},
        # {"question": "정부의 저출산 대책에 대한 비판적인 시각을 보여줄 수 있는 제목을 만들어줘"},
        {"question": "이재명 어떤 일을 한 사람임?"}
    ]

    for i, case in enumerate(test_cases):
        print(f"\n--- 테스트 케이스 {i+1} 실행 ---")
        print(f"질문: {case['question']}")
        
        plan_result = plan_retrieval_node(case)
        
        print("\n--- 노드 실행 결과 ---")
        print(json.dumps(plan_result, indent=2, ensure_ascii=False))
        print("------------------------")