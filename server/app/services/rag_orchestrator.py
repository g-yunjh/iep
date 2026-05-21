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

ICT_CONTEXT_TERMS = (
    "정보통신", "컴퓨터", "스마트", "태블릿", "모니터", "마우스", "키보드",
    "클릭", "아이콘", "메뉴", "프로그램", "응용 프로그램", "앱", "ppt",
    "파워포인트", "글자 크기", "글꼴", "슬라이드", "화면", "디지털",
)

MIXED_SUBJECT_ALIASES = {
    "integrated_subjects": {"integrated_subjects", "통합교과", "통합 교과"},
    "elective_subjects": {"elective_subjects", "선택교과", "선택 교과"},
}

DOMAIN_LABELS = {
    "right_living": "바른 생활",
    "wise_living": "슬기로운 생활",
    "joyful_living": "즐거운 생활",
    "information_communication": "정보통신",
    "life_english": "생활영어",
    "health": "보건",
}

DOMAIN_ROUTE_RULES = {
    "integrated_subjects": {
        "right_living": {
            "strong": (
                "가방", "사물함", "알림장", "등교", "정리", "정돈", "제자리",
                "청소", "쓰레기", "책임", "역할", "규칙", "규범", "예절",
                "습관", "실천", "차례", "순서판", "루틴", "해야 할 일",
                "준비물", "공동생활", "바르게",
            ),
            "weak": ("교실", "학교생활", "생활", "도움", "멈", "시각", "번호"),
        },
        "wise_living": {
            "strong": (
                "탐색", "알아보", "살펴보", "관찰", "비교", "장소", "시설",
                "도구", "쓰임새", "이용", "자연", "계절", "날씨", "동식물",
                "마을", "지역사회", "학교의 모습",
            ),
            "weak": ("교실", "학교", "생활", "물건"),
        },
        "joyful_living": {
            "strong": (
                "놀이", "노래", "음악", "미술", "그림", "그리", "만들",
                "꾸미", "춤", "움직임", "신체 표현", "표현 활동", "작품",
                "악기", "감상",
            ),
            "weak": ("친구", "함께", "활동", "표현"),
        },
    },
    "elective_subjects": {
        "information_communication": {
            "strong": ICT_CONTEXT_TERMS + (
                "정보 기기", "응용프로그램", "기본 프로그램", "인터넷",
                "소프트웨어", "앱", "전원", "입력", "출력",
            ),
            "weak": ("매체", "선택", "조작", "순서", "화면"),
        },
        "life_english": {
            "strong": (
                "영어", "알파벳", "낱말", "어구", "영단어", "영문장",
                "듣기", "말하기", "발음", "철자", "push", "pull", "open", "close",
            ),
            "weak": ("문장", "표현", "쓰기", "읽기", "말"),
        },
        "health": {
            "strong": (
                "보건", "건강", "질병", "위생", "감염", "손 씻", "약",
                "병원", "영양", "식습관", "운동", "수면", "스트레스",
                "흡연", "음주", "성교육", "안전사고", "응급",
            ),
            "weak": ("몸", "마음", "생활 습관", "예방"),
        },
    },
}

STANDARD_PREFIX_LABELS = {
    "국어": "국어",
    "수학": "수학",
    "사회": "사회",
    "과학": "과학",
    "실과": "실과",
    "체육": "체육",
    "음악": "음악",
    "미술": "미술",
    "도덕": "도덕",
    "영어": "영어",
    "정통": "정보통신",
    "생영": "생활영어",
    "보건": "보건",
    "바생": "바른 생활",
    "슬생": "슬기로운 생활",
    "즐생": "즐거운 생활",
    "진로": "진로직업",
    "진직": "진로직업",
}


class RAGOrchestrator:
    """
    Main orchestrator for the RAG pipeline.
    Handles the complete flow from request to recommendation.
    """

    def __init__(self):
        self.rag_service = RAGService()
        self.llm_service: Optional[LLMService] = None
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

            # Step 3: Analyze with LLM by default; callers may set use_llm=false
            # for a fast curriculum-grounded fallback.
            if request.use_llm:
                try:
                    self.llm_service = self.llm_service or LLMService()
                    llm_analysis = self.llm_service.analyze_student_description(
                        teacher_description=request.teacher_description,
                        grade=request.grade,
                        subject=request.subject,
                        disability_type=student.disability_type or "",
                        retrieved_standards=retrieved_standards,
                        past_feedback=past_feedback,
                        student_profile=self._student_profile_context(student),
                    )
                except Exception as llm_error:
                    self.logger.warning(
                        "LLM unavailable for scaffolding analysis (%s): %s. "
                        "Using rule-based fallback analysis.",
                        llm_error.__class__.__name__,
                        str(llm_error),
                    )
                    llm_analysis = self._create_rule_based_analysis(request, retrieved_standards)
            else:
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
                llm_analysis=self._create_rule_based_analysis(request, []),
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
        domain_scores = self._route_mixed_subject_domains(request)
        routed_context = " ".join(
            f"{DOMAIN_LABELS.get(domain, domain)} {domain}"
            for domain, score in sorted(domain_scores.items(), key=lambda item: item[1], reverse=True)
            if score >= 1.0
        )
        search_query = f"{request.subject} {routed_context} {disability_type} {request.teacher_description}"

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
                k=15,  # Retrieve more, then rerank with subject/domain context.
            )
            if search_results:
                break

        search_results = self._rerank_curriculum_results(search_results, request, domain_scores)[:3]

        # Convert to AchievementStandardReference objects
        standards = []
        for result in search_results:
            metadata = result.get("metadata", {})
            content = result.get("content", "")
            standard_id = str(metadata.get("achievement_standard_id", "") or "")
            standard = AchievementStandardReference(
                standard_id=standard_id,
                grade=metadata.get("grade", ""),
                subject=self._infer_standard_subject_label(metadata, standard_id, content),
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

    def _student_profile_context(self, student: Student) -> Dict[str, Any]:
        """Return compact profile context for Gemini prompt composition."""
        return {
            "name": student.name,
            "current_level": student.current_level,
            "disability_type": student.disability_type,
            "additional_diagnoses": student.additional_diagnoses,
            "behavioral_traits": student.behavioral_traits,
        }

    def _rerank_curriculum_results(
        self,
        search_results: List[Dict[str, Any]],
        request: ScaffoldingRecommendationRequest,
        domain_scores: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """Boost domain-specific matches that vector search can under-rank."""
        if not search_results:
            return []

        request_text = f"{request.subject} {request.teacher_description}".lower()
        ict_context = self._has_ict_context(request_text)
        domain_scores = domain_scores or self._route_mixed_subject_domains(request)
        strongest_domain_score = max(domain_scores.values(), default=0.0)

        ranked: List[Tuple[float, int, Dict[str, Any]]] = []
        for index, result in enumerate(search_results):
            metadata = result.get("metadata", {})
            content = str(result.get("content", ""))
            standard_id = str(metadata.get("achievement_standard_id", "") or "")
            domain = str(metadata.get("domain", "") or "")
            source = str(metadata.get("source", "") or "")

            score = float(result.get("score") or 0.0)
            priority = score

            if domain_scores:
                domain_score = domain_scores.get(domain, 0.0)
                if domain_score:
                    priority += min(0.65, domain_score * 0.08)
                elif strongest_domain_score >= 4.0 and domain in DOMAIN_LABELS:
                    priority -= 0.18

            priority += self._specific_standard_boost(
                request_text=request_text,
                standard_id=standard_id,
                domain=domain,
                content=content,
            )

            if ict_context:
                combined = f"{content} {standard_id} {domain} {source}".lower()
                if "정통" in standard_id:
                    priority += 0.45
                if domain == "information_communication" or "information_communication" in source:
                    priority += 0.35
                if "정보통신" in combined:
                    priority += 0.20
                if any(term in combined for term in ("응용 프로그램", "기본 프로그램", "아이콘", "조작 버튼", "컴퓨터")):
                    priority += 0.18
                # 생활영어 documents contain words like media/sentence/input and can
                # look similar to ICT observations, but they are usually not the
                # right evidence for PPT/menu/clicking tasks.
                if "생영" in standard_id or domain == "life_english":
                    priority -= 0.45

            ranked.append((priority, index, result))

        ranked.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        return [result for _, _, result in ranked]

    def _specific_standard_boost(
        self,
        request_text: str,
        standard_id: str,
        domain: str,
        content: str,
    ) -> float:
        """Fine tune standards inside an already routed mixed-subject domain."""
        boost = 0.0
        combined = f"{content} {standard_id}".lower()

        if domain == "right_living":
            routine_terms = (
                "가방", "사물함", "알림장", "정리", "정돈", "제자리",
                "청소", "책꽂이", "도구함", "역할", "책임", "해야 할 일",
            )
            if any(term in request_text for term in routine_terms):
                if standard_id == "2바생01-05" or "역할과 책임" in combined or "정해 진 자리에 정리" in combined:
                    boost += 0.55
                if standard_id in {"2바생01-06", "2바생01-07"}:
                    boost -= 0.12

            rule_terms = ("규칙", "규범", "약속", "공동생활")
            if any(term in request_text for term in rule_terms) and standard_id == "2바생01-06":
                boost += 0.35

            etiquette_terms = ("예절", "인사", "차례", "존중")
            if any(term in request_text for term in etiquette_terms) and standard_id == "2바생01-07":
                boost += 0.35

        if domain == "information_communication":
            if any(term in request_text for term in ("ppt", "파워포인트", "앱", "프로그램", "아이콘", "메뉴")):
                if standard_id == "12정통01-03" or "응용 프로그램" in combined:
                    boost += 0.35
                elif standard_id == "9정통01-03" or "기본 프로그램" in combined:
                    boost += 0.18

        return boost

    def _route_mixed_subject_domains(
        self,
        request: ScaffoldingRecommendationRequest,
    ) -> Dict[str, float]:
        """Classify mixed-subject tabs into internal curriculum domains."""
        subject_group = self._mixed_subject_group(request.subject)
        if not subject_group:
            return {}

        rules = DOMAIN_ROUTE_RULES.get(subject_group, {})
        text = f"{request.subject} {request.teacher_description}".lower()
        scores: Dict[str, float] = {}

        for domain, groups in rules.items():
            score = 0.0
            for term in groups.get("strong", ()):
                if str(term).lower() in text:
                    score += 2.0
            for term in groups.get("weak", ()):
                if str(term).lower() in text:
                    score += 0.6
            if DOMAIN_LABELS.get(domain, "").lower() in text:
                score += 3.0
            if score:
                scores[domain] = score

        # In 통합교과, routine/role/action words should win over exploratory words
        # when both appear in school-life observations.
        if subject_group == "integrated_subjects":
            right = scores.get("right_living", 0.0)
            wise = scores.get("wise_living", 0.0)
            if right >= 4.0:
                scores["right_living"] = right + 1.0
                if wise:
                    scores["wise_living"] = max(0.0, wise - 1.5)

        return scores

    def _mixed_subject_group(self, subject: str) -> Optional[str]:
        raw = str(subject or "").strip()
        normalized = raw.lower().replace("-", "_").replace(" ", "_")
        for group, aliases in MIXED_SUBJECT_ALIASES.items():
            normalized_aliases = {
                alias.lower().replace("-", "_").replace(" ", "_")
                for alias in aliases
            }
            if raw in aliases or normalized in normalized_aliases:
                return group
        return None

    def _has_ict_context(self, text: str) -> bool:
        lowered = (text or "").lower()
        return any(term.lower() in lowered for term in ICT_CONTEXT_TERMS)

    def _infer_standard_subject_label(
        self,
        metadata: Dict[str, Any],
        standard_id: str,
        content: str,
    ) -> str:
        """Display a user-facing subject label, including elective subdomains."""
        prefix_match = re.match(r"^\d+([가-힣]+)\d", standard_id or "")
        if prefix_match:
            prefix = prefix_match.group(1)
            if prefix in STANDARD_PREFIX_LABELS:
                return STANDARD_PREFIX_LABELS[prefix]

        domain = str(metadata.get("domain", "") or "")
        if domain == "information_communication":
            return "정보통신"
        if domain == "life_english":
            return "생활영어"

        subject_label = str(metadata.get("subject_label", "") or "").strip()
        if subject_label:
            return subject_label

        subject = str(metadata.get("subject", "") or "").strip()
        if subject:
            return subject

        if "정보통신" in content:
            return "정보통신"
        return ""

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
            teacher_description=request.teacher_description,
            detected_level=llm_analysis.detected_level,
            strategies=final_strategies,
            primary_standard=primary_standard
        )

        # Create rationale
        rationale = self._create_rationale(llm_analysis, primary_standard)
        teaching_points = self._normalize_teaching_points(
            getattr(llm_analysis, "teaching_points", []),
            teacher_description=request.teacher_description,
            primary_standard=primary_standard,
        )

        return ScaffoldingRecommendation(
            recommended_level=self._level_to_korean(llm_analysis.detected_level),
            rationale=rationale,
            scaffolding_details=scaffolding_details,
            achievement_standard=primary_standard,
            teaching_points=teaching_points,
            related_achievement_standards=self._collect_related_standard_texts(retrieved_standards),
            additional_notes=None
        )

    def _normalize_teaching_points(
        self,
        points: List[str],
        teacher_description: str,
        primary_standard: Optional[AchievementStandardReference],
    ) -> List[str]:
        cleaned: List[str] = []
        for point in points or []:
            text = re.sub(r"\s+", " ", str(point or "")).strip()
            text = re.sub(r"^(?:[-*•·]\s*|\d+[.)]\s*)+", "", text).strip()
            if text and text not in cleaned:
                cleaned.append(text)

        if len(cleaned) < 4:
            for point in self._fallback_teaching_points(teacher_description, primary_standard):
                if point not in cleaned:
                    cleaned.append(point)

        return cleaned[:4]

    def _fallback_teaching_points(
        self,
        teacher_description: str,
        primary_standard: Optional[AchievementStandardReference],
    ) -> List[str]:
        text = f"{teacher_description or ''} {primary_standard.standard_text if primary_standard else ''}".lower()

        if self._has_ict_context(text):
            points = [
                "PPT 활동 전 번호 안내 카드를 모니터 옆에 배치",
                "클릭 순서는 한 번에 한 단계씩 짧게 안내",
                "시각 단서 없는 구두 지시만으로 진행하지 않기",
                "첫 단계에서 멈출 때 도움 요청 신호를 관찰",
            ]
        else:
            points = [
                "수업 전 학생의 컨디션과 주의 상태를 확인",
                "처음 과제는 한 단계씩 짧게 제시",
                "막히는 지점은 시각 단서로 즉시 보완",
                "완료 행동을 보고 다음 지원 강도를 조절",
            ]

        if primary_standard and primary_standard.standard_id:
            points[-1] = f"{primary_standard.standard_id} 기준에 맞춰 성공 행동을 관찰"

        return points[:4]

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
            teaching_points=self._fallback_teaching_points(
                request.teacher_description,
                retrieved_standards[0] if retrieved_standards else None,
            ),
            confidence_score=confidence,
            analysis_summary="외부 LLM 호출이 불가해 규칙 기반 분석으로 대체했습니다.",
        )

    def _create_scaffolding_details(
        self,
        teacher_description: str,
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

        activities = self._build_learning_activities(
            teacher_description=teacher_description,
            primary_standard=primary_standard,
            strategies=strategies,
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

    def _build_learning_activities(
        self,
        teacher_description: str,
        primary_standard: AchievementStandardReference,
        strategies: List[str],
    ) -> List[LearningActivity]:
        """Create service-facing activity cards instead of exposing raw curriculum rows."""
        context = " ".join(
            [
                teacher_description or "",
                primary_standard.standard_text or "",
                " ".join(primary_standard.activities or []),
                " ".join(str(item) for item in strategies or []),
            ]
        )

        if self._has_ict_context(context) or "정보통신" in (primary_standard.subject or ""):
            return [
                LearningActivity(
                    name="아이콘 순서 카드로 따라 하기",
                    description="PPT 글자 크기 변경에 필요한 아이콘을 1-2-3 번호 카드로 제시하고, 학생이 카드 순서대로 클릭해 과제를 완수하게 합니다.",
                    duration=None,
                    materials=["번호 안내 카드", "PPT 실행 화면"],
                ),
                LearningActivity(
                    name="메뉴 위치 표시 후 점진적 제거",
                    description="처음에는 클릭 위치를 색 표시나 스티커로 안내하고, 성공하면 표시를 하나씩 줄여 독립 수행으로 옮깁니다.",
                    duration=None,
                    materials=["색 표시 스티커", "체크리스트"],
                ),
                LearningActivity(
                    name="구두 지시와 시각 단서 함께 제공",
                    description="말 지시는 한 문장·한 단계로 줄이고, 같은 순서가 적힌 시각 자료를 동시에 보여 주어 첫 단계에서 멈추지 않게 합니다.",
                    duration=None,
                    materials=["단계 카드"],
                ),
                LearningActivity(
                    name="도움 요청 신호 연습",
                    description="시각 자료 없이 멈추는 조건에서는 도움 요청 카드나 손들기 신호를 먼저 연습해, 막힌 지점에서 도움을 요청하도록 지도합니다.",
                    duration=None,
                    materials=["도움 요청 카드"],
                ),
            ]

        activities: List[LearningActivity] = []
        for idx, activity_text in enumerate((primary_standard.activities or [])[:4], start=1):
            cleaned_activity = self._to_action_phrase(activity_text)
            activities.append(
                LearningActivity(
                    name=self._activity_title(cleaned_activity, idx),
                    description=cleaned_activity,
                    duration=None,
                    materials=None,
                )
            )

        return activities

    def _activity_title(self, activity_text: str, index: int) -> str:
        text = re.sub(r"^(교육과정|적용 시 고려사항|교육과정 내용요소)\s*[:：]\s*", "", activity_text or "").strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            return f"추천 활동 {index}"
        first_clause = re.split(r"[.。]|,|·", text)[0].strip()
        if 6 <= len(first_clause) <= 24:
            return first_clause
        return f"추천 활동 {index}"

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
