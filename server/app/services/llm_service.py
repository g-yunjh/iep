"""
LLM Service for analyzing teacher descriptions and generating scaffolding recommendations.
Gemini-only implementation.
"""

import json
import logging
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types

from ..core.config import settings
from ..schemas.rag import LLMAnalysisResult, AchievementStandardReference
from ..utils.json_utils import parse_json_with_salvage

logger = logging.getLogger(__name__)


def _coerce_json_string_list(items: Any) -> List[str]:
    """로컬 LLM이 문자열 리스트 대신 dict 등을 넣는 경우를 문자열로 평탄화."""
    if items is None:
        return []
    if isinstance(items, str):
        return [items.strip()] if items.strip() else []
    if not isinstance(items, list):
        return [str(items)] if str(items).strip() else []

    out: List[str] = []
    for item in items:
        if isinstance(item, str):
            if item.strip():
                out.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("skill_name") or item.get("name") or item.get("text") or item.get("gap")
            level = item.get("level") or item.get("target_level")
            if name is not None and str(name).strip():
                line = str(name).strip()
                if level is not None and str(level).strip():
                    line = f"{line} ({level})"
                out.append(line)
            else:
                out.append("; ".join(f"{k}: {v}" for k, v in item.items() if v is not None))
        else:
            s = str(item).strip()
            if s:
                out.append(s)
    return out


def _google_api_key() -> Optional[str]:
    return settings.resolved_google_api_key


def _trim_text(value: Any, limit: int = 180) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)].rstrip() + "..."


LLM_ANALYSIS_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "detected_level": {"type": "string", "enum": ["high", "medium", "low"]},
        "learning_gaps": {"type": "array", "items": {"type": "string"}},
        "recommended_strategies": {"type": "array", "items": {"type": "string"}},
        "teaching_points": {"type": "array", "items": {"type": "string"}},
        "confidence_score": {"type": "number"},
        "analysis_summary": {"type": "string"},
    },
    "required": [
        "detected_level",
        "learning_gaps",
        "recommended_strategies",
        "teaching_points",
        "confidence_score",
        "analysis_summary",
    ],
}

CAREER_SKILL_GAP_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "current_level": {"type": "array", "items": {"type": "string"}},
        "required_level": {"type": "array", "items": {"type": "string"}},
        "gap_skills": {"type": "array", "items": {"type": "string"}},
        "development_suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "current_level",
        "required_level",
        "gap_skills",
        "development_suggestions",
    ],
}

CAREER_PATH_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "stages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "stage": {"type": "string"},
                    "focus": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["stage", "focus", "description"],
            },
        },
        "estimated_timeline": {"type": "string"},
    },
    "required": ["stages", "estimated_timeline"],
}

CAREER_RECOMMENDATION_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "recommended_careers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "job_title": {"type": "string"},
                    "match_score": {"type": "number"},
                    "required_skills": {"type": "array", "items": {"type": "string"}},
                    "outlook": {"type": "string"},
                },
                "required": ["job_title", "match_score", "required_skills", "outlook"],
            },
        },
        "skill_gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "job_title": {"type": "string"},
                    "current_level": {"type": "array", "items": {"type": "string"}},
                    "required_level": {"type": "array", "items": {"type": "string"}},
                    "gap_skills": {"type": "array", "items": {"type": "string"}},
                    "development_suggestions": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "job_title",
                    "current_level",
                    "required_level",
                    "gap_skills",
                    "development_suggestions",
                ],
            },
        },
        "career_paths": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target_career": {"type": "string"},
                    "stages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "stage": {"type": "string"},
                                "focus": {"type": "string"},
                                "description": {"type": "string"},
                            },
                            "required": ["stage", "focus", "description"],
                        },
                    },
                    "estimated_timeline": {"type": "string"},
                },
                "required": ["target_career", "stages", "estimated_timeline"],
            },
        },
    },
    "required": ["recommended_careers", "skill_gaps", "career_paths"],
}

CAREER_QUERY_PROFILE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "recommended_query": {"type": "string"},
        "prefer_keywords": {"type": "array", "items": {"type": "string"}},
        "avoid_keywords": {"type": "array", "items": {"type": "string"}},
        "student_strengths": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["recommended_query", "prefer_keywords", "avoid_keywords", "student_strengths"],
}


class LLMService:
    """
    Service for LLM-powered analysis of student descriptions and scaffolding recommendations.
    """

    def __init__(self, model: Optional[str] = None, temperature: float = 0.3):
        requested_model = model or settings.gemini_chat_model
        self.model_name = requested_model

        self.temperature = temperature
        self.logger = logging.getLogger(__name__)
        api_key = _google_api_key()
        if not api_key:
            raise ValueError(
                "Gemini API key is required. Set GOOGLE_API_KEY or GEMINI_API_KEY."
            )
        self.client: Optional[genai.Client] = genai.Client(api_key=api_key)

    def analyze_student_description(
        self,
        teacher_description: str,
        grade: Optional[str],
        subject: str,
        disability_type: str,
        retrieved_standards: List[AchievementStandardReference],
        past_feedback: Optional[List[Dict[str, Any]]] = None,
        student_profile: Optional[Dict[str, Any]] = None,
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
            student_profile=student_profile,
            standards_context=standards_context,
            feedback_context=feedback_context
        )

        try:
            result_data = self._call_json_model(
                prompt=prompt,
                system_instruction=self._get_system_prompt(),
                response_schema=LLM_ANALYSIS_RESPONSE_SCHEMA,
                max_output_tokens=settings.gemini_analysis_max_output_tokens,
                trace_label="scaffolding_analysis",
            )
            return self._parse_llm_response(result_data)

        except Exception as e:
            self.logger.error(
                "LLM analysis failed (%s): %s. "
                "Likely causes: Gemini quota/network/model availability issue.",
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
5. **수업 체크포인트 작성**: 학생 프로필, 과거 피드백, 현재 추천 전략, 근거 성취기준을 종합해 교사가 수업 직전에 볼 4개 문장 작성
6. **신뢰도 평가**: 분석의 확실성을 0.0-1.0 사이의 점수로 표시

수준 판별 규칙:
- high: 기준의 대부분(약 70% 이상)에 부합하고 부분적 지원만 필요
- medium: 일부 기준(약 40~70%)에 부합하며 핵심 기능에 간헐적 지원 필요
- low: 기준 충족이 제한적(약 40% 미만)이고 핵심 기능에서 지속적 지원 필요

중요:
- 출력은 반드시 유효한 JSON 객체 1개만 출력
- 마크다운(```), 주석, 설명 문장, 접두/접미 텍스트를 절대 포함하지 말 것
- 아래 스키마는 RAGAnalysisResult의 llm_analysis 필드로 바로 들어갈 값이므로 키 이름을 정확히 지킬 것
- teaching_points는 정확히 4개 작성
- teaching_points는 교사용 수업 전 체크리스트 문장으로 작성
- teaching_points는 과도하게 기술적인 설명이 아니라 바로 실행할 행동으로 작성
- teaching_points 각 문장은 45자 이내를 권장

응답 JSON 스키마:
{
  "detected_level": "high|medium|low",
  "learning_gaps": ["격차1", "격차2", ...],
  "recommended_strategies": ["전략1", "전략2", ...],
  "teaching_points": ["체크포인트1", "체크포인트2", "체크포인트3", "체크포인트4"],
  "confidence_score": 0.0-1.0,
  "analysis_summary": "분석 요약문"
}"""

    def _create_analysis_prompt(
        self,
        teacher_description: str,
        grade: Optional[str],
        subject: str,
        disability_type: str,
        student_profile: Optional[Dict[str, Any]],
        standards_context: str,
        feedback_context: str
    ) -> str:
        """Create the analysis prompt for the LLM."""
        profile = student_profile or {}

        prompt = f"""
다음 정보를 바탕으로 학생의 학습 수준을 분석하고 스캐폴딩 전략을 추천해주세요:

**학생 정보:**
- 학년: {grade or "정보 없음"}
- 과목: {subject}
- 장애 유형: {disability_type}
- 현재 수준: {profile.get("current_level") or "정보 없음"}
- 동반 진단: {profile.get("additional_diagnoses") or "정보 없음"}
- 과제·주의 특성: {profile.get("behavioral_traits") or "정보 없음"}

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
4. teaching_points는 교사가 수업 직전 확인할 4개의 짧은 체크포인트로 작성하세요
   - 학생 프로필, 과거 피드백, 이번 추천 전략, 근거 성취기준을 모두 반영하세요
   - "준비할 것", "지시 방식", "주의할 조건", "관찰할 성공 기준"이 드러나게 작성하세요
   - 각 문장은 45자 이내로 짧고 자연스럽게 작성하세요
5. 분석의 신뢰도를 평가하세요

응답은 반드시 유효한 JSON 객체만 출력하고, 마크다운/설명문을 포함하지 마세요.
"""
        return prompt.strip()

    def _build_standards_context(self, standards: List[AchievementStandardReference]) -> str:
        """Build context string from retrieved achievement standards."""
        if not standards:
            return "관련 성취기준이 없습니다."

        context_parts = []
        for i, standard in enumerate(standards[:1], 1):
            criteria_text = (
                "\n".join(
                    f"     - {_trim_text(criterion, 120)}"
                    for criterion in standard.diagnostic_criteria[:3]
                )
                if standard.diagnostic_criteria
                else "     - (진단 준거 정보 없음)"
            )
            context_parts.append(f"""
{i}. {standard.grade} {standard.subject} ({standard.disability_type})
   성취기준: {_trim_text(standard.standard_text, 160)}
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
        for feedback in past_feedback[-2:]:  # 최근 2개만
            performance = _trim_text(feedback.get('performance', 'N/A'), 120)
            effectiveness = _trim_text(feedback.get('scaffolding_effectiveness', 'N/A'), 120)
            teacher_description = _trim_text(feedback.get('teacher_description', ''), 160)
            detected_level = ""
            llm_analysis = feedback.get("llm_analysis") or {}
            if isinstance(llm_analysis, dict):
                detected_level = _trim_text(llm_analysis.get("detected_level", ""), 40)
            created_at = feedback.get('created_at', 'N/A')

            context_parts.append(f"""
- 날짜: {created_at}
  관찰 기록: {teacher_description or "N/A"}
  수행도: {performance}
  스캐폴딩 효과: {effectiveness}
  최근 수준: {detected_level or "N/A"}
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
            teaching_points = response_data.get('teaching_points', [])
            confidence_score = float(response_data.get('confidence_score', 0.5))
            analysis_summary = response_data.get('analysis_summary', '분석 완료')
            if not isinstance(analysis_summary, str):
                analysis_summary = str(analysis_summary) if analysis_summary is not None else "분석 완료"

            # Validate detected_level
            if detected_level not in ['high', 'medium', 'low']:
                detected_level = 'medium'

            learning_gaps = _coerce_json_string_list(learning_gaps)
            recommended_strategies = _coerce_json_string_list(recommended_strategies)
            teaching_points = _coerce_json_string_list(teaching_points)
            if not learning_gaps:
                learning_gaps = ["교사 설명만으로 세부 격차를 특정하기 어렵습니다."]
            if not recommended_strategies:
                recommended_strategies = ["단계별 지원과 시각 단서를 활용합니다."]

            # Clamp confidence score
            confidence_score = max(0.0, min(1.0, confidence_score))

            return LLMAnalysisResult(
                detected_level=detected_level,
                learning_gaps=learning_gaps,
                recommended_strategies=recommended_strategies,
                teaching_points=teaching_points[:4],
                confidence_score=confidence_score,
                analysis_summary=analysis_summary
            )

        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            raise ValueError(
                f"Failed to parse Gemini JSON response: {e}"
            )

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
                response_schema=CAREER_SKILL_GAP_RESPONSE_SCHEMA,
                max_output_tokens=settings.gemini_gap_max_output_tokens,
                trace_label="career_skill_gap",
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
                "Likely causes: Gemini quota/network/model availability issue.",
                e.__class__.__name__,
                str(e),
            )
            raise

    def generate_career_recommendation(
        self,
        current_skills: str,
        career_candidates: List[Dict[str, Any]],
        grade: Optional[str] = None,
        interests: Optional[List[str]] = None,
        disability_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate the complete career recommendation from RAG-retrieved candidates.
        The model may only choose from the provided candidates.
        """
        candidate_context = self._build_career_candidate_context(career_candidates)
        prompt = f"""
학생의 현재 역량을 바탕으로 직업 후보를 추천하고, 역량 격차와 단계별 경로를 작성하세요.

학생 정보:
- 학년: {grade or "정보 없음"}
- 장애 유형: {disability_type or "정보 없음"}
- 현재 역량/학습 상태: {current_skills}
- 관심 활동: {interests or []}

RAG로 찾은 직업 후보:
{candidate_context}

요청:
1) 반드시 위 후보 안에서만 3~5개 직업을 고르세요.
2) 학생의 현재 강점, 관심 활동, 장애 특성, 직업 요구 역량을 함께 반영해 순위를 정하세요.
3) match_score는 0.0~1.0 사이 점수로 쓰세요.
4) 각 추천 직업에 대해 현재 보유 역량, 필요한 역량, 부족한 역량, 수업에서 키울 제안을 작성하세요.
5) 각 추천 직업에 대해 현재-단기-중기-장기 흐름의 단계별 경로를 작성하세요.
6) 표현은 교사와 학부모가 바로 이해할 수 있게 자연스럽고 간결하게 쓰세요.

반드시 유효한 JSON 객체만 출력:
{{
  "recommended_careers": [
    {{
      "job_title": "후보에 있는 직업명",
      "match_score": 0.0,
      "required_skills": ["..."],
      "outlook": "..."
    }}
  ],
  "skill_gaps": [
    {{
      "job_title": "후보에 있는 직업명",
      "current_level": ["..."],
      "required_level": ["..."],
      "gap_skills": ["..."],
      "development_suggestions": ["..."]
    }}
  ],
  "career_paths": [
    {{
      "target_career": "후보에 있는 직업명",
      "stages": [
        {{"stage": "현재", "focus": "...", "description": "..."}}
      ],
      "estimated_timeline": "..."
    }}
  ]
}}
"""
        try:
            result = self._call_json_model(
                prompt=prompt.strip(),
                system_instruction=(
                    "당신은 특수교육 기반 진로지도 전문가입니다. "
                    "검색된 직업 후보를 근거로 학생에게 맞는 진로 후보, 역량 격차, 실행 경로를 작성합니다. "
                    "후보에 없는 직업을 새로 만들지 마세요."
                ),
                response_schema=CAREER_RECOMMENDATION_RESPONSE_SCHEMA,
                max_output_tokens=settings.gemini_career_max_output_tokens,
                trace_label="career_recommendation",
            )
            return {
                "recommended_careers": result.get("recommended_careers", []),
                "skill_gaps": result.get("skill_gaps", []),
                "career_paths": result.get("career_paths", []),
            }
        except Exception as e:
            self.logger.error(
                "Career recommendation generation failed (%s): %s. "
                "Rule-based career recommendation fallback will be used.",
                e.__class__.__name__,
                str(e),
            )
            raise

    def _build_career_candidate_context(self, candidates: List[Dict[str, Any]]) -> str:
        if not candidates:
            return "직업 후보가 없습니다."

        lines: List[str] = []
        for idx, candidate in enumerate(candidates[:6], start=1):
            required = candidate.get("required_skills") or []
            if not isinstance(required, list):
                required = [str(required)]
            required_text = ", ".join(str(skill) for skill in required[:8] if str(skill).strip()) or "정보 없음"
            outlook = str(candidate.get("outlook") or "")[:420]
            lines.append(
                "\n".join([
                    f"{idx}. 직업명: {candidate.get('job_title') or '직업명 없음'}",
                    f"   분류: {candidate.get('category') or '기타'}",
                    f"   검색 관련도: {candidate.get('match_score', 0)}",
                    f"   요구 역량: {required_text}",
                    f"   직업 설명/전망: {outlook or '정보 없음'}",
                ])
            )
        return "\n\n".join(lines)

    def extract_career_query_profile(
        self,
        current_skills: str,
        interests: Optional[List[str]] = None,
        grade: Optional[str] = None,
        disability_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lightweight AI call used on every career recommendation request.
        It normalizes free-form student descriptions into search/rerank hints.
        """
        prompt = f"""
학생의 현재 역량 설명을 읽고, 진로 추천 검색에 바로 쓸 핵심 표현만 추출하세요.

학생 정보:
- 학년: {grade or "정보 없음"}
- 장애 유형: {disability_type or "정보 없음"}
- 현재 역량 설명: {current_skills}
- 관심 활동: {interests or []}

규칙:
1) recommended_query는 직업 검색에 유리한 짧은 한국어 표현 1문장으로 작성
2) prefer_keywords에는 학생의 강점/선호를 2~5개까지
3) avoid_keywords에는 학생이 어려워하거나 피해야 할 조건을 0~5개까지
4) student_strengths에는 수업/직무 연결에 도움이 되는 강점을 2~5개까지
5) 직업명은 쓰지 말고, 역량/작업 방식 중심으로만 정리

반드시 유효한 JSON 객체만 출력:
{{
  "recommended_query": "...",
  "prefer_keywords": ["..."],
  "avoid_keywords": ["..."],
  "student_strengths": ["..."]
}}
"""
        result = self._call_json_model(
            prompt=prompt.strip(),
            system_instruction=(
                "당신은 특수교육 기반 진로추천을 위한 입력 정규화 도우미입니다. "
                "자유 서술을 짧고 검색 가능한 역량 표현으로 바꾸세요."
            ),
            response_schema=CAREER_QUERY_PROFILE_SCHEMA,
            max_output_tokens=settings.gemini_query_profile_max_output_tokens,
            trace_label="career_query_profile",
        )
        return {
            "recommended_query": str(result.get("recommended_query") or "").strip(),
            "prefer_keywords": _coerce_json_string_list(result.get("prefer_keywords")),
            "avoid_keywords": _coerce_json_string_list(result.get("avoid_keywords")),
            "student_strengths": _coerce_json_string_list(result.get("student_strengths")),
        }

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
                response_schema=CAREER_PATH_RESPONSE_SCHEMA,
                max_output_tokens=settings.gemini_path_max_output_tokens,
                trace_label="career_path",
            )
            return {
                "stages": result.get("stages", []),
                "estimated_timeline": result.get("estimated_timeline", "개별 평가 필요"),
            }
        except Exception as e:
            self.logger.error(
                "Career path generation failed (%s): %s. "
                "Likely causes: Gemini quota/network/model availability issue.",
                e.__class__.__name__,
                str(e),
            )
            raise

    def _call_json_model(
        self,
        prompt: str,
        system_instruction: str,
        response_schema: Optional[Dict[str, Any]] = None,
        max_output_tokens: int = 1024,
        trace_label: str = "json_task",
    ) -> Dict[str, Any]:
        """Call Gemini model and parse a JSON object response."""
        return self._call_gemini_json_model(
            prompt,
            system_instruction,
            response_schema=response_schema,
            max_output_tokens=max_output_tokens,
            trace_label=trace_label,
        )

    def _call_gemini_json_model(
        self,
        prompt: str,
        system_instruction: str,
        response_schema: Optional[Dict[str, Any]] = None,
        max_output_tokens: int = 1024,
        trace_label: str = "json_task",
    ) -> Dict[str, Any]:
        """Call Gemini model and parse a JSON object response."""
        if not self.client:
            raise ValueError("Gemini client is not initialized. Check API key settings.")

        last_error: Optional[Exception] = None
        for attempt_idx in range(2):
            try:
                attempt_prompt = prompt
                if attempt_idx == 1:
                    attempt_prompt = (
                        f"{prompt}\n\n"
                        "중요: 반드시 JSON 객체 1개만 출력하세요. "
                        "설명 문장/마크다운/코드블록을 절대 출력하지 마세요."
                    )
                config_kwargs: Dict[str, Any] = {
                    "system_instruction": system_instruction,
                    "temperature": 0.0 if attempt_idx == 1 else self.temperature,
                    "max_output_tokens": max_output_tokens,
                    "response_mime_type": "application/json",
                    "candidate_count": 1,
                    "thinking_config": types.ThinkingConfig(
                        thinking_budget=settings.gemini_thinking_budget,
                    ),
                }
                if response_schema:
                    config_kwargs["response_schema"] = response_schema

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=attempt_prompt,
                    config=types.GenerateContentConfig(**config_kwargs),
                )
                parsed = getattr(response, "parsed", None)
                if parsed is not None:
                    if isinstance(parsed, dict):
                        self.logger.info(
                            "Gemini generate_content succeeded for model '%s' [%s] via parsed response (attempt %d/2).",
                            self.model_name,
                            trace_label,
                            attempt_idx + 1,
                        )
                        return parsed
                    if hasattr(parsed, "model_dump"):
                        self.logger.info(
                            "Gemini generate_content succeeded for model '%s' [%s] via model_dump parsed response (attempt %d/2).",
                            self.model_name,
                            trace_label,
                            attempt_idx + 1,
                        )
                        return parsed.model_dump(mode="json")
                    if hasattr(parsed, "dict"):
                        self.logger.info(
                            "Gemini generate_content succeeded for model '%s' [%s] via dict parsed response (attempt %d/2).",
                            self.model_name,
                            trace_label,
                            attempt_idx + 1,
                        )
                        return parsed.dict()
                result_text = response.text
                if not result_text:
                    raise ValueError("Empty response from Gemini model")
                result = parse_json_with_salvage(result_text)
                self.logger.info(
                    "Gemini generate_content succeeded for model '%s' [%s] via JSON text salvage (attempt %d/2).",
                    self.model_name,
                    trace_label,
                    attempt_idx + 1,
                )
                return result
            except json.JSONDecodeError as e:
                last_error = e
                self.logger.warning(
                    "Gemini JSON parse failed with model '%s' (attempt %d/2): %s",
                    self.model_name,
                    attempt_idx + 1,
                    str(e),
                )
                continue
            except Exception as e:
                last_error = e
                self.logger.warning(
                    "Gemini generate_content failed with model '%s' (%s): %s",
                    self.model_name,
                    e.__class__.__name__,
                    str(e),
                )
                break

        self.logger.error(
            "Gemini generate_content failed for model '%s'. Last error (%s): %s. "
            "Rule-based analysis fallback will be used by orchestrator.",
            self.model_name,
            last_error.__class__.__name__ if last_error else "UnknownError",
            str(last_error) if last_error else "No error details",
        )
        if last_error:
            raise last_error
        raise RuntimeError("Gemini generate_content failed without error details")
