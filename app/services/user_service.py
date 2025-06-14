# app/services/user_service.py
from app.models.user import UserInDB
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import uuid
import os

ATLAS_URI = os.getenv("ATLAS_URI")
client = AsyncIOMotorClient(ATLAS_URI)

db = client['uploadedbyusers']
collection = db['users']

async def find_or_create_user(user_id, user_name, user_email, provider):
    # provider+user_email로 유저 구분!
    user = await collection.find_one({"user_email": user_email, "provider": provider})
    if user:
        return UserInDB(**user)
    doc = {
        "user_id": user_id,
        "user_name": user_name,
        "user_email": user_email,
        "provider": provider,
        "create_dt": datetime.utcnow()
    }
    result = await collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return UserInDB(**doc)

async def find_user_by_email_provider(user_email, provider):
    user = await collection.find_one({"user_email": user_email, "provider": provider})
    if user:
        return UserInDB(**user)
    return None

async def find_user_by_id(user_id: str):
    user = await collection.find_one({"user_id": user_id})
    if user:
        return UserInDB(**user)
    return None

def generate_user_id():
    return str(uuid.uuid4())
