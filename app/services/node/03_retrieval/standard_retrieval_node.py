from datetime import datetime
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

# --- 설정 ---
PERSIST_DIR = "chroma_db"
COLLECTION_NAME = "langchain"
embedding_function = OpenAIEmbeddings()

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

# --- 검색 노드 함수 ---
def standard_retrieval_node(state: GraphState) -> GraphState:
    """
    메타데이터 필터링과 함께 유사도 점수를 포함하여 문서를 검색합니다.
    """
    print("--- 노드 실행: standard_retrieval (유사도 점수 포함) ---")
    plan = state["plan"]
    rewritten_question = plan["rewritten_question"]
    
    vectorstore = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embedding_function,
        collection_name=COLLECTION_NAME
    )

    parameters = plan.get("parameters") or {}
    filters = plan.get("filters") or {}
    k = parameters.get("k", 10)

    filter_conditions = []

    # 1. 날짜 범위 필터링 (date_int 사용)
    start_date_int = date_to_int(filters.get("startdate"))
    if start_date_int is not None:
        filter_conditions.append({'date_int': {'$gte': start_date_int}})

    end_date_int = date_to_int(filters.get("enddate"))
    if end_date_int is not None:
        filter_conditions.append({'date_int': {'$lte': end_date_int}})
    
    # # 2. 토픽 필터링 추가 해야돼!!
    # topic_filter = filters.get("topic")
    # if topic_filter:
    #     filter_conditions.append({'topic': {'$eq': topic_filter}})

    # 3. 데이터 타입 필터링 (복수 선택 허용)
    data_types = plan.get("data_type")
    if data_types and isinstance(data_types, list) and len(data_types) > 0:
        filter_conditions.append({'data_type': {'$in': data_types}})

    # 4. 최종 필터 조합
    if len(filter_conditions) > 1:
        search_filter = {"$and": filter_conditions}
    elif len(filter_conditions) == 1:
        search_filter = filter_conditions[0]
    else:
        search_filter = {}

    print(f"🔍 검색 필터: {search_filter}")
    
    # 5. 유사도 점수 포함 검색
    docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
        query=rewritten_question,
        k=k,
        filter=search_filter
    )

    print(f"✅ 검색된 문서 수 (with relevance scores): {len(docs_with_scores)}")
    return {"docs_with_scores": docs_with_scores}


# --- 단독 테스트 실행 ---
if __name__ == '__main__':
    input_state = GraphState({
        "plan": {
            "strategy": "standard_retrieval",
            "rewritten_question": "부동산 정책",
            "filters": {
                "startdate": "2024-03-01",
                "enddate": "2025-03-31",
                # "topic": "부동산",
                "data_type": ["opinion"]
            },
            "parameters": {"k": 5}
        },
        "question": "",
        "original_question": ""
    })

    result = standard_retrieval_node(input_state)

    print("\n--- 🔍 검색 결과 ---")
    if result.get("docs_with_scores"):
        for doc, score in result["docs_with_scores"]:
            print(f"🧠 Score: {score:.3f}\n📄 내용: {doc.page_content}\n📌 메타데이터: {doc.metadata}\n")
    else:
        print("❌ 검색된 문서가 없습니다.")
