from typing import List, TypedDict, Optional
from langchain_core.documents import Document

class GraphState(TypedDict):
    question: str
    original_question: Optional[str]
    plan: Optional[dict]
    documents: List[Document]
    selected_text: Optional[str]
    use_full_document: Optional[bool]
    generation: str
    context: Optional[str]
    retries: int
    doc_id: Optional[str]
    suggestion: Optional[str]
    apply_title: Optional[str]
    apply_body: Optional[str]
