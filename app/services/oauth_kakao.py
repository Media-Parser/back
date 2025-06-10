import os
import requests
from urllib.parse import urlencode
from fastapi import HTTPException
from app.core.security import create_jwt_token

KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERINFO_URL = "https://kapi.kakao.com/v2/user/me"

CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

def get_kakao_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
    }
    return f"{KAKAO_AUTH_URL}?{urlencode(params)}"


def get_kakao_user_info(code: str):
    token_data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    token_res = requests.post(KAKAO_TOKEN_URL, data=token_data)
    if not token_res.ok:
        raise HTTPException(status_code=400, detail="카카오 토큰 요청 실패")

    access_token = token_res.json().get("access_token")
    user_res = requests.get(
        KAKAO_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if not user_res.ok:
        raise HTTPException(status_code=400, detail="카카오 사용자 정보 요청 실패")

    data = user_res.json()
    kakao_account = data.get("kakao_account")

    if not kakao_account or not kakao_account.get("email"):
        raise HTTPException(status_code=400, detail="카카오 계정에 이메일이 없습니다.")

    email = kakao_account.get("email")
    return create_jwt_token(email)
