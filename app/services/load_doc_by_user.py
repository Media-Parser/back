from fastapi import UploadFile # FastAPI에서 업로드된 파일을 다룰 수 있는 UploadFile 클래스 불러옴
from typing import List, Optional  # 타입 힌트용 List와 Optional 불러옴 (여기선 사용되진 않지만 다른 데서 쓰일 수 있음) ??
import uuid # 고유한 ID를 생성하기 위한 uuid 모듈 불러옴
import os
from pymongo import MongoClient
from datetime import datetime  
from pydantic import BaseModel, Field

ATLAS_URI = os.getenv("ATLAS_URI")
client = MongoClient(ATLAS_URI)

db = client['uploadedbyusers'] # Database name, equivalent to "use mydb"
collection = db['docs'] # Collection(Table) name

class Doc(BaseModel):
    doc_id: str
    user_id: str = Field(...)
    title: str = Field(..., title="문서 제목", min_length=1)  
    contents: str = Field(..., min_length=1)  
    created_dt: datetime = Field(default=datetime.now())
    updated_dt: datetime = Field(default=datetime.now())
    file_type: str
    category: Optional[str] = Field(default="/")
    delete_Yn: Optional[str] =  Field(default="n")


# 파일을 저장하고 문서 정보를 반환하는 함수
def create_file(file: Doc):
    file_dict = file.model_dump()  # Pydantic 모델을 dict로 변환 (dict() deprecated) 

    result = collection.insert_one(file_dict)
    print("Insert result:", result.inserted_id)  # 로그 추가

    if result.inserted_id:
        return {"message": "Doc registered successfully", "doc_id": file_dict["doc_id"]}
    else:
        return {"message": "Failed to register doc"}


# 저장된 모든 문서를 리스트 형태로 반환하는 함수
def get_all_documents():
    docs = list(collection.find())
    for doc in docs:
        doc["_id"] = str(doc["_id"])  # ObjectId를 문자열로 변환
    return docs

# 특정 문서 ID(document_id)에 해당하는 문서를 찾아 반환
def get_document_file(document_id: str): 
    doc = collection.find_one({"doc_id": document_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

# 특정 문서 ID(document_id)에 해당하는 문서를 삭제하고, 성공 시 그 데이터를 반환
def delete_document(document_id: str):
    doc = collection.find_one_and_delete({"doc_id": document_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


# Update_document 추가 해야함