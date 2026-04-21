from pydantic import BaseModel
from typing import List, Dict, Any

class GoalRecommendationRequest(BaseModel):
    subject: str  # 과목 (국어/수학)
    current_level: str  # 학생 현재 수준
    grade: int  # 학년

class LearningStep(BaseModel):
    step_number: int
    description: str
    activities: List[str]

class GoalRecommendationResponse(BaseModel):
    subject: str
    grade: int
    recommended_goals: List[str]  # 성취기준 문항들
    learning_steps: List[LearningStep]  # 학습 단계
    rationale: str  # 추천 근거