# 📁 app/routes/auth.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.services import oauth_google, oauth_kakao, oauth_naver
import os

router = APIRouter()

@router.get("/auth/google")
def auth_google():
    return RedirectResponse(oauth_google.get_google_auth_url())

@router.get("/auth/google/callback")
def auth_google_callback(request: Request):
    code = request.query_params.get("code")
    token = oauth_google.get_google_user_info(code)
    frontend_url = os.getenv("FRONTEND_URL")
    return RedirectResponse(f"{frontend_url}/oauth/callback?token={token}")

@router.get("/auth/kakao")
def auth_kakao():
    return RedirectResponse(oauth_kakao.get_kakao_auth_url())

@router.get("/auth/kakao/callback")
def auth_kakao_callback(request: Request):
    code = request.query_params.get("code")
    token = oauth_kakao.get_kakao_user_info(code)
    frontend_url = os.getenv("FRONTEND_URL")
    return RedirectResponse(f"{frontend_url}/oauth/callback?token={token}")

@router.get("/auth/naver")
def auth_naver():
    return RedirectResponse(oauth_naver.get_naver_auth_url())

@router.get("/auth/naver/callback")
def auth_naver_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    token = oauth_naver.get_naver_user_info(code, state)
    frontend_url = os.getenv("FRONTEND_URL")
    return RedirectResponse(f"{frontend_url}/oauth/callback?token={token}")