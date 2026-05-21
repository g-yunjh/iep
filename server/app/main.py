from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api import student, rag
from app.db import models, database
from app.services.rag_service import RAGService

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="IEP API", version="1.0.0")
logger = logging.getLogger(__name__)

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


@app.on_event("startup")
def warmup_rag_runtime():
    """Prime local embeddings/vector store so the first UI request is not slow."""
    try:
        rag_service = RAGService()
        rag_service.search_career("손작업 순서 기억 시각 자료", k=1)
        rag_service.search_curriculum("수학 시각 자료 단계별 지원", subject="수학", k=1)
    except Exception as exc:
        logger.warning("RAG warmup skipped: %s", exc)


@app.get("/")
async def root():
    return {"message": "IEP API Server"}
