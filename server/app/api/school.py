from fastapi import APIRouter, HTTPException
from typing import Dict, List
from app.schemas.school import GoalRecommendationRequest, GoalRecommendationResponse, LearningStep

router = APIRouter()

@router.post("/goals", response_model=GoalRecommendationResponse)
async def recommend_goals(request: GoalRecommendationRequest):
    """
    성취목표 추천 API
    - RAG 기반 최적 성취기준 문항 및 학습 단계 추출
    - 2022 개정 특수교육 성취기준 기반
    """
    try:
        # 실제로는 RAG 시스템으로 성취기준 데이터베이스 검색
        # 지금은 과목/학년/수준에 따른 모의 데이터 반환

        if request.subject == "국어":
            if request.grade <= 3:  # 저학년
                goals = [
                    "받침 있는 글자를 읽고 쓸 수 있다.",
                    "단순한 문장을 이해하고 응답할 수 있다.",
                    "기본적인 단어를 인식하고 사용할 수 있다."
                ]
                steps = [
                    LearningStep(
                        step_number=1,
                        description="기초 글자 인식",
                        activities=["받침 없는 글자 연습", "단순한 단어 카드 사용"]
                    ),
                    LearningStep(
                        step_number=2,
                        description="받침 있는 글자 도입",
                        activities=["받침 있는 단어 보여주기", "소리 내어 읽기 연습"]
                    ),
                    LearningStep(
                        step_number=3,
                        description="문장 수준 적용",
                        activities=["단순 문장 읽기", "그림과 함께 문장 이해"]
                    )
                ]
                rationale = "저학년 국어 학습의 기초를 다지기 위해 단계적 접근을 추천합니다."
            else:  # 고학년
                goals = [
                    "복잡한 문장을 이해하고 요약할 수 있다.",
                    "다양한 어휘를 사용한 의사소통이 가능하다.",
                    "독서를 통한 정보 습득이 가능하다."
                ]
                steps = [
                    LearningStep(
                        step_number=1,
                        description="어휘 확장",
                        activities=["새로운 단어 학습", "단어장 만들기"]
                    ),
                    LearningStep(
                        step_number=2,
                        description="문장 이해",
                        activities=["문장 구조 분석", "요약 연습"]
                    ),
                    LearningStep(
                        step_number=3,
                        description="응용 및 실습",
                        activities=["독서 활동", "토론 참여"]
                    )
                ]
                rationale = "고학년 국어 학습의 심화 내용을 고려한 목표 설정입니다."

        elif request.subject == "수학":
            if request.grade <= 3:  # 저학년
                goals = [
                    "기본적인 덧셈과 뺄셈을 할 수 있다.",
                    "1-20까지의 수를 인식하고 사용할 수 있다.",
                    "단순한 도형을 인식할 수 있다."
                ]
                steps = [
                    LearningStep(
                        step_number=1,
                        description="수 인식",
                        activities=["숫자 카드 사용", "세기 연습"]
                    ),
                    LearningStep(
                        step_number=2,
                        description="기본 연산 도입",
                        activities=["구슬이나 블록으로 덧셈/뺄셈", "시각적 보조 도구 사용"]
                    ),
                    LearningStep(
                        step_number=3,
                        description="도형 인식",
                        activities=["기본 도형 찾기", "도형 맞추기 게임"]
                    )
                ]
                rationale = "수학의 기초 개념을 단계적으로 습득할 수 있도록 구성했습니다."
            else:  # 고학년
                goals = [
                    "복잡한 계산을 할 수 있다.",
                    "기본적인 분수와 소수를 이해한다.",
                    "단순한 문제 해결 능력을 갖는다."
                ]
                steps = [
                    LearningStep(
                        step_number=1,
                        description="계산 능력 향상",
                        activities=["다양한 계산 연습", "계산기 사용 학습"]
                    ),
                    LearningStep(
                        step_number=2,
                        description="분수/소수 개념",
                        activities=["시각적 분수 표현", "실생활 적용 예시"]
                    ),
                    LearningStep(
                        step_number=3,
                        description="문제 해결",
                        activities=["단계적 문제 풀이", "논리적 사고 훈련"]
                    )
                ]
                rationale = "고학년 수학의 심화 개념을 고려한 학습 계획입니다."

        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 과목입니다.")

        # 학생 수준에 따른 조정 (간단한 예시)
        if "고급" in request.current_level:
            rationale += " 학생의 높은 수준을 고려하여 심화 내용을 추가했습니다."
        elif "기초" in request.current_level:
            rationale += " 학생의 기초 수준을 고려하여 기본 개념부터 시작합니다."

        return GoalRecommendationResponse(
            subject=request.subject,
            grade=request.grade,
            recommended_goals=goals,
            learning_steps=steps,
            rationale=rationale
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목표 추천 중 오류 발생: {str(e)}")