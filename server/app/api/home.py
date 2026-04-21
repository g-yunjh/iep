from fastapi import APIRouter, HTTPException
from typing import Dict, List

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
async def get_career_link():
    """
    교과-진로 로드맵 시각화
    - 현재 배우는 과목이 향후 직업으로 이어지는 경로
    """
    # 실제로는 학생의 현재 학년/과목 기반
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