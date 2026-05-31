import os
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock API Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = BASE_DIR / "fixtures"

# 픽스처 로드 함수 (매번 파일을 새로 읽어 반환하므로 원본 훼손 안 됨 - clone 기능 내장)
def get_fixture(name: str) -> dict:
    file_path = FIXTURES_DIR / f"{name}.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Fixture '{name}.json' not found")

@app.get("/health")
def health_check():
    return {"ok": True, "mode": "fixed-mock"}

# 끝에 슬래시(/)가 있는 경로와 없는 경로 모두 매핑
@app.get("/student")
@app.get("/student/")
def get_student():
    return get_fixture("student")

@app.patch("/student")
@app.patch("/student/")
async def patch_student(request: Request):
    data = get_fixture("student")
    try:
        # req.body가 비어있지 않으면 파싱해서 기존 데이터에 병합 (update)
        body = await request.json()
        data.update(body)
    except Exception:
        pass
    return data

@app.get("/student/progress")
def get_student_progress():
    return get_fixture("student-progress")

@app.delete("/student/feedbacks")
async def delete_student_feedbacks(request: Request):
    progress = get_fixture("student-progress")
    feedbacks = progress.get("feedbacks", [])
    total = len(feedbacks) if isinstance(feedbacks, list) else 0
    
    try:
        body = await request.json()
    except Exception:
        body = {}

    requested_ids = body.get("feedback_ids", [])
    requested = len(requested_ids) if isinstance(requested_ids, list) else 0
    
    delete_all = body.get("delete_all", False)
    deleted = total if delete_all else requested
    
    remaining = 0 if delete_all else max(total - deleted, 0)
    
    return {
        "deleted_count": deleted,
        "remaining_count": remaining
    }

@app.get("/student/school-life")
def get_school_life():
    return get_fixture("school-life")

@app.post("/rag/scaffolding-recommendation")
def post_scaffolding_recommendation():
    return get_fixture("scaffolding-recommendation")

@app.get("/rag/curriculum-subjects")
def get_curriculum_subjects():
    return get_fixture("curriculum-subjects")

@app.get("/rag/curriculum-search")
def get_curriculum_search(query: Optional[str] = None):
    data = get_fixture("curriculum-search")
    if query:
        data["query"] = query
    return data

@app.get("/rag/career-search")
def get_career_search(query: Optional[str] = None):
    data = get_fixture("career-search")
    if query:
        data["query"] = query
    return data

@app.post("/rag/career-recommendation")
def post_career_recommendation():
    return get_fixture("career-recommendation")

# 404 에러 커스텀 핸들링
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    # fixture 파일을 못 찾아서 발생한 404와 라우트를 못 찾은 404 구분
    detail = exc.detail if exc.detail != "Not Found" else "Fixed mock endpoint not found"
    return JSONResponse(
        status_code=404,
        content={
            "detail": detail,
            "method": request.method,
            "path": request.url.path,
        }
    )

if __name__ == "__main__":
    import uvicorn
    # 환경변수 PORT가 있으면 사용하고, 없으면 8000 사용
    port = int(os.getenv("PORT", 8000))
    print(f"Mock API server running at http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)