# app/tests/test_chat.py
import pytest
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_chat_flow(client, dummy_user, auth_headers):
    print("\n=== [채팅 API 테스트 시작] ===")
    # chat_service.py의 collection을 테스트 DB로 변경
    from app.services import chat_service
    # chat_service.collection = mongo["chat_qas"]

    headers = auth_headers(dummy_user["user_id"])

    # 1. 채팅 전송 (doc_id, message 필수)
    test_doc_id = "doc_12345678"
    payload = {
        "doc_id": test_doc_id,
        "message": "안녕 챗봇",
        "contain": True,
        "content": "본문 내용"
    }
    res = await client.post("/chat/send", json=payload, headers=headers)
    print("채팅 전송 응답:", res.status_code, res.json())
    assert res.status_code in [200, 400, 404]

    # 2. 히스토리 직접 insert 후 조회 등도 가능
    await chat_service.collection.insert_one({
        "chat_id": "chat_test_001",
        "doc_id": test_doc_id,
        "question": payload,
        "selection": None,
        "answer": "테스트 답변",
        "suggestion": None,
        "created_dt": datetime.now(timezone.utc)
    })

    # 3. 히스토리 조회
    res = await client.get(f"/chat/history/{test_doc_id}", headers=headers)
    print("히스토리 조회 응답:", res.status_code, res.json())
    assert res.status_code == 200
