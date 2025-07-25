# ✅ app/models/analyze_model.py
from typing import List
from pydantic import BaseModel, Field

class SentenceAnalysis(BaseModel):
    index: int
    text: str
    flag: bool
    label: str
    highlighted: List[str] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list)

class DocumentAnalysisResponse(BaseModel):
    sentences: List[SentenceAnalysis]