# ssami-back

## 개요
ssami-back은 AI 기반의 문서 분석 및 처리 시스템의 백엔드 서버입니다. FastAPI를 기반으로 구축되어 있으며, 다양한 AI 서비스와 문서 처리 기능을 제공합니다.

## 프로젝트 구조
```
ssami-back/
├── app/                     # FastAPI 애플리케이션 코드
│   ├── core/               # 핵심 설정 및 유틸리티
│   ├── models/             # Pydantic 모델 정의
│   ├── routes/             # API 라우트 정의
│   ├── services/           # 비즈니스 로직 구현
│   │   ├── ai_service.py   # AI 관련 서비스
│   │   ├── analyze_service.py # 문서 분석 서비스
│   │   ├── document_service.py # 문서 처리 서비스
│   │   ├── user_service.py  # 사용자 관리 서비스
│   │   ├── chat_service.py  # 채팅 관련 서비스
│   │   ├── category_service.py # 카테고리 관리 서비스
│   │   ├── oauth_*.py      # OAuth 인증 서비스
│   │   └── node/          # Node.js 관련 서비스
│   ├── utils/              # 유틸리티 함수들
│   └── tests/              # 테스트 코드
├── chroma_db_*            # 벡터 스토어 데이터베이스
└── requirements.txt       # Python 패키지 의존성
```

## 주요 서비스

### AI 서비스
- `ai_service.py`: AI 관련 기능 제공
- `analyze_service.py`: 문서 분석 및 처리
- `doc_topic.py`: 문서 토픽 분석

### 문서 처리 서비스
- `document_service.py`: 문서 처리 및 관리
- `hwp_extractor.py`: HWP 파일 처리
- `hwpx_extractor.py`: HWPX 파일 처리
- `trash_service.py`: 문서 관리

### 사용자 서비스
- `user_service.py`: 사용자 관리
- `oauth_google.py`: Google OAuth
- `oauth_kakao.py`: Kakao OAuth
- `oauth_naver.py`: Naver OAuth

### 분석 서비스
- `category_service.py`: 카테고리 관리
- `chat_service.py`: 채팅 기능
- `exaone_client.py`: 외부 API 클라이언트

## 설치 및 실행
```bash
# 패키지 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Docker를 통한 실행
docker build -t ssami-back .
docker run -p 8000:8000 ssami-back
```

## API 문서
API 문서는 Swagger UI를 통해 확인할 수 있습니다:
- http://localhost:8000/docs
- http://localhost:8000/redoc

## 기술 스택
- **Backend**: FastAPI
- **AI/ML**: BERTopic, LangChain, OpenAI
- **NLP**: KoNLPy, MeCab
- **문서 처리**: HWP/HWPX
- **인증**: OAuth (Google, Kakao, Naver)
- **Container**: Docker

## 라이선스
MIT License
