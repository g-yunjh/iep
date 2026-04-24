"""
Pydantic schemas for RAG (Retrieval-Augmented Generation) operations.
Handles requests and responses for scaffolding recommendations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ScaffoldingRecommendationRequest(BaseModel):
    """Request model for scaffolding recommendation based on teacher/parent description."""

    grade: str = Field(..., description="Student's grade (e.g., '초등학교 1학년')")
    subject: str = Field(..., description="Subject (e.g., '국어', '수학')")
    teacher_description: str = Field(..., description="Teacher or parent's description of the child's current state and abilities")
    past_feedback_ids: Optional[List[int]] = Field(None, description="Optional list of past feedback IDs to consider for context")


class LearningActivity(BaseModel):
    """Represents a specific learning activity."""

    name: str = Field(..., description="Name of the activity")
    description: str = Field(..., description="Detailed description of how to conduct the activity")
    duration: Optional[str] = Field(None, description="Estimated duration (e.g., '15분', '30분')")
    materials: Optional[List[str]] = Field(None, description="Required materials or tools")


class ScaffoldingLevel(BaseModel):
    """Represents scaffolding recommendations for different support levels."""

    level: str = Field(..., description="Support level (high/medium/low)")
    description: str = Field(..., description="Description of the support level")
    activities: List[LearningActivity] = Field(..., description="Recommended activities for this level")
    strategies: List[str] = Field(..., description="Specific teaching strategies")


class AchievementStandardReference(BaseModel):
    """Reference to the achievement standard used for the recommendation."""

    grade: str = Field(..., description="Grade level")
    subject: str = Field(..., description="Subject")
    disability_type: str = Field(..., description="Disability type")
    standard_text: str = Field(..., description="The achievement standard text")
    relevance_score: float = Field(..., description="How relevant this standard was to the analysis")


class ScaffoldingRecommendation(BaseModel):
    """Complete scaffolding recommendation response."""

    recommended_level: str = Field(..., description="Recommended scaffolding level (high/medium/low)")
    rationale: str = Field(..., description="Explanation of why this level was recommended")
    scaffolding_details: ScaffoldingLevel = Field(..., description="Detailed scaffolding recommendations")
    achievement_standard: AchievementStandardReference = Field(..., description="Reference to the relevant achievement standard")
    additional_notes: Optional[str] = Field(None, description="Additional notes or considerations")


class LLMAnalysisResult(BaseModel):
    """Result from LLM analysis of student description."""

    detected_level: str = Field(..., description="Detected ability level (high/medium/low)")
    learning_gaps: List[str] = Field(..., description="Identified learning gaps or challenges")
    recommended_strategies: List[str] = Field(..., description="Recommended teaching strategies")
    confidence_score: float = Field(..., description="Confidence in the analysis (0.0-1.0)")
    analysis_summary: str = Field(..., description="Brief summary of the analysis")


class RAGAnalysisResult(BaseModel):
    """Complete result from RAG analysis including LLM response."""

    teacher_description: str
    retrieved_standards: List[AchievementStandardReference] = Field(..., description="Standards retrieved from vector store")
    llm_analysis: LLMAnalysisResult = Field(..., description="LLM analysis result")
    scaffolding_recommendation: ScaffoldingRecommendation = Field(..., description="Final scaffolding recommendation")
    processing_time: float = Field(..., description="Time taken for analysis in seconds")


class VectorStoreStatus(BaseModel):
    """Status information about the vector store."""

    status: str = Field(..., description="Status of the vector store (initialized/not_initialized/error)")
    document_count: Optional[int] = Field(None, description="Number of documents in the store")
    collection_name: Optional[str] = Field(None, description="Name of the collection")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")


class StudentProgressResponse(BaseModel):
    """Response for student progress history."""

    feedbacks: List[Dict[str, Any]] = Field(..., description="List of past feedback and recommendations")
    progress_summary: Optional[str] = Field(None, description="Summary of student's progress over time")


# =============================================================================
# Career RAG Schemas
# =============================================================================

class CareerRecommendationRequest(BaseModel):
    """Request model for career recommendation based on student's current skills/learning."""

    current_skills: str = Field(..., description="Student's current skills or learning content (e.g., '기본적인 덧셈 계산', '글자 쓰기')")
    grade: Optional[str] = Field(None, description="Student's grade")
    interests: Optional[List[str]] = Field(None, description="Student's interests or preferred activities")
    disability_type: Optional[str] = Field(None, description="Type of disability for personalized recommendations")


class RecommendedCareer(BaseModel):
    """Recommended career with match score and required skills."""

    job_id: str = Field(..., description="Job ID from career data")
    job_title: str = Field(..., description="Job title")
    category: str = Field(..., description="Job category")
    match_score: float = Field(..., description="Match score based on current skills (0.0-1.0)")
    required_skills: List[str] = Field(..., description="Skills required for this job")
    outlook: str = Field(..., description="Career outlook and scaffolding information")


class SkillGap(BaseModel):
    """Analysis of skill gaps between current and required skills."""

    job_title: str = Field(..., description="Target job title")
    current_level: List[str] = Field(..., description="Skills student currently has")
    required_level: List[str] = Field(..., description="Skills required for the job")
    gap_skills: List[str] = Field(..., description="Skills that need development")
    development_suggestions: List[str] = Field(..., description="Suggestions for developing gap skills")


class CareerPath(BaseModel):
    """Career path from current learning to target career."""

    current_learning: str = Field(..., description="Current learning or skill")
    target_career: str = Field(..., description="Target career")
    stages: List[Dict[str, str]] = Field(..., description="Stages from current to target (current, short-term, mid-term, long-term)")
    estimated_timeline: str = Field(..., description="Estimated time to reach target career")


class CareerRecommendationResponse(BaseModel):
    """Complete career recommendation response."""

    current_skills: str = Field(..., description="Student's current skills")
    recommended_careers: List[RecommendedCareer] = Field(..., description="List of recommended careers")
    skill_gaps: List[SkillGap] = Field(..., description="Analysis of skill gaps")
    career_paths: List[CareerPath] = Field(..., description="Career paths from current to target")