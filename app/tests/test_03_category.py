# app/tests/test_category.py
import pytest

@pytest.mark.asyncio
async def test_category_crud(client, dummy_user, auth_headers):
    print("\n=== [카테고리 API 테스트 시작] ===")
    headers = auth_headers(dummy_user["user_id"])

    # 1. 카테고리 생성
    res = await client.post("/categories/", json={"user_id": dummy_user["user_id"], "label": "테스트카테고리"}, headers=headers)
    print("카테고리 생성 응답:", res.status_code, res.json())
    assert res.status_code == 200
    category = res.json()
    category_id = category.get("category_id")

    # 2. 카테고리 전체 조회
    res = await client.get(f"/categories/", params={"user_id": dummy_user["user_id"]}, headers=headers)
    print("카테고리 전체 조회 응답:", res.status_code, res.json())
    assert res.status_code == 200

    # 3. 카테고리 수정
    if category_id:
        res = await client.patch(f"/categories/{category_id}", json={"label": "수정된카테고리"}, headers=headers)
        print("카테고리 수정 응답:", res.status_code, res.json())
        assert res.status_code == 200

    # 4. 카테고리 삭제
    if category_id:
        res = await client.delete(f"/categories/{category_id}", headers=headers)
        print("카테고리 삭제 응답:", res.status_code)
        assert res.status_code in [200, 404]
    print("=== [카테고리 API 테스트 끝] ===\n")
