# app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

def allow_all_if_asterisk(lst):
    return ["*"] if len(lst) == 1 and lst[0] == "*" else lst

class Settings:
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
    FRONTEND_URL = os.getenv("FRONTEND_URL")
    SECRET_KEY = os.getenv("SECRET_KEY", "ssami-secret")
    ATLAS_URI = os.getenv("ATLAS_URI")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # CORS
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    CORS_ALLOW_METHODS = allow_all_if_asterisk([m.strip() for m in os.getenv("CORS_ALLOW_METHODS", "*").split(",") if m.strip()])
    CORS_ALLOW_HEADERS = allow_all_if_asterisk([h.strip() for h in os.getenv("CORS_ALLOW_HEADERS", "*").split(",") if h.strip()])

settings = Settings()