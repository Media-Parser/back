# app/tests/conftest.py

import os
import jwt
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
import pytest_asyncio
import sys
import asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

SECRET_KEY = os.getenv("SECRET_KEY", "ssami-secret")

@pytest_asyncio.fixture(scope="function", autouse=True)
async def patch_mongo(monkeypatch):
    from motor.motor_asyncio import AsyncIOMotorClient
    test_client = AsyncIOMotorClient(os.getenv("ATLAS_URI"))
    test_db = test_client["uploadedbyusers"]

    # document services
    import app.services.document_service as doc_service
    doc_service.collection = test_db["docs"]
    doc_service.temp_collection = test_db["temp_docs"]
    await test_db["docs"].delete_many({})
    await test_db["temp_docs"].delete_many({})

    # category services
    import app.services.category_service as cat_service
    cat_service.collection = test_db["categories"]
    cat_service.doc_collection = test_db["docs"]
    await test_db["categories"].delete_many({})

    # ✅ chat services (추가!)
    import app.services.chat_service as chat_service
    chat_service.collection = test_db["chat_qas"]
    await test_db["chat_qas"].delete_many({})

    yield

    test_client.close()
    await asyncio.sleep(0.1)

# 2. 인증 토큰 헤더
@pytest.fixture
def auth_headers():
    def make_headers(user_id="user_00000004"):
        payload = {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}
    return make_headers

# 3. FastAPI 테스트 클라이언트
@pytest_asyncio.fixture(scope="function")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

# 4. 더미 유저/문서
@pytest.fixture
def dummy_user():
    return {"user_id": "user_00000004", "email": "eotjrdl1594@gmail.com"}

@pytest.fixture
def dummy_doc():
    return {"doc_id": "doc_12345678", "user_id": "user_00000004", "title": "테스트문서", "contents": "테스트 본문"}
