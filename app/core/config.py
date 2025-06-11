# app/core/config.py
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

class Settings:
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
    FRONTEND_URL = os.getenv("FRONTEND_URL")
    SECRET_KEY = os.getenv("SECRET_KEY", "ssami-secret")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", True)
    CORS_ALLOW_METHODS = os.getenv("CORS_ALLOW_METHODS", ["*"])
    CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", ["*"])

settings = Settings()