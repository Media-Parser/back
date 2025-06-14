# 📁 app/routes/auth.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.services import oauth_google, oauth_kakao, oauth_naver
import os

router = APIRouter()

# Google OAuth 인증
@router.get("/auth/google")
def auth_google():
    return RedirectResponse(oauth_google.get_google_auth_url())

# Google OAuth Callback
@router.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    code = request.query_params.get("code")
    user, token = await oauth_google.get_google_user_info(code) 
    frontend_url = os.getenv("FRONTEND_URL")
    # 로그인 성공 후 user_id, token을 쿼리 파라미터로 프론트에 리다이렉트
    return RedirectResponse(f"{frontend_url}/oauth/callback?token={token}&user_id={user.user_id}")

# Kakao OAuth 인증
@router.get("/auth/kakao")
def auth_kakao():
    return RedirectResponse(oauth_kakao.get_kakao_auth_url())

# Kakao OAuth Callback
@router.get("/auth/kakao/callback")
async def auth_kakao_callback(request: Request):
    code = request.query_params.get("code")
    user, token = await oauth_kakao.get_kakao_user_info(code)
    frontend_url = os.getenv("FRONTEND_URL")
    return RedirectResponse(f"{frontend_url}/oauth/callback?token={token}&user_id={user.user_id}")

# Naver OAuth 인증
@router.get("/auth/naver")
def auth_naver():
    return RedirectResponse(oauth_naver.get_naver_auth_url())

# Naver OAuth Callback
@router.get("/auth/naver/callback")
async def auth_naver_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    user, token = await oauth_naver.get_naver_user_info(code, state)
    frontend_url = os.getenv("FRONTEND_URL")
    return RedirectResponse(f"{frontend_url}/oauth/callback?token={token}&user_id={user.user_id}")