# app/services/analyze_service.py
import hashlib
from typing import List, Dict
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import Settings
from app.models.analyze_model import SentenceAnalysis
from langdetect import detect
import kss
from nltk.tokenize import sent_tokenize
import nltk
from app.services.exaone_client import run_exaone_batch

nltk.download('punkt', quiet=True)

def smart_sentence_split(text: str):
    try:
        lang = detect(text)
        print(f"[LOG] 감지된 언어: {lang}")
        if lang == "ko":
            # 1. 먼저 줄바꿈(\n)을 기준으로 텍스트를 나눕니다.
            lines = text.splitlines()
            all_sentences = []
            # 2. 나눠진 각 줄에 대해 kss로 다시 문장 분리를 수행합니다.
            for line in lines:
                if line.strip(): # 비어있는 줄은 무시합니다.
                    all_sentences.extend(kss.split_sentences(line))
            return all_sentences
        elif lang == "en":
            return sent_tokenize(text)
        else:
            return [text]
    except Exception:
        # langdetect가 비어 있거나 너무 짧은 텍스트에 대해 오류를 발생시킬 수 있음
        return text.splitlines()

ATLAS_URI = Settings.ATLAS_URI
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']

"""
분석 결과 저장을 위한 별도 컬렉션 지정
"""
analysis_collection = db["analysis_cache"]

def hash_sentence(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

async def get_prev_analysis(doc_id: str) -> List[Dict]:
    doc = await analysis_collection.find_one({"doc_id": doc_id})
    if doc and "sentence_analysis" in doc:
        return doc["sentence_analysis"]
    return []

async def save_analysis(doc_id: str, analysis: List[SentenceAnalysis]):
    await analysis_collection.update_one(
        {"doc_id": doc_id},
        {"$set": {"sentence_analysis": [a.model_dump() for a in analysis]}},
        upsert=True,
    )

def process_exaone_results(sentences: List[str]) -> List[SentenceAnalysis]:
    print(f"[LOG] EXAONE 요청 문장 목록: {sentences}")
    batch_results = run_exaone_batch(sentences)
    print(f"[LOG] EXAONE 응답: {batch_results}")
    
    results = []
    for idx, (sent, result) in enumerate(zip(sentences, batch_results)):
        print(f"[LOG] 모델 raw 응답 ({idx}): {result}")
        results.append(
            SentenceAnalysis(
                index=idx,
                text=sent,
                flag=result.get("flag", False),
                label=result.get("label", "문제 없음"),
                highlighted=result.get("highlighted", []),
                explanation=result.get("explanation", []),
            )
        )
    print(f"[LOG] 파싱된 결과: {results}")
    return results

async def analyze_document(doc_id: str, contents: str) -> List[SentenceAnalysis]:
    if not contents or not contents.strip():
        return []
        
    sentences = smart_sentence_split(contents)
    prev_analysis_list = await get_prev_analysis(doc_id)
    
    final_analysis: List[SentenceAnalysis] = [None] * len(sentences)
    prev_map = {hash_sentence(s["text"]): s for s in prev_analysis_list}
    
    sentences_to_analyze_map = {}
    
    for i, s in enumerate(sentences):
        h = hash_sentence(s)
        if h in prev_map:
            cached_data = prev_map[h]
            cached_data['index'] = i
            final_analysis[i] = SentenceAnalysis(**cached_data)
        else:
            sentences_to_analyze_map[i] = s
            
    if sentences_to_analyze_map:
        indices_to_analyze = list(sentences_to_analyze_map.keys())
        texts_to_analyze = list(sentences_to_analyze_map.values())
        
        updated_results = process_exaone_results(texts_to_analyze)
        
        for i, analysis_result in enumerate(updated_results):
            original_index = indices_to_analyze[i]
            analysis_result.index = original_index
            final_analysis[original_index] = analysis_result
            
    final_analysis = [res for res in final_analysis if res is not None]
    
    await save_analysis(doc_id, final_analysis)
    return final_analysis
