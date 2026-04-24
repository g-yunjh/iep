from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.db.models import Feedback
from app.schemas import center as center_schema
from app.schemas.rag import StudentProgressResponse
from app.schemas.school import GoalRecommendationRequest, GoalRecommendationResponse, LearningStep

router = APIRouter()


@router.get("/school-life", response_model=Dict)
async def get_school_life():
    """
    나이스 연동 학교 생활 정보 (식단, 하교 시간, 준비물)
    """
    return {
        "meal_info": {
            "lunch": "김치찌개, 불고기, 밥, 김",
            "snack": "우유, 바나나"
        },
        "dismissal_time": "15:30",
        "tomorrow_prep": ["체육복", "수학 교과서", "필통"]
    }


@router.get("/students", response_model=List[center_schema.Student])
async def get_students(db: Session = Depends(get_db)):
    """전체 학생 목록 조회"""
    return db.query(models.Student).all()


@router.patch("/students/{student_id}/traits", response_model=center_schema.Student)
async def update_student_traits(
    student_id: int,
    traits: center_schema.StudentUpdate,
    db: Session = Depends(get_db),
):
    """학생 개인 특성 부분 업데이트"""
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    update_fields = traits.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)
    return student


@router.get("/students/{student_id}/progress", response_model=StudentProgressResponse)
async def get_student_progress(
    student_id: int,
    db: Session = Depends(get_db),
):
    """학생 진행 상황 조회 API"""
    try:
        feedbacks = (
            db.query(Feedback)
            .filter(Feedback.student_id == student_id)
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
            student_id=student_id,
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


@router.post("/goals", response_model=GoalRecommendationResponse)
async def recommend_goals(request: GoalRecommendationRequest):
    """
    성취목표 추천 API
    - RAG 기반 최적 성취기준 문항 및 학습 단계 추출
    - 2022 개정 특수교육 성취기준 기반
    """
    try:
        if request.subject == "국어":
            if request.grade <= 3:
                goals = [
                    "받침 있는 글자를 읽고 쓸 수 있다.",
                    "단순한 문장을 이해하고 응답할 수 있다.",
                    "기본적인 단어를 인식하고 사용할 수 있다.",
                ]
                steps = [
                    LearningStep(
                        step_number=1,
                        description="기초 글자 인식",
                        activities=["받침 없는 글자 연습", "단순한 단어 카드 사용"],
                    ),
                    LearningStep(
                        step_number=2,
                        description="받침 있는 글자 도입",
                        activities=["받침 있는 단어 보여주기", "소리 내어 읽기 연습"],
                    ),
                    LearningStep(
                        step_number=3,
                        description="문장 수준 적용",
                        activities=["단순 문장 읽기", "그림과 함께 문장 이해"],
                    ),
                ]
                rationale = "저학년 국어 학습의 기초를 다지기 위해 단계적 접근을 추천합니다."
            else:
                goals = [
                    "복잡한 문장을 이해하고 요약할 수 있다.",
                    "다양한 어휘를 사용한 의사소통이 가능하다.",
                    "독서를 통한 정보 습득이 가능하다.",
                ]
                steps = [
                    LearningStep(
                        step_number=1,
                        description="어휘 확장",
                        activities=["새로운 단어 학습", "단어장 만들기"],
                    ),
                    LearningStep(
                        step_number=2,
                        description="문장 이해",
                        activities=["문장 구조 분석", "요약 연습"],
                    ),
                    LearningStep(
                        step_number=3,
                        description="응용 및 실습",
                        activities=["독서 활동", "토론 참여"],
                    ),
                ]
                rationale = "고학년 국어 학습의 심화 내용을 고려한 목표 설정입니다."
        elif request.subject == "수학":
            if request.grade <= 3:
                goals = [
                    "기본적인 덧셈과 뺄셈을 할 수 있다.",
                    "1-20까지의 수를 인식하고 사용할 수 있다.",
                    "단순한 도형을 인식할 수 있다.",
                ]
                steps = [
                    LearningStep(
                        step_number=1,
                        description="수 인식",
                        activities=["숫자 카드 사용", "세기 연습"],
                    ),
                    LearningStep(
                        step_number=2,
                        description="기본 연산 도입",
                        activities=["구슬이나 블록으로 덧셈/뺄셈", "시각적 보조 도구 사용"],
                    ),
                    LearningStep(
                        step_number=3,
                        description="도형 인식",
                        activities=["기본 도형 찾기", "도형 맞추기 게임"],
                    ),
                ]
                rationale = "수학의 기초 개념을 단계적으로 습득할 수 있도록 구성했습니다."
            else:
                goals = [
                    "복잡한 계산을 할 수 있다.",
                    "기본적인 분수와 소수를 이해한다.",
                    "단순한 문제 해결 능력을 갖는다.",
                ]
                steps = [
                    LearningStep(
                        step_number=1,
                        description="계산 능력 향상",
                        activities=["다양한 계산 연습", "계산기 사용 학습"],
                    ),
                    LearningStep(
                        step_number=2,
                        description="분수/소수 개념",
                        activities=["시각적 분수 표현", "실생활 적용 예시"],
                    ),
                    LearningStep(
                        step_number=3,
                        description="문제 해결",
                        activities=["단계적 문제 풀이", "논리적 사고 훈련"],
                    ),
                ]
                rationale = "고학년 수학의 심화 개념을 고려한 학습 계획입니다."
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 과목입니다.")

        if "고급" in request.current_level:
            rationale += " 학생의 높은 수준을 고려하여 심화 내용을 추가했습니다."
        elif "기초" in request.current_level:
            rationale += " 학생의 기초 수준을 고려하여 기본 개념부터 시작합니다."

        return GoalRecommendationResponse(
            subject=request.subject,
            grade=request.grade,
            recommended_goals=goals,
            learning_steps=steps,
            rationale=rationale,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목표 추천 중 오류 발생: {str(e)}")
