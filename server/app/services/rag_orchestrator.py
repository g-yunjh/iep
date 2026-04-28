"""
RAG Orchestrator: Main pipeline for Retrieval-Augmented Generation.
Coordinates vector search, LLM analysis, and recommendation generation.
"""

import time
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session

from .rag_service import RAGService
from .llm_service import LLMService
from ..schemas.rag import (
    ScaffoldingRecommendationRequest,
    RAGAnalysisResult,
    LLMAnalysisResult,
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

            # Step 3: Analyze with LLM (or deterministic fallback when quota/network fails)
            try:
                llm_analysis = self.llm_service.analyze_student_description(
                    teacher_description=request.teacher_description,
                    grade=request.grade,
                    subject=request.subject,
                    disability_type=student.disability_type or "",
                    retrieved_standards=retrieved_standards,
                    past_feedback=past_feedback
                )
            except Exception as llm_error:
                self.logger.warning(
                    "LLM unavailable for scaffolding analysis (%s): %s. "
                    "Using rule-based fallback analysis.",
                    llm_error.__class__.__name__,
                    str(llm_error),
                )
                llm_analysis = self._create_rule_based_analysis(request, retrieved_standards)

            # Step 4: Generate scaffolding recommendation
            scaffolding_recommendation = self._generate_scaffolding_recommendation(
                request=request,
                llm_analysis=llm_analysis,
                retrieved_standards=retrieved_standards,
                student_disability_type=student.disability_type or "",
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
        # Grade is intentionally excluded from strict filtering.
        # Many special-education learners do not align with grade-based progression.
        search_query = f"{request.subject} {disability_type} {request.teacher_description}"

        # Multi-pass retrieval: progressively relax filters so recommendation does not
        # collapse to fallback only because one metadata field failed exact matching.
        search_attempts = [
            {"grade": None, "subject": request.subject, "disability_type": None},
            {"grade": None, "subject": None, "disability_type": None},
        ]

        search_results: List[Dict[str, Any]] = []
        for attempt in search_attempts:
            search_results = self.rag_service.search_curriculum(
                query=search_query,
                grade=attempt["grade"],
                subject=attempt["subject"],
                disability_type=attempt["disability_type"],
                k=3,  # Get top 3 most relevant standards
            )
            if search_results:
                break

        # Convert to AchievementStandardReference objects
        standards = []
        for result in search_results:
            metadata = result.get("metadata", {})
            content = result.get("content", "")
            standard = AchievementStandardReference(
                standard_id=str(metadata.get("achievement_standard_id", "") or ""),
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
            # Curriculum loader stores flattened bank lines under this section.
            # Map them to level defaults so downstream response is still curriculum-grounded.
            elif line.startswith("일반:"):
                general_text = line.replace("일반:", "").strip()
                if general_text and general_text != "N/A":
                    for level_key in ("high", "medium", "low"):
                        levels.setdefault(level_key, general_text)
            elif line.startswith("장애특성:"):
                disability_text = line.replace("장애특성:", "").strip()
                if disability_text and disability_text != "N/A":
                    for level_key in ("high", "medium", "low"):
                        levels.setdefault(level_key, disability_text)

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
            # Flattened format from curriculum documents.
            if line.startswith("일반:"):
                raw = line.replace("일반:", "").strip()
                if raw and raw != "N/A":
                    for part in [p.strip() for p in raw.split(";") if p.strip()]:
                        strategies.append(part)
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
            # Flattened format from curriculum documents:
            # 장애특성: 지적장애: 전략1; 자폐성장애: 전략2
            if line.startswith("장애특성:"):
                raw = line.replace("장애특성:", "").strip()
                if raw and raw != "N/A":
                    entries = [entry.strip() for entry in raw.split(";") if entry.strip()]
                    for entry in entries:
                        if ":" in entry:
                            disability, strategy = entry.split(":", 1)
                            disability = disability.strip()
                            strategy = strategy.strip()
                            if disability and strategy:
                                strategies[disability] = strategy
                        else:
                            strategies["default"] = entry
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
        retrieved_standards: List[AchievementStandardReference],
        student_disability_type: str,
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
            self.logger.warning(
                "No curriculum standards retrieved for scaffolding request "
                "(grade=%s, subject=%s). Falling back to default recommendation.",
                request.grade,
                request.subject,
            )
            return self._create_error_recommendation(request)

        matched_strategies = self._match_curriculum_strategies(
            teacher_description=request.teacher_description,
            detected_level=llm_analysis.detected_level,
            retrieved_standards=retrieved_standards,
            student_disability_type=student_disability_type,
        )
        # Curriculum-first: always prioritize retrieved standard strategies.
        # Use LLM strategies only as strict fallback when curriculum parsing yields nothing.
        final_strategies = matched_strategies
        if not final_strategies:
            final_strategies = llm_analysis.recommended_strategies

        scaffolding_details = self._create_scaffolding_details(
            detected_level=llm_analysis.detected_level,
            strategies=final_strategies,
            primary_standard=primary_standard
        )

        # Create rationale
        rationale = self._create_rationale(llm_analysis, primary_standard)

        return ScaffoldingRecommendation(
            recommended_level=self._level_to_korean(llm_analysis.detected_level),
            rationale=rationale,
            scaffolding_details=scaffolding_details,
            achievement_standard=primary_standard,
            related_achievement_standards=self._collect_related_standard_texts(retrieved_standards),
            additional_notes=None
        )

    def _create_rule_based_analysis(
        self,
        request: ScaffoldingRecommendationRequest,
        retrieved_standards: List[AchievementStandardReference],
    ) -> LLMAnalysisResult:
        """
        Deterministic analysis used when external LLM call is unavailable.
        """
        text = (request.teacher_description or "").lower()

        low_signals = ["어려", "힘들", "도움", "지원", "못", "불안정", "지시", "거부"]
        high_signals = ["스스로", "자발", "독립", "정확", "유지", "가능", "완료"]

        low_hits = sum(1 for token in low_signals if token in text)
        high_hits = sum(1 for token in high_signals if token in text)

        if high_hits >= low_hits + 2:
            detected_level = "high"
        elif low_hits >= high_hits + 2:
            detected_level = "low"
        else:
            detected_level = "medium"

        gaps: List[str] = []
        if retrieved_standards:
            for standard in retrieved_standards[:2]:
                gaps.extend((standard.diagnostic_criteria or [])[:2])
        if not gaps:
            gaps = ["교사 설명 기반으로 우선 지원 우선순위를 정리해 단계적으로 적용이 필요합니다."]

        # Confidence: reflect rule-match strength + retrieval relevance instead of fixed value.
        signal_gap = abs(high_hits - low_hits)
        signal_conf = min(0.18, 0.04 * signal_gap)
        top_relevance = 0.0
        if retrieved_standards:
            top_relevance = max(float(s.relevance_score or 0.0) for s in retrieved_standards[:3])
        relevance_conf = min(0.20, top_relevance * 0.25)
        confidence = max(0.35, min(0.78, 0.42 + signal_conf + relevance_conf))

        return LLMAnalysisResult(
            detected_level=detected_level,
            learning_gaps=gaps[:4],
            recommended_strategies=[],
            confidence_score=confidence,
            analysis_summary="외부 LLM 호출이 불가해 규칙 기반 분석으로 대체했습니다.",
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
            cleaned_activity = self._to_action_phrase(activity_text)
            activities.append(
                LearningActivity(
                    name=f"교육과정 활동 {idx}",
                    description=cleaned_activity,
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
            level=self._level_to_korean(detected_level),
            description=description,
            activities=activities,
            strategies=strategies
        )

    def _match_curriculum_strategies(
        self,
        teacher_description: str,
        detected_level: str,
        retrieved_standards: List[AchievementStandardReference],
        student_disability_type: str,
    ) -> List[str]:
        """
        Match strategies from curriculum scaffolding bank across retrieved standards.
        Priority:
        1) bank/general + disability_specific from top relevant standards
        2) level descriptions as fallback
        Then rank by lexical overlap with teacher_description and standard relevance.
        """
        if not retrieved_standards:
            return []

        query_tokens = self._tokenize(teacher_description)
        scored_items: List[Tuple[float, str]] = []

        for standard in retrieved_standards:
            candidate_text = " ".join(
                [standard.standard_text, " ".join(standard.activities or [])]
            )
            candidate_tokens = self._tokenize(candidate_text)
            overlap = 0.0
            if query_tokens and candidate_tokens:
                overlap = len(query_tokens.intersection(candidate_tokens)) / len(query_tokens)

            base_score = float(standard.relevance_score or 0.0)
            score = base_score + (0.3 * overlap)

            for item in (standard.scaffolding_bank_general or []):
                if item and item != "N/A":
                    scored_items.append((score, item))

            disability_specific = standard.scaffolding_bank_disability_specific or {}
            normalized_disability = (student_disability_type or "").strip()
            if disability_specific:
                if normalized_disability:
                    for key, item in disability_specific.items():
                        key_text = str(key or "").strip()
                        if key_text and (
                            normalized_disability in key_text or key_text in normalized_disability
                        ):
                            if item and item != "N/A":
                                scored_items.append((score + 0.20, item))
                elif "default" in disability_specific:
                    default_item = disability_specific.get("default")
                    if default_item and default_item != "N/A":
                        scored_items.append((score + 0.05, default_item))

            level_text = (standard.scaffolding_levels or {}).get(detected_level)
            if level_text and level_text != "N/A":
                scored_items.append((score - 0.05, level_text))

        scored_items.sort(key=lambda item: item[0], reverse=True)
        matched: List[str] = [text for _, text in scored_items]

        unique: List[str] = []
        for item in matched:
            if item and item not in unique:
                unique.append(item)
        return unique[:6]

    def _tokenize(self, text: str) -> set:
        tokens = re.split(r"[^0-9A-Za-z가-힣]+", (text or "").lower())
        return {t for t in tokens if len(t) >= 2}

    def _to_action_phrase(self, criterion: str) -> str:
        """
        Convert diagnostic question-style criterion into intervention action sentence.
        """
        text = (criterion or "").strip()
        if not text:
            return "학생의 현재 수행을 관찰하고 단계적 지원을 제공합니다."
        if text.endswith("는가?"):
            core = re.sub(r"는가\?$", "기", text).strip()
            if core:
                return f"{core}를 짧은 단계로 나누어 반복 연습합니다."
        if text.endswith("?"):
            core = text[:-1].strip()
            if core:
                return f"{core} 과제를 체크리스트 기반으로 연습합니다."
        return text

    def _level_to_korean(self, level: str) -> str:
        mapping = {
            "high": "상",
            "medium": "중",
            "low": "하",
            "상": "상",
            "중": "중",
            "하": "하",
        }
        return mapping.get((level or "").strip().lower(), "중")

    def _collect_related_standard_texts(
        self,
        retrieved_standards: List[AchievementStandardReference],
    ) -> List[str]:
        texts: List[str] = []
        for standard in retrieved_standards[:3]:
            standard_label = (
                f"[{standard.standard_id}] {standard.standard_text}"
                if standard.standard_id
                else standard.standard_text
            )
            line = f"{standard_label} (관련도 {standard.relevance_score:.2f})"
            if line not in texts:
                texts.append(line)
        return texts

    def _create_rationale(self, llm_analysis: Any, primary_standard: AchievementStandardReference) -> str:
        """Create rationale for the recommendation."""
        standard_label = (
            f"[{primary_standard.standard_id}] {primary_standard.standard_text}"
            if primary_standard.standard_id
            else primary_standard.standard_text
        )
        level_text = self._level_to_korean(llm_analysis.detected_level)
        level_phrase = self._level_with_particle(level_text)
        return f"""학생의 현재 능력 수준을 '{level_text}'{level_phrase[len(level_text):]} 평가했습니다.
주요 학습 격차: {', '.join(llm_analysis.learning_gaps)}
관련 성취기준: {standard_label[:120]}...
신뢰도: {llm_analysis.confidence_score:.2f}"""

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
            recommended_level="중",
            rationale="분석 과정에서 오류가 발생하여 기본 추천을 제공합니다.",
            scaffolding_details=ScaffoldingLevel(
                level="중",
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
                standard_id="",
                grade=request.grade or "",
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
            related_achievement_standards=[],
            additional_notes=None
        )

    def _level_with_particle(self, level_korean: str) -> str:
        """
        Attach proper particle:
        - 상/중 -> 으로
        - 하 -> 로
        """
        if level_korean == "하":
            return f"{level_korean}로"
        return f"{level_korean}으로"

    def _get_persona_student(self, db: Session) -> Optional[Student]:
        return db.query(Student).order_by(Student.id.asc()).first()