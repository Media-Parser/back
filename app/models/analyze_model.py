# app/models/analyze_model.py
from typing import List, Optional
from pydantic import BaseModel

class SentenceAnalysis(BaseModel):
    index: int
    text: str
    flag: bool
    highlighted: List[str] = []
    explanation: List[str] = []

class DocumentAnalysisResponse(BaseModel):
    sentences: List[SentenceAnalysis]
