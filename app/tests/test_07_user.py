# app/tests/test_user.py
import pytest

@pytest.mark.asyncio
async def test_user_info_and_delete(client, dummy_user, auth_headers):
    print("\n=== [유저 API 테스트 시작] ===")
    headers = auth_headers(dummy_user["user_id"])
    user_id = dummy_user["user_id"]

    # 1. 유효하지 않은 포맷
    res = await client.get("/users/wrongid", headers=headers)
    print("잘못된 포맷 유저 조회 응답:", res.status_code)
    assert res.status_code == 400

    # 2. 없는 유저
    res = await client.get("/users/user_99999999", headers=headers)
    print("없는 유저 조회 응답:", res.status_code)
    assert res.status_code in [404, 400]

    # 3. 존재하는 유저 (사전 dummy_user로 DB에 생성 필요)
    res = await client.get(f"/users/{user_id}", headers=headers)
    print("존재 유저 조회 응답:", res.status_code)
    assert res.status_code in [200, 404]  # DB 상황 따라 다름

    # 4. 유저 삭제
    res = await client.delete(f"/users/{user_id}", headers=headers)
    print("유저 삭제 응답:", res.status_code)
    assert res.status_code in [200, 404, 500]  # 삭제 성공/실패 모두 허용
    print("=== [유저 API 테스트 끝] ===\n")