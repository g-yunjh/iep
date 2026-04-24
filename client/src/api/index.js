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
  meal_info: {
    lunch: '된장국, 닭갈비, 계절나물, 밥',
    snack: '요거트, 사과',
  },
  dismissal_time: '15:30',
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

function withFallback(requestFn, fallbackData) {
  return requestFn().catch(() => fallbackData)
}

export function getStudent() {
  return withFallback(async () => (await apiClient.get('/student')).data, sampleStudent)
}

export function patchStudentTraits(payload) {
  return withFallback(async () => (await apiClient.patch('/student/traits', payload)).data, {
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

export function searchCurriculum(query) {
  return withFallback(
    async () => (await apiClient.get('/rag/curriculum-search', { params: { query } })).data,
    { ...sampleCurriculumResults, query },
  )
}

export function searchCareer(query) {
  return withFallback(
    async () => (await apiClient.get('/rag/career-search', { params: { query } })).data,
    { ...sampleCareerSearch, query },
  )
}
