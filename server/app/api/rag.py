"""Common RAG API for curriculum and career data.
This API is shared across home, school, and center endpoints.
Provides RAG-based recommendations for scaffolding and career guidance.
"""

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
from app.db.database import get_db
from app.db.models import Feedback

router = APIRouter()


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
        orchestrator = RAGOrchestrator()

        # RAG 분석 수행
        analysis_result = orchestrator.analyze_and_recommend(request, db)

        # 결과를 데이터베이스에 저장
        feedback = Feedback(
            student_id=request.student_id,
            disability_type=request.disability_type,
            teacher_description=request.teacher_description,
            llm_analysis=analysis_result.llm_analysis.dict(),
            scaffolding_recommendations=analysis_result.scaffolding_recommendation.dict(),
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
        rag_service = RAGService()
        
        # 1. 학생의 현재 역량/학습 내용을 기반으로 관련 직업 검색
        career_results = rag_service.search_career(
            query=request.current_skills,
            k=10
        )
        
        if not career_results:
            raise HTTPException(status_code=404, detail="관련 직업을 찾을 수 없습니다.")
        
        # 2. LLM을 통해 분석 (현재 역량과 직업 요구 역량 비교)
        # TODO: LLM 서비스 연동하여 더精细한 분석 수행
        
        # 3. 결과 구성
        recommended_careers = []
        skill_gaps = []
        
        for idx, career in enumerate(career_results[:5]):
            metadata = career.get("metadata", {})
            content = career.get("content", "")
            
            # 역량 추출 (간단한 파싱)
            competencies = _extract_competencies(content)
            
            recommended_careers.append(RecommendedCareer(
                job_id=metadata.get("job_id", ""),
                job_title=metadata.get("job_title", ""),
                category=metadata.get("category", ""),
                match_score=career.get("score", 0),
                required_skills=competencies["required"],
                outlook=metadata.get("outlook_scaffolding", "")
            ))
        
        # 4. 역량 격차 분석
        skill_gaps = _analyze_skill_gaps(request.current_skills, recommended_careers)
        
        # 5. 커리어 경로 생성
        career_paths = _generate_career_paths(request, recommended_careers)
        
        return CareerRecommendationResponse(
            student_id=request.student_id,
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
    student_id: Optional[int] = None,  # 학생 ID 파라미터 추가
    db: Session = Depends(get_db)      # DB 세션 추가
):
    """
    커리어 데이터 검색 및 역량 격차 분석 API
    """
    try:
        # 1. 기본 직업 검색 수행
        rag_service = RAGService()
        results = rag_service.search_career(query=query, k=k)
        
        # 2. 학생 정보가 있을 경우 현재 역량(설명) 가져오기
        current_skills = ""
        if student_id:
            latest_fb = db.query(Feedback).filter(Feedback.student_id == student_id).order_by(Feedback.created_at.desc()).first()
            if latest_fb:
                current_skills = latest_fb.teacher_description

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


def _analyze_skill_gaps(current_skills: str, recommended_careers: List[RecommendedCareer]) -> List[SkillGap]:
    """현재 역량과 목표 직업의 요구 역량 간 격차를 분석합니다."""
    skill_gaps = []
    
    current_skills_set = set(current_skills.lower().split())
    
    for career in recommended_careers[:3]:
        required_skills = set(skill.lower() for skill in career.required_skills)
        missing_skills = required_skills - current_skills_set
        
        if missing_skills:
            skill_gaps.append(SkillGap(
                job_title=career.job_title,
                current_level=list(current_skills_set & required_skills),
                required_level=career.required_skills,
                gap_skills=list(missing_skills),
                development_suggestions=_generate_development_suggestions(list(missing_skills))
            ))
    
    return skill_gaps


def _generate_development_suggestions(gap_skills: List[str]) -> List[str]:
    """결격난 역량을 개발하기 위한 제안을 생성합니다."""
    suggestions = []
    
    for skill in gap_skills:
        if "도면" in skill or "설계" in skill:
            suggestions.append(f"- {skill}: 기초 설계 도면 읽기 연습")
        elif "손재주" in skill or "실습" in skill:
            suggestions.append(f"- {skill}: 관련 분야 실습 경험 쌓기")
        elif "コミュニケーション" in skill or "소통" in skill:
            suggestions.append(f"- {skill}: 팀 프로젝트 참여하여 소통 역량 강화")
        else:
            suggestions.append(f"- {skill}: 관련 교과 학습 및 자격증 준비")
    
    return suggestions


def _generate_career_paths(
    request: CareerRecommendationRequest,
    recommended_careers: List[RecommendedCareer]
) -> List[CareerPath]:
    """학생의 현재 학습에서부터 목표 직업까지의 경로를 생성합니다."""
    paths = []
    
    for career in recommended_careers[:3]:
        # 현재 학습 단계에서 해당 직업까지의 경로
        path = CareerPath(
            current_learning=request.current_skills,
            target_career=career.job_title,
            stages=[
                {
                    "stage": "현재",
                    "focus": request.current_skills,
                    "description": "현재 학습 중인 내용"
                },
                {
                    "stage": "단기",
                    "focus": "기초 역량 확보",
                    "description": f"{career.job_title}에 필요한 기본 역량 학습"
                },
                {
                    "stage": "중기",
                    "focus": "전문 역량 개발",
                    "description": "관련 자격증 취득 및 실습 경험"
                },
                {
                    "stage": "장기",
                    "focus": "취업 준비",
                    "description": f"{career.job_title} 관련 직종 취직"
                }
            ],
            estimated_timeline="3-5년"
        )
        paths.append(path)
    
    return paths