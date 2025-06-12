# app/services/document_service.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.document_model import Doc

ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)

db = client['uploadedbyusers']
collection = db['docs']

# 유저별 문서 조회
async def get_documents(user_id: str):
    docs = []
    cursor = collection.find({"user_id": user_id})
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs

async def create_file(file: Doc):
    file_dict = file.model_dump()
    result = collection.insert_one(file_dict)
    if result.inserted_id:
        return {"message": "Doc registered successfully", "doc_id": file_dict["doc_id"]}
    else:
        return {"message": "Failed to register doc"}

async def get_all_documents():
    docs = list(collection.find())
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs

async def get_document_file(document_id: str):
    doc = collection.find_one({"doc_id": document_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

async def delete_document(document_id: str):
    doc = collection.find_one_and_delete({"doc_id": document_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

# update_document 같은 추가 함수도 여기에 작성
