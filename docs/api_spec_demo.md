# API 명세 문서 — 시연용

---

## 1. `GET /student/`

학생 기본 정보를 반환합니다.

**Response**
```json
{
  "name": "이지훈",
  "id": 1,
  "created_at": "2026-04-25T06:07:35",
  "current_level": "초등학교 1~2학년 수준의 기초 문해력 및 수감각 보유",
  "disability_type": "지적 장애 (경도)",
  "additional_diagnoses": "ADHD (주의력 결핍 및 과잉 행동 장애)",
  "behavioral_traits": "3단계 이상의 긴 지시어에 혼란을 느낌. 과제 수행 중 어려움을 느끼면 그림을 그리며 회피함. 시각적 타이머와 캐릭터 보상 시 집중 시간 15분 유지."
}
```

---

## 2. `GET /student/school-life`

오늘의 시간표, 급식, 학사 일정, 하교 시간을 반환합니다.

**Response**
```json
{
  "lunch_menu": "참치야채비빔밥, 북어국, 갈릭미트볼야채볶음, 고구마맛탕, 백김치, 우유컵케익",
  "dismissal_time": "16:15",
  "academic_calendar": "일정 없음",
  "today_timetable": [
    "종교와 삶Ⅰ",
    "수학",
    "음악",
    "기술·가정",
    "사회",
    "과학",
    "(창)자율·자치활동"
  ]
}
```

---

## 3. `GET /student/progress`

학생의 누적 피드백 및 AI 분석 이력을 반환합니다.

**Response 구조**
```json
{
  "feedbacks": [
    {
      "id": 1,
      "performance": "AI 분석: medium 수준",
      "scaffolding_effectiveness": "AI 추천 적용 전",
      "disability_type": "자폐성 장애",
      "teacher_description": "교사 관찰 내용",
      "llm_analysis": {
        "detected_level": "medium",
        "learning_gaps": ["학습 격차 항목들"],
        "recommended_strategies": ["추천 전략들"],
        "confidence_score": 0.85,
        "analysis_summary": "분석 요약"
      },
      "scaffolding_recommendations": {
        "recommended_level": "medium",
        "rationale": "추천 근거",
        "scaffolding_details": {
          "level": "medium",
          "description": "지원 방향 설명",
          "activities": [
            {
              "name": "활동명",
              "description": "활동 설명",
              "duration": "15분",
              "materials": ["기본 교재"]
            }
          ],
          "strategies": ["개별화된 접근", "긍정적 강화"]
        },
        "achievement_standard": {
          "grade": "3",
          "subject": "국어",
          "standard_text": "성취기준 내용",
          "relevance_score": 0.5
        },
        "additional_notes": "전문가 상담 권고 등 추가 메모"
      },
      "created_at": "2026-04-27T03:04:12"
    }
    // ... 총 29건
  ],
  "progress_summary": "총 29개의 피드백 기록이 있습니다. 최근 분석 결과: 중간 수준: 3회"
}
```

> **시연 포인트**: 피드백 #3, #10 등 `confidence_score`가 0.8 이상인 케이스에서 `learning_gaps`와 `recommended_strategies`가 상세하게 채워지는 것을 확인할 수 있습니다.

---

## 4. `POST /rag/scaffolding-recommendation`

교사 관찰 내용을 입력하면 AI가 스캐폴딩 수준과 전략을 추천합니다.

**Request**
```json
{
  "grade": "초등학교 3학년",
  "subject": "수학",
  "teacher_description": "수 모형을 사용할 때는 일의 자리 계산을 수행하나, 받아올림 단계에서 과제를 중단하고 학습지에 캐릭터 그림을 그림. 구두 지시에는 '어려워요'라고 답하며 도움 요청을 먼저 하지 못함.",
  "past_feedback_ids": []
}
```

**Response**
```json
{
  "recommended_level": "하",
  "rationale": "학생의 현재 능력 수준을 '하'로 평가. 주요 학습 격차: 실생활 문제 연산 도출, 세로셈 자릿값 계산 등. 신뢰도: 0.72",
  "scaffolding_details": {
    "level": "하",
    "description": "문제 해결을 돕는 삽화나 도식을 활용하여 이해 지원; 식 도출을 중점으로 지도하며 계산 방법은 학생의 자율성 존중",
    "activities": [
      { "name": "교육과정 활동 1", "description": "거스름돈 계산이나 물건 수 합산 문제를 짧은 단계로 나누어 반복 연습" },
      { "name": "교육과정 활동 2", "description": "실생활 상황을 보고 연산 식을 도출하기를 짧은 단계로 나누어 반복 연습" },
      { "name": "교육과정 활동 3", "description": "구체물로 상황을 재현하고 전체/남은 수를 구하기를 짧은 단계로 나누어 반복 연습" }
    ],
    "strategies": [
      "세로셈 지도 시 자릿값 위치를 시각적으로 가이드 함",
      "구체물 10개 묶음을 더하거나 빼며 전체 개수 확인",
      "문제 해결을 돕는 삽화나 도식을 활용하여 이해 지원",
      "식 도출을 중점으로 지도하며 계산 방법은 학생의 자율성 존중"
    ]
  },
  "achievement_standard": {
    "standard_id": "6수학01-08",
    "standard_text": "받아올림(내림)이 없는 몇십의 덧셈, 뺄셈과 관련된 실생활 문제를 해결한다.",
    "grade": "6",
    "subject": "math",
    "disability_type": "중도중복장애",
    "relevance_score": 0.5676
  },
  "related_achievement_standards": [
    "[6수학01-08] 받아올림(내림)이 없는 몇십의 덧셈, 뺄셈과 관련된 실생활 문제를 해결한다. (관련도 0.57)",
    "[6수학01-07] 받아올림(내림)이 없는 몇십의 덧셈과 뺄셈을 한다. (관련도 0.56)",
    "[4수학01-03] 9 이하의 수를 읽고 쓴다. (관련도 0.52)"
  ]
}
```

---

## 5. `POST /rag/career-recommendation`

학생의 현재 역량과 관심사를 입력하면 적합한 직업과 진로 경로를 추천합니다.

**Request**
```json
{
  "current_skills": "좋아하는 캐릭터의 특징을 세밀하게 기억하여 그림. 반복 루틴과 시각 자료가 있는 작업에서 20분 이상의 높은 몰입도를 보임.",
  "grade": "초등학교 3학년",
  "interests": ["캐릭터 그리기", "색칠하기", "만들기"],
  "disability_type": "지적 장애 (경도)"
}
```

**Response**
```json
{
  "recommended_careers": [
    { "job_title": "캐릭터디자이너", "category": "예술분야(전문직)", "match_score": 0.508 },
    { "job_title": "화가",           "category": "예술분야(전문직)", "match_score": 0.475 },
    { "job_title": "일러스트레이터", "category": "예술분야(전문직)", "match_score": 0.472 },
    { "job_title": "애니메이션작가", "category": "예술분야(전문직)", "match_score": 0.462 },
    { "job_title": "만화가",         "category": "예술분야(전문직)", "match_score": 0.456 }
  ],
  "skill_gaps": [
    {
      "job_title": "캐릭터디자이너",
      "gap_skills": ["손재능", "공간시각능력", "창의력", "기발한 발상", "컴퓨터 그래픽 지식"],
      "development_suggestions": [
        "핵심 역량을 10~15분 단위 반복 과제로 나눠 연습",
        "체크리스트 기반으로 과제 시작-중간-완료 단계를 시각화",
        "주 1회 동일 과업 재수행으로 수행 정확도를 기록"
      ]
    }
    // 화가, 일러스트레이터 동일 구조
  ],
  "career_paths": [
    {
      "target_career": "캐릭터디자이너",
      "estimated_timeline": "6~12개월",
      "stages": [
        { "stage": "현재",          "focus": "현재 강점 파악",    "description": "직무 요구 역량과 현재 역량 비교" },
        { "stage": "단기(1~3개월)", "focus": "핵심 기초 역량 강화", "description": "손재능·공간시각능력·창의력 중심 반복 과제" },
        { "stage": "중기(3~6개월)", "focus": "실습 기반 적용",     "description": "체크리스트 기반 모의/현장 실습" },
        { "stage": "장기(6개월+)",  "focus": "직무 전환 및 유지",  "description": "실제 업무 환경 역할 확장 + 피드백 루프" }
      ]
    }
    // 화가, 일러스트레이터 동일 구조
  ]
}
```