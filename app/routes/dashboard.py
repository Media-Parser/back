from fastapi import APIRouter, UploadFile, HTTPException # FastAPI에서 라우팅 기능(APIRouter), 파일 업로드(UploadFile), 에러 처리(HTTPException)를 불러옴

from fastapi.responses import FileResponse # 파일 다운로드 응답을 위한 FileResponse 클래스를 불러옴 (현재 코드는 사용 안 하지만 import만 되어 있음)
from app.services import load_doc_by_user # 문서 저장/조회/삭제 기능이 담긴 서비스 로직을 불러옴

from app.models.document_model import Document # 응답 모델로 사용할 Document 데이터 구조를 불러옴
from typing import List # 타입 힌팅을 위한 List 불러옴 (ex. List[Document])

# 라우터 생성
router = APIRouter()

# 문서 업로드 API (POST 요청)
@router.post("/documents", response_model=Document)
def upload_file(file: UploadFile):  #?? 이부분 API명세서랑 똑같이 해야하는지 집에서체크해보기
    return load_doc_by_user.save_file(file)  # 업로드된 파일을 document_service에 전달하여 저장하고 결과 반환

# 저장된 문서 목록을 조회하는 API (GET 요청)
@router.get("/documents", response_model=List[Document])
def get_documents():
    return load_doc_by_user.get_all_documents() # 모든 문서를 리스트 형태로 반환

# 특정 문서를 다운로드하는 API (GET 요청)
@router.get("/documents/{document_id}/download")
def download_document(document_id: str):
    doc = load_doc_by_user.get_document_file(document_id)  # 주어진 ID에 해당하는 문서를 서비스에서 가져옴
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")  # 문서가 존재하지 않으면 404 에러 반환
    return {"filename": doc["filename"], "content": doc["content"]}  # 문서가 존재하면 파일명과 내용을 JSON 형태로 반환

# 특정 문서를 삭제하는 API (DELETE 요청)
@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    result = load_doc_by_user.delete_document(document_id)    # 문서를 삭제 시도
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")    # 삭제할 문서가 없으면 404 에러 반환
    return {"message": "Document deleted"}     # 삭제 성공 시 메시지 반환