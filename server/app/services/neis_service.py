import logging
import re
from typing import Any

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """급식/시간표 텍스트 정제"""
    if not text: return "정보 없음"
    # 알레르기 정보(숫자) 및 불필요한 태그 제거
    return re.sub(r'\([0-9.]+\)', '', text).replace('<br/>', ', ').strip(', ')

async def _fetch_neis(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{settings.neis_base_url}/{endpoint}"
    async with httpx.AsyncClient(timeout=settings.neis_http_timeout_sec) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def _base_params() -> dict[str, str | None]:
    return {
        "KEY": settings.neis_api_key,
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": settings.neis_atpt_code,
        "SD_SCHUL_CODE": settings.neis_school_code,
    }


async def get_neis_meal(date_str: str):
    """급식 정보 (중식 기준)"""
    params = {**_base_params(), "MLSV_YMD": date_str}
    try:
        res = await _fetch_neis("mealServiceDietInfo", params)
        if "mealServiceDietInfo" in res:
            rows = res["mealServiceDietInfo"][1]["row"]
            lunch = next((r["DDISH_NM"] for r in rows if r["MMEAL_SC_CODE"] == "2"), "식단 정보가 없습니다.")
            return clean_text(lunch)
    except Exception as e:
        logger.exception("급식 정보 조회 실패: %s", str(e))
    return "정보 없음"

async def get_neis_schedule(date_str: str):
    """학사 일정 조회 (오늘의 행사)"""
    params = {**_base_params(), "AA_YMD": date_str}
    try:
        res = await _fetch_neis("SchoolSchedule", params)
        if "SchoolSchedule" in res:
            return res["SchoolSchedule"][1]["row"][0]["EVENT_NM"]
    except Exception as e:
        logger.exception("학사 일정 조회 실패: %s", str(e))
    return "일정 없음"

async def get_neis_timetable(date_str: str, grade: str = "1", class_nm: str = "1"):
    """중학교 시간표 정보 및 하교 시간 계산"""
    # 중학교 시간표 엔드포인트: misTimetable
    params = {
        **_base_params(),
        "ALL_TI_YMD": date_str, 
        "GRADE": grade, 
        "CLASS_NM": class_nm
    }
    
    subjects = []
    dismissal = "정보 없음"
    
    try:
        res = await _fetch_neis("misTimetable", params)
        
        if "misTimetable" in res:
            rows = res["misTimetable"][1]["row"]
            subjects = [r["ITRT_CNTNT"] for r in rows]
            max_period = len(subjects)
            
            # 수업이 하나라도 있는 경우에만 하교 시간 계산
            if max_period >= 7:
                dismissal = settings.neis_dismissal_7_plus
            elif max_period == 6:
                dismissal = settings.neis_dismissal_6
            elif max_period > 0:
                dismissal = settings.neis_dismissal_default
            # max_period가 0이면 여전히 "정보 없음" 유지
    except Exception as e:
        logger.exception("시간표 조회 실패: %s", str(e))
        
    return subjects, dismissal
