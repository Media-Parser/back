# app/tests/conftest.py

import pytest
import os
import jwt
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
import pytest_asyncio

SECRET_KEY = os.getenv("SECRET_KEY", "ssami-secret")

@pytest.fixture
def auth_headers():
    def make_headers(user_id="user_00000001"):
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}
    return make_headers

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

@pytest.fixture
def dummy_user():
    return {"user_id": "user_00000001", "email": "dummy@test.com"}

@pytest.fixture
def dummy_doc():
    return {"doc_id": "doc_12345678", "user_id": "user_00000001", "title": "테스트문서", "contents": "테스트 본문"}
