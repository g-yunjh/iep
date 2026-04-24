from fastapi import APIRouter
from typing import Dict

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
