from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CenterBase(BaseModel):
    name: str
    strategies: List[str] = []

class CenterCreate(CenterBase):
    pass

class Center(CenterBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class StudentBase(BaseModel):
    name: str
    center_id: Optional[int] = None

class StudentCreate(StudentBase):
    pass

class Student(StudentBase):
    id: int
    created_at: datetime
    disability_type: Optional[str] = None
    additional_diagnoses: Optional[str] = None
    behavioral_traits: Optional[str] = None
    center: Optional[Center] = None

    class Config:
        from_attributes = True

class FeedbackBase(BaseModel):
    student_id: int
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

class StudentUpdate(BaseModel):
    disability_type: Optional[str] = None
    additional_diagnoses: Optional[str] = None  # "ADHD, 시각장애"
    behavioral_traits: Optional[str] = None           # "어려운 걸 보면 화를 냄"
