# service/node/04_retrieval/grade_and_filter_node.py

from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

# --- 상태(State) 모방 클래스 ---
class GraphState(dict):
    pass

# --- 노드 함수 ---
def grade_and_filter_node(state: GraphState) -> GraphState:
    print("--- 노드 실행: 3. grade_and_filter ---")
    question = state["original_question"]
    documents = state["documents"]
    
    if not documents:
        print("❌ 평가할 문서가 없습니다.")
        return {"documents": []}

    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
    useful_docs = []
    
    print("문서 평가 시작:")
    for i, doc in enumerate(documents):
        grader_prompt = ChatPromptTemplate.from_template(
            """아래 문서가 질문에 답변하는 데 유용합니까? 'yes' 또는 'no'로만 답변하세요.

[문서]
{doc}

[질문]
{question}

[유용 여부 (yes/no)]"""
        )
        grader_chain = grader_prompt | llm | StrOutputParser()
        decision = grader_chain.invoke({"question": question, "doc": doc.page_content})
        print(f"LLM 응답: {decision}")
        if "yes" in decision.lower():
            print(f"  - 문서 {i+1}: 유용함 (✅)")
            useful_docs.append(doc)
        else:
            print(f"  - 문서 {i+1}: 유용하지 않음 (❌)")

    if not useful_docs:
        print("모든 문서가 유용하지 않은 것으로 평가되었습니다.")
    
    print(f"✅ 총 {len(useful_docs)}개의 유용한 문서를 필터링했습니다.")
    return {"documents": useful_docs}

# --- 이 노드를 단독으로 실행하기 위한 코드 ---
if __name__ == '__main__':
    # 1. 입력 상태(State) 정의: 검색 노드의 출력을 모방
    input_state = GraphState({
        "documents": [
            Document(page_content="집권 여당은 종부세 완화가 중산층 부담을 덜어줄 것이라고 주장했다.", metadata={'score': 1}),
            Document(page_content="지난 분기 KOSPI 지수는 소폭 하락 마감했습니다.", metadata={'score': 0}),
            Document(page_content="정부의 종합부동산세 완화는 부자 감세일 뿐이다.", metadata={'score': -1})
        ],
        "original_question": "종부세 완화에 대한 여야 입장 알려줘"
    })
    
    # 2. 노드 함수 실행
    filter_result = grade_and_filter_node(input_state)
    
    # 3. 결과 확인
    print("\n--- 노드 실행 결과 (필터링된 문서) ---")
    if filter_result["documents"]:
        for doc in filter_result["documents"]:
            print(f"- 내용: {doc.page_content}")
    else:
        print("유용한 문서가 없습니다.")