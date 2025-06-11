# app/models/document_model.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Doc(BaseModel):
    doc_id: str
    user_id: str = Field(...)
    title: str = Field(..., title="문서 제목", min_length=1)  
    contents: str = Field(..., min_length=1)  
    created_dt: datetime = Field(default_factory=datetime.now)
    updated_dt: datetime = Field(default_factory=datetime.now)
    file_type: str
    category: Optional[str] = Field(default="/")
    delete_Yn: Optional[str] =  Field(default="n")
