from fastapi import UploadFile # FastAPI에서 업로드된 파일을 다룰 수 있는 UploadFile 클래스 불러옴
from typing import List  # 타입 힌트용 List 불러옴 (여기선 사용되진 않지만 다른 데서 쓰일 수 있음) ??
import uuid # 고유한 ID를 생성하기 위한 uuid 모듈 불러옴

# 문서들을 임시로 저장해둘 딕셔너리 ( 진짜 DB 대신 사용하는 가짜 데이터베이스)
fake_document_db = {}

# 파일을 저장하고 문서 정보를 반환하는 함수
def save_file(file: UploadFile):
    doc_id = str(uuid.uuid4())  # 랜덤하고 고유한 문서 ID 생성 (예: '2a8d...f3a')
    content = file.file.read().decode("utf-8", errors="ignore") # 업로드된 파일 내용을 문자열로 읽음 (decode로 바이너리를 텍스트로 변환)
    fake_document_db[doc_id] = {    # 위에서 만든 ID를 키로 해서, 딕셔너리에 문서 정보를 저장
        "id": doc_id, # 문서 고유 ID
        "filename": file.filename, # 원래 파일명 (예: bank_db문제.txt)
        "content": content  # 파일 안의 실제 내용 (텍스트 형태)
        #업로드 시간정보도 추가해야함
        #계정정보(파일을올린 계정)
    }
    return fake_document_db[doc_id]                      # 저장된 문서 내용을 그대로 반환

# 저장된 모든 문서를 리스트 형태로 반환하는 함수
def get_all_documents():
    return list(fake_document_db.values())

# 특정 문서 ID(document_id)에 해당하는 문서를 찾아 반환
def get_document_file(document_id: str): 
    return fake_document_db.get(document_id)

# 특정 문서 ID(document_id)에 해당하는 문서를 삭제하고, 성공 시 그 데이터를 반환
def delete_document(document_id: str):
    return fake_document_db.pop(document_id, None)