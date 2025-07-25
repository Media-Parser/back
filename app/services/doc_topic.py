# services/doc_topic.py

import os
from fastapi import APIRouter, Depends, HTTPException
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from openai import OpenAI
from app.core.config import Settings
import builtins
from app.utils.tokenizer import bertopic_tokenizer, korean_stopwords  # ✅ import만 함
builtins.bertopic_tokenizer = bertopic_tokenizer
from typing import Any, Dict, Tuple
import numpy as np

OPENAI_API_KEY = Settings.OPENAI_API_KEY

# --- OpenAI 임베딩 함수 정의 ---
def embed_openai(texts: list[str]) -> list[list[float]]:
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(
        input=texts,
        model="text-embedding-3-small"
    )
    return np.array([r.embedding for r in response.data])

# --- BERTopic 모델 로드 ---
def load_topic_model():
    return BERTopic.load("my_bertopic_model_fixed")

topic_model = load_topic_model()

# --- 단일 문서 토픽 추출 함수 ---
def get_topic_info_with_docs(doc: str) -> Tuple[int, list]:
    # 1. doc이 None이거나 빈 값이면 즉시 예외
    if not isinstance(doc, str) or not doc.strip():
        raise ValueError(f"입력 문서가 비어있거나 문자열이 아닙니다: {doc} (type={type(doc)})")
    
    # 2. log로 확인
    print(f"[get_topic_info_with_docs] doc type: {type(doc)}, doc: {repr(doc)[:200]}")
    
    # 3. 임베딩 생성
    embeddings = embed_openai([doc])
    topics, probs = topic_model.transform([doc], embeddings=embeddings)
    
    topic_id = int(topics[0]) if topics and topics[0] != -1 else -1
    keywords = topic_model.get_topic(topic_id) if topic_id != -1 else []
    top_words = [kw[0] for kw in keywords if isinstance(kw, (list, tuple)) and len(kw) > 0][:6]
    keywords = top_words
    return topic_id, keywords
