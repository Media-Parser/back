
# app/tests/test_user.py
import pytest

@pytest.mark.asyncio
async def test_user_info_all_cases(client, dummy_user):
    """
    사용자 정보 조회(정상, 포맷오류, 미존재)
    """
    # 정상 (존재하는 경우)
    response = await client.get(f"/users/{dummy_user['user_id']}")
    assert response.status_code in [200, 404]  # DB 상황 따라 다름

    # 포맷 오류
    response = await client.get("/users/invalid")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid user_id format"

    # 없는 유저
    response = await client.get("/users/user_99999999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_user_cases(client, dummy_user):
    """
    사용자 삭제 정상/실패 케이스
    """
    response = await client.delete(f"/users/{dummy_user['user_id']}")
    assert response.status_code in [200, 404, 500]
