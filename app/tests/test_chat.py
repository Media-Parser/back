# app/tests/test_chat.py
import pytest
import sys

@pytest.mark.skipif(
    sys.platform == "win32" and sys.version_info >= (3, 12),
    reason="motor + pytest-asyncio + Windows + Python 3.12+ event loop bug"
)
async def test_chat_send_and_history(client, dummy_doc):
    """
    챗봇 Q/A 저장, 히스토리, 전체삭제 플로우
    """
    # Q/A 저장
    payload = {
        "message": "챗봇테스트",
        "doc_id": dummy_doc["doc_id"],
        "selected_text": "일부",
        "selected_yn": True
    }
    res = await client.post("/chat/send", json=payload)
    assert res.status_code == 200

    # 히스토리
    res = await client.get(f"/chat/history/{dummy_doc['doc_id']}")
    assert res.status_code == 200

    # 전체 삭제
    res = await client.delete(f"/chat/history/{dummy_doc['doc_id']}")
    assert res.status_code == 200
    assert "deleted_count" in res.json()
