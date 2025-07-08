# 📁 app/core/security.py
import jwt
import os
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("SECRET_KEY")


def create_jwt_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.now() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
