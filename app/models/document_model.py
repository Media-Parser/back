# app/models/document_model.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Doc(BaseModel):
    doc_id: str
    user_id: str = Field(...)
    title: str = Field(..., title="문서 제목", min_length=1)  
    contents: str = Field("", description="본문")
    file_type: str
    file_blob: Optional[bytes] = None
    category_id: Optional[str] = Field(default="")
    created_dt: datetime = Field(default_factory=datetime.now)
    updated_dt: Optional[datetime] = None
    delete_yn: Optional[str] =  Field(default="n")