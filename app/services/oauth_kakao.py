import os
import requests
from urllib.parse import urlencode
from fastapi import HTTPException
from app.core.security import create_jwt_token
from app.services.user_service import find_user_by_email_provider, find_or_create_user

KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERINFO_URL = "https://kapi.kakao.com/v2/user/me"

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")  # 없으면 생략 가능

def get_kakao_auth_url():
    params = {
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "response_type": "code"
    }
    return f"{KAKAO_AUTH_URL}?{urlencode(params)}"

async def get_kakao_user_info(code: str):
    token_data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }
    if KAKAO_CLIENT_SECRET:
        token_data["client_secret"] = KAKAO_CLIENT_SECRET

    token_res = requests.post(KAKAO_TOKEN_URL, data=token_data)
    if not token_res.ok:
        raise HTTPException(status_code=400, detail="Failed to fetch token from Kakao")
    token_json = token_res.json()
    access_token = token_json.get("access_token")
    user_res = requests.get(KAKAO_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if not user_res.ok:
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Kakao")

    user_data = user_res.json()
    kakao_account = user_data.get("kakao_account", {})
    profile = kakao_account.get("profile", {})

    user_email = kakao_account.get("email") or f"{user_data.get('id')}@kakao.com"  # email이 필수가 아니어서 대체
    user_name = profile.get("nickname") or "카카오사용자"
    provider = "kakao"

    # 1. 기존 이메일로 유저 검색 (이미 있으면 기존 user_id 사용)
    user = await find_user_by_email_provider(user_email, provider)
    if user:
        user_id = user.user_id
    else:
        user = await find_or_create_user(user_name, user_email, provider)
        user_id = user.user_id

    jwt_token = create_jwt_token(user_id)
    return user, jwt_token
