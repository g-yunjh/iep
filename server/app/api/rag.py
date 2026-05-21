"""Common RAG API for curriculum and career data.
This API is shared across home, school, and center endpoints.
Provides RAG-based recommendations for scaffolding and career guidance.
"""

import json
import logging
import math
import re
from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.schemas.rag import (
    ScaffoldingRecommendationRequest,
    ScaffoldingRecommendation,
    RAGAnalysisResult,
    VectorStoreStatus
)
from app.schemas.rag import (
    CareerRecommendationRequest,
    CareerRecommendationResponse,
    CareerPath,
    SkillGap,
    RecommendedCareer
)
from app.services.rag_orchestrator import RAGOrchestrator
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Feedback, Student

router = APIRouter()
logger = logging.getLogger(__name__)


def _to_json_compatible(model_obj) -> Dict:
    """
    Convert a Pydantic model to a DB-safe JSON object.
    Supports both Pydantic v1 (`dict`) and v2 (`model_dump`).
    """
    if model_obj is None:
        return {}

    if hasattr(model_obj, "model_dump"):
        return model_obj.model_dump(mode="json")

    if hasattr(model_obj, "dict"):
        return model_obj.dict()

    # Last-resort fallback for plain dict-like objects.
    return json.loads(json.dumps(model_obj))


def _get_persona_student(db: Session) -> Student:
    student = db.query(Student).order_by(Student.id.asc()).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생 프로필이 없습니다. 먼저 /student/traits에서 프로필을 설정해 주세요.")
    return student


def _extract_query_constraints(query: str) -> Dict[str, List[str]]:
    """
    Extract preference/avoidance phrases from free-form query without job hardcoding.
    """
    text = (query or "").strip()
    if not text:
        return {"prefer": [], "avoid": []}

    prefer: List[str] = []
    avoid: List[str] = []
    chunks = [
        part.strip()
        for part in re.split(
            r"[,.]|하지만|있지만|지만|그러나|그런데|반면|다만|면서|이고|이며",
            text,
        )
        if part.strip()
    ]

    for chunk in chunks:
        lowered = chunk.lower()
        is_avoid = any(
            token in lowered
            for token in [
                "어렵", "힘들", "싫", "부담", "약함", "약하", "못하", "못 ",
                "안 되", "전무", "없", "부족", "낮", "불가", "제한",
            ]
        )
        if is_avoid:
            avoid.append(chunk)
        else:
            prefer.append(chunk)

    return {"prefer": prefer[:5], "avoid": avoid[:5]}


_NEGATIVE_STOPWORDS = {
    "능력", "역량", "전무", "없음", "없는", "없다", "어려움", "어렵다", "부족",
    "낮음", "낮다", "약함", "약하다", "못함", "못하다", "불가", "제한",
}


_CAREER_AVOIDANCE_SYNONYMS = {
    "언어": ["언어", "의사소통", "말", "말투", "발음", "어휘", "문법", "청력", "표현", "글쓰기", "문장", "전달", "상담", "설득", "설명", "발표", "가르치", "수업", "교육", "교사", "강사", "속기", "통역", "번역", "텔레"],
    "의사소통": ["언어", "의사소통", "말", "표현", "전달", "상담", "설득", "설명", "발표", "교육", "교사", "강사", "속기", "통역", "번역", "텔레"],
    "대인": ["대인", "고객", "상담", "서비스", "설득", "친화", "관계", "영업"],
    "신체": ["신체", "체력", "육체", "운동", "활동", "이동", "서 있", "장시간", "현장", "야외", "노무", "제조", "생산", "조립", "수리", "수선", "도장", "시공", "작업원"],
    "손": ["손", "손재주", "정교", "수작업", "미세", "조작", "세밀", "수리", "수선", "부착", "도배", "도장", "판금", "공작", "제조"],
    "시각": ["시각", "색", "색채", "관찰", "디자인", "도면"],
    "소음": ["소음", "음향", "녹음", "성우", "방송", "공연", "기계", "제조", "생산", "압연", "도장", "설비"],
}


def _extract_negative_capability_terms(query: str) -> List[str]:
    constraints = _extract_query_constraints(query)
    terms: List[str] = []

    for phrase in constraints.get("avoid", []):
        phrase_tokens = _tokenize_korean_text(phrase)
        for token in phrase_tokens:
            if token in _NEGATIVE_STOPWORDS:
                continue
            terms.append(token)

        phrase_text = phrase.lower()
        for key, synonyms in _CAREER_AVOIDANCE_SYNONYMS.items():
            if key in phrase_text or any(synonym in phrase_text for synonym in synonyms):
                terms.extend(synonyms)

    unique: List[str] = []
    for term in terms:
        cleaned = str(term).strip().lower()
        if len(cleaned) >= 2 and cleaned not in unique:
            unique.append(cleaned)
    return unique[:20]


def _career_avoidance_score(career: RecommendedCareer, avoid_terms: List[str]) -> float:
    if not avoid_terms:
        return 0.0

    title = (career.job_title or "").lower()
    category = (career.category or "").lower()
    skills_text = " ".join(career.required_skills or []).lower()
    outlook = (career.outlook or "").lower()

    score = 0.0
    if any(term in avoid_terms for term in _CAREER_AVOIDANCE_SYNONYMS["언어"]):
        language_heavy_titles = ["교사", "강사", "상담", "치료사", "아나운서", "통역", "번역", "리포터", "속기사", "텔레마케터"]
        if any(token in title for token in language_heavy_titles):
            score += 0.55

    if any(term in avoid_terms for term in _CAREER_AVOIDANCE_SYNONYMS["손"]):
        hand_heavy_titles = ["조작", "수리", "부착", "도배", "판금", "공작", "제조", "공예", "조율"]
        if any(token in title for token in hand_heavy_titles):
            score += 0.45

    if any(term in avoid_terms for term in _CAREER_AVOIDANCE_SYNONYMS["신체"]):
        physical_heavy_titles = ["노무", "제조", "생산", "조립", "수리", "수선", "시공", "조작", "판금", "도배", "도장", "운전", "가구"]
        if any(token in title for token in physical_heavy_titles):
            score += 0.45

    if any(term in avoid_terms for term in _CAREER_AVOIDANCE_SYNONYMS["소음"]):
        noise_heavy_titles = ["음향", "녹음", "성우", "방송", "공연", "기계", "제조", "생산", "압연", "도장", "설비", "공작"]
        if any(token in title for token in noise_heavy_titles):
            score += 0.45

    for term in avoid_terms:
        if term in title:
            score += 0.38
        if term in category:
            score += 0.12
        if term in skills_text:
            score += 0.24
        if term in outlook:
            score += 0.06
    return max(0.0, min(1.0, score))


def _copy_career_with_score(career: RecommendedCareer, score: float) -> RecommendedCareer:
    return RecommendedCareer(
        job_id=career.job_id,
        job_title=career.job_title,
        category=career.category,
        match_score=max(0.0, min(1.0, score)),
        required_skills=career.required_skills,
        outlook=career.outlook,
    )


def _rerank_careers_for_constraints(
    current_skills: str,
    careers: List[RecommendedCareer],
) -> List[RecommendedCareer]:
    avoid_terms = _extract_negative_capability_terms(current_skills)
    if not avoid_terms:
        return careers

    ranked = []
    for idx, career in enumerate(careers):
        penalty = _career_avoidance_score(career, avoid_terms)
        adjusted = float(career.match_score or 0.0) - (0.55 * penalty)
        # Heavily constrained jobs should sink below weakly matched alternatives.
        blocked = 1 if penalty >= 0.35 else 0
        ranked.append((blocked, -adjusted, idx, _copy_career_with_score(career, adjusted)))

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return [career for _, _, _, career in ranked]


def _tokenize_korean_text(text: str) -> List[str]:
    tokens = [token for token in re.split(r"[^0-9A-Za-z가-힣]+", (text or "").lower()) if token]
    return [token for token in tokens if len(token) >= 2]


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def _semantic_constraint_score(
    candidate_text: str,
    constraints: List[str],
    embeddings,
) -> float:
    """
    Score semantic relevance using embedding cosine similarity (0~1).
    """
    if not constraints:
        return 0.0
    try:
        candidate_vec = embeddings.embed_query(candidate_text)
    except Exception:
        return 0.0

    sims: List[float] = []
    for phrase in constraints:
        try:
            phrase_vec = embeddings.embed_query(phrase)
            sim = _cosine_similarity(candidate_vec, phrase_vec)
            sims.append(max(0.0, min(1.0, (sim + 1.0) / 2.0)))
        except Exception:
            continue

    if not sims:
        return 0.0
    return sum(sims) / len(sims)


def _compute_skill_alignment(current_skills: str, required_skills: List[str]) -> Dict[str, Any]:
    """
    Lightweight, deterministic skill alignment without LLM/API dependency.
    """
    current_tokens = set(_tokenize_korean_text(current_skills))
    normalized_required = [skill.strip() for skill in required_skills if skill and skill.strip()]
    if not normalized_required:
        return {
            "match_ratio": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "recommendation_strength": "unknown",
        }

    matched: List[str] = []
    missing: List[str] = []
    for skill in normalized_required:
        skill_tokens = set(_tokenize_korean_text(skill))
        if skill_tokens and current_tokens.intersection(skill_tokens):
            matched.append(skill)
        else:
            missing.append(skill)

    ratio = len(matched) / max(len(normalized_required), 1)
    if ratio >= 0.6:
        strength = "high"
    elif ratio >= 0.3:
        strength = "medium"
    else:
        strength = "low"

    return {
        "match_ratio": ratio,
        "matched_skills": matched[:5],
        "missing_skills": missing[:5],
        "recommendation_strength": strength,
    }


# =============================================================================
# Curriculum RAG Endpoints (Scaffolding Recommendations)
# =============================================================================

@router.post("/scaffolding-recommendation", response_model=ScaffoldingRecommendation)
async def get_scaffolding_recommendation(
    request: ScaffoldingRecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    스캐폴딩 추천 API - RAG 기반
    선생님/부모님의 아동 상태 설명을 분석하여 적절한 스캐폴딩 전략 추천
    
    Curriculum RAG를 통해 학생의 현재 수준에 맞는 성취 목표와
    단계별 개입 전략(Physical/Verbal Prompt 등)을 추천합니다.
    """
    try:
        student = _get_persona_student(db)
        orchestrator = RAGOrchestrator()

        # RAG 분석 수행
        analysis_result = orchestrator.analyze_and_recommend(request, db)

        # 결과를 데이터베이스에 저장
        feedback = Feedback(
            student_id=student.id,
            disability_type=student.disability_type,
            teacher_description=request.teacher_description,
            llm_analysis=_to_json_compatible(analysis_result.llm_analysis),
            scaffolding_recommendations=_to_json_compatible(analysis_result.scaffolding_recommendation),
            performance=f"AI 분석: {analysis_result.llm_analysis.detected_level} 수준",
            scaffolding_effectiveness="AI 추천 적용 전"
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return analysis_result.scaffolding_recommendation

    except Exception as e:
        logger.exception("스캐폴딩 추천 생성 실패: %s", str(e))
        raise HTTPException(status_code=500, detail=f"스캐폴딩 추천 생성 실패: {str(e)}")


@router.get("/curriculum-search")
async def search_curriculum(
    query: str,
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    disability_type: Optional[str] = None,
    k: int = 5
):
    """
    커리큘럼 성취기준 검색 API
    학생 상태서술을 기반으로 관련 성취기준을 검색합니다.
    """
    try:
        rag_service = RAGService()
        results = rag_service.search_curriculum(
            query=query,
            grade=grade,
            subject=subject,
            disability_type=disability_type,
            k=k
        )
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.exception("커리큘럼 검색 실패: %s", str(e))
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")


@router.get("/curriculum-subjects")
async def get_curriculum_subjects():
    """
    현재 curriculum 디렉토리에서 자동 인식한 과목 목록 조회 API
    새 과목 폴더를 추가하면 별도 하드코딩 없이 여기서 함께 노출됩니다.
    """
    try:
        rag_service = RAGService()
        subjects = rag_service.list_curriculum_subjects()
        return {
            "subjects": subjects,
            "count": len(subjects),
        }
    except Exception as e:
        logger.exception("과목 목록 조회 실패: %s", str(e))
        raise HTTPException(status_code=500, detail=f"과목 목록 조회 실패: {str(e)}")


# =============================================================================
# Career RAG Endpoints (Career Path Recommendations)
# =============================================================================

@router.post("/career-recommendation", response_model=CareerRecommendationResponse)
async def get_career_recommendation(
    request: CareerRecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    진로 추천 API - RAG 기반
    학생의 현재 역량과 학습 내용을 분석하여 적합한 직업을 추천하고,
    해당 직업이 되기 위해 필요한 역량과 현재 역량과의 격차를 분석합니다.
    
    - 현재 역량 기반 추천: 지금 보이는 강점을 바탕으로 적합한 직업 추천
    - 역량 격차 분석: 목표 직업을 위해 부족한 역량 파악
    - 커리어넷 데이터 연계: 향후 어떤 직업적 역량으로 이어지는지 시각화
    """
    try:
        student = _get_persona_student(db)
        rag_service = RAGService()
        constraints = _extract_query_constraints(request.current_skills)
        interest_query = " ".join(request.interests or []).strip()
        llm_service: Optional[LLMService] = None
        ai_query_profile: Dict[str, Any] = {}

        # 공모전 요구에 맞춰 진로 추천은 매 요청마다 AI를 한 번 호출한다.
        # 다만 긴 전체 생성 대신, 먼저 자유 서술을 짧은 검색/제약 프로필로 정규화한다.
        if request.use_llm:
            try:
                llm_service = LLMService()
                ai_query_profile = llm_service.extract_career_query_profile(
                    current_skills=request.current_skills,
                    interests=request.interests or [],
                    grade=request.grade,
                    disability_type=request.disability_type or student.disability_type,
                )
            except Exception as llm_error:
                logger.warning(
                    "LLM unavailable for career query profiling (%s): %s. "
                    "Using rule-based search query fallback.",
                    llm_error.__class__.__name__,
                    str(llm_error),
                )
                ai_query_profile = {}

        ai_prefer = " ".join(ai_query_profile.get("prefer_keywords") or []).strip()
        ai_strengths = " ".join(ai_query_profile.get("student_strengths") or []).strip()
        ai_query = str(ai_query_profile.get("recommended_query") or "").strip()
        positive_query = " ".join(
            [
                ai_query,
                ai_strengths,
                ai_prefer,
                *constraints.get("prefer", []),
                interest_query,
            ]
        ).strip()
        if positive_query:
            career_query = positive_query
        elif constraints.get("avoid") or ai_query_profile.get("avoid_keywords"):
            career_query = "반복 루틴 단순 확인 정리 보조 작업"
        else:
            career_query = request.current_skills
        
        # 1. 학생의 현재 역량/학습 내용을 기반으로 관련 직업 검색
        career_results = rag_service.search_career(
            query=career_query,
            k=30
        )
        
        if not career_results:
            raise HTTPException(status_code=404, detail="관련 직업을 찾을 수 없습니다.")
        
        # 2. 결과 구성
        recommended_careers = []
        career_profiles = []

        for career in career_results[:30]:
            metadata = career.get("metadata", {})
            content = career.get("content", "")

            competencies = _extract_competencies(content)
            profile = _extract_career_profile(content)
            outlook = profile.get("outlook_scaffolding", "")
            if not outlook:
                outlook = metadata.get("outlook_scaffolding", "")

            required_skills = competencies["required"]
            # jobs_batch 구조(교육/자격/전망)를 required context에 반영
            required_skills.extend(profile.get("certifications", []))
            required_skills.extend(profile.get("education", []))
            required_skills = [skill for skill in dict.fromkeys(required_skills) if skill]
            
            # Coerce potentially missing/null vectorstore metadata to schema-safe values.
            job_id = str(metadata.get("job_id") or "")
            job_title = str(metadata.get("job_title") or "")
            category = str(metadata.get("category") or "기타")
            try:
                match_score = float(career.get("score", 0) or 0)
            except (TypeError, ValueError):
                match_score = 0.0

            recommended_careers.append(RecommendedCareer(
                job_id=job_id,
                job_title=job_title or "직무 정보 없음",
                category=category,
                match_score=match_score,
                required_skills=required_skills,
                outlook=str(outlook or "")
            ))

            career_profiles.append({
                "job_title": job_title,
                "required_skills": required_skills,
                "outlook_scaffolding": str(outlook or ""),
                "education": profile.get("education", []),
                "certifications": profile.get("certifications", []),
            })

        constraint_text = " ".join(
            [
                request.current_skills,
                " ".join(ai_query_profile.get("avoid_keywords") or []),
                " ".join(ai_query_profile.get("prefer_keywords") or []),
            ]
        ).strip()
        recommended_careers = _rerank_careers_for_constraints(
            constraint_text or request.current_skills,
            recommended_careers,
        )

        # 3. 최종 추천 조합은 빠른 RAG+규칙 기반으로 생성한다.
        # AI는 위에서 항상 입력 정규화에 사용되며, 전체 장문 생성은 제거해 속도를 줄인다.
        recommended_careers = recommended_careers[:5]
        skill_gaps = []
        career_paths = []

        if not skill_gaps:
            skill_gaps = _analyze_skill_gaps(
                current_skills=request.current_skills,
                recommended_careers=recommended_careers,
                llm_service=None,
                grade=request.grade,
                disability_type=student.disability_type,
            )

        if not career_paths:
            career_paths = _generate_career_paths(
                request=request,
                recommended_careers=recommended_careers,
                llm_service=None,
                disability_type=student.disability_type,
                career_profiles=career_profiles,
            )
        
        return CareerRecommendationResponse(
            current_skills=request.current_skills,
            recommended_careers=recommended_careers,
            skill_gaps=skill_gaps,
            career_paths=career_paths
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("진로 추천 생성 실패: %s", str(e))
        raise HTTPException(status_code=500, detail=f"진로 추천 생성 실패: {str(e)}")


@router.get("/career-search")
async def search_careers(
    query: str,
    k: int = 5,
    current_skills: Optional[str] = None,
):
    """
    커리어 데이터 검색 API
    - 직업 후보 검색 + 쿼리 제약 기반 재정렬만 수행
    - 현재 역량 비교는 간단한 규칙 기반으로 제공
    - 정밀 역량/경로 분석은 POST /career-recommendation에서 수행
    """
    try:
        # 1. 기본 직업 검색 수행
        rag_service = RAGService()
        # Retrieve a wider candidate pool first, then rerank and trim to k.
        candidate_k = max(k * 12, 60)
        results = rag_service.search_career(query=query, k=candidate_k)

        # 2. 검색 결과 구성 (격차 분석은 recommendation endpoint에서 수행)
        enhanced_results = []
        constraints = _extract_query_constraints(query)
        effective_current_skills = (
            (current_skills or "").strip()
            or settings.career_search_default_current_skills.strip()
        )
        for res in results:
            content = res.get("content", "")
            metadata = res.get("metadata", {})
            
            # 직업 문서에서 요구 역량 추출
            required = _extract_competencies(content)["required"]

            base_score = float(res.get("score", 0))
            candidate_text = " ".join([
                metadata.get("job_title", "") or "",
                metadata.get("category", "") or "",
                " ".join(required),
                content,
            ])
            prefer_score = _semantic_constraint_score(
                candidate_text=candidate_text,
                constraints=constraints.get("prefer", []),
                embeddings=rag_service.embeddings,
            )
            avoid_score = _semantic_constraint_score(
                candidate_text=candidate_text,
                constraints=constraints.get("avoid", []),
                embeddings=rag_service.embeddings,
            )
            # Keep semantic retrieval as primary signal, then apply lightweight constraint reranking.
            adjusted_score = max(0.0, min(1.0, base_score + (0.20 * prefer_score) - (0.35 * avoid_score)))

            alignment = (
                _compute_skill_alignment(effective_current_skills, required)
                if effective_current_skills
                else {
                    "match_ratio": 0.0,
                    "matched_skills": [],
                    "missing_skills": [],
                    "recommendation_strength": "unknown",
                }
            )

            enhanced_results.append({
                "job_title": metadata.get("job_title"),
                "required_skills": required,
                "score": adjusted_score,
                "base_score": base_score,
                "prefer_match_score": prefer_score,
                "avoid_match_score": avoid_score,
                "skill_alignment": alignment,
            })

        enhanced_results.sort(key=lambda item: item.get("score", 0), reverse=True)

        top_results = enhanced_results[:k]
        return {
            "query": query,
            "results": top_results,
            "count": len(top_results)
        }

    except Exception as e:
        logger.exception("직업 검색/역량 분석 실패: %s", str(e))
        # 상세한 에러 메시지와 함께 예외 처리
        raise HTTPException(
            status_code=500, 
            detail=f"직업 검색 및 역량 분석 중 오류가 발생했습니다: {str(e)}"
        )

# =============================================================================
# Vector Store Management Endpoints
# =============================================================================

@router.post("/initialize-vector-stores")
async def initialize_vector_stores(
    force_recreate: bool = False,
    data_type: Optional[str] = None
):
    """
    벡터 스토어 초기화 API
    curriculum과 career 데이터의 벡터 스토어를 초기화합니다.
    
    Args:
        force_recreate: True면 기존 스토어를 삭제하고 다시 생성
        data_type: "curriculum", "career", 또는 None(전체)
    """
    try:
        rag_service = RAGService()
        
        if data_type:
            # 특정 타입만 초기화
            success = rag_service.initialize_vector_store(data_type, force_recreate)
            return {
                "data_type": data_type,
                "status": "success" if success else "failed",
                "message": f"{data_type} 벡터 스토어 초기화 완료" if success else "초기화 실패"
            }
        else:
            # 전체 초기화
            results = rag_service.initialize_all_stores(force_recreate)
            return {
                "curriculum": results.get("curriculum", False),
                "career": results.get("career", False),
                "status": "success" if all(results.values()) else "partial",
                "message": "전체 벡터 스토어 초기화 완료"
            }
    except Exception as e:
        logger.exception("벡터 스토어 초기화 실패: %s", str(e))
        raise HTTPException(status_code=500, detail=f"초기화 실패: {str(e)}")


@router.get("/vector-store-status", response_model=VectorStoreStatus)
async def get_vector_store_status(data_type: Optional[str] = None):
    """
    벡터 스토어 상태 조회 API
    각 데이터 타입의 벡터 스토어 상태를 반환합니다.
    """
    try:
        rag_service = RAGService()
        
        if data_type:
            info = rag_service.get_collection_info(data_type)
            return VectorStoreStatus(
                status=info.get("status", "error"),
                document_count=info.get("document_count"),
                collection_name=info.get("collection_name"),
                last_updated=None
            )
        else:
            # 전체 상태
            all_info = rag_service.get_all_collections_info()
            total_docs = sum(
                info.get("document_count", 0) 
                for info in all_info.values()
            )
            return VectorStoreStatus(
                status=(
                    "initialized"
                    if all_info.get("curriculum", {}).get("status") == "initialized"
                    and all_info.get("career", {}).get("status") == "initialized"
                    else "not_initialized"
                ),
                document_count=total_docs,
                collection_name="all",
                last_updated=None
            )
    except Exception as e:
        logger.exception("벡터 스토어 상태 조회 실패: %s", str(e))
        raise HTTPException(status_code=500, detail=f"상태 조회 실패: {str(e)}")


# =============================================================================
# Helper Functions
# =============================================================================

def _extract_competencies(content: str) -> Dict[str, List[str]]:
    """커리어 내용에서 역량 정보를 추출합니다."""
    required = []
    
    # 간단한 파싱 (실제로는 LLM을 통해 더精细하게 추출)
    if "핵심 역량:" in content:
        start = content.find("핵심 역량:")
        end = content.find("자격증:", start) if "자격증:" in content else len(content)
        competencies_section = content[start:end]
        
        # "-" 로 시작하는 줄 추출
        for line in competencies_section.split("\n"):
            if line.strip().startswith("-"):
                required.append(line.strip().replace("- ", ""))
    
    return {
        "required": required,
        "preferred": []
    }


def _extract_career_profile(content: str) -> Dict[str, Any]:
    """Extract structured career profile from indexed career document content."""
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    education: List[str] = []
    certifications: List[str] = []
    outlook_scaffolding = ""

    for line in lines:
        if line.startswith("자격증:"):
            cert_text = line.replace("자격증:", "").strip()
            certifications = [c.strip() for c in cert_text.split(",") if c.strip()]
        elif line.startswith("진로 전망:"):
            outlook_scaffolding = line.replace("진로 전망:", "").strip()

    # 일부 문서는 본문에 교육 정보가 없어 빈 리스트일 수 있음
    return {
        "education": education,
        "certifications": certifications,
        "outlook_scaffolding": outlook_scaffolding,
    }


def _coerce_llm_string_list(raw: Any, fallback: Optional[List[str]] = None) -> List[str]:
    """
    로컬 LLM이 List[str] 대신 dict 리스트를 반환하는 경우가 있어 SkillGap 스키마용으로 정규화.
    """
    if raw is None:
        return list(fallback or [])
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else list(fallback or [])
    if not isinstance(raw, list):
        return list(fallback or [])

    out: List[str] = []
    for item in raw:
        if isinstance(item, str):
            if item.strip():
                out.append(item.strip())
            continue
        if isinstance(item, dict):
            name = (
                item.get("skill_name")
                or item.get("name")
                or item.get("text")
                or item.get("label")
                or item.get("description")
            )
            level = item.get("level") or item.get("target_level") or item.get("수준")
            if name is not None and str(name).strip():
                line = str(name).strip()
                if level is not None and level != "":
                    line = f"{line} (관련 수준: {level})"
                out.append(line)
            else:
                parts = [f"{k}: {v}" for k, v in item.items() if v is not None and str(v).strip()]
                if parts:
                    out.append("; ".join(parts))
            continue
        s = str(item).strip()
        if s:
            out.append(s)

    return out if out else list(fallback or [])


def _normalize_match_score(raw: Any, fallback: float = 0.0) -> float:
    try:
        score = float(raw)
    except (TypeError, ValueError):
        score = fallback
    if score > 1:
        score = score / 100 if score <= 100 else 1.0
    return max(0.0, min(1.0, score))


def _find_career_by_title(title: str, careers: List[RecommendedCareer]) -> Optional[RecommendedCareer]:
    normalized = (title or "").strip()
    if not normalized:
        return None
    for career in careers:
        if career.job_title == normalized:
            return career
    for career in careers:
        if normalized in career.job_title or career.job_title in normalized:
            return career
    return None


def _merge_llm_recommended_careers(
    llm_result: Dict[str, Any],
    base_careers: List[RecommendedCareer],
) -> List[RecommendedCareer]:
    """Use LLM ranking while preserving RAG metadata and schema-safe values."""
    llm_items = llm_result.get("recommended_careers", [])
    if not isinstance(llm_items, list) or not llm_items:
        return base_careers[:5]

    merged: List[RecommendedCareer] = []
    used_titles = set()
    for item in llm_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("job_title") or "").strip()
        base = _find_career_by_title(title, base_careers)
        if not base or base.job_title in used_titles:
            continue

        required_skills = _coerce_llm_string_list(item.get("required_skills"), base.required_skills)
        merged.append(RecommendedCareer(
            job_id=base.job_id,
            job_title=base.job_title,
            category=base.category,
            match_score=_normalize_match_score(item.get("match_score"), base.match_score),
            required_skills=required_skills or base.required_skills,
            outlook=str(item.get("outlook") or base.outlook or ""),
        ))
        used_titles.add(base.job_title)

    for career in base_careers:
        if career.job_title not in used_titles:
            merged.append(career)
        if len(merged) >= 5:
            break

    return merged[:5]


def _build_skill_gaps_from_llm(
    llm_result: Dict[str, Any],
    recommended_careers: List[RecommendedCareer],
    current_skills: str,
) -> List[SkillGap]:
    items = llm_result.get("skill_gaps", [])
    if not isinstance(items, list):
        return []

    out: List[SkillGap] = []
    for career in recommended_careers[:3]:
        item = next(
            (
                raw for raw in items
                if isinstance(raw, dict)
                and _find_career_by_title(str(raw.get("job_title") or ""), [career])
            ),
            None,
        )
        if not item:
            continue

        required_level = _coerce_llm_string_list(item.get("required_level"), career.required_skills)
        alignment = _compute_skill_alignment(current_skills, required_level)
        current_level = _coerce_llm_string_list(
            item.get("current_level"),
            alignment.get("matched_skills", []),
        )
        gap_skills = _coerce_llm_string_list(
            item.get("gap_skills"),
            alignment.get("missing_skills", [])[:5],
        )
        development_suggestions = _coerce_llm_string_list(
            item.get("development_suggestions"),
            [f"'{skill}' 역량을 짧은 수업 활동으로 나누어 반복합니다." for skill in gap_skills[:3]],
        )

        if required_level or gap_skills or development_suggestions:
            out.append(SkillGap(
                job_title=career.job_title,
                current_level=current_level,
                required_level=required_level,
                gap_skills=gap_skills,
                development_suggestions=development_suggestions,
            ))

    return out


def _build_career_paths_from_llm(
    llm_result: Dict[str, Any],
    request: CareerRecommendationRequest,
    recommended_careers: List[RecommendedCareer],
) -> List[CareerPath]:
    items = llm_result.get("career_paths", [])
    if not isinstance(items, list):
        return []

    out: List[CareerPath] = []
    for career in recommended_careers[:3]:
        item = next(
            (
                raw for raw in items
                if isinstance(raw, dict)
                and _find_career_by_title(str(raw.get("target_career") or ""), [career])
            ),
            None,
        )
        if not item:
            continue

        stages: List[Dict[str, str]] = []
        raw_stages = item.get("stages", [])
        if isinstance(raw_stages, list):
            for idx, stage in enumerate(raw_stages[:5], start=1):
                if not isinstance(stage, dict):
                    continue
                stages.append({
                    "stage": str(stage.get("stage") or f"단계 {idx}"),
                    "focus": str(stage.get("focus") or ""),
                    "description": str(stage.get("description") or ""),
                })

        if stages:
            out.append(CareerPath(
                current_learning=request.current_skills,
                target_career=career.job_title,
                stages=stages,
                estimated_timeline=str(item.get("estimated_timeline") or "개별 평가 필요"),
            ))

    return out


def _analyze_skill_gaps(
    current_skills: str,
    recommended_careers: List[RecommendedCareer],
    llm_service: Optional[LLMService] = None,
    grade: Optional[str] = None,
    disability_type: Optional[str] = None,
) -> List[SkillGap]:
    """규칙 기반으로 현재 역량과 목표 직업 요구 역량 간의 격차를 분석합니다."""
    skill_gaps = []
    service = None
    if llm_service:
        try:
            service = llm_service
        except Exception:
            service = None

    def _default_suggestions(gaps: List[str]) -> List[str]:
        suggestions = []
        for skill in gaps[:3]:
            suggestions.append(f"'{skill}' 역량을 10~15분 단위 반복 과제로 나눠 연습합니다.")
        suggestions.append("체크리스트 기반으로 과제 시작-중간-완료 단계를 시각화합니다.")
        suggestions.append("주 1회 동일 과업 재수행으로 수행 정확도를 기록합니다.")
        # 중복 제거
        unique: List[str] = []
        for s in suggestions:
            if s not in unique:
                unique.append(s)
        return unique[:5]

    for career in recommended_careers[:3]:
        gap_result: Dict[str, Any] = {}
        if service:
            try:
                gap_result = service.analyze_career_skill_gap(
                    current_skills=current_skills,
                    job_title=career.job_title,
                    required_skills=career.required_skills,
                    outlook_scaffolding=career.outlook,
                    grade=grade,
                    disability_type=disability_type,
                )
            except Exception:
                gap_result = {}

        # Deterministic fallback / primary path
        required_level = _coerce_llm_string_list(gap_result.get("required_level"), career.required_skills)
        if not required_level:
            required_level = career.required_skills[:6]

        alignment = _compute_skill_alignment(current_skills, required_level)
        current_level = alignment.get("matched_skills", [])[:6]
        gap_skills = alignment.get("missing_skills", [])[:6]
        if not gap_skills:
            gap_skills = _coerce_llm_string_list(gap_result.get("gap_skills"), required_level[:4])

        development_suggestions = _coerce_llm_string_list(
            gap_result.get("development_suggestions"),
            _default_suggestions(gap_skills),
        )

        if gap_skills:
            skill_gaps.append(SkillGap(
                job_title=career.job_title,
                current_level=current_level,
                required_level=required_level,
                gap_skills=gap_skills,
                development_suggestions=development_suggestions,
            ))

    return skill_gaps


def _generate_career_paths(
    request: CareerRecommendationRequest,
    recommended_careers: List[RecommendedCareer],
    llm_service: Optional[LLMService] = None,
    disability_type: Optional[str] = None,
    career_profiles: Optional[List[Dict[str, Any]]] = None,
) -> List[CareerPath]:
    """규칙 기반으로 outlook 기반 학생 맞춤 커리어 경로를 생성합니다."""
    paths = []

    profile_map = {p.get("job_title", ""): p for p in (career_profiles or [])}
    service = None
    if llm_service:
        try:
            service = llm_service
        except Exception:
            service = None

    for career in recommended_careers[:3]:
        profile = profile_map.get(career.job_title, {})
        roadmap: Dict[str, Any] = {}
        if service:
            try:
                roadmap = service.generate_career_path(
                    current_skills=request.current_skills,
                    job_title=career.job_title,
                    required_skills=career.required_skills,
                    outlook_scaffolding=career.outlook or profile.get("outlook_scaffolding", ""),
                    certifications=profile.get("certifications", []),
                    education_paths=profile.get("education", []),
                    disability_type=disability_type,
                )
            except Exception:
                roadmap = {}

        stages = roadmap.get("stages", [])
        if not isinstance(stages, list):
            stages = []

        normalized_stages: List[Dict[str, str]] = []
        for idx, stage in enumerate(stages[:5], start=1):
            if isinstance(stage, dict):
                normalized_stages.append({
                    "stage": str(stage.get("stage", f"단계 {idx}")),
                    "focus": str(stage.get("focus", "")),
                    "description": str(stage.get("description", "")),
                })

        if not normalized_stages:
            top_required = ", ".join((career.required_skills or [])[:3]) or "기초 직무 역량"
            normalized_stages = [
                {
                    "stage": "현재",
                    "focus": "현재 강점 파악",
                    "description": f"현재 역량({request.current_skills})을 직무 요구 역량과 비교해 출발점을 정리합니다."
                },
                {
                    "stage": "단기(1~3개월)",
                    "focus": "핵심 기초 역량 강화",
                    "description": f"{top_required} 중심의 반복 과제로 기본 수행 정확도를 높입니다."
                },
                {
                    "stage": "중기(3~6개월)",
                    "focus": "실습 기반 적용",
                    "description": "체크리스트 기반 모의/현장 실습으로 작업 지속력과 독립 수행 비율을 높입니다."
                },
                {
                    "stage": "장기(6개월+)",
                    "focus": "직무 전환 및 유지",
                    "description": "실제 업무 환경에서 역할을 확장하고 피드백 루프로 성과를 안정화합니다."
                },
            ]

        path = CareerPath(
            current_learning=request.current_skills,
            target_career=career.job_title,
            stages=normalized_stages,
            estimated_timeline=str(roadmap.get("estimated_timeline", "6~12개월"))
        )
        paths.append(path)

    return paths
