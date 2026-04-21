"""
Pydantic schemas for RAG (Retrieval-Augmented Generation) operations.
Handles requests and responses for scaffolding recommendations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ScaffoldingRecommendationRequest(BaseModel):
    """Request model for scaffolding recommendation based on teacher/parent description."""

    student_id: int = Field(..., description="ID of the student")
    grade: str = Field(..., description="Student's grade (e.g., '초등학교 1학년')")
    subject: str = Field(..., description="Subject (e.g., '국어', '수학')")
    disability_type: str = Field(..., description="Type of disability (e.g., '지적장애', '학습장애', '자폐성장애')")
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

    student_id: int = Field(..., description="ID of the student")
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

    student_id: int
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

    student_id: int
    feedbacks: List[Dict[str, Any]] = Field(..., description="List of past feedback and recommendations")
    progress_summary: Optional[str] = Field(None, description="Summary of student's progress over time")