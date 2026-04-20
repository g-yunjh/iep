## 개발 환경 설정

### 1. Node.js 설치 및 확인
* **권장 버전**: Node.js `v20.14.0` 이상
* **버전 확인**:
```powershell
node -v
```

### 2. 의존성 패키지 설치
* **명령어**: 프로젝트 구동에 필요한 모든 라이브러리(Vue, Tailwind 등) 일괄 설치
```powershell
npm install
```

### 3. 로컬 개발 서버 구동
* **명령어**: 실시간 코드 변경 사항 반영(HMR)을 위한 개발 서버 실행
```powershell
npm run dev
```
* **접속 주소**: `http://localhost:5173`

### 4. 프로젝트 빌드 및 배포
* **명령어**: 운영 환경 배포를 위한 정적 파일 최적화 및 빌드
```powershell
npm run build
```

---

## 📂 주요 디렉토리 구조
* **src/api**: FastAPI 서버와의 통신을 위한 API 호출 함수 관리
* **src/assets**: Tailwind CSS 설정 파일 및 이미지, 폰트 자원
* **src/components**: 대시보드, 가이드 등 재사용 가능한 UI 컴포넌트
* **src/views**: 교사용 IEP 어시스턴트, 학부모용 에듀-내비게이터 등 주요 페이지
* **src/layouts**: 사용자 유형별(교사/학부모) 공통 레이아웃 구성
