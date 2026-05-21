import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 180000,
})

/** 서버 레벨 토큰 → UI용 한글 (상·중·하) */
const LEVEL_EN_TO_KO = { high: '상', medium: '중', low: '하' }

export function mapLevelToKorean(level) {
  if (level == null || level === '') return null
  const raw = String(level).trim()
  const key = raw.toLowerCase()
  if (LEVEL_EN_TO_KO[key]) return LEVEL_EN_TO_KO[key]
  if (['상', '중', '하'].includes(raw)) return raw
  return raw
}

export function mapLevelTokensInString(text) {
  if (typeof text !== 'string') return text
  return text.replace(/\bhigh\b/gi, '상').replace(/\bmedium\b/gi, '중').replace(/\blow\b/gi, '하')
}

function cleanDisplayText(text) {
  return mapLevelTokensInString(String(text || ''))
    .replace(/\r\n?/g, '\n')
    .split('\n')
    .map((line) => line.trim().replace(/^(?:[-*•·]\s*|\d+[.)]\s*)+/, ''))
    .filter(Boolean)
    .join(' ')
    .replace(/\s*([?!])\s*,+\s*/g, '$1 ')
    .replace(/\s*\.\s*,\s*/g, '. ')
    .replace(/\s*,\s*,+\s*/g, ', ')
    .replace(/^[,;:\s]+|[,;:\s]+$/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function appendTextFragment(base, next) {
  const value = cleanDisplayText(next)
  if (!value) return base
  return base ? `${base} ${value}` : value
}

function normalizeRationaleForParsing(text) {
  return mapLevelTokensInString(String(text || ''))
    .replace(/\r\n?/g, '\n')
    .replace(/\s*(?=(?:평가\s*요약|분석\s*요약|주요\s*학습\s*격차|관련\s*성취기준|근거\s*성취기준|신뢰도)\s*[:：])/g, '\n')
    .split('\n')
    .map((line) => line.trim().replace(/^(?:[-*•·]\s*|\d+[.)]\s*)+/, ''))
    .filter(Boolean)
}

function formatConfidenceValue(value) {
  if (value == null || value === '') return ''
  const raw = String(value).trim()
  if (!raw) return ''
  if (raw.endsWith('%')) return raw
  const numeric = Number(raw)
  if (Number.isNaN(numeric)) return raw
  return numeric <= 1 ? numeric.toFixed(2) : `${Math.round(numeric)}%`
}

function extractConfidenceFromText(text) {
  const match = String(text || '').match(/신뢰도\s*[:：]\s*([0-9]+(?:\.[0-9]+)?%?)/)
  return formatConfidenceValue(match?.[1])
}

function getLearningGapText(analysis, rec) {
  const candidates = [
    analysis?.learning_gaps,
    rec?.learning_gaps,
    rec?.analysis?.learning_gaps,
  ]
  const gapList = candidates.find((value) => Array.isArray(value) && value.length)
  if (gapList) {
    return gapList.map((item) => cleanDisplayText(item)).filter(Boolean).join(' · ')
  }
  return ''
}

function getStandardDisplayText(standard) {
  if (!standard || typeof standard !== 'object') return ''
  const text = standard.standard_text || standard.text || ''
  if (!text) return ''
  const id = standard.standard_id || standard.id
  const cleanText = cleanDisplayText(text)
  return id ? `[${id}] ${cleanText}` : cleanText
}

export function buildScaffoldingPresentation(rec, llmAnalysis = null) {
  const sections = {
    assessment: '',
    gap: '',
    standard: '',
    confidence: '',
  }

  if (!rec || typeof rec !== 'object') return sections

  const analysis = llmAnalysis || rec.llm_analysis || rec.analysis || {}
  let current = 'assessment'

  normalizeRationaleForParsing(rec.rationale).forEach((line) => {
    const confidenceMatch = line.match(/^신뢰도\s*[:：]\s*(.*)$/)
    if (confidenceMatch) {
      sections.confidence = sections.confidence || formatConfidenceValue(confidenceMatch[1])
      return
    }

    const assessmentMatch = line.match(/^(?:평가\s*요약|분석\s*요약)\s*[:：]\s*(.*)$/)
    if (assessmentMatch) {
      current = 'assessment'
      sections.assessment = appendTextFragment(sections.assessment, assessmentMatch[1])
      return
    }

    const gapMatch = line.match(/^주요\s*학습\s*격차\s*[:：]\s*(.*)$/)
    if (gapMatch) {
      current = 'gap'
      sections.gap = appendTextFragment(sections.gap, gapMatch[1])
      return
    }

    const standardMatch = line.match(/^(?:관련|근거)\s*성취기준\s*[:：]\s*(.*)$/)
    if (standardMatch) {
      current = 'standard'
      sections.standard = appendTextFragment(sections.standard, standardMatch[1])
      return
    }

    if (/^[상중하]\s*[:：]/.test(line)) {
      sections.assessment = appendTextFragment(sections.assessment, line.replace(/^[상중하]\s*[:：]\s*/, ''))
      return
    }

    sections[current] = appendTextFragment(sections[current], line)
  })

  if (!sections.assessment && typeof analysis.analysis_summary === 'string') {
    sections.assessment = cleanDisplayText(analysis.analysis_summary)
  }
  if (!sections.gap) sections.gap = getLearningGapText(analysis, rec)
  const standardDisplay = getStandardDisplayText(rec.achievement_standard)
  if (standardDisplay) {
    sections.standard = standardDisplay
  } else {
    sections.standard = cleanDisplayText(sections.standard)
  }
  sections.assessment = cleanDisplayText(sections.assessment)
  sections.gap = cleanDisplayText(sections.gap)

  const directConfidence =
    rec.confidence_score ??
    rec.confidence ??
    analysis.confidence_score ??
    analysis.confidence
  sections.confidence =
    sections.confidence ||
    formatConfidenceValue(directConfidence) ||
    extractConfidenceFromText(rec.rationale)

  return sections
}

function normalizeScaffoldingDetailsBlock(details) {
  if (!details || typeof details !== 'object') return details
  const next = { ...details }
  if (next.level != null) next.level = mapLevelToKorean(next.level) ?? next.level
  if (typeof next.description === 'string') next.description = cleanDisplayText(next.description)
  if (Array.isArray(next.strategies)) {
    next.strategies = next.strategies.map((s) => (typeof s === 'string' ? cleanDisplayText(s) : s))
  }
  if (Array.isArray(next.activities)) {
    next.activities = next.activities.map((a) => {
      if (!a || typeof a !== 'object') return a
      const act = { ...a }
      if (typeof act.name === 'string') act.name = cleanDisplayText(act.name)
      if (typeof act.description === 'string') act.description = cleanDisplayText(act.description)
      return act
    })
  }
  return next
}

function pickAchievementStandardForScaffolding(ach) {
  if (!ach || typeof ach !== 'object') return ach
  const keys = ['standard_id', 'standard_text', 'grade', 'subject', 'disability_type', 'relevance_score']
  const out = {}
  for (const k of keys) {
    if (ach[k] !== undefined) out[k] = ach[k]
  }
  return Object.keys(out).length ? out : ach
}

function normalizeScaffoldingRecommendations(rec, llmAnalysis = null) {
  if (rec == null) return rec
  if (typeof rec === 'string') return mapLevelTokensInString(rec)
  const next = { ...rec }
  if (next.recommended_level != null) next.recommended_level = mapLevelToKorean(next.recommended_level) ?? next.recommended_level
  if (typeof next.rationale === 'string') next.rationale = cleanDisplayText(next.rationale)
  if (typeof next.additional_notes === 'string') next.additional_notes = cleanDisplayText(next.additional_notes)
  if (next.scaffolding_details) next.scaffolding_details = normalizeScaffoldingDetailsBlock(next.scaffolding_details)
  if (next.achievement_standard) {
    next.achievement_standard = pickAchievementStandardForScaffolding({ ...next.achievement_standard })
  }
  next.presentation = buildScaffoldingPresentation(next, llmAnalysis)
  return next
}

function normalizeFeedbackItem(fb) {
  if (!fb || typeof fb !== 'object') return fb
  const next = { ...fb }
  if (typeof next.performance === 'string') next.performance = cleanDisplayText(next.performance)
  if (next.llm_analysis && typeof next.llm_analysis === 'object') {
    next.llm_analysis = { ...next.llm_analysis }
    if (next.llm_analysis.detected_level != null) {
      next.llm_analysis.detected_level = mapLevelToKorean(next.llm_analysis.detected_level) ?? next.llm_analysis.detected_level
    }
    if (typeof next.llm_analysis.analysis_summary === 'string') {
      next.llm_analysis.analysis_summary = cleanDisplayText(next.llm_analysis.analysis_summary)
    }
    if (Array.isArray(next.llm_analysis.learning_gaps)) {
      next.llm_analysis.learning_gaps = next.llm_analysis.learning_gaps.map((g) =>
        typeof g === 'string' ? cleanDisplayText(g) : g,
      )
    }
    if (Array.isArray(next.llm_analysis.recommended_strategies)) {
      next.llm_analysis.recommended_strategies = next.llm_analysis.recommended_strategies.map((s) =>
        typeof s === 'string' ? cleanDisplayText(s) : s,
      )
    }
  }
  if (next.scaffolding_recommendations != null) {
    next.scaffolding_recommendations = normalizeScaffoldingRecommendations(next.scaffolding_recommendations, next.llm_analysis)
  }
  return next
}

function normalizeProgressPayload(data) {
  if (!data || typeof data !== 'object') return data
  const out = {
    ...data,
    feedbacks: (data.feedbacks || []).map(normalizeFeedbackItem),
  }
  if (typeof out.progress_summary === 'string') {
    out.progress_summary = mapLevelTokensInString(out.progress_summary)
  }
  return out
}

function normalizeScaffoldingApiResponse(data) {
  if (!data || typeof data !== 'object') return data
  const next = { ...data }
  if (next.recommended_level != null) next.recommended_level = mapLevelToKorean(next.recommended_level) ?? next.recommended_level
  if (typeof next.rationale === 'string') next.rationale = cleanDisplayText(next.rationale)
  if (next.scaffolding_details) next.scaffolding_details = normalizeScaffoldingDetailsBlock(next.scaffolding_details)
  if (next.achievement_standard) {
    next.achievement_standard = pickAchievementStandardForScaffolding({ ...next.achievement_standard })
  }
  if (Array.isArray(next.related_achievement_standards)) {
    next.related_achievement_standards = next.related_achievement_standards.map((item) =>
      typeof item === 'string' ? cleanDisplayText(item) : item,
    )
  }
  if (typeof next.additional_notes === 'string') next.additional_notes = cleanDisplayText(next.additional_notes)
  next.presentation = buildScaffoldingPresentation(next, next.llm_analysis)
  return next
}

function normalizeCareerGapItem(gap) {
  if (!gap || typeof gap !== 'object') return gap
  const out = {
    job_title: gap.job_title,
    gap_skills: gap.gap_skills ?? gap.missing_skills ?? [],
    development_suggestions: gap.development_suggestions ?? gap.development_paths ?? [],
  }
  return out
}

function normalizeCareerRecommendationPayload(data) {
  if (!data || typeof data !== 'object') return data
  const next = { ...data }
  if (Array.isArray(next.recommended_careers)) {
    next.recommended_careers = next.recommended_careers.map((c) => {
      if (!c || typeof c !== 'object') return c
      return {
        job_title: c.job_title,
        category: c.category,
        match_score: typeof c.match_score === 'number' ? c.match_score : Number(c.score) || 0,
      }
    })
  }
  if (Array.isArray(next.skill_gaps)) {
    next.skill_gaps = next.skill_gaps.map(normalizeCareerGapItem)
  }
  return next
}

const sampleStudent = {
  id: 1,
  name: '이지훈',
  disability_type: '자폐 스펙트럼',
  additional_diagnoses: 'ADHD',
  current_level: '초등 3학년 수준 읽기/쓰기 보조 필요',
  behavioral_traits: '어려운 과제를 만나면 감정이 급격히 올라감',
}

const sampleProgress = {
  feedbacks: [
    {
      id: 1,
      performance: 'AI 분석: 중 수준',
      scaffolding_effectiveness: 'AI 추천 적용 전',
      disability_type: '자폐성 장애',
      teacher_description: '읽기 시간에 집중이 흐트러졌지만 짧은 지시에는 잘 반응함',
      llm_analysis: {
        detected_level: '중',
        learning_gaps: ['한 번에 여러 지시를 처리하는 데 어려움', '과제 전환 시 예고 없이 바뀌면 멈춤'],
        recommended_strategies: ['한 문장·한 단계 지시', '시각 일정표로 전환 예고', '완료 직후 구체적 강화'],
        confidence_score: 0.88,
        analysis_summary: '짧고 예측 가능한 지시가 주어질 때 참여도가 높아집니다.',
      },
      scaffolding_recommendations: {
        recommended_level: '중',
        rationale: '짧은 지시와 시각 단서 제공 시 과제 지속 시간이 늘어납니다.',
        scaffolding_details: {
          level: '중',
          description: '언어적 안내와 시각적 힌트를 병행합니다.',
          activities: [
            {
              name: '핵심 문장 찾기',
              description: '짧은 문단에서 핵심 문장을 색 스티커로 표시합니다.',
              duration: '15분',
              materials: ['기본 교재', '색 스티커'],
            },
          ],
          strategies: ['한 번에 한 단계 지시', '시각 일정표 제시', '성공 즉시 강화 피드백'],
        },
        achievement_standard: {
          grade: '3',
          subject: '국어',
          standard_text: '중심 내용을 짐작하고 듣거나 읽은 내용을 다른 표현으로 나타낼 수 있다.',
          relevance_score: 0.72,
        },
        additional_notes: '가정에서도 동일한 지시 방식을 유지하면 전환이 안정됩니다.',
      },
      created_at: '2026-04-21T09:30:00',
    },
    {
      id: 2,
      performance: 'AI 분석: 상 수준',
      scaffolding_effectiveness: '시각 자료 적용 후',
      disability_type: '자폐성 장애',
      teacher_description: '수학 활동에서 시각 자료를 활용하니 참여도가 높아짐',
      llm_analysis: {
        detected_level: '상',
        learning_gaps: ['복잡한 언어 설명만 있을 때 시작이 늦음'],
        recommended_strategies: ['수 모형·그림 단서 먼저 제시', '문제를 두 단계로 나누기'],
        confidence_score: 0.81,
        analysis_summary: '구체적 자료가 먼저 제시되면 스스로 절차를 이어가는 경향이 있습니다.',
      },
      scaffolding_recommendations: {
        recommended_level: '상',
        rationale: '시각 자료와 구조화된 순서가 있으면 독립에 가까운 수행이 가능합니다.',
        scaffolding_details: {
          level: '상',
          description: '확인 질문과 선택지 중심으로 최소 개입을 유지합니다.',
          activities: [
            {
              name: '스스로 순서 말하기',
              description: '풀이 후 스스로 단계를 말로 정리하게 합니다.',
              duration: '10분',
              materials: ['학습지'],
            },
          ],
          strategies: ['완료 후 요약 질문', '틀렸을 때 힌트 한 가지만 제시'],
        },
        achievement_standard: {
          grade: '3',
          subject: '수학',
          standard_text: '덧셈과 뺄셈의 의미를 이해하고 다양한 방법으로 계산할 수 있다.',
          relevance_score: 0.68,
        },
        additional_notes: '전문가 상담 권고 등 추가 메모가 있으면 기록에 남깁니다.',
      },
      created_at: '2026-04-23T10:10:00',
    },
  ],
  progress_summary: '',
}

const FIXED_TOMORROW_PREP = ['체육복', '색연필', '국어 공책']

const sampleSchoolLife = {
  lunch_menu: '참치야채비빔밥, 북어국, 갈릭미트볼야채볶음, 고구마맛탕, 백김치, 우유컵케익',
  dismissal_time: '16:15',
  academic_calendar: '일정 없음',
  today_timetable: ['종교와 삶Ⅰ', '수학', '음악', '기술·가정', '사회', '과학', '(창)자율·자치활동'],
  tomorrow_prep: FIXED_TOMORROW_PREP,
}

const sampleScaffolding = normalizeScaffoldingApiResponse({
  recommended_level: '하',
  rationale:
    "학생의 현재 능력 수준을 '하'로 평가. 주요 학습 격차: 실생활 문제 연산 도출, 세로셈 자릿값 계산 등. 신뢰도: 0.72",
  scaffolding_details: {
    level: '하',
    description:
      '문제 해결을 돕는 삽화나 도식을 활용하여 이해 지원; 식 도출을 중점으로 지도하며 계산 방법은 학생의 자율성 존중',
    activities: [
      {
        name: '교육과정 활동 1',
        description: '거스름돈 계산이나 물건 수 합산 문제를 짧은 단계로 나누어 반복 연습',
      },
      {
        name: '교육과정 활동 2',
        description: '실생활 상황을 보고 연산 식을 도출하기를 짧은 단계로 나누어 반복 연습',
      },
      {
        name: '교육과정 활동 3',
        description: '구체물로 상황을 재현하고 전체/남은 수를 구하기를 짧은 단계로 나누어 반복 연습',
      },
    ],
    strategies: [
      '세로셈 지도 시 자릿값 위치를 시각적으로 가이드 함',
      '구체물 10개 묶음을 더하거나 빼며 전체 개수 확인',
      '문제 해결을 돕는 삽화나 도식을 활용하여 이해 지원',
      '식 도출을 중점으로 지도하며 계산 방법은 학생의 자율성 존중',
    ],
  },
  achievement_standard: {
    standard_id: '6수학01-08',
    standard_text: '받아올림(내림)이 없는 몇십의 덧셈, 뺄셈과 관련된 실생활 문제를 해결한다.',
    grade: '6',
    subject: 'math',
    disability_type: '중도중복장애',
    relevance_score: 0.5676,
  },
  related_achievement_standards: [
    '[6수학01-08] 받아올림(내림)이 없는 몇십의 덧셈, 뺄셈과 관련된 실생활 문제를 해결한다. (관련도 0.57)',
    '[6수학01-07] 받아올림(내림)이 없는 몇십의 덧셈과 뺄셈을 한다. (관련도 0.56)',
    '[4수학01-03] 9 이하의 수를 읽고 쓴다. (관련도 0.52)',
  ],
})

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

const sampleCareerRecommendation = normalizeCareerRecommendationPayload({
  current_skills: '손작업과 순서 기억이 안정적이며 시각 자료를 활용한 활동에 오래 참여합니다.',
  recommended_careers: [
    { job_title: '캐릭터디자이너', category: '예술분야(전문직)', match_score: 0.508 },
    { job_title: '화가', category: '예술분야(전문직)', match_score: 0.475 },
    { job_title: '일러스트레이터', category: '예술분야(전문직)', match_score: 0.472 },
  ],
  skill_gaps: [
    {
      job_title: '캐릭터디자이너',
      gap_skills: ['손재능', '공간시각능력', '창의력', '기발한 발상', '컴퓨터 그래픽 지식'],
      development_suggestions: [
        '핵심 역량을 10~15분 단위 반복 과제로 나눠 연습',
        '체크리스트 기반으로 과제 시작-중간-완료 단계를 시각화',
        '주 1회 동일 과업 재수행으로 수행 정확도를 기록',
      ],
    },
    {
      job_title: '화가',
      gap_skills: ['미적 감각', '색채 구성', '창의력'],
      development_suggestions: ['짧은 스케치 루틴으로 관찰·표현 연습', '완성보다 과정 기록에 칭찬 집중'],
    },
  ],
  career_paths: [
    {
      target_career: '캐릭터디자이너',
      estimated_timeline: '6~12개월',
      stages: [
        { stage: '현재', focus: '현재 강점 파악', description: '직무 요구 역량과 현재 역량 비교' },
        { stage: '단기(1~3개월)', focus: '핵심 기초 역량 강화', description: '손재능·공간시각능력·창의력 중심 반복 과제' },
        { stage: '중기(3~6개월)', focus: '실습 기반 적용', description: '체크리스트 기반 모의/현장 실습' },
        { stage: '장기(6개월+)', focus: '직무 전환 및 유지', description: '실제 업무 환경 역할 확장 + 피드백 루프' },
      ],
    },
  ],
})

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
  return withFallback(async () => {
    const data = (await apiClient.get('/student/progress')).data
    return normalizeProgressPayload(data)
  }, normalizeProgressPayload(sampleProgress))
}

export function getSchoolLife() {
  return withFallback(async () => {
    const data = (await apiClient.get('/student/school-life')).data
    return { ...(data && typeof data === 'object' ? data : {}), tomorrow_prep: FIXED_TOMORROW_PREP }
  }, { ...sampleSchoolLife, tomorrow_prep: FIXED_TOMORROW_PREP })
}

export function getScaffoldingRecommendation(payload) {
  return withFallback(async () => {
    const data = (await apiClient.post('/rag/scaffolding-recommendation', payload)).data
    return normalizeScaffoldingApiResponse(data)
  }, sampleScaffolding)
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
  return withFallback(async () => {
    const data = (await apiClient.post('/rag/career-recommendation', payload)).data
    return normalizeCareerRecommendationPayload(data)
  }, {
    ...sampleCareerRecommendation,
    current_skills: payload?.current_skills || sampleCareerRecommendation.current_skills,
  })
}
