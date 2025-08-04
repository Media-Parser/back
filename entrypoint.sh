#!/bin/bash

echo "📦 패키지 점검 및 설치 중..."

REQUIRED_PYTHON_PACKAGES=("pandas" "torch" "transformers" "scikit-learn" "numpy")

for package in "${REQUIRED_PYTHON_PACKAGES[@]}"
do
  pip show "$package" > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo "🚨 $package 누락됨 → 설치 시도"
    pip install "$package"
  else
    echo "✅ $package 설치됨"
  fi
done

echo "🚀 FastAPI 서버 실행"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
