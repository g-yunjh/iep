"""
LLM Service for analyzing teacher descriptions and generating scaffolding recommendations.
Uses Google Gemini models to process student descriptions and provide educational insights.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types

from ..schemas.rag import LLMAnalysisResult, AchievementStandardReference

logger = logging.getLogger(__name__)


def _google_api_key() -> Optional[str]:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


class LLMService:
    """
    Service for LLM-powered analysis of student descriptions and scaffolding recommendations.
    """

    def __init__(self, model: Optional[str] = None, temperature: float = 0.3):
        requested_model = model or os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
        self.model_name = requested_model
        self.fallback_models = [
            "gemini-2.0-flash",
            "gemini-2.5-flash",
        ]
        self.temperature = temperature
        self.logger = logging.getLogger(__name__)
        self.client: Optional[genai.Client] = None
        api_key = _google_api_key()
        if not api_key:
            raise ValueError(
                "Gemini API key is required. Set GOOGLE_API_KEY or GEMINI_API_KEY."
            )
        self.client = genai.Client(api_key=api_key)

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
            result_data = self._call_json_model(
                prompt=prompt,
                system_instruction=self._get_system_prompt(),
            )
            return self._parse_llm_response(result_data)

        except Exception as e:
            self.logger.error(
                "LLM analysis failed (%s): %s. "
                "Likely causes: invalid API key, quota/permission issue, network timeout, or Gemini API error.",
                e.__class__.__name__,
                str(e),
            )
            raise

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
            raise ValueError(
                f"Failed to parse Gemini JSON response: {e}"
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

    def analyze_career_skill_gap(
        self,
        current_skills: str,
        job_title: str,
        required_skills: List[str],
        outlook_scaffolding: str,
        grade: Optional[str] = None,
        disability_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze semantic skill gaps between student current skills and career requirements.
        Returns a JSON-compatible dict with keys:
        - current_level: List[str]
        - required_level: List[str]
        - gap_skills: List[str]
        - development_suggestions: List[str]
        """
        prompt = f"""
학생의 현재 역량과 직업 요구 역량을 문맥적으로 비교해 격차를 분석하세요.

학생 정보:
- 학년: {grade or "정보 없음"}
- 장애 유형: {disability_type or "정보 없음"}
- 현재 역량/학습 상태: {current_skills}

목표 직업:
- 직업명: {job_title}
- 요구 역량: {required_skills}
- 진로 전망 및 환경: {outlook_scaffolding or "정보 없음"}

요청:
1) 학생이 이미 보유한 역량(current_level)을 요구 역량 맥락에서 추출
2) 직업 적응을 위해 부족한 핵심 역량(gap_skills) 도출
3) 교육 가능한 형태의 구체적 제안(development_suggestions) 작성

반드시 유효한 JSON 객체만 출력:
{{
  "current_level": ["..."],
  "required_level": ["..."],
  "gap_skills": ["..."],
  "development_suggestions": ["..."]
}}
"""
        try:
            result = self._call_json_model(
                prompt=prompt.strip(),
                system_instruction="당신은 특수교육 진로지도 전문가입니다. 문맥 기반 역량 격차를 분석하고, 학생 맞춤 발달 제안을 제공합니다.",
            )
            return {
                "current_level": result.get("current_level", []),
                "required_level": result.get("required_level", required_skills),
                "gap_skills": result.get("gap_skills", []),
                "development_suggestions": result.get("development_suggestions", []),
            }
        except Exception as e:
            self.logger.error(
                "Career skill-gap analysis failed (%s): %s. "
                "Likely causes: invalid API key, quota/permission issue, network timeout, or Gemini API error.",
                e.__class__.__name__,
                str(e),
            )
            raise

    def generate_career_path(
        self,
        current_skills: str,
        job_title: str,
        required_skills: List[str],
        outlook_scaffolding: str,
        certifications: Optional[List[str]] = None,
        education_paths: Optional[List[str]] = None,
        disability_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate customized career path grounded in outlook_scaffolding.
        Returns:
        - stages: List[Dict[str, str]]
        - estimated_timeline: str
        """
        prompt = f"""
학생 맞춤 진로 로드맵을 생성하세요.

학생 현재 역량:
{current_skills}

목표 직업:
- 직업명: {job_title}
- 요구 역량: {required_skills}
- 관련 자격: {certifications or []}
- 관련 교육 경로: {education_paths or []}
- 진로 전망/근무 환경 정보: {outlook_scaffolding or "정보 없음"}
- 장애 유형: {disability_type or "정보 없음"}

요청:
1) outlook_scaffolding을 반영해 실제 진입 가능성을 고려한 단계 설계
2) 학생 수준에 맞춘 3~5개 단계(stages) 생성
3) 각 단계는 stage, focus, description 키를 포함
4) 예상 소요 기간(estimated_timeline) 제시

반드시 유효한 JSON 객체만 출력:
{{
  "stages": [
    {{"stage": "...", "focus": "...", "description": "..."}}
  ],
  "estimated_timeline": "..."
}}
"""
        try:
            result = self._call_json_model(
                prompt=prompt.strip(),
                system_instruction="당신은 특수교육 기반 진로설계 전문가입니다. 학생 맞춤형, 실행 가능한 단계 로드맵을 작성하세요.",
            )
            return {
                "stages": result.get("stages", []),
                "estimated_timeline": result.get("estimated_timeline", "개별 평가 필요"),
            }
        except Exception as e:
            self.logger.error(
                "Career path generation failed (%s): %s. "
                "Likely causes: invalid API key, quota/permission issue, network timeout, or Gemini API error.",
                e.__class__.__name__,
                str(e),
            )
            raise

    def _call_json_model(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """Call Gemini model and parse a JSON object response."""
        if not self.client:
            raise ValueError("Gemini client is not initialized. Check API key settings.")

        candidate_models: List[str] = []
        for model_name in [self.model_name, *self.fallback_models]:
            if model_name not in candidate_models:
                candidate_models.append(model_name)

        last_error: Optional[Exception] = None
        for model_name in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=self.temperature,
                        max_output_tokens=2000,
                        response_mime_type="application/json",
                    ),
                )
                result_text = response.text
                if not result_text:
                    raise ValueError("Empty response from Gemini model")
                if model_name != self.model_name:
                    self.logger.warning(
                        "Gemini model '%s' unavailable. Using fallback model '%s'.",
                        self.model_name,
                        model_name,
                    )
                    self.model_name = model_name
                return json.loads(self._extract_json_payload(result_text))
            except Exception as e:
                last_error = e
                self.logger.warning(
                    "Gemini generate_content failed with model '%s' (%s): %s",
                    model_name,
                    e.__class__.__name__,
                    str(e),
                )

        self.logger.error(
            "Gemini generate_content failed for all candidate models %s. Last error (%s): %s. "
            "Check API key validity, model availability, billing/quota, and network connectivity.",
            candidate_models,
            last_error.__class__.__name__ if last_error else "UnknownError",
            str(last_error) if last_error else "No error details",
        )
        if last_error:
            raise last_error
        raise RuntimeError("Gemini generate_content failed without error details")
