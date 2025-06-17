# app/models/category_model.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Category(BaseModel):
    category_id: str
    user_id: str
    label: str
    path: str
    created_dt: Optional[datetime] = Field(default_factory=datetime.now)
    updated_dt: Optional[datetime] = None