"""
RAG Orchestrator: Main pipeline for Retrieval-Augmented Generation.
Coordinates vector search, LLM analysis, and recommendation generation.
"""

import time
import logging
import re
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from .rag_service import RAGService
from .llm_service import LLMService
from ..schemas.rag import (
    ScaffoldingRecommendationRequest,
    RAGAnalysisResult,
    ScaffoldingRecommendation,
    AchievementStandardReference,
    LearningActivity,
    ScaffoldingLevel
)
from ..db.models import Feedback, Student

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """
    Main orchestrator for the RAG pipeline.
    Handles the complete flow from request to recommendation.
    """

    def __init__(self):
        self.rag_service = RAGService()
        self.llm_service = LLMService()
        self.logger = logging.getLogger(__name__)

    def analyze_and_recommend(
        self,
        request: ScaffoldingRecommendationRequest,
        db: Session
    ) -> RAGAnalysisResult:
        """
        Main method: Analyze teacher description and generate scaffolding recommendations.

        Args:
            request: Scaffolding recommendation request
            db: Database session

        Returns:
            Complete RAG analysis result
        """
        start_time = time.time()

        try:
            # Step 1: Get past feedback for context
            student = self._get_persona_student(db)
            if not student:
                raise ValueError("학생 프로필이 없습니다.")

            past_feedback = self._get_past_feedback(student.id, request.past_feedback_ids, db)

            # Step 2: Search for relevant achievement standards
            retrieved_standards = self._retrieve_relevant_standards(
                request=request,
                disability_type=student.disability_type or "",
            )

            # Step 3: Analyze with LLM
            llm_analysis = self.llm_service.analyze_student_description(
                teacher_description=request.teacher_description,
                grade=request.grade,
                subject=request.subject,
                disability_type=student.disability_type or "",
                retrieved_standards=retrieved_standards,
                past_feedback=past_feedback
            )

            # Step 4: Generate scaffolding recommendation
            scaffolding_recommendation = self._generate_scaffolding_recommendation(
                request=request,
                llm_analysis=llm_analysis,
                retrieved_standards=retrieved_standards
            )

            # Step 5: Calculate processing time
            processing_time = time.time() - start_time

            # Step 6: Create complete result
            result = RAGAnalysisResult(
                teacher_description=request.teacher_description,
                retrieved_standards=retrieved_standards,
                llm_analysis=llm_analysis,
                scaffolding_recommendation=scaffolding_recommendation,
                processing_time=processing_time
            )

            self.logger.info(f"RAG analysis completed for student {student.id} in {processing_time:.2f}s")
            return result

        except Exception as e:
            self.logger.error(f"Error in RAG orchestration: {e}")
            processing_time = time.time() - start_time

            # Return error result
            return RAGAnalysisResult(
                teacher_description=request.teacher_description,
                retrieved_standards=[],
                llm_analysis=self.llm_service._parse_llm_response({}),  # Fallback
                scaffolding_recommendation=self._create_error_recommendation(request),
                processing_time=processing_time
            )

    def _retrieve_relevant_standards(
        self,
        request: ScaffoldingRecommendationRequest,
        disability_type: str,
    ) -> List[AchievementStandardReference]:
        """
        Retrieve relevant achievement standards from vector store.

        Args:
            request: The recommendation request

        Returns:
            List of relevant achievement standards
        """
        # Create search query from teacher description
        search_query = f"{request.grade} {request.subject} {disability_type} {request.teacher_description}"

        # Search vector store
        search_results = self.rag_service.search_similar_standards(
            query=search_query,
            grade=request.grade,
            subject=request.subject,
            disability_type=disability_type,
            k=3,  # Get top 3 most relevant standards
            score_threshold=0.6
        )

        # Convert to AchievementStandardReference objects
        standards = []
        for result in search_results:
            metadata = result.get("metadata", {})
            content = result.get("content", "")
            standard = AchievementStandardReference(
                grade=metadata.get("grade", ""),
                subject=metadata.get("subject", ""),
                disability_type=metadata.get("disability_type", ""),
                standard_text=self._extract_standard_text(content),
                diagnostic_criteria=self._extract_diagnostic_criteria(content),
                activities=self._extract_activities(content),
                scaffolding_levels=self._extract_scaffolding_levels(content),
                scaffolding_bank_general=self._extract_scaffolding_bank_general(content),
                scaffolding_bank_disability_specific=self._extract_scaffolding_bank_disability_specific(content),
                relevance_score=result.get("score", 0.0)
            )
            standards.append(standard)

        return standards

    def _extract_standard_text(self, content: str) -> str:
        """Extract the achievement standard text from document content."""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('성취기준:'):
                return line.replace('성취기준:', '').strip()
        return content[:200] + "..."  # Fallback

    def _extract_diagnostic_criteria(self, content: str) -> List[str]:
        """Extract diagnostic criteria listed under the '활동:' section."""
        lines = content.split('\n')
        criteria: List[str] = []
        in_activity_section = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("활동:"):
                in_activity_section = True
                continue

            # Stop at the next major section-like line.
            if in_activity_section and (line.endswith(":") and not line.startswith("-")):
                break

            if in_activity_section and line.startswith("-"):
                criteria.append(line[1:].strip())

        return criteria

    def _extract_activities(self, content: str) -> List[str]:
        """Extract activities listed under the '활동:' section."""
        lines = content.split('\n')
        activities: List[str] = []
        in_activity_section = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("활동:"):
                in_activity_section = True
                continue

            if in_activity_section and (line.endswith(":") and not line.startswith("-")):
                break

            if in_activity_section and line.startswith("-"):
                activities.append(line[1:].strip())

        return activities

    def _extract_scaffolding_levels(self, content: str) -> Dict[str, str]:
        """Extract level descriptions from '스캐폴딩 수준' section."""
        levels: Dict[str, str] = {}
        lines = content.split('\n')
        in_scaffolding_section = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("스캐폴딩 수준:"):
                in_scaffolding_section = True
                continue

            if in_scaffolding_section and (line.endswith(":") and not line.startswith("-")):
                break

            if not in_scaffolding_section:
                continue

            if line.startswith("높음:"):
                levels["high"] = line.replace("높음:", "").strip()
            elif line.startswith("중간:"):
                levels["medium"] = line.replace("중간:", "").strip()
            elif line.startswith("낮음:"):
                levels["low"] = line.replace("낮음:", "").strip()

        return levels

    def _extract_scaffolding_bank_general(self, content: str) -> List[str]:
        """
        Extract general scaffolding strategies.
        Supports both explicit 'general' section and flattened level lines.
        """
        lines = content.split('\n')
        strategies: List[str] = []
        in_general_section = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if re.match(r"^general\s*:\s*$", line, flags=re.IGNORECASE):
                in_general_section = True
                continue

            if in_general_section and (line.endswith(":") and not line.startswith("-")):
                break

            if in_general_section and line.startswith("-"):
                strategies.append(line[1:].strip())

        return strategies

    def _extract_scaffolding_bank_disability_specific(self, content: str) -> Dict[str, str]:
        """
        Extract disability-specific strategies.
        Expected line format in section: '- 장애유형: 전략내용'
        """
        lines = content.split('\n')
        strategies: Dict[str, str] = {}
        in_disability_section = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if re.match(r"^disability_specific\s*:\s*$", line, flags=re.IGNORECASE):
                in_disability_section = True
                continue

            if in_disability_section and (line.endswith(":") and not line.startswith("-")):
                break

            if in_disability_section and line.startswith("-"):
                entry = line[1:].strip()
                if ":" in entry:
                    disability, strategy = entry.split(":", 1)
                    strategies[disability.strip()] = strategy.strip()
                else:
                    strategies["default"] = entry

        return strategies

    def _get_past_feedback(
        self,
        student_id: int,
        feedback_ids: Optional[List[int]],
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Get past feedback for the student.

        Args:
            student_id: ID of the student
            feedback_ids: Specific feedback IDs to retrieve (optional)
            db: Database session

        Returns:
            List of past feedback records
        """
        try:
            query = db.query(Feedback).filter(Feedback.student_id == student_id)

            if feedback_ids:
                query = query.filter(Feedback.id.in_(feedback_ids))

            # Get recent feedback (last 5)
            feedbacks = query.order_by(Feedback.created_at.desc()).limit(5).all()

            # Convert to dict format
            feedback_list = []
            for fb in feedbacks:
                feedback_dict = {
                    'id': fb.id,
                    'performance': fb.performance,
                    'scaffolding_effectiveness': fb.scaffolding_effectiveness,
                    'created_at': fb.created_at.isoformat() if fb.created_at else None,
                    'llm_analysis': fb.llm_analysis,
                    'scaffolding_recommendations': fb.scaffolding_recommendations
                }
                feedback_list.append(feedback_dict)

            return feedback_list

        except Exception as e:
            self.logger.error(f"Error retrieving past feedback: {e}")
            return []

    def _generate_scaffolding_recommendation(
        self,
        request: ScaffoldingRecommendationRequest,
        llm_analysis: Any,  # LLMAnalysisResult
        retrieved_standards: List[AchievementStandardReference]
    ) -> ScaffoldingRecommendation:
        """
        Generate detailed scaffolding recommendation based on LLM analysis.

        Args:
            request: Original request
            llm_analysis: LLM analysis result
            retrieved_standards: Retrieved achievement standards

        Returns:
            Complete scaffolding recommendation
        """
        # Use the most relevant standard as reference
        primary_standard = retrieved_standards[0] if retrieved_standards else None

        if not primary_standard:
            return self._create_error_recommendation(request)

        matched_strategies = self._match_curriculum_strategies(
            detected_level=llm_analysis.detected_level,
            primary_standard=primary_standard
        )
        # Keep LLM strategies as fallback/additional context.
        final_strategies = matched_strategies or llm_analysis.recommended_strategies

        scaffolding_details = self._create_scaffolding_details(
            detected_level=llm_analysis.detected_level,
            strategies=final_strategies,
            primary_standard=primary_standard
        )

        # Create rationale
        rationale = self._create_rationale(llm_analysis, primary_standard)

        return ScaffoldingRecommendation(
            recommended_level=llm_analysis.detected_level,
            rationale=rationale,
            scaffolding_details=scaffolding_details,
            achievement_standard=primary_standard,
            additional_notes=self._create_additional_notes(llm_analysis)
        )

    def _create_scaffolding_details(
        self,
        detected_level: str,
        strategies: List[str],
        primary_standard: AchievementStandardReference
    ) -> ScaffoldingLevel:
        """
        Create detailed scaffolding information based on the detected level.
        """
        level_descriptions = primary_standard.scaffolding_levels or {}
        description = level_descriptions.get(detected_level)
        if not description or description == "N/A":
            description = "해당 수준에 맞춰 교육과정 기반 스캐폴딩 전략을 적용합니다."

        activities = []
        for idx, activity_text in enumerate(primary_standard.activities, start=1):
            activities.append(
                LearningActivity(
                    name=f"교육과정 활동 {idx}",
                    description=activity_text,
                    duration=None,
                    materials=None
                )
            )

        if not activities:
            activities.append(
                LearningActivity(
                    name="기본 활동",
                    description="해당 성취기준을 중심으로 단계적 지원을 제공합니다.",
                    duration=None,
                    materials=None
                )
            )

        return ScaffoldingLevel(
            level=detected_level,
            description=description,
            activities=activities,
            strategies=strategies
        )

    def _match_curriculum_strategies(
        self,
        detected_level: str,
        primary_standard: AchievementStandardReference
    ) -> List[str]:
        """
        Match strategies from curriculum scaffolding data.
        Priority:
        1) explicit scaffolding_bank.general + disability_specific
        2) fallback to level description line
        """
        matched: List[str] = []

        if primary_standard.scaffolding_bank_general:
            matched.extend(primary_standard.scaffolding_bank_general)

        disability_specific = primary_standard.scaffolding_bank_disability_specific or {}
        if disability_specific:
            # Prefer exact disability_type key, then partial match, then default, then first strategy.
            key = primary_standard.disability_type.strip()
            if key and key in disability_specific:
                matched.append(disability_specific[key])
            elif key:
                for disability_name, strategy in disability_specific.items():
                    if key in disability_name or disability_name in key:
                        matched.append(strategy)
                        break
                else:
                    if "default" in disability_specific:
                        matched.append(disability_specific["default"])
            elif "default" in disability_specific:
                matched.append(disability_specific["default"])

            if not matched and disability_specific:
                matched.append(next(iter(disability_specific.values())))

        if not matched:
            level_text = (primary_standard.scaffolding_levels or {}).get(detected_level)
            if level_text and level_text != "N/A":
                matched.append(level_text)

        # De-duplicate while preserving order.
        unique: List[str] = []
        for item in matched:
            if item and item not in unique:
                unique.append(item)
        return unique

    def _create_rationale(self, llm_analysis: Any, primary_standard: AchievementStandardReference) -> str:
        """Create rationale for the recommendation."""
        return f"""학생의 현재 능력 수준을 '{llm_analysis.detected_level}'로 평가했습니다.
주요 학습 격차: {', '.join(llm_analysis.learning_gaps)}
관련 성취기준: {primary_standard.standard_text[:100]}...
신뢰도: {llm_analysis.confidence_score:.1f}"""

    def _create_additional_notes(self, llm_analysis: Any) -> str:
        """Create additional notes based on analysis."""
        confidence = llm_analysis.confidence_score
        if confidence < 0.6:
            return "분석 신뢰도가 낮아 전문가 상담을 권장합니다."
        elif confidence > 0.8:
            return "분석 결과가 안정적입니다. 추천 전략을 적용해보세요."
        else:
            return "적절한 수준의 지원 전략을 적용하시고 효과를 모니터링하세요."

    def _create_error_recommendation(self, request: ScaffoldingRecommendationRequest) -> ScaffoldingRecommendation:
        """Create a fallback recommendation when analysis fails."""
        return ScaffoldingRecommendation(
            recommended_level="medium",
            rationale="분석 과정에서 오류가 발생하여 기본 추천을 제공합니다.",
            scaffolding_details=ScaffoldingLevel(
                level="medium",
                description="중간 수준의 지원을 제공하세요.",
                activities=[
                    LearningActivity(
                        name="기본 학습 활동",
                        description="학생의 반응을 관찰하며 적절한 지원을 제공하세요.",
                        duration="15분",
                        materials=["기본 교재"]
                    )
                ],
                strategies=["개별화된 접근", "긍정적 강화"]
            ),
            achievement_standard=AchievementStandardReference(
                grade=request.grade,
                subject=request.subject,
                disability_type="",
                standard_text="기본적인 학습 지원이 필요한 수준",
                diagnostic_criteria=[],
                activities=[],
                scaffolding_levels={},
                scaffolding_bank_general=[],
                scaffolding_bank_disability_specific={},
                relevance_score=0.5
            ),
            additional_notes="전문가와 상담하여 자세한 평가를 받으시길 권장합니다."
        )

    def _get_persona_student(self, db: Session) -> Optional[Student]:
        return db.query(Student).order_by(Student.id.asc()).first()