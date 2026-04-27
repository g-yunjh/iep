"""Common RAG API for curriculum and career data.
This API is shared across home, school, and center endpoints.
Provides RAG-based recommendations for scaffolding and career guidance.
"""

import json
import math
import os
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
from app.db.database import get_db
from app.db.models import Feedback, Student

router = APIRouter()


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
    chunks = [part.strip() for part in re.split(r"[,.]|하지만|그런데|다만|면서|이고|이며", text) if part.strip()]

    for chunk in chunks:
        lowered = chunk.lower()
        is_avoid = any(token in lowered for token in ["어렵", "힘들", "싫", "부담", "약함", "못하", "안 되"])
        if is_avoid:
            avoid.append(chunk)
        else:
            prefer.append(chunk)

    return {"prefer": prefer[:5], "avoid": avoid[:5]}


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
    학생 상태描述을 기반으로 관련 성취기준을 검색합니다.
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
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")


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
        llm_service = LLMService()
        
        # 1. 학생의 현재 역량/학습 내용을 기반으로 관련 직업 검색
        career_results = rag_service.search_career(
            query=request.current_skills,
            k=10
        )
        
        if not career_results:
            raise HTTPException(status_code=404, detail="관련 직업을 찾을 수 없습니다.")
        
        # 2. 결과 구성
        recommended_careers = []
        career_profiles = []

        for career in career_results[:5]:
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
            
            recommended_careers.append(RecommendedCareer(
                job_id=metadata.get("job_id", ""),
                job_title=metadata.get("job_title", ""),
                category=metadata.get("category", ""),
                match_score=career.get("score", 0),
                required_skills=required_skills,
                outlook=outlook
            ))

            career_profiles.append({
                "job_title": metadata.get("job_title", ""),
                "required_skills": required_skills,
                "outlook_scaffolding": outlook,
                "education": profile.get("education", []),
                "certifications": profile.get("certifications", []),
            })

        # 3. LLM 기반 역량 격차 분석
        skill_gaps = _analyze_skill_gaps(
            current_skills=request.current_skills,
            recommended_careers=recommended_careers,
            llm_service=llm_service,
            grade=request.grade,
            disability_type=student.disability_type,
        )

        # 4. LLM 기반 커리어 경로 생성
        career_paths = _generate_career_paths(
            request=request,
            recommended_careers=recommended_careers,
            llm_service=llm_service,
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
            or os.getenv("CAREER_SEARCH_DEFAULT_CURRENT_SKILLS", "").strip()
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


def _analyze_skill_gaps(
    current_skills: str,
    recommended_careers: List[RecommendedCareer],
    llm_service: Optional[LLMService] = None,
    grade: Optional[str] = None,
    disability_type: Optional[str] = None,
) -> List[SkillGap]:
    """LLM을 사용해 현재 역량과 목표 직업 요구 역량 간의 문맥적 격차를 분석합니다."""
    skill_gaps = []
    try:
        service = llm_service or LLMService()
    except Exception:
        service = None
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

        gap_skills = gap_result.get("gap_skills", [])
        # Fallback: LLM 실패 시 단순 규칙 기반 gap 생성으로 API 500 방지
        if not gap_skills:
            gap_skills = career.required_skills[:5]

        if gap_skills:
            skill_gaps.append(SkillGap(
                job_title=career.job_title,
                current_level=gap_result.get("current_level", []),
                required_level=gap_result.get("required_level", career.required_skills),
                gap_skills=gap_skills,
                development_suggestions=gap_result.get(
                    "development_suggestions",
                    [
                        "관찰 가능한 행동 단위로 목표를 쪼개서 연습합니다.",
                        "시각/촉각 단서와 반복 루틴으로 요구 역량을 단계적으로 학습합니다.",
                    ],
                ),
            ))

    return skill_gaps


def _generate_career_paths(
    request: CareerRecommendationRequest,
    recommended_careers: List[RecommendedCareer],
    llm_service: Optional[LLMService] = None,
    disability_type: Optional[str] = None,
    career_profiles: Optional[List[Dict[str, Any]]] = None,
) -> List[CareerPath]:
    """LLM을 사용해 outlook 기반 학생 맞춤 커리어 경로를 생성합니다."""
    paths = []

    profile_map = {p.get("job_title", ""): p for p in (career_profiles or [])}
    try:
        service = llm_service or LLMService()
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
            normalized_stages = [
                {
                    "stage": "현재",
                    "focus": request.current_skills,
                    "description": "현재 역량을 기준으로 직무 적합도를 점검합니다."
                }
            ]

        path = CareerPath(
            current_learning=request.current_skills,
            target_career=career.job_title,
            stages=normalized_stages,
            estimated_timeline=str(roadmap.get("estimated_timeline", "개별 평가 필요"))
        )
        paths.append(path)

    return paths