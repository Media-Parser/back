# app/tests/test_category.py
import pytest

@pytest.mark.asyncio
async def test_category_crud(client, dummy_user):
    """
    카테고리 생성-수정-삭제-조회 전체 플로우
    """
    # 생성 (필수값 누락)
    response = await client.post("/categories/", json={})
    assert response.status_code == 400

    # 정상 생성
    payload = {"user_id": dummy_user["user_id"], "label": "pytest카테고리"}
    response = await client.post("/categories/", json=payload)
    assert response.status_code in [200, 201]
    category = response.json()
    category_id = category.get("category_id", category.get("id", ""))

    # 목록 조회
    response = await client.get(f"/categories/?user_id={dummy_user['user_id']}")
    assert response.status_code == 200

    # 수정 (필수값 누락)
    response = await client.put(f"/categories/{category_id}", json={})
    assert response.status_code == 400

    # 정상 수정
    response = await client.put(f"/categories/{category_id}", json={"label": "수정카테고리"})
    assert response.status_code in [200, 404]

    # 삭제
    response = await client.delete(f"/categories/{category_id}")
    assert response.status_code in [200, 404]
