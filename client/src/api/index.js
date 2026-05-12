import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
})

const sampleStudent = {
  id: 1,
  name: '나의 아이',
  disability_type: '자폐 스펙트럼',
  additional_diagnoses: 'ADHD',
  current_level: '초등 3학년 수준 읽기/쓰기 보조 필요',
  behavioral_traits: '어려운 과제를 만나면 감정이 급격히 올라감',
}

const sampleProgress = {
  feedbacks: [
    {
      id: 1,
      teacher_description: '읽기 시간에 집중이 흐트러졌지만 짧은 지시에는 잘 반응함',
      llm_analysis: { detected_level: 'medium' },
      created_at: '2026-04-21T09:30:00',
    },
    {
      id: 2,
      teacher_description: '수학 활동에서 시각 자료를 활용하니 참여도가 높아짐',
      llm_analysis: { detected_level: 'high' },
      created_at: '2026-04-23T10:10:00',
    },
  ],
  progress_summary: '최근 시각적 단서 제공 시 학습 몰입도가 향상되고 있습니다.',
}

const sampleSchoolLife = {
  lunch_menu: '된장국, 닭갈비, 계절나물, 밥',
  dismissal_time: '15:30',
  academic_calendar: '일정 없음',
  today_timetable: ['국어', '수학', '미술'],
  tomorrow_prep: ['체육복', '색연필', '국어 공책'],
}

const sampleScaffolding = {
  recommended_level: 'medium',
  rationale: '짧은 지시와 시각 단서 제공 시 과제 지속 시간이 늘어납니다.',
  scaffolding_details: {
    level: 'medium',
    description: '언어적 안내와 시각적 힌트를 병행합니다.',
    strategies: ['한 번에 한 단계 지시', '시각 일정표 제시', '성공 즉시 강화 피드백'],
    activities: [
      {
        name: '핵심 문장 찾기',
        description: '짧은 문단에서 핵심 문장을 색 스티커로 표시합니다.',
        duration: '15분',
      },
    ],
  },
  achievement_standard: {
    standard_id: '3수학01-01',
    grade: '초3',
    subject: '수학',
    disability_type: '자폐 스펙트럼',
    standard_text: '두 자리 수의 덧셈과 뺄셈 과정을 시각 자료와 함께 설명할 수 있다.',
    diagnostic_criteria: ['시각 자료를 활용한 연산 과정 설명', '단계별 도움 요청'],
    activities: ['수 모형으로 받아올림 설명하기', '그림 단서로 풀이 순서 정리하기'],
    scaffolding_levels: { high: '독립 수행', medium: '언어·시각 단서', low: '모델링 제공' },
    scaffolding_bank_general: ['한 단계 지시', '즉각 강화', '시각 일정표'],
    scaffolding_bank_disability_specific: { '자폐 스펙트럼': '예측 가능한 순서와 그림 단서를 먼저 제공합니다.' },
    relevance_score: 0.82,
  },
  related_achievement_standards: [
    '국어: 핵심 낱말의 의미를 문맥에서 파악한다.',
    '수학: 수 모형을 활용해 연산 과정을 나타낸다.',
  ],
  additional_notes: '수업 적용 후 반응을 피드백 기록에 남기면 다음 추천에 반영됩니다.',
}

const sampleCurriculumResults = {
  query: '',
  count: 2,
  results: [
    {
      content: '국어 읽기: 주요 낱말의 의미를 문맥에서 파악한다.',
      metadata: { subject: '국어', grade: '초3' },
      score: 0.84,
    },
    {
      content: '수학: 두 자리 수의 덧셈과 뺄셈 과정을 설명할 수 있다.',
      metadata: { subject: '수학', grade: '초3' },
      score: 0.81,
    },
  ],
}

const sampleCareerSearch = {
  query: '',
  count: 2,
  results: [
    {
      job_title: '디지털 콘텐츠 디자이너',
      required_skills: ['시각 표현', '도구 활용', '협업 커뮤니케이션'],
      skill_gap: {
        gap_skills: ['도구 활용', '협업 커뮤니케이션'],
        development_suggestions: [
          '- 도구 활용: 기초 디자인 툴 사용 경험 쌓기',
          '- 협업 커뮤니케이션: 팀 프로젝트 참여로 소통 역량 강화',
        ],
      },
      score: 0.79,
    },
    {
      job_title: '서비스 도우미 트레이너',
      required_skills: ['절차 이해', '상황 대응', '대인 소통'],
      skill_gap: {
        gap_skills: ['상황 대응'],
        development_suggestions: ['- 상황 대응: 역할 놀이 기반 시나리오 훈련'],
      },
      score: 0.75,
    },
  ],
}

const sampleCareerRecommendation = {
  current_skills: '손작업과 순서 기억이 안정적이며 시각 자료를 활용한 활동에 오래 참여합니다.',
  recommended_careers: [
    {
      job_id: 'sample-baker',
      job_title: '제과제빵사',
      category: '음식 서비스',
      match_score: 0.82,
      required_skills: ['손의 정교함', '순서 기억', '위생 절차'],
      outlook: '반복 루틴과 손작업 강점을 작은 체험으로 연결할 수 있습니다.',
    },
  ],
  skill_gaps: [
    {
      job_title: '제과제빵사',
      current_level: ['손작업', '순서 기억'],
      required_level: ['도구 활용', '작업 절차 언어화'],
      gap_skills: ['도구 활용', '작업 절차 언어화'],
      development_suggestions: ['도구 이름 맞히기', '작업 순서를 그림 카드로 정리하기'],
    },
  ],
  career_paths: [
    {
      current_learning: '손작업과 순서 기억 활동',
      target_career: '제과제빵사',
      estimated_timeline: '장기 탐색',
      stages: [
        { stage: '현재', description: '손작업과 순서 기억 활동' },
        { stage: '단기', description: '도구 사용과 작업 순서 연습' },
        { stage: '중기', description: '반복 작업 루틴과 위생 절차' },
        { stage: '장기', description: '직무 체험과 현장 적응' },
      ],
    },
  ],
}

function withFallback(requestFn, fallbackData) {
  return requestFn().catch(() => fallbackData)
}

function toCurriculumSubjectCode(subject) {
  const map = {
    수학: 'math',
    국어: 'korean',
  }
  return map[subject] || subject
}

function toGradeCode(grade) {
  if (!grade) return grade
  const match = String(grade).match(/[1-6]/)
  return match ? match[0] : grade
}

export function getStudent() {
  return withFallback(async () => (await apiClient.get('/student/')).data, sampleStudent)
}

export function patchStudentTraits(payload) {
  return withFallback(async () => (await apiClient.patch('/student/', payload)).data, {
    ...sampleStudent,
    ...payload,
  })
}

export function getStudentProgress() {
  return withFallback(async () => (await apiClient.get('/student/progress')).data, sampleProgress)
}

export function getSchoolLife() {
  return withFallback(async () => (await apiClient.get('/student/school-life')).data, sampleSchoolLife)
}

export function getScaffoldingRecommendation(payload) {
  return withFallback(async () => (await apiClient.post('/rag/scaffolding-recommendation', payload)).data, sampleScaffolding)
}

export function searchCurriculum(query, params = {}) {
  const normalizedParams = {
    ...params,
    subject: params.subject ? toCurriculumSubjectCode(params.subject) : params.subject,
    grade: params.grade ? toGradeCode(params.grade) : params.grade,
  }
  return withFallback(
    async () => (await apiClient.get('/rag/curriculum-search', { params: { query, ...normalizedParams } })).data,
    { ...sampleCurriculumResults, query },
  )
}

export function searchCareer(query, params = {}) {
  return withFallback(
    async () => (await apiClient.get('/rag/career-search', { params: { query, ...params } })).data,
    { ...sampleCareerSearch, query },
  )
}

export function getCareerRecommendation(payload) {
  return withFallback(
    async () => (await apiClient.post('/rag/career-recommendation', payload)).data,
    { ...sampleCareerRecommendation, current_skills: payload?.current_skills || sampleCareerRecommendation.current_skills },
  )
}
