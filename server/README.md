### 1. 가상환경 구성 및 활성화
* **가상환경 생성**: `server` 디렉토리 내에서 독립된 개발 환경 구축을 위한 `venv` 모듈 실행
```powershell
python -m venv venv
```
* **활성화 (Windows PowerShell)**: 현재 쉘 세션에 가상환경 적용
```powershell
.\venv\Scripts\activate
```
* **활성화 (Mac/Linux)**: 
```bash
source venv/bin/activate
```

### 2. 의존성 패키지 설치
* **라이브러리 설치**: FastAPI, OpenAI, SQLAlchemy 등 프로젝트 핵심 패키지 일괄 설치
```powershell
pip install -r requirements.txt
```

### 3. 환경 변수 설정 (.env)
* **파일 관리**: `server/` 루트에 `.env` 파일을 생성하여 보안이 필요한 API 키 및 DB 접속 정보 관리
* **필수 항목**:
    * `OPENAI_API_KEY`: Gemini 기반 RAG 시스템 연동용 키
    * `DATABASE_URL`: PostgreSQL 및 벡터 지식 베이스 접속 정보

### 4. 로컬 서버 실행 및 검증
* **FastAPI 구동**: 비동기 통신 지원을 위한 Uvicorn 서버 실행
```powershell
uvicorn app.main:app --reload
```
* **API 문서 확인**: 브라우저를 통해 `http://127.0.0.1:8000/docs` (Swagger UI) 접속 및 엔드포인트 정상 작동 확인

### 서버 디렉토리 구조 요약
* **app/services**: RAG 엔진 및 LLM 프롬프트 로직 배치
* **app/api**: IEP 어시스턴트 및 가이드 생성 엔드포인트 정의
* **data**: 공공데이터 포털 기반 성취기준 및 직업백과 데이터 저장
