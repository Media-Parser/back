# app/routes/analyze.py

from fastapi import APIRouter, Body
from app.services.gen_model_service import analyze_with_generation
from app.models.analyze_model import SentenceAnalysis, DocumentAnalysisResponse

router = APIRouter(prefix="/analyze", tags=["문서AI분석"])

@router.post("", response_model=DocumentAnalysisResponse)
async def analyze_route(doc_id: str = Body(...), contents: str = Body(...)):
    sentences = contents.strip().split("\n")
    response = []

    for idx, sent in enumerate(sentences):
        parsed = analyze_with_generation(sent)
        if parsed == [{"label": "문제 없음", "highlight": ""}]:
            response.append(SentenceAnalysis(
                index=idx,
                text=sent,
                flag=False,
                label="문제 없음",
                highlighted=[],
                explanation=[]
            ))
        else:
            labels = list(set(p["label"] for p in parsed))
            spans = [p["highlight"] for p in parsed]
            explanation = [f"{p['label']}: {p['highlight']}" for p in parsed]
            response.append(SentenceAnalysis(
                index=idx,
                text=sent,
                flag=True,
                label=", ".join(labels),
                highlighted=spans,
                explanation=explanation
            ))

    return DocumentAnalysisResponse(sentences=response)