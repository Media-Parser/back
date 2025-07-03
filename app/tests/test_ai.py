# app/tests/test_ai.py
import pytest

@pytest.mark.asyncio
async def test_ai_chat_send(client, dummy_doc):
    """
    AI 엔드포인트 테스트 (정상/에러)
    """
    payload = {
        "message": "AI 질문 테스트",
        "doc_id": dummy_doc["doc_id"],
        "contain": True,
        "content": "테스트내용"
    }
    res = await client.post("/chat/send", json=payload)
    assert res.status_code == 200
    assert "answer" in res.json()
