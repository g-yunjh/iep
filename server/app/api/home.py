from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.schemas.rag import CareerRecommendationRequest
from app.db.database import get_db

router = APIRouter()


@router.get("/school-life", response_model=Dict)
async def get_school_life():
    """
    나이스 연동 학교 생활 정보
    - 식단 정보, 하교 시간, 내일의 준비물 알림
    """
    # 실제로는 나이스 API 호출
    # 지금은 모의 데이터 반환
    return {
        "meal_info": {
            "lunch": "김치찌개, 불고기, 밥, 김",
            "snack": "우유, 바나나"
        },
        "dismissal_time": "15:30",
        "tomorrow_prep": [
            "체육복",
            "수학 교과서",
            "필통"
        ]
    }


@router.get("/daily-guide", response_model=Dict)
async def get_daily_guide():
    """
    가정 내 교과 복습 가이드
    - 오늘 학교에서 배운 내용 기반 실생활 가이드
    """
    # 실제로는 학생의 오늘 학습 내용 기반
    return {
        "subject": "국어",
        "topic": "받침 있는 글자",
        "home_guide": "오늘 학교에서 배운 '받침 있는 글자', 집에서는 마트 전단지로 찾아보세요. 예를 들어 '김치', '불고기' 같은 단어들을 찾아보는 거예요!",
        "activity_suggestion": "가족과 함께 장을 보면서 받침 있는 단어들을 찾아보는 게임을 해보세요."
    }


@router.get("/career-link", response_model=Dict)
async def get_career_link(
    current_skills: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    교과-진로 로드맵 시각화
    - 현재 배우는 과목이 향후 직업으로 이어지는 경로
    
    RAG API를 통해 학생의 현재 학습 내용을 기반으로
    관련 직업을 추천하고 역량 격차를 분석합니다.
    """
    if not current_skills:
        # 기본 응답 (파라미터 없는 경우)
        return {
            "current_subject": "수학",
            "current_topic": "덧셈",
            "career_path": [
                {
                    "stage": "초등학교",
                    "skill": "기본적인 덧셈 계산",
                    "future_role": "일상생활 계산 능력"
                },
                {
                    "stage": "중학교",
                    "skill": "복잡한 수학 문제 해결",
                    "future_role": "논리적 사고력"
                },
                {
                    "stage": "고등학교",
                    "skill": "고급 수학",
                    "future_role": "과학/공학 분야 기초"
                },
                {
                    "stage": "직업",
                    "careers": ["계산원", "서비스직", "엔지니어", "연구원"],
                    "description": "수학적 사고는 다양한 직업에서 필수적인 역량입니다."
                }
            ]
        }
    
    # RAG API를 통해 진로 추천 받기
    # Note: 실제 구현에서는 /rag/career-recommendation 엔드포인트를 호출
    return {
        "current_subject": "수학",
        "current_topic": current_skills,
        "career_path": [
            {
                "stage": "초등학교",
                "skill": f"현재 학습: {current_skills}",
                "future_role": "기초 역량 형성"
            },
            {
                "stage": "중학교",
                "skill": "복잡한 문제 해결",
                "future_role": "논리적 사고력"
            },
            {
                "stage": "고등학교",
                "skill": "고급 전문 지식",
                "future_role": "전문 분야 준비"
            },
            {
                "stage": "직업",
                "careers": [],
                "description": "RAG API를 통해 맞춤형 진로 추천을 받으려면 /rag/career-recommendation를 호출하세요."
            }
        ],
        "note": "상세한 진로 추천은 /rag/career-recommendation API를 사용하세요."
    }


@router.post("/career-recommendation", response_model=Dict)
async def get_career_recommendation_home(
    request: CareerRecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    가정용 진로 추천 API
    - 학생의 현재 역량을 기반으로 관련 직업 추천
    - RAG 공통 API를 활용
    """
    # RAG 공통 API 호출을 위한 응답
    # 실제 구현에서는 rag API를 직접 호출하거나 프록시
    return {
        "student_id": request.student_id,
        "current_skills": request.current_skills,
        "message": "진로 추천을 받으려면 /rag/career-recommendation API를 사용하세요.",
        "rag_endpoint": "/rag/career-recommendation"
    }