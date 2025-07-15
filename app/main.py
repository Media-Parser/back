# 📁 app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.core.config import settings

load_dotenv()

from app.routes import auth, documents, trash, user, category, chat, ai, analyze

app = FastAPI()

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
app.include_router(ai.router)
app.include_router(analyze.router)
