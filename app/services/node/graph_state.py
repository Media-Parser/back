# service/node/graph_state.py

from typing import List, TypedDict, Optional
from langchain_core.documents import Document

class GraphState(TypedDict):
    question: str
    original_question: str
    plan: Optional[dict]
    documents: List[Document]
    generation: str
    context: str
    retries: int
    doc_id: Optional[str] # ✨ doc_id 필드 추가
    suggestion: Optional[str]
    value_type : str
    apply_title: Optional[str]
    apply_body: Optional[str]

    