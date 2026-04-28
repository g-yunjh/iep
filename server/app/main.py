from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import student, rag
from app.db import models, database

app = FastAPI(title="IEP API", version="1.0.0")

# CORS 설정 (교차 출처)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 테이블 생성
models.Base.metadata.create_all(bind=database.engine)

# 라우터 등록
app.include_router(student.router, prefix="/student", tags=["Student"])
app.include_router(rag.router, prefix="/rag", tags=["RAG"])

@app.get("/")
async def root():
    return {"message": "IEP API Server"}