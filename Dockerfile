# ssami/ssami-back/Dockerfile

FROM python:3.10

# Java 설치
RUN apt-get update && \
    apt-get install -y default-jdk && \
    apt-get clean

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

WORKDIR /app

# pip 업그레이드 및 multipart 제거
RUN pip install --upgrade pip && pip uninstall -y multipart || true

# requirements.txt 복사 및 설치
COPY ssami/ssami-back/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 백엔드 코드 복사
COPY ssami/ssami-back/ ./

# ✅ 컨테이너 루트 경로에 finetune 복사
COPY finetune/ /finetune

# ✅ 컨테이너 루트 경로에 ai 복사
COPY ai/ /ai

# entrypoint 복사 및 권한 설정
COPY ssami/ssami-back/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]