# IEP Dual Dashboard

공공데이터와 RAG 기반 AI를 활용한 특수학급 개별화교육(IEP) 지원 플랫폼입니다.  
교사는 학생 관찰 기록을 기반으로 성취기준, 스캐폴딩 전략, 진로 추천을 확인할 수 있고, 학부모는 자녀의 학교생활과 성장 정보를 모바일 중심 UI에서 확인할 수 있습니다.

## 주요 기능

* 교사용 대시보드
  * 학생 현황 요약
  * 스캐폴딩 추천
  * 국어·수학 성취기준 검색
  * 피드백 기록 및 분석
  * 학생 역량 기반 진로 추천

* 학부모용 대시보드
  * 오늘의 학교생활 요약
  * 급식, 시간표, 준비물 정보
  * 학생 특성 확인 및 수정
  * 성장 경로와 진로 추천 확인

* AI/RAG 기능
  * 국어·수학 성취기준 데이터 기반 검색
  * 학생 상태에 맞는 스캐폴딩 전략 추천
  * 직업 데이터 기반 진로 추천
  * Gemini API 기반 분석 및 추천 응답 생성

## 프로젝트 구조

```text
.
├── client/   # Vue 기반 프론트엔드
└── server/   # FastAPI 기반 백엔드
```

## 실행 방법

프론트엔드와 백엔드는 각각 별도로 실행합니다.

### 1. 백엔드 실행

```bash
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell에서는 가상환경을 아래 명령어로 활성화합니다.

```powershell
.\venv\Scripts\activate
```

백엔드 기본 주소:

```text
http://127.0.0.1:8000
```

API 문서:

```text
http://127.0.0.1:8000/docs
```

### 2. 프론트엔드 실행

```bash
cd client
npm install
npm run dev
```

프론트엔드 기본 주소:

```text
http://localhost:5173
```

## 환경 변수

백엔드 실행 전 `server/.env` 파일을 생성해야 합니다.

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_CHAT_MODEL=gemini-2.0-flash
SQLALCHEMY_DATABASE_URL=sqlite:///./iep.db
```

프론트엔드에서 백엔드 주소를 변경하려면 `client/.env` 또는 `client/.env.local`에 아래 값을 설정합니다.

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 세부 문서

* 프론트엔드 상세 설명: `client/README.md`
* 백엔드 상세 설명: `server/README.md`


## 브랜치 작업 안내

이번 프론트엔드 및 데이터 정리 작업은 `client` 브랜치에서 진행합니다.  
`main` 브랜치는 기존 GitHub 원본 상태를 유지하고, 작업 완료 후 Pull Request를 통해 병합합니다.
