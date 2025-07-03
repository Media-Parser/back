# app/tests/test_trash.py
import pytest

@pytest.mark.asyncio
async def test_trash_flow(client, dummy_user, auth_headers):
    print("\n=== [휴지통 API 테스트 시작] ===")
    headers = auth_headers(dummy_user["user_id"])

    # 1. 문서 목록 조회 (빈 경우도 가능)
    res = await client.get("/trash/", params={"user_id": dummy_user["user_id"]}, headers=headers)
    print("휴지통 목록 조회 응답:", res.status_code, res.json())
    assert res.status_code == 200
    doc_list = res.json()
    if doc_list:
        doc_id = doc_list[0]["doc_id"]
    else:
        doc_id = None

    # 2. (선택) 존재할 경우 복원 테스트
    if doc_id:
        res = await client.post(f"/trash/restore/{doc_id}", headers=headers)
        print("휴지통 복원 응답:", res.status_code, res.json())
        assert res.status_code in [200, 404]

    # 3. 전체 삭제 (휴지통 비우기)
    res = await client.delete("/trash/all", headers=headers)
    print("휴지통 전체 삭제 응답:", res.status_code, res.json())
    assert res.status_code == 200

    # 4. 개별 삭제 (임의의 ID 사용)
    res = await client.delete("/trash/some_invalid_id", headers=headers)
    print("휴지통 개별 삭제 응답:", res.status_code, res.json())
    assert res.status_code in [200, 404, 500]
    print("=== [휴지통 API 테스트 끝] ===\n")