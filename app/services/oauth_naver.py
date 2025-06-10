import os
import requests
from urllib.parse import urlencode
from fastapi import HTTPException
from app.core.security import create_jwt_token

NAVER_AUTH_URL = "https://nid.naver.com/oauth2.0/authorize"
NAVER_TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
NAVER_USERINFO_URL = "https://openapi.naver.com/v1/nid/me"

CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
REDIRECT_URI = os.getenv("NAVER_REDIRECT_URI")


def get_naver_auth_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": "random_state_123",  # CSRF 방지를 위한 값 (실제로는 더 안전하게 관리)
    }
    return f"{NAVER_AUTH_URL}?{urlencode(params)}"


def get_naver_user_info(code: str, state: str):
    token_params = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "state": state
    }
    token_res = requests.post(NAVER_TOKEN_URL, params=token_params)
    if not token_res.ok:
        raise HTTPException(status_code=400, detail="Failed to get token from Naver")

    access_token = token_res.json().get("access_token")
    user_res = requests.get(
        NAVER_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if not user_res.ok:
        raise HTTPException(status_code=400, detail="Failed to get user info from Naver")

    user_data = user_res.json().get("response")
    email = user_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided")

    return create_jwt_token(email)
