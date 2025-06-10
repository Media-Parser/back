# app/models/user.py
# (임시 - 실제 DB 모델로 확장 가능)

class User:
    def __init__(self, email: str, name: str = ""):
        self.email = email
        self.name = name