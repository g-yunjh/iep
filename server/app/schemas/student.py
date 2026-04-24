from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


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
    additional_diagnoses: Optional[str] = None
    behavioral_traits: Optional[str] = None


class GoalRecommendationRequest(BaseModel):
    subject: str
    current_level: str
    grade: int


class LearningStep(BaseModel):
    step_number: int
    description: str
    activities: List[str]


class GoalRecommendationResponse(BaseModel):
    subject: str
    grade: int
    recommended_goals: List[str]
    learning_steps: List[LearningStep]
    rationale: str
