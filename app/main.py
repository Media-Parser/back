# 📁 app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.core.config import settings
from app.services.exaone_client import load_dependencies
import sys

load_dotenv()

from app.routes import auth, documents, trash, user, category, chat, analyze

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    print("[INFO] FastAPI 애플리케이션 시작: 의존성 로딩...")
    try:
        load_dependencies()
        print("[INFO] EXAONE 클라이언트 의존성 로드 완료.")
    except Exception as e:
        print(f"[CRITICAL] 애플리케이션 시작 실패: {e}", file=sys.stderr)
        # 실제 운영 환경에서는 여기에서 애플리케이션 종료를 고려할 수 있음
        # raise
        
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # allow_origins=["*"],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(trash.router)
app.include_router(user.router)
app.include_router(category.router)
app.include_router(chat.router)
app.include_router(analyze.router)
