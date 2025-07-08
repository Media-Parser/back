# app/tests/test_03_category.py
import pytest
import io

@pytest.mark.asyncio
async def test_category_move(client, dummy_user, auth_headers):
    headers = auth_headers(dummy_user["user_id"])
    # 먼저 테스트용 문서 업로드 (문서 생성 API에 맞게 작성)
    file_content = b"test file"
    files = {
        "file": ("test.hwpx", io.BytesIO(file_content), "application/octet-stream")
    }
    data = {"user_id": dummy_user["user_id"], "category_id": ""}
    upload_res = await client.post("/documents/upload/hwpx", files=files, data=data, headers=headers)
    doc_id = upload_res.json()["doc_id"]

    # 테스트용 카테고리 생성
    res = await client.post("/categories/", json={
        "user_id": dummy_user["user_id"],
        "label": "이동테스트카테고리"
    }, headers=headers)
    category_id = res.json()["category_id"]

    # 문서 카테고리 이동
    res = await client.post(f"/categories/move/{doc_id}", json={
        "category_id": category_id
    }, headers=headers)
    print("문서 카테고리 이동 응답:", res.status_code, res.json())
    assert res.status_code == 200
    assert res.json()["success"] is True

@pytest.mark.asyncio
async def test_category_crud(client, dummy_user, auth_headers):
    print("\n=== [카테고리 API 테스트 시작] ===")
    headers = auth_headers(dummy_user["user_id"])

    # 1. 카테고리 생성
    res = await client.post("/categories/", json={
        "user_id": dummy_user["user_id"],
        "label": "테스트카테고리"
    }, headers=headers)
    print("카테고리 생성 응답:", res.status_code, res.json())
    assert res.status_code == 200
    category = res.json()
    category_id = category.get("category_id")

    # 2. 카테고리 전체 조회
    res = await client.get("/categories/", params={"user_id": dummy_user["user_id"]}, headers=headers)
    print("카테고리 전체 조회 응답:", res.status_code, res.json())
    assert res.status_code == 200

    # 3. 카테고리 수정 (PUT)
    if category_id:
        res = await client.put(f"/categories/{category_id}", json={
            "label": "수정된카테고리"
        }, headers=headers)
        print("카테고리 수정 응답:", res.status_code, res.json())
        assert res.status_code == 200
        assert res.json()["label"] == "수정된카테고리"

    # 4. 카테고리 삭제 (DELETE)
    if category_id:
        res = await client.delete(f"/categories/{category_id}", headers=headers)
        print("카테고리 삭제 응답:", res.status_code, res.json())
        assert res.status_code == 200
        assert res.json()["success"] is True

    print("=== [카테고리 API 테스트 끝] ===\n")