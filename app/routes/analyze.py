# app/routes/analyze.py

from fastapi import APIRouter, Body
from app.services.analyze_service import analyze_document
from app.models.analyze_model import DocumentAnalysisResponse

router = APIRouter(prefix="/analyze", tags=["문서AI분석"])

@router.post("/", response_model=DocumentAnalysisResponse)
async def analyze_route(doc_id: str = Body(...), contents: str = Body(...)):
    print(f"[LOG] 분석 요청: doc_id={doc_id}, contents={contents[:200]}...")
    analysis = await analyze_document(doc_id, contents)
    return DocumentAnalysisResponse(sentences=analysis)