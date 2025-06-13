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
    cursor = collection.find({"user_id": user_id, "delete_Yn": {"$ne": "y"}})
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs

# 문서 업로드
async def upload_file(file: Doc):
    file_dict = file.model_dump()

    result = await collection.insert_one(file_dict)
    if result.inserted_id:
        return {"message": "Doc registered successfully", "doc_id": file_dict["doc_id"]}
    else:
        return {"message": "Failed to register doc"}

# 문서 다운로드
async def download_file(document_id: str):
    doc = await collection.find_one({"doc_id": document_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

# 문서 삭제
async def delete_file(document_id: str):
    result = await collection.update_one(
        {"doc_id": document_id},
        {"$set": {"delete_Yn": "y"}}
    )
    if result.modified_count > 0:
        return True
    else:
        return False


