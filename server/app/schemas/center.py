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