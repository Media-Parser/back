# app/tests/test_documents.py
import pytest
import io

@pytest.mark.asyncio
async def test_hwpx_upload_and_download(client, dummy_user, auth_headers):
    print("\n=== [문서 업로드/다운로드 테스트 시작] ===")
    headers = auth_headers(dummy_user["user_id"])

    # 파일 업로드
    file_content = b"dummy hwpx file content"
    files = {
        "file": ("test.hwpx", io.BytesIO(file_content), "application/octet-stream")
    }
    data = {"user_id": dummy_user["user_id"], "category_id": ""}
    response = await client.post("/documents/upload/hwpx", files=files, data=data, headers=headers)
    print("파일 업로드 응답:", response.status_code, response.json())
    assert response.status_code == 200
    json_res = response.json()
    assert "doc_id" in json_res
    assert "parse_error" in json_res   # 본문 추출 에러/정상 모두 대응
    doc_id = json_res["doc_id"]

    # 문서 다운로드
    response = await client.get(f"/documents/download/{doc_id}", headers=headers)
    print("파일 다운로드 응답:", response.status_code)
    assert response.status_code == 200
    assert response.content == file_content

    # 없는 문서 다운로드 (정상 에러 반환)
    response = await client.get("/documents/download/invalid_doc_id", headers=headers)
    print("없는 문서 다운로드 응답:", response.status_code)
    assert response.status_code == 404
    print("=== [문서 업로드/다운로드 테스트 끝] ===\n")


@pytest.mark.asyncio
async def test_hwpx_upload_failures(client, dummy_user, auth_headers):
    print("\n=== [파일 업로드 실패 케이스] ===")
    headers = auth_headers(dummy_user["user_id"])
    # 잘못된 확장자
    files = {
        "file": ("test.txt", io.BytesIO(b"not hwpx"), "application/octet-stream")
    }
    data = {"user_id": dummy_user["user_id"]}
    response = await client.post("/documents/upload/hwpx", files=files, data=data, headers=headers)
    print("잘못된 확장자 응답:", response.status_code, response.json())
    assert response.status_code == 400
    assert "Only .hwpx files" in response.json()["detail"]

    # 필수값 누락 (user_id)
    files = {
        "file": ("test.hwpx", io.BytesIO(b"hwpx"), "application/octet-stream")
    }
    response = await client.post("/documents/upload/hwpx", files=files, headers=headers)
    print("user_id 누락 응답:", response.status_code)
    assert response.status_code == 422  # FastAPI의 필수 파라미터 누락
    print("=== [파일 업로드 실패 케이스 끝] ===\n")


@pytest.mark.asyncio
async def test_list_and_delete(client, dummy_user, auth_headers):
    print("\n=== [문서 목록조회/삭제 테스트 시작] ===")
    headers = auth_headers(dummy_user["user_id"])

    # 목록 조회
    response = await client.get("/documents/", params={"user_id": dummy_user["user_id"]}, headers=headers)
    print("목록 조회 응답:", response.status_code)
    assert response.status_code == 200

    # 삭제 (존재하지 않는 문서)
    response = await client.delete("/documents/invalid_doc_id", headers=headers)
    print("존재하지 않는 문서 삭제 응답:", response.status_code)
    assert response.status_code in [404, 500]

    # (옵션) 실제 업로드 후 삭제 테스트
    files = {
        "file": ("test.hwpx", io.BytesIO(b"new hwpx content"), "application/octet-stream")
    }
    data = {"user_id": dummy_user["user_id"], "category_id": ""}
    upload_res = await client.post("/documents/upload/hwpx", files=files, data=data, headers=headers)
    doc_id = upload_res.json()["doc_id"]
    del_res = await client.delete(f"/documents/{doc_id}", headers=headers)
    print("실제 문서 삭제 응답:", del_res.status_code)
    assert del_res.status_code == 200
    print("=== [문서 목록조회/삭제 테스트 끝] ===\n")