# 📁 app/services/oauth_google.py
import os
import requests
from urllib.parse import urlencode
from fastapi import Request, HTTPException
from app.core.security import create_jwt_token

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


def get_google_user_info(code: str):
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
    jwt_token = create_jwt_token(user_data["email"])

    # print("🔍 GOOGLE_CLIENT_ID:", CLIENT_ID)
    # print("🔍 GOOGLE_CLIENT_SECRET:", CLIENT_SECRET)
    # print("🔍 REDIRECT_URI:", REDIRECT_URI)

    return jwt_token
