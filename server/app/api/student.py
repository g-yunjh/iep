from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.db.models import Feedback
from app.schemas.rag import StudentProgressResponse
from app.schemas.student import Student, StudentUpdate
import app.services.neis_service as neis_service

router = APIRouter()


@router.get("/school-life", response_model=Dict)
async def get_school_life():
    """
    나이스 Open API 실시간 연동 (급식, 시간표, 학사일정)
    """
    today = datetime.now().strftime("%Y%m%d")
    
    # 1. 급식 정보 (중식)
    lunch_menu = neis_service.get_neis_meal(today)
    
    # 2. 학사 일정 (오늘의 행사)
    today_event = neis_service.get_neis_schedule(today)
    
    # 3. 시간표 및 계산된 하교 시간
    timetable, dismissal = neis_service.get_neis_timetable(today, grade="1", class_nm="1")

    return {
        "lunch_menu": lunch_menu,
        "dismissal_time": dismissal,
        "academic_calendar": today_event,
        "today_timetable": timetable
    }


def _get_or_create_persona_student(db: Session) -> models.Student:
    student = db.query(models.Student).order_by(models.Student.id.asc()).first()
    if student:
        return student

    student = models.Student(name="나의 아이")
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/", response_model=Student)
async def get_student_profile(db: Session = Depends(get_db)):
    """단일 학생(페르소나) 프로필 조회"""
    return _get_or_create_persona_student(db)


@router.patch("/traits", response_model=Student)
async def update_student_traits(traits: StudentUpdate, db: Session = Depends(get_db)):
    """단일 학생(페르소나) 특성 및 수준 업데이트"""
    student = _get_or_create_persona_student(db)

    update_fields = traits.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)
    return student


@router.get("/progress", response_model=StudentProgressResponse)
async def get_student_progress(db: Session = Depends(get_db)):
    """학생 진행 상황 조회 API"""
    try:
        student = _get_or_create_persona_student(db)
        feedbacks = (
            db.query(Feedback)
            .filter(Feedback.student_id == student.id)
            .order_by(Feedback.created_at.asc())
            .all()
        )

        feedback_list = []
        for fb in feedbacks:
            feedback_list.append(
                {
                    "id": fb.id,
                    "performance": fb.performance,
                    "scaffolding_effectiveness": fb.scaffolding_effectiveness,
                    "disability_type": fb.disability_type,
                    "teacher_description": fb.teacher_description,
                    "llm_analysis": fb.llm_analysis,
                    "scaffolding_recommendations": fb.scaffolding_recommendations,
                    "created_at": fb.created_at.isoformat() if fb.created_at else None,
                }
            )

        return StudentProgressResponse(
            feedbacks=feedback_list,
            progress_summary=_generate_progress_summary(feedback_list),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"학생 진행 상황 조회 실패: {str(e)}")


def _generate_progress_summary(feedbacks: List[Dict]) -> str:
    """학생의 진행 상황 요약 생성"""
    if not feedbacks:
        return "아직 피드백 데이터가 없습니다."

    total_feedbacks = len(feedbacks)
    recent_feedbacks = feedbacks[-3:]

    levels = []
    for fb in recent_feedbacks:
        analysis = fb.get("llm_analysis", {})
        if isinstance(analysis, dict):
            level = analysis.get("detected_level")
            if level:
                levels.append(level)

    level_counts = {}
    for level in levels:
        level_counts[level] = level_counts.get(level, 0) + 1

    summary_parts = [f"총 {total_feedbacks}개의 피드백 기록이 있습니다."]

    if level_counts:
        level_names = {"high": "높음", "medium": "중간", "low": "낮음"}
        level_summary = []
        for level, count in level_counts.items():
            korean_level = level_names.get(level, level)
            level_summary.append(f"{korean_level} 수준: {count}회")
        summary_parts.append(f"최근 분석 결과: {', '.join(level_summary)}")

    return " ".join(summary_parts)


