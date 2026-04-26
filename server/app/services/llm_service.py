"""
LLM Service for analyzing teacher descriptions and generating scaffolding recommendations.
Uses Google Gemini models to process student descriptions and provide educational insights.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

import google.generativeai as genai

from ..schemas.rag import LLMAnalysisResult, AchievementStandardReference

logger = logging.getLogger(__name__)


def _google_api_key() -> Optional[str]:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


class LLMService:
    """
    Service for LLM-powered analysis of student descriptions and scaffolding recommendations.
    """

    def __init__(self, model: Optional[str] = None, temperature: float = 0.3):
        self.model_name = model or os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash")
        self.temperature = temperature
        api_key = _google_api_key()
        if api_key:
            genai.configure(api_key=api_key)
        self.logger = logging.getLogger(__name__)

    def analyze_student_description(
        self,
        teacher_description: str,
        grade: str,
        subject: str,
        disability_type: str,
        retrieved_standards: List[AchievementStandardReference],
        past_feedback: Optional[List[Dict[str, Any]]] = None
    ) -> LLMAnalysisResult:
        """
        Analyze teacher/parent description using LLM to determine student's level and needs.

        Args:
            teacher_description: Description from teacher or parent
            grade: Student grade
            subject: Subject area
            disability_type: Type of disability
            retrieved_standards: Relevant achievement standards from RAG
            past_feedback: Previous feedback and performance data

        Returns:
            LLMAnalysisResult with detected level, gaps, and recommendations
        """

        if not _google_api_key():
            self.logger.error("GOOGLE_API_KEY or GEMINI_API_KEY is not set")
            return LLMAnalysisResult(
                detected_level="medium",
                learning_gaps=["API 키가 설정되지 않았습니다"],
                recommended_strategies=["GOOGLE_API_KEY 또는 GEMINI_API_KEY를 .env에 설정하세요"],
                confidence_score=0.0,
                analysis_summary="Gemini API 키가 없어 분석을 수행할 수 없습니다"
            )

        # Build context from retrieved standards
        standards_context = self._build_standards_context(retrieved_standards)

        # Build past feedback context
        feedback_context = self._build_feedback_context(past_feedback)

        # Create the analysis prompt
        prompt = self._create_analysis_prompt(
            teacher_description=teacher_description,
            grade=grade,
            subject=subject,
            disability_type=disability_type,
            standards_context=standards_context,
            feedback_context=feedback_context
        )

        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self._get_system_prompt(),
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=2000,
                    response_mime_type="application/json",
                ),
            )

            response = model.generate_content(prompt)
            result_text = response.text
            if not result_text:
                raise ValueError("Empty response from LLM")

            # Parse JSON response
            result_data = json.loads(self._extract_json_payload(result_text))
            return self._parse_llm_response(result_data)

        except Exception as e:
            self.logger.error(f"Error in LLM analysis: {e}")
            # Return a fallback result
            return LLMAnalysisResult(
                detected_level="medium",
                learning_gaps=["분석 중 오류가 발생했습니다"],
                recommended_strategies=["기본적인 지원 전략을 적용하세요"],
                confidence_score=0.5,
                analysis_summary="LLM 분석에 실패하여 기본 추천을 제공합니다"
            )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM analysis."""
        return """당신은 특수교육 전문가로서, 발달장애 아동의 학습 상태를 분석하고 적절한 스캐폴딩 전략을 추천하는 AI 어시스턴트입니다.

다음 지침을 따라 분석을 수행하세요:

1. **장애 유형 이해**: 지적장애, 학습장애, 자폐성장애 등의 특성을 고려하여 분석
2. **능력 수준 평가**: 제공된 성취기준 및 diagnostic_criteria와 교사 설명의 일치도를 비교하여 high/medium/low로 분류
3. **학습 격차 식별**: 각 diagnostic_criteria와 비교해 학생이 못하고 있는 지점을 구체 문장으로 추출
4. **스캐폴딩 전략 추천**: 아동의 수준에 맞는 구체적이고 실천 가능한 전략 제안
5. **신뢰도 평가**: 분석의 확실성을 0.0-1.0 사이의 점수로 표시

수준 판별 규칙:
- high: 기준의 대부분(약 70% 이상)에 부합하고 부분적 지원만 필요
- medium: 일부 기준(약 40~70%)에 부합하며 핵심 기능에 간헐적 지원 필요
- low: 기준 충족이 제한적(약 40% 미만)이고 핵심 기능에서 지속적 지원 필요

중요:
- 출력은 반드시 유효한 JSON 객체 1개만 출력
- 마크다운(```), 주석, 설명 문장, 접두/접미 텍스트를 절대 포함하지 말 것
- 아래 스키마는 RAGAnalysisResult의 llm_analysis 필드로 바로 들어갈 값이므로 키 이름을 정확히 지킬 것

응답 JSON 스키마:
{
  "detected_level": "high|medium|low",
  "learning_gaps": ["격차1", "격차2", ...],
  "recommended_strategies": ["전략1", "전략2", ...],
  "confidence_score": 0.0-1.0,
  "analysis_summary": "분석 요약문"
}"""

    def _create_analysis_prompt(
        self,
        teacher_description: str,
        grade: str,
        subject: str,
        disability_type: str,
        standards_context: str,
        feedback_context: str
    ) -> str:
        """Create the analysis prompt for the LLM."""

        prompt = f"""
다음 정보를 바탕으로 학생의 학습 수준을 분석하고 스캐폴딩 전략을 추천해주세요:

**학생 정보:**
- 학년: {grade}
- 과목: {subject}
- 장애 유형: {disability_type}

**선생님/부모님 설명:**
{teacher_description}

**관련 성취기준:**
{standards_context}

**과거 피드백 이력:**
{feedback_context}

**분석 요청:**
1. retrieved_standards의 각 diagnostic_criteria를 기준으로 teacher_description과 비교해 학생의 현재 수준(high/medium/low)을 판별하세요
2. learning_gaps는 반드시 diagnostic_criteria와의 비교 근거가 드러나도록 구체적으로 작성하세요
3. 적절한 스캐폴딩 전략을 추천하세요
4. 분석의 신뢰도를 평가하세요

응답은 반드시 유효한 JSON 객체만 출력하고, 마크다운/설명문을 포함하지 마세요.
"""
        return prompt.strip()

    def _build_standards_context(self, standards: List[AchievementStandardReference]) -> str:
        """Build context string from retrieved achievement standards."""
        if not standards:
            return "관련 성취기준이 없습니다."

        context_parts = []
        for i, standard in enumerate(standards, 1):
            criteria_text = (
                "\n".join(f"     - {criterion}" for criterion in standard.diagnostic_criteria)
                if standard.diagnostic_criteria
                else "     - (진단 준거 정보 없음)"
            )
            context_parts.append(f"""
{i}. {standard.grade} {standard.subject} ({standard.disability_type})
   성취기준: {standard.standard_text}
   diagnostic_criteria:
{criteria_text}
   관련도: {standard.relevance_score:.2f}
""")

        return "\n".join(context_parts)

    def _build_feedback_context(self, past_feedback: Optional[List[Dict[str, Any]]]) -> str:
        """Build context string from past feedback."""
        if not past_feedback:
            return "과거 피드백 이력이 없습니다."

        context_parts = []
        for feedback in past_feedback[-3:]:  # 최근 3개만
            performance = feedback.get('performance', 'N/A')
            effectiveness = feedback.get('scaffolding_effectiveness', 'N/A')
            created_at = feedback.get('created_at', 'N/A')

            context_parts.append(f"""
- 날짜: {created_at}
  수행도: {performance}
  스캐폴딩 효과: {effectiveness}
""")

        return "\n".join(context_parts) if context_parts else "과거 피드백이 유효하지 않습니다."

    def _parse_llm_response(self, response_data: Dict[str, Any]) -> LLMAnalysisResult:
        """Parse the LLM JSON response into a structured result."""
        try:
            if "llm_analysis" in response_data and isinstance(response_data["llm_analysis"], dict):
                response_data = response_data["llm_analysis"]

            detected_level = response_data.get('detected_level', 'medium')
            learning_gaps = response_data.get('learning_gaps', [])
            recommended_strategies = response_data.get('recommended_strategies', [])
            confidence_score = float(response_data.get('confidence_score', 0.5))
            analysis_summary = response_data.get('analysis_summary', '분석 완료')

            # Validate detected_level
            if detected_level not in ['high', 'medium', 'low']:
                detected_level = 'medium'

            # Ensure lists are actually lists
            if not isinstance(learning_gaps, list):
                learning_gaps = [str(learning_gaps)]
            if not isinstance(recommended_strategies, list):
                recommended_strategies = [str(recommended_strategies)]

            # Clamp confidence score
            confidence_score = max(0.0, min(1.0, confidence_score))

            return LLMAnalysisResult(
                detected_level=detected_level,
                learning_gaps=learning_gaps,
                recommended_strategies=recommended_strategies,
                confidence_score=confidence_score,
                analysis_summary=analysis_summary
            )

        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return LLMAnalysisResult(
                detected_level="medium",
                learning_gaps=["응답 파싱 오류"],
                recommended_strategies=["기본 전략 적용"],
                confidence_score=0.3,
                analysis_summary="LLM 응답 파싱에 실패했습니다"
            )

    def _extract_json_payload(self, raw_text: str) -> str:
        """Extract JSON payload from model output, tolerating fenced blocks."""
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # Remove opening/closing fences if present.
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text
