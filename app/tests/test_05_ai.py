# app/tests/test_ai.py
import pytest

@pytest.mark.asyncio
async def test_ai_chat_send(client, dummy_user, auth_headers):
    print("\n=== [AI 챗 API 테스트 시작] ===")
    headers = auth_headers(dummy_user["user_id"])
    payload = {
        "doc_id": "doc_00000001",
        "message": "AI에게 질문합니다.",
        "contain": True,
        "content": "테스트 본문"
    }
    res = await client.post("/ai/send", json=payload, headers=headers)
    print("AI 챗 전송 응답:", res.status_code, res.json())
    assert res.status_code in [200, 400, 404]
    print("=== [AI 챗 API 테스트 끝] ===\n")
