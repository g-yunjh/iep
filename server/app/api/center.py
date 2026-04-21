from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db import models, database
from app.schemas import center as center_schema

router = APIRouter()

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/strategy", response_model=center_schema.StrategyResponse)
async def get_center_strategy(student_id: int, db: Session = Depends(get_db)):
    """
    통합 교육 전략 공유
    - 학생별 센터에서 효과가 좋았던 학습 촉구 방식 히스토리 조회
    """
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    if not student.center:
        raise HTTPException(status_code=404, detail="학생이 등록된 센터가 없습니다.")

    # 해당 센터의 학생 수 계산
    student_count = db.query(models.Student).filter(models.Student.center_id == student.center_id).count()

    return center_schema.StrategyResponse(
        center_name=student.center.name,
        strategies=student.center.strategies,
        student_count=student_count
    )

@router.post("/feedback", response_model=center_schema.Feedback)
async def create_feedback(feedback: center_schema.FeedbackCreate, db: Session = Depends(get_db)):
    """
    센터 치료/학습 결과 등록
    - 학습 수행도, 사용된 스캐폴딩 효과성 피드백
    """
    # 학생 존재 확인
    student = db.query(models.Student).filter(models.Student.id == feedback.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    db_feedback = models.Feedback(
        student_id=feedback.student_id,
        performance=feedback.performance,
        scaffolding_effectiveness=feedback.scaffolding_effectiveness
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

# 추가: 학생 관리 API (가정에서 센터 등록용)
@router.post("/students", response_model=center_schema.Student)
async def create_student(student: center_schema.StudentCreate, db: Session = Depends(get_db)):
    """학생 등록"""
    db_student = models.Student(name=student.name, center_id=student.center_id)
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@router.get("/students", response_model=List[center_schema.Student])
async def get_students(db: Session = Depends(get_db)):
    """전체 학생 목록 조회"""
    students = db.query(models.Student).all()
    return students

@router.put("/students/{student_id}/center", response_model=center_schema.Student)
async def update_student_center(student_id: int, center_id: int, db: Session = Depends(get_db)):
    """학생 센터 변경 (가정에서 센터 등록/변경용)"""
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    center = db.query(models.Center).filter(models.Center.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="센터를 찾을 수 없습니다.")

    student.center_id = center_id
    db.commit()
    db.refresh(student)
    return student

# 추가: 센터 관리 API
@router.post("/centers", response_model=center_schema.Center)
async def create_center(center: center_schema.CenterCreate, db: Session = Depends(get_db)):
    """센터 등록"""
    db_center = models.Center(name=center.name, strategies=center.strategies)
    db.add(db_center)
    db.commit()
    db.refresh(db_center)
    return db_center

@router.get("/centers", response_model=List[center_schema.Center])
async def get_centers(db: Session = Depends(get_db)):
    """전체 센터 목록 조회"""
    centers = db.query(models.Center).all()
    return centers