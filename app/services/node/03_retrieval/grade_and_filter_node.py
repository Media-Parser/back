# 파일: 3_grade_and_filter_node.py

import torch
import torch.nn.functional as F
import numpy as np
from typing import List
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from langchain_core.documents import Document
from graph_state import GraphState
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

# --- 정규화 함수 ---
def exp_normalize(x: np.ndarray) -> np.ndarray:
    b = x.max()
    y = np.exp(x - b)
    return y / y.sum()

# --- GPU 설정 ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"📡 현재 디바이스: {device}")

# --- KoBGE Cross-Encoder 로드 ---
# 실제 서버에 올릴 땐 미리 캐시해두고 쓸 수 있게 할 예정. (get_instance)
MODEL_PATH = "Dongjin-kr/ko-reranker"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH).to(device)
model.eval()

# --- 리랭크 함수 ---
def rerank_documents(query: str, documents: List[Document], top_k: int = 5, batch_size: int = 8) -> List[Document]:
    print(f"📥 총 {len(documents)}개 문서 리랭킹 중...")

    pairs = [[query, doc.page_content] for doc in documents]
    scores = []

    for i in range(0, len(pairs), batch_size):
        batch_pairs = pairs[i:i+batch_size]
        batch_docs = documents[i:i+batch_size]

        inputs = tokenizer(batch_pairs, padding=True, truncation=True, return_tensors='pt', max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = model(**inputs).logits.view(-1).float().cpu()

        batch_scores = exp_normalize(logits.numpy())
        scores.extend(zip(batch_scores, batch_docs))

    scored_docs = sorted(scores, key=lambda x: x[0], reverse=True)
    top_docs = [doc for score, doc in scored_docs[:top_k]]

    for i, (score, doc) in enumerate(scored_docs[:top_k]):
        print(f"✅ {i+1}위 문서 (score={score:.4f}): {doc.page_content[:60]}...")

    return top_docs

# --- LangGraph 노드 ---
def chunk_documents(documents: List[Document], chunk_size=300, chunk_overlap=50) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(documents)

# 노드 함수 개선
def grade_and_filter_node(state: GraphState) -> GraphState:
    print("--- 노드 실행: 3. grade_and_filter (GPU 리랭커 + 청킹) ---")
    question = state.get("question")
    documents = state.get("documents")

    # 0. 혹시 Tuple(Document, score) 구조이면 Document만 추출
    if documents and isinstance(documents[0], tuple):
        print("📌 튜플 형식 문서 감지 → Document만 추출 중")
        documents = [doc for doc, score in documents]

    if not documents:
        print("❌ 평가할 문서가 없습니다.")
        return {**state, "documents": [], "generation": "관련 문서를 찾을 수 없습니다."}
    
    # 1. 문서 청킹
    chunked_docs = chunk_documents(documents)
    print(f"📦 총 {len(chunked_docs)}개 청크로 변환 완료.")

    # 2. 리랭크
    top_k = min(5, len(chunked_docs))
    top_chunks = rerank_documents(question, chunked_docs, top_k=top_k)

    print(f"🎯 최종 선택 문서 조각 수: {len(top_chunks)}")

    # 3. generate 생략 시 → 하이퍼링크 목록 생성
    plan = state.get("plan", {})
    if not plan.get("generation_required"):
        # 문서 제목과 url 추출
        link_lines = []
        for doc in top_chunks:
            meta = doc.metadata
            title = meta.get("title", "제목 없음")
            url = meta.get("url", "#")
            line = f"- [{title}]({url})"
            link_lines.append(line)
        summary_text = "\n".join(link_lines) if link_lines else "관련 문서를 찾을 수 없습니다."
        return {**state, "documents": top_chunks, "generation": summary_text}

    # 4. 평소처럼 다음 노드(generate)로 넘길 경우
    return {**state, "documents": top_chunks}
