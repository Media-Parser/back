# app/tests/test_trash.py
import pytest

@pytest.mark.asyncio
async def test_trash_api(client, dummy_user):
    """
    휴지통 기능 전체 (조회/복원/전체삭제/개별삭제)
    """
    # 휴지통 목록 조회
    response = await client.get("/trash/", params={"user_id": dummy_user["user_id"]})
    assert response.status_code == 200

    # 없는 문서 복원
    response = await client.post("/trash/restore/nonexistent-doc")
    assert response.status_code in [404, 500]

    # 전체 삭제
    response = await client.delete("/trash/all")
    assert response.status_code == 200

    # 없는 문서 개별 삭제
    response = await client.delete("/trash/nonexistent-doc")
    assert response.status_code in [404, 500]
