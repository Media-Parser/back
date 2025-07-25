# ✅ app/services/node/03_retrieval/balanced_retrieval_node.py
import os
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
from datetime import datetime
from graph_state import GraphState
load_dotenv()

embedding_function = OpenAIEmbeddings()
DEFAULT_PARTIES = ["더불어민주당", "국민의힘"]

def date_to_int(date_str: str) -> int | None:
    try:
        return int(datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d"))
    except (ValueError, TypeError):
        return None

def balanced_retrieval_node(state: GraphState) -> GraphState:
    print("--- 노드 실행: 2b. balanced_retrieval ---")
    plan = state["plan"]
    rewritten_question = plan["rewritten_question"]
    parameters = plan.get("parameters") or {}
    filters = plan.get("filters") or {}
    k_per_side = parameters.get("k_per_side", 2)

    data_types = plan.get("data_type", [])
    parties = filters.get("party", DEFAULT_PARTIES)
    if not isinstance(parties, list):
        parties = DEFAULT_PARTIES

    # 날짜 및 데이터타입 공통 조건
    base_conditions = []
    start_date = date_to_int(filters.get("startdate"))
    if start_date:
        base_conditions.append({'date_int': {'$gte': start_date}})
    end_date = date_to_int(filters.get("enddate"))
    if end_date:
        base_conditions.append({'date_int': {'$lte': end_date}})
    if data_types:
        base_conditions.append({'data_type': {'$in': data_types}})

    # 결과 누적
    all_party_results = []

    for party in parties:
        # 정당 조건 추가
        party_filter = base_conditions + [{'party': {'$eq': party}}]
        search_filter = {"$and": party_filter} if len(party_filter) > 1 else party_filter[0]

        print(f"🔍 [정당: {party}] 검색 필터: {search_filter}")

        try:
            persist_dir = f"chroma_opinion"  # 고정 DB 경로
            vectorstore = Chroma(
                persist_directory=persist_dir,
                embedding_function=embedding_function,
                collection_name="langchain"
            )

            docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
                query=rewritten_question,
                k=k_per_side,
                filter=search_filter
            )
            docs = [doc for doc, _ in docs_with_scores]

            all_party_results.append({
                "party": party,
                "documents": docs
            })
            print(f"✅ {party}: {len(docs)}개 검색됨")

        except Exception as e:
            print(f"⚠️ {party} 검색 중 오류 발생: {e}")

    return {**state, "documents_by_party": all_party_results}
