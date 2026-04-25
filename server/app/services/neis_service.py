import os
import requests
import re

NEIS_API_KEY = os.getenv("NEIS_API_KEY")
ATPT_CODE = os.getenv("NEIS_ATPT_CODE")
SCHOOL_CODE = os.getenv("NEIS_SCHOOL_CODE")
BASE_URL = "https://open.neis.go.kr/hub"

def clean_text(text: str) -> str:
    """급식/시간표 텍스트 정제"""
    if not text: return "정보 없음"
    # 알레르기 정보(숫자) 및 불필요한 태그 제거
    return re.sub(r'\([0-9.]+\)', '', text).replace('<br/>', ', ').strip(', ')

def get_neis_meal(date_str: str):
    """급식 정보 (중식 기준)"""
    params = {"KEY": NEIS_API_KEY, "Type": "json", "ATPT_OFCDC_SC_CODE": ATPT_CODE, 
              "SD_SCHUL_CODE": SCHOOL_CODE, "MLSV_YMD": date_str}
    try:
        res = requests.get(f"{BASE_URL}/mealServiceDietInfo", params=params).json()
        if "mealServiceDietInfo" in res:
            rows = res["mealServiceDietInfo"][1]["row"]
            lunch = next((r["DDISH_NM"] for r in rows if r["MMEAL_SC_CODE"] == "2"), "식단 정보가 없습니다.")
            return clean_text(lunch)
    except: pass
    return "정보 없음"

def get_neis_schedule(date_str: str):
    """학사 일정 조회 (오늘의 행사)"""
    params = {"KEY": NEIS_API_KEY, "Type": "json", "ATPT_OFCDC_SC_CODE": ATPT_CODE, 
              "SD_SCHUL_CODE": SCHOOL_CODE, "AA_YMD": date_str}
    try:
        res = requests.get(f"{BASE_URL}/SchoolSchedule", params=params).json()
        if "SchoolSchedule" in res:
            return res["SchoolSchedule"][1]["row"][0]["EVENT_NM"]
    except: pass
    return "일정 없음"

def get_neis_timetable(date_str: str, grade: str = "1", class_nm: str = "1"):
    """중학교 시간표 정보 및 하교 시간 계산"""
    # 중학교 시간표 엔드포인트: misTimetable
    params = {
        "KEY": NEIS_API_KEY, 
        "Type": "json", 
        "ATPT_OFCDC_SC_CODE": ATPT_CODE, 
        "SD_SCHUL_CODE": SCHOOL_CODE, 
        "ALL_TI_YMD": date_str, 
        "GRADE": grade, 
        "CLASS_NM": class_nm
    }
    
    subjects = []
    dismissal = "정보 없음"
    
    try:
        res = requests.get(f"{BASE_URL}/misTimetable", params=params).json()
        
        if "misTimetable" in res:
            rows = res["misTimetable"][1]["row"]
            subjects = [r["ITRT_CNTNT"] for r in rows]
            max_period = len(subjects)
            
            # 수업이 하나라도 있는 경우에만 하교 시간 계산
            if max_period >= 7:
                dismissal = "16:15"
            elif max_period == 6:
                dismissal = "15:20"
            elif max_period > 0:
                dismissal = "14:30"
            # max_period가 0이면 여전히 "정보 없음" 유지
    except Exception as e:
        print(f"시간표 조회 중 오류 발생: {e}")
        pass
        
    return subjects, dismissal
