# ✅ app/services/analyze_service.py

import hashlib
import re
from typing import List, Dict
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import Settings
from app.models.analyze_model import SentenceAnalysis
from app.services.exaone_client import run_exaone_batch
import kss
from nltk.tokenize import sent_tokenize
from langdetect import detect
import nltk

nltk.download('punkt', quiet=True)

# 문장 분리 함수
def smart_sentence_split(text: str):
    lang = detect(text)
    print(f"[LOG] 감지된 언어: {lang}")
    if lang == "ko":
        return kss.split_sentences(text)
    elif lang == "en":
        return sent_tokenize(text)
    else:
        print(f"[LOG] 분리된 문장: {text}")
        return [text]

# MongoDB 연결 설정
ATLAS_URI = Settings.ATLAS_URI
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']
analysis_collection = db["analysis_cache"]

# 해시 생성 함수
def hash_sentence(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# 이전 분석 결과 가져오기
async def get_prev_analysis(doc_id: str) -> List[Dict]:
    # 1. temp_docs에서 먼저 찾기
    doc = await db["temp_docs"].find_one({"doc_id": doc_id})
    if doc and "sentence_analysis" in doc:
        return doc["sentence_analysis"]
    # 2. 없으면 docs에서 찾기
    doc = await db["docs"].find_one({"doc_id": doc_id})
    if doc and "sentence_analysis" in doc:
        return doc["sentence_analysis"]
    # 3. 둘 다 없으면 빈 리스트
    return []

# 분석 결과 저장
async def save_analysis(doc_id: str, analysis: List[SentenceAnalysis]):
    await analysis_collection.update_one(
        {"doc_id": doc_id},
        {"$set": {"sentence_analysis": [a.model_dump() for a in analysis]}},
        upsert=True,
    )

# ✅ EXAONE 결과 처리
async def run_exaone(sentences: List[str]) -> List[SentenceAnalysis]:
    print(f"[LOG] EXAONE 요청 문장 목록: {sentences}")
    batch_results = run_exaone_batch(sentences)
    print(f"[LOG] EXAONE 응답: {batch_results}")
    
    results = []
    for idx, (sent, result) in enumerate(zip(sentences, batch_results)):
        print(f"[LOG] 모델 raw 응답 ({idx}): {result}")
        results.append(
            SentenceAnalysis(
                index=idx, # 이 인덱스는 run_exaone_batch 내에서 0부터 다시 시작하므로, 나중에 최종적으로 올바른 인덱스로 업데이트해야 함.
                           # 이 문제는 아래 analyze_document에서 updated_idx_map을 만들 때 해결됩니다.
                text=sent,
                flag=result.get("flag", False),
                label=result.get("label", "문제 없음"),
                highlighted=result.get("highlighted") if isinstance(result.get("highlighted"), list) else [],
                explanation=result.get("explanation") if isinstance(result.get("explanation"), list) else [],
            )
        )
    print(f"[LOG] 파싱된 결과: {results}")
    return results

# 문서 전체 분석
async def analyze_document(doc_id: str, contents: str) -> List[SentenceAnalysis]:
    new_sentences_list = smart_sentence_split(contents)
    
    # 이전 분석 결과를 문장 해시 기준으로 맵핑하여 빠르게 접근
    # `prev`는 SentenceAnalysis 객체의 리스트이므로, dict로 변환할 때 `.text` 속성을 사용
    prev_analysis_map = {hash_sentence(s["text"]): SentenceAnalysis(**s) for s in await get_prev_analysis(doc_id)}
    
    # 새로 분석해야 할 문장들 (원래 인덱스와 텍스트)
    to_analyze_indexed_sentences = []
    
    # 최종 결과를 저장할 리스트 (미리 크기만큼 None으로 초기화하여 순서 보장)
    final_analysis_results = [None] * len(new_sentences_list)
    
    # 1차 순회: 캐시된 결과 사용 또는 분석 대상에 추가
    for idx, new_sent_text in enumerate(new_sentences_list):
        new_sent_hash = hash_sentence(new_sent_text)
        
        if new_sent_hash in prev_analysis_map:
            # 내용이 변경되지 않았으므로 이전 캐시된 결과를 재활용
            cached_analysis = prev_analysis_map[new_sent_hash]
            cached_analysis.index = idx # 캐시된 결과의 인덱스를 현재 위치로 업데이트
            final_analysis_results[idx] = cached_analysis
        else:
            # 새로운 문장이거나 내용이 변경된 문장 -> 분석 대상에 추가
            to_analyze_indexed_sentences.append((idx, new_sent_text))

    # 2차 순회: 변경되거나 새로 추가된 문장만 EXAONE으로 분석
    if to_analyze_indexed_sentences:
        # EXAONE 모델에 보낼 텍스트 리스트
        sentences_for_exaone = [sent_text for _, sent_text in to_analyze_indexed_sentences]
        updated_exaone_results = await run_exaone(sentences_for_exaone)
        
        # 분석 결과를 최종 결과 리스트의 올바른 위치에 삽입
        for i, (original_idx, _) in enumerate(to_analyze_indexed_sentences):
            analyzed_sentence = updated_exaone_results[i]
            analyzed_sentence.index = original_idx # 분석 결과의 인덱스를 원래 위치로 업데이트
            final_analysis_results[original_idx] = analyzed_sentence
    
    # None 값이 남아있으면 오류 (모든 인덱스에 결과가 채워져야 함)
    if any(item is None for item in final_analysis_results):
        print(f"[ERROR] analyze_document: 일부 문장이 처리되지 않았습니다. {final_analysis_results.count(None)}개 누락.", file=sys.stderr)
        # 상황에 따라 예외를 발생시키거나 빈 리스트 반환
        raise RuntimeError("문서 분석 중 예상치 못한 누락 발생.")

    # 최종 결과를 정렬할 필요 없음 (미리 순서대로 채워졌으므로)
    # analysis_results.sort(key=lambda x: x.index) # 제거

    await save_analysis(doc_id, final_analysis_results)
    return final_analysis_results
