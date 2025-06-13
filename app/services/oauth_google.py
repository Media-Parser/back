# 📁 app/services/oauth_google.py
import os
import requests
from urllib.parse import urlencode
from fastapi import HTTPException
from app.core.security import create_jwt_token
from app.services.user_service import find_user_by_email_provider, find_or_create_user, generate_user_id

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

def get_google_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

async def get_google_user_info(code: str):
    token_data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    token_res = requests.post(GOOGLE_TOKEN_URL, data=token_data)
    if not token_res.ok:
        raise HTTPException(status_code=400, detail="Failed to fetch token from Google")
    token_json = token_res.json()
    access_token = token_json.get("access_token")
    user_res = requests.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if not user_res.ok:
        raise HTTPException(status_code=400, detail="Failed to fetch user info")

    user_data = user_res.json()
    user_email = user_data.get("email")
    user_name = user_data.get("name")
    provider = "google"

    # 1. 기존 이메일로 유저 검색 (이미 있으면 기존 user_id 사용)
    user = await find_user_by_email_provider(user_email, provider)
    if user:
        user_id = user.user_id
    else:
        user_id = generate_user_id()
        user = await find_or_create_user(user_id, user_name, user_email, provider)

    jwt_token = create_jwt_token(user_id)
    return user, jwt_token
