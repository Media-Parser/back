import os
import requests
from urllib.parse import urlencode
from fastapi import HTTPException
from app.core.security import create_jwt_token
from app.services.user_service import find_user_by_email_provider, find_or_create_user, generate_user_id

NAVER_AUTH_URL = "https://nid.naver.com/oauth2.0/authorize"
NAVER_TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
NAVER_USERINFO_URL = "https://openapi.naver.com/v1/nid/me"

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI = os.getenv("NAVER_REDIRECT_URI")

def get_naver_auth_url():
    params = {
        "response_type": "code",
        "client_id": NAVER_CLIENT_ID,
        "redirect_uri": NAVER_REDIRECT_URI,
        "state": "RANDOM_STATE_STRING"
    }
    return f"{NAVER_AUTH_URL}?{urlencode(params)}"

async def get_naver_user_info(code: str, state: str):
    token_params = {
        "grant_type": "authorization_code",
        "client_id": NAVER_CLIENT_ID,
        "client_secret": NAVER_CLIENT_SECRET,
        "code": code,
        "state": state
    }
    token_res = requests.post(NAVER_TOKEN_URL, data=token_params)
    if not token_res.ok:
        raise HTTPException(status_code=400, detail="Failed to fetch token from Naver")
    token_json = token_res.json()
    access_token = token_json.get("access_token")
    user_res = requests.get(NAVER_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if not user_res.ok:
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Naver")

    user_data = user_res.json().get("response", {})
    user_email = user_data.get("email") or f"{user_data.get('id')}@naver.com"
    user_name = user_data.get("name") or user_data.get("nickname") or "네이버사용자"
    provider = "naver"

    user = await find_user_by_email_provider(user_email, provider)
    if user:
        user_id = user.user_id
    else:
        user_id = generate_user_id()
        user = await find_or_create_user(user_id, user_name, user_email, provider)

    jwt_token = create_jwt_token(user_id)
    return user, jwt_token
