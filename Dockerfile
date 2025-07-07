# ssami-back/Dockerfile
# 1. Python 공식 이미지 사용
FROM python:3.11

# 2. 작업 디렉터리 생성
WORKDIR /app

# 3. 의존성 복사 및 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 4. 소스 전체 복사
COPY . .

# 5. 환경변수 설정 (예시, 필요시)
# ENV YOUR_ENV_VAR=your_value

# 6. FastAPI 실행 (Uvicorn)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
