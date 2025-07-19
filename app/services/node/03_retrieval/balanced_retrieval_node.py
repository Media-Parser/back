import os
from typing import List, Dict, Any
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- ChromaDB 및 임베딩 설정 ---
embedding_function = OpenAIEmbeddings()
persist_directory = "chroma_db"



# --- 상태(State) 모방 클래스 ---
class GraphState(dict):
    pass

# --- 날짜 변환 헬퍼 함수 ---
def date_to_int(date_str: str) -> int | None:
    """YYYY-MM-DD 형식의 문자열을 YYYYMMDD 형식의 정수로 변환합니다."""
    try:
        return int(datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d"))
    except (ValueError, TypeError):
        return None

# --- 노드 함수 ---
def balanced_retrieval_node(state: GraphState) -> GraphState:
    """
    'balanced' 검색 전략을 수행하는 노드.
    정제된 질문(rewritten_question)을 사용하고, 여러 메타데이터(날짜 범위, 데이터 타입 등)를 복합적으로 필터링합니다.
    """
    print("--- 노드 실행: 2b. balanced_retrieval ---")
    plan = state["plan"]
    rewritten_question = plan["rewritten_question"]
    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_function)

    parameters = plan.get("parameters") or {}
    filters = plan.get("filters") or {}
    k = parameters.get("k", 5)

    filter_conditions = []

    # 1. 날짜 범위 필터링 조건 추가 (***수정된 부분***)
    # 각 날짜 조건을 별개의 딕셔너리로 분리합니다.
    start_date = date_to_int(filters.get("startdate"))
    if start_date:
        filter_conditions.append({'date_int': {'$gte': start_date}})

    end_date = date_to_int(filters.get("enddate"))
    if end_date:
        filter_conditions.append({'date_int': {'$lte': end_date}})
        
    # 2. 데이터 타입 필터링 조건 추가
    data_types = plan.get("data_type")
    if data_types and isinstance(data_types, list) and len(data_types) > 0:
        filter_conditions.append({'data_type': {'$in': data_types}})


    # 3. 최종 필터 조합
    search_filter = {}
    if len(filter_conditions) > 1:
        # 조건이 여러 개일 경우 '$and'로 묶습니다.
        search_filter = {"$and": filter_conditions}
    elif len(filter_conditions) == 1:
        search_filter = filter_conditions[0]

    print(f"🔍 검색 필터: {search_filter}")

    retriever = vectorstore.as_retriever(search_kwargs={'k': k, 'filter': search_filter})
    documents = retriever.invoke(rewritten_question)

    print(f"✅ 'balanced' 전략으로 {len(documents)}개의 문서를 검색했습니다.")
    return {**state, "documents": documents}