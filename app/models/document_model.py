from pydantic import BaseModel
from typing import List, Optional

# 문서 하나를 표현하는 모델 정의
class Document(BaseModel):
    id: str                             # 문서의 고유 ID
    filename: str                       # 파일 이름
    content: Optional[str] = None      # 파일 내용 (없을 수도 있음)