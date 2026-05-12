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
* **라이브러리 설치**: FastAPI, Google Gemini(LangChain), SQLAlchemy 등 프로젝트 핵심 패키지 일괄 설치
```powershell
pip install -r requirements.txt
```

### 3. 환경 변수 설정 (.env)
* **파일 관리**: `server/` 루트에 `.env` 파일을 생성하여 보안이 필요한 API 키 및 DB 접속 정보 관리
* **필수 항목**:
    * `GOOGLE_API_KEY` (또는 `GEMINI_API_KEY`): [Google AI Studio](https://aistudio.google.com/apikey)에서 발급한 Gemini API 키
    * `DATABASE_URL`: PostgreSQL 및 벡터 지식 베이스 접속 정보
* **선택 항목**:
    * `GEMINI_CHAT_MODEL`: 대화·분석용 모델 (기본값 `gemini-2.0-flash`)
    * `GEMINI_EMBEDDING_MODEL`: 임베딩 모델 (기본값 `models/text-embedding-004`)
* **벡터 스토어 재구축**: 이전에 OpenAI 임베딩으로 만든 Chroma 데이터는 차원이 달라 호환되지 않습니다. Gemini 전환 후에는 RAG 초기화 API에서 `force_recreate=true`로 스토어를 다시 만들어야 합니다.

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

### 5. 서버 수정사항 요약

이번 작업에서는 프론트엔드 연동과 RAG 추천 기능에서 사용할 수 있도록 `server` 폴더 내 데이터 및 API 구조를 보강했습니다.

* **수학 성취기준 데이터 추가**
    * `server/data/curriculum/math/` 경로에 수학 성취기준 데이터를 영역별로 분리하여 정리했습니다.
    * 영역은 `수와 연산`, `도형`, `측정`, `규칙성`, `자료와 가능성` 기준으로 구성했습니다.
    * 각 JSON 파일은 기존 `example.jsonc` 형식을 유지하여 RAG 검색 및 추천 로직에서 활용할 수 있도록 정리했습니다.

* **국어 성취기준 데이터 추가**
    * `server/data/curriculum/korean/` 경로에 국어 성취기준 데이터를 추가했습니다.
    * `듣기·말하기`, `읽기`, `쓰기` 영역을 분리하여 저장했습니다.
    * 수학 데이터와 동일한 구조를 사용해 과목별 성취기준 검색 방식이 일관되도록 구성했습니다.

* **직업 추천 데이터 추가**
    * `server/data/careers/` 경로에 직업 데이터 배치 파일을 추가했습니다.
    * 학생의 현재 역량과 특성을 기반으로 진로 추천 및 역량 차이 분석에 활용할 수 있도록 구성했습니다.

* **RAG 검색 및 추천 API 보강**
    * 성취기준 검색, 스캐폴딩 추천, 진로 추천 기능에서 과목별·영역별 데이터를 참조할 수 있도록 서버 데이터 구조를 정리했습니다.
    * 프론트엔드의 교사용/학부모용 대시보드에서 호출하는 API 응답 구조와 맞춰 사용할 수 있도록 유지했습니다.

* **민감 정보 및 로컬 파일 제외**
    * 실제 API 키가 포함된 `.env` 파일, SQLite DB 파일, `vector_store`, 가상환경 폴더는 업로드 대상에서 제외합니다.
    * API 키는 `.env.example` 또는 README 안내를 참고해 각자 로컬에서 설정해야 합니다.

