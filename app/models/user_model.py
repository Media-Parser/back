# app/models/user_model.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserInDB(BaseModel):
    user_id: str
    user_name: str
    user_email: EmailStr
    provider: str
    create_dt: Optional[datetime] = None