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

# 언어 감지 후 KSS/EN/기타 구분하여 문장 분리
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

ATLAS_URI = Settings.ATLAS_URI
client = AsyncIOMotorClient(ATLAS_URI)
db = client['uploadedbyusers']

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
    await db["temp_docs"].update_one(
        {"doc_id": doc_id},
        {"$set": {"sentence_analysis": [a.model_dump() for a in analysis]}},
        upsert=True,
    )

# EXAONE 결과 처리
async def run_exaone(sentences: List[str]) -> List[SentenceAnalysis]:
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
                highlighted=result.get("highlighted") if isinstance(result.get("highlighted"), list) else [],
                explanation=result.get("explanation") if isinstance(result.get("explanation"), list) else [],
            )
        )
    print(f"[LOG] 파싱된 결과: {results}")
    return results

# 문서 전체 분석
async def analyze_document(doc_id: str, contents: str) -> List[SentenceAnalysis]:
    sentences = smart_sentence_split(contents)
    prev = await get_prev_analysis(doc_id)
    prev_hashes = [hash_sentence(s["text"]) for s in prev]
    new_hashes = [hash_sentence(s) for s in sentences]

    to_analyze = []
    for i, h in enumerate(new_hashes):
        if i >= len(prev_hashes) or h != prev_hashes[i]:
            to_analyze.append((i, sentences[i]))

    updated = await run_exaone([x[1] for x in to_analyze])

    analysis = []
    upd_idx = 0
    for i, s in enumerate(sentences):
        if i < len(prev_hashes) and new_hashes[i] == prev_hashes[i]:
            analysis.append(SentenceAnalysis(**prev[i]))
        else:
            analysis.append(updated[upd_idx])
            upd_idx += 1

    await save_analysis(doc_id, analysis)
    return analysis