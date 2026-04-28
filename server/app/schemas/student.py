from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel



class StudentBase(BaseModel):
    name: str

class StudentCreate(StudentBase):
    pass


class Student(StudentBase):
    id: int
    created_at: datetime
    current_level: Optional[str] = None
    disability_type: Optional[str] = None
    additional_diagnoses: Optional[str] = None
    behavioral_traits: Optional[str] = None

    class Config:
        from_attributes = True

class StudentUpdate(BaseModel):
    name: Optional[str] = None # 이제 이름 수정 가능
    current_level: Optional[str] = None
    disability_type: Optional[str] = None
    additional_diagnoses: Optional[str] = None
    behavioral_traits: Optional[str] = None


class SchoolLifeResponse(BaseModel):
    lunch_menu: str
    dismissal_time: str
    academic_calendar: str
    today_timetable: List[str]


class FeedbackBase(BaseModel):
    student_id: Optional[int] = None
    performance: str
    scaffolding_effectiveness: str


class FeedbackCreate(FeedbackBase):
    pass


class Feedback(FeedbackBase):
    id: int
    created_at: datetime
    student: Optional[Student] = None

    class Config:
        from_attributes = True


class StrategyResponse(BaseModel):
    center_name: str
    strategies: List[str]
    student_count: int
