from datetime import datetime
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

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
    parameters = plan.get("parameters") or {}
    filters = plan.get("filters") or {}
    k = parameters.get("k", 10)

    filter_conditions = []

    # 1. 날짜 범위 필터링
    start_date_int = date_to_int(filters.get("startdate"))
    if start_date_int is not None:
        filter_conditions.append({'date_int': {'$gte': start_date_int}})

    end_date_int = date_to_int(filters.get("enddate"))
    if end_date_int is not None:
        filter_conditions.append({'date_int': {'$lte': end_date_int}})

    # 2. 토픽 필터링 (예정)
    # topic_filter = filters.get("topic")
    # if topic_filter:
    #     filter_conditions.append({'topic': {'$eq': topic_filter}})

    # 3. 최종 검색 필터 조합
    if len(filter_conditions) > 1:
        search_filter = {"$and": filter_conditions}
    elif filter_conditions:
        search_filter = filter_conditions[0]
    else:
        search_filter = {}

    print(f"🔍 검색 필터: {search_filter}")

    # 4. 데이터 타입별 DB 순회
    all_results = []
    data_types = plan.get("data_type", [])
    for dtype in data_types:
        persist_path = f"chroma_db_{dtype}"
        print(f"📁 검색 대상 DB: {persist_path}")
        try:
            vectorstore = Chroma(
                persist_directory=persist_path,
                embedding_function=embedding_function,
                collection_name="langchain"
            )
            docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
                query=rewritten_question,
                k=k,
                filter=search_filter
            )
            all_results.extend(docs_with_scores)
        except Exception as e:
            print(f"⚠️ {dtype} 컬렉션 검색 중 오류 발생: {e}")

    # 5. 결과 정렬 및 top-k 추출
    all_results_sorted = sorted(all_results, key=lambda x: x[1], reverse=True)
    top_docs = all_results_sorted[:k]
    retrieved_docs = [doc for doc, score in top_docs]
    print(f"📦 최종 문서 개수: {len(retrieved_docs)}")
    for i, doc in enumerate(retrieved_docs, 1):
        print(f"\n📄 문서 {i} (score: {top_docs[i-1][1]:.4f})")
        print(f"내용: {doc.page_content[:500]}...")  # 500자까지만 출력
        print(f"메타데이터: {doc.metadata}")

    return {**state, "documents": retrieved_docs}

