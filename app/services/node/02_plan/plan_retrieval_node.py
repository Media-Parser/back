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
    strategy: str = Field(description="사용할 검색 전략. 'standard_retrieval', 'balanced_retrieval', 'no_retrieval', 'title_generation' 중 하나여야 함")
    data_type: List[str] = Field(description="검색에 필요한 데이터 유형. '사설','논평', '기사' 중 하나 이상을 포함하는 리스트. 검색이 필요 없으면 빈 리스트.")
    rewritten_question: str = Field(description="검색에 더 용이하도록 재구성된 질문. 검색이 필요 없으면 원래 질문을 그대로 반환. 시간에 대한 내용은 제외.")
    filters: Filters = Field(description="검색에 적용할 메타데이터 필터")
    parameters: Parameters = Field(None, description="선택된 전략에 필요한 파라미터")

# --- 노드 함수 (bind_tools 방식으로 리팩토링) ---
def plan_retrieval_node(state: GraphState) -> GraphState:
    """LLM의 Tool Calling 기능을 사용하여 구조화된 검색 전략을 계획합니다."""
    print("--- 노드 실행: 1. plan_retrieval (bind_tools 방식 적용) ---")

    # 🎯 1. 프롬프트 단순화
    # 더 이상 JSON 형식을 직접 지시할 필요 없이, 역할과 최종 목표만 명확히 전달합니다.
    planner_prompt_template = """
    당신은 사용자의 질문을 분석하여 최적의 문서 검색 전략을 수립하는 '검색 전략가'입니다.
    질문의 의도, 필요한 정보의 종류(사실, 의견), 시간적 맥락을 종합적으로 분석하여,
    주어진 `RetrievalPlan` 도구를 사용해 검색 계획을 반드시 호출해야 합니다.

    **[분석 가이드라인]**
    - **전략(strategy)**: 질문이 제목 생성인지, 찬반 양론/입장 비교인지, 단순 정보 검색인지, 검색이 불필요한지 판단하세요.
    - **데이터 유형(data_type)**: 질문에 '입장/의견'이 필요하면 "사설", 정당별 의견이 필요하면 "논평"을, '사실/사건' 정보가 필요하면 "기사"를 선택하세요. 여러개가 필요할 수도 있습니다. 검색이 불필요하면 빈 리스트로 두세요.
    - **질문 재작성(rewritten_question)**: 검색에 용이한 키워드 중심으로 질문을 다시 만들고 시간 표현은 제외. 검색이 불필요하면 원본 질문을 사용.
    - **날짜 필터(filters)**: '작년 이맘때','최신'같은 시간 표현을 `YYYY-MM-DD` 형식으로 변환하세요. 없으면 [오늘 날짜]로 두세요. no_retrieval인 경우엔 비워두세요.
        - **기간 설정 규칙**:
        - **시간 표현이 있는 경우**: 해당 표현에 맞는 `startdate`와 `enddate`를 `YYYY-MM-DD` 형식으로 직접 계산하여 채우세요.
          - 예시 1: "지난주" -> `startdate`는 지난주 월요일, `enddate`는 지난주 일요일로 설정합니다.
          - 예시 2: "작년 이맘때" -> 작년 오늘을 기준으로 약 1~2주의 유연한 기간을 설정합니다.
          - 예시 3: "5월 10일" -> `startdate`와 `enddate` 모두 해당 날짜로 설정합니다.
          - 예시 4: 1년보다 이전인 경우 -> 날짜를 사용할 수 없음.
        - **시간 표현이 없는 경우 (기본값)**: `startdate`는 **[오늘 날짜] 기준 한 달 전**, `enddate`는 **[오늘 날짜]** 로 설정하세요.
        - **최종 날짜 검증**:
            - `enddate`는 `startdate`보다 빠르면 안 됩니다.
            - `enddate`는 **[오늘 날짜]** 보다 미래일 수 없습니다.
    ---
    **[오늘 날짜]**: {today}
    **[사용자 질문]**: {question}
    ---
    """
    planner_prompt = ChatPromptTemplate.from_template(planner_prompt_template)
    
    # 🎯 2. LLM에 Pydantic 모델(Tool)을 바인딩
    planner_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
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

    return {
        "plan": plan_dict
    }


# --- 이 노드를 단독으로 실행하기 위한 코드 (변경 없음) ---
if __name__ == '__main__':
    test_cases = [
        {"question": "작년 이맘때에 발표된 부동산 정책에 대한 여야의 입장은 어때?"},
        {"question": "최신 AI 기술 동향에 대해 알려줘."},
        {"question": "안녕하세요, 오늘 하루도 좋은 하루 되세요!"},
        {"question": "양자컴퓨터의 원리가 뭐야?"},
        {"question": "정부의 저출산 대책에 대한 비판적인 시각을 보여줄 수 있는 제목을 만들어줘"},
    ]

    for i, case in enumerate(test_cases):
        print(f"\n--- 테스트 케이스 {i+1} 실행 ---")
        print(f"질문: {case['question']}")
        
        plan_result = plan_retrieval_node(case)
        
        print("\n--- 노드 실행 결과 ---")
        print(json.dumps(plan_result, indent=2, ensure_ascii=False))
        print("------------------------")