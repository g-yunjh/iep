"""Common RAG API for curriculum and career data.
This API is shared across home, school, and center endpoints.
Provides RAG-based recommendations for scaffolding and career guidance.
"""

import json
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
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
    db: Session = Depends(get_db)
):
    """
    커리어 데이터 검색 및 역량 격차 분석 API
    """
    try:
        # 1. 기본 직업 검색 수행
        rag_service = RAGService()
        results = rag_service.search_career(query=query, k=k)
        
        # 2. 단일 학생 정보에서 현재 역량(설명) 가져오기
        current_skills = ""
        student = db.query(Student).order_by(Student.id.asc()).first()
        if student:
            latest_fb = (
                db.query(Feedback)
                .filter(Feedback.student_id == student.id)
                .order_by(Feedback.created_at.desc())
                .first()
            )
            current_skills = (
                latest_fb.teacher_description
                if latest_fb and latest_fb.teacher_description
                else " ".join(
                    filter(
                        None,
                        [student.current_level, student.behavioral_traits, student.additional_diagnoses],
                    )
                )
            )

        # 3. 검색 결과에 역량 격차 정보 추가
        enhanced_results = []
        for res in results:
            content = res.get("content", "")
            metadata = res.get("metadata", {})
            
            # 기존 헬퍼 함수로 역량 추출 및 격차 분석
            required = _extract_competencies(content)["required"]
            
            gap_data = None
            if current_skills:
                # 임시 객체를 생성하여 기존 분석 함수 재활용
                temp_career = RecommendedCareer(
                    job_id=metadata.get("job_id", ""),
                    job_title=metadata.get("job_title", ""),
                    category=metadata.get("category", ""),
                    match_score=res.get("score", 0),
                    required_skills=required,
                    outlook=metadata.get("outlook_scaffolding", "")
                )
                gaps = _analyze_skill_gaps(current_skills, [temp_career])
                gap_data = gaps[0] if gaps else None

            enhanced_results.append({
                "job_title": metadata.get("job_title"),
                "required_skills": required,
                "skill_gap": gap_data,  # 분석된 격차 정보 추가
                "score": res.get("score")
            })

        return {
            "query": query,
            "results": enhanced_results,
            "count": len(enhanced_results)
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
                status="initialized" if all_info.get("curriculum", {}).get("status") == "initialized" else "not_initialized",
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

    service = llm_service or LLMService()
    for career in recommended_careers[:3]:
        gap_result = service.analyze_career_skill_gap(
            current_skills=current_skills,
            job_title=career.job_title,
            required_skills=career.required_skills,
            outlook_scaffolding=career.outlook,
            grade=grade,
            disability_type=disability_type,
        )

        gap_skills = gap_result.get("gap_skills", [])
        if gap_skills:
            skill_gaps.append(SkillGap(
                job_title=career.job_title,
                current_level=gap_result.get("current_level", []),
                required_level=gap_result.get("required_level", career.required_skills),
                gap_skills=gap_skills,
                development_suggestions=gap_result.get("development_suggestions", []),
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
    service = llm_service or LLMService()

    for career in recommended_careers[:3]:
        profile = profile_map.get(career.job_title, {})
        roadmap = service.generate_career_path(
            current_skills=request.current_skills,
            job_title=career.job_title,
            required_skills=career.required_skills,
            outlook_scaffolding=career.outlook or profile.get("outlook_scaffolding", ""),
            certifications=profile.get("certifications", []),
            education_paths=profile.get("education", []),
            disability_type=disability_type,
        )

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