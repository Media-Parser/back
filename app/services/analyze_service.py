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
import sys # sys 모듈 임포트 추가

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
                # run_exaone_batch의 결과를 SentenceAnalysis로 매핑
                # 이 단계의 index는 batch_results 내에서의 순서 (0부터 시작)
                # 최종 index는 analyze_document에서 다시 설정됨
                index=idx, 
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
    print(f"[LOG] 문서 분석 시작: doc_id={doc_id}, contents 길이={len(contents)}") # ✅ 추가
    
    # 1. 새로운 문장 리스트로 분리
    new_sentences_list = smart_sentence_split(contents)
    print(f"[LOG] 분리된 새 문장 수: {len(new_sentences_list)}") # ✅ 추가
    
    # 2. 이전 분석 결과 가져오기 및 해시 맵 생성
    # SentenceAnalysis 객체를 딕셔너리로 변환할 때 `.model_dump()` 대신 직접 키-값을 가져오는 것이 더 안정적
    prev_analysis_raw = await get_prev_analysis(doc_id)
    prev_analysis_map = {}
    for s_dict in prev_analysis_raw:
        if "text" in s_dict:
            try:
                # DB에서 가져온 딕셔너리를 다시 SentenceAnalysis 객체로 만들어 캐시
                sa_obj = SentenceAnalysis(**s_dict)
                prev_analysis_map[hash_sentence(sa_obj.text)] = sa_obj
            except Exception as e:
                print(f"[ERROR] 캐시된 문장 데이터 로드 오류: {s_dict}, 오류: {e}", file=sys.stderr)
                continue
    print(f"[LOG] 캐시된 이전 문장 수: {len(prev_analysis_map)}") # ✅ 추가
    
    # 3. 최종 결과를 저장할 리스트 (미리 크기만큼 None으로 초기화하여 순서 보장)
    final_analysis_results = [None] * len(new_sentences_list)
    
    # 4. 새로 분석해야 할 문장들 (원래 인덱스와 텍스트)
    to_analyze_indexed_sentences = []
    
    # 5. 1차 순회: 캐시된 결과 사용 또는 분석 대상에 추가
    for idx, new_sent_text in enumerate(new_sentences_list):
        new_sent_hash = hash_sentence(new_sent_text)
        
        cached_analysis = prev_analysis_map.get(new_sent_hash) # 해시로 직접 찾기
        
        if cached_analysis: # 캐시된 결과가 존재하고 해시가 일치하면 재활용
            # 내용이 변경되지 않았으므로 이전 캐시된 결과를 재활용
            # 주의: 캐시된 객체를 직접 수정하면 다음 맵 조회가 영향을 받을 수 있으므로, 복사본을 사용하는 것이 안전
            reused_analysis = cached_analysis.model_copy() # Pydantic v2 .model_copy()
            reused_analysis.index = idx # 캐시된 결과의 인덱스를 현재 위치로 업데이트
            final_analysis_results[idx] = reused_analysis
            print(f"[DEBUG] 재활용된 문장: {idx}") 
        else:
            # 새로운 문장이거나 내용이 변경된 문장 -> 분석 대상에 추가
            to_analyze_indexed_sentences.append((idx, new_sent_text))
            print(f"[DEBUG] 분석 대상 문장: {idx}") 

    print(f"[LOG] 재분석이 필요한 문장 수: {len(to_analyze_indexed_sentences)}") # ✅ 추가

    # 6. 2차 순회: 변경되거나 새로 추가된 문장만 EXAONE으로 분석
    if to_analyze_indexed_sentences:
        # EXAONE 모델에 보낼 텍스트 리스트
        sentences_for_exaone = [sent_text for _, sent_text in to_analyze_indexed_sentences]
        updated_exaone_results = await run_exaone(sentences_for_exaone)
        
        # 분석 결과를 최종 결과 리스트의 올바른 위치에 삽입
        for i, (original_idx, _) in enumerate(to_analyze_indexed_sentences):
            analyzed_sentence = updated_exaone_results[i]
            analyzed_sentence.index = original_idx # 분석 결과의 인덱스를 원래 위치로 업데이트
            final_analysis_results[original_idx] = analyzed_sentence
    
    # 7. None 값이 남아있으면 오류 (모든 인덱스에 결과가 채워져야 함)
    if any(item is None for item in final_analysis_results):
        print(f"[ERROR] analyze_document: 일부 문장이 처리되지 않았습니다. {final_analysis_results.count(None)}개 누락.", file=sys.stderr)
        # 상황에 따라 예외를 발생시키거나 빈 리스트 반환
        raise RuntimeError("문서 분석 중 예상치 못한 누락 발생: 모든 문장이 처리되지 않았습니다.")

    # 8. 최종 결과 저장
    await save_analysis(doc_id, final_analysis_results)
    print(f"[LOG] 문서 분석 완료 및 결과 저장. 최종 문장 수: {len(final_analysis_results)}") # ✅ 추가
    return final_analysis_results
