# app/tests/test_documents.py
import pytest
import io

@pytest.mark.asyncio
async def test_hwpx_upload_and_download(client, dummy_user):
    """
    hwpx 파일 업로드 및 다운로드 테스트
    """
    # 파일 업로드 (성공 케이스)
    file_content = b"dummy hwpx file content"
    files = {
        "file": ("test.hwpx", io.BytesIO(file_content), "application/octet-stream")
    }
    data = {
        "user_id": dummy_user["user_id"],
        "category_id": ""
    }
    # Form 데이터로 요청 (multipart/form-data)
    response = await client.post("/documents/upload/hwpx", files=files, data=data)
    assert response.status_code == 200
    json_res = response.json()
    assert "doc_id" in json_res
    doc_id = json_res["doc_id"]

    # 문서 다운로드 (정상)
    response = await client.get(f"/documents/download/{doc_id}")
    assert response.status_code == 200
    assert response.content == file_content  # 실제 내용이 같아야 함

@pytest.mark.asyncio
async def test_upload_failures(client):
    """
    파일 확장자 오류, 필수값 누락 등 업로드 실패 케이스
    """
    # 잘못된 확장자
    files = {
        "file": ("test.txt", io.BytesIO(b"not hwpx"), "application/octet-stream")
    }
    data = {"user_id": "user_00000001"}
    response = await client.post("/documents/upload/hwpx", files=files, data=data)
    assert response.status_code == 400
    assert "Only .hwpx files" in response.json()["detail"]

    # 필수값 누락 (user_id)
    files = {
        "file": ("test.hwpx", io.BytesIO(b"hwpx"), "application/octet-stream")
    }
    response = await client.post("/documents/upload/hwpx", files=files)
    assert response.status_code == 422  # FastAPI 필수값 누락

@pytest.mark.asyncio
async def test_list_and_delete(client, dummy_user):
    """
    문서 목록 조회, 잘못된 문서 삭제 등
    """
    # 목록 조회 (user_id 필수)
    response = await client.get("/documents/", params={"user_id": dummy_user["user_id"]})
    assert response.status_code == 200
    # 삭제 (존재하지 않는 문서)
    response = await client.delete("/documents/invalid_doc_id")
    assert response.status_code in [404, 500]
