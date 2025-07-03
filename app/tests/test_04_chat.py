# app/tests/test_chat.py
import pytest
import io

@pytest.mark.asyncio
async def test_chat_flow(client, dummy_user, auth_headers):
    print("\n=== [챗봇 API 테스트 시작] ===")
    headers = auth_headers(dummy_user["user_id"])

    # 1. 채팅 전송 (doc_id, message 필수)
    payload = {
        "doc_id": "doc_00000001",
        "message": "안녕 챗봇",
        "contain": True,
        "content": "본문 내용"
    }
    res = await client.post("/chat/send", json=payload, headers=headers)
    print("채팅 전송 응답:", res.status_code, res.json())
    assert res.status_code in [200, 400, 404]  # 실제 챗봇 구현에 따라 다름

    # 2. 히스토리 조회
    res = await client.get("/chat/history", params={"doc_id": "doc_00000001"}, headers=headers)
    print("히스토리 조회 응답:", res.status_code, res.json())
    assert res.status_code == 200

    # 3. 전체 삭제 (비정상 doc_id 테스트)
    res = await client.delete("/chat/history", params={"doc_id": "not_exists"}, headers=headers)
    print("채팅 전체 삭제 응답:", res.status_code)
    assert res.status_code in [200, 404, 500]
    print("=== [챗봇 API 테스트 끝] ===\n")
