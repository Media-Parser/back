# app/tests/conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest_asyncio.fixture
async def client():
    # 이전: transport=ASGITransport(app=app, lifespan="auto"),
    # 수정:
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
