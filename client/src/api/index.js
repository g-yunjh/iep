import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 180000,
})

const DEFAULT_CURRICULUM_SUBJECTS = [
  { slug: 'math', label: '수학' },
  { slug: 'korean', label: '국어' },
]

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
  if (Array.isArray(next.teaching_points)) {
    next.teaching_points = next.teaching_points.map((s) => (typeof s === 'string' ? cleanDisplayText(s) : s))
  }
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
    if (Array.isArray(next.llm_analysis.teaching_points)) {
      next.llm_analysis.teaching_points = next.llm_analysis.teaching_points.map((s) =>
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
  if (Array.isArray(next.teaching_points)) {
    next.teaching_points = next.teaching_points.map((s) => (typeof s === 'string' ? cleanDisplayText(s) : s))
  }
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

const emptyStudent = null
const emptyProgress = { feedbacks: [], progress_summary: '' }
const emptySchoolLife = {
  lunch_menu: '참치야채비빔밥 , 북어국 , 갈릭미트볼야채볶음 , 고구마맛탕 , 백김치 , 우유컵케익',
  dismissal_time: '16:15',
  academic_calendar: '6월 3일 통합체육 활동 · 6월 5일 현장체험학습 안내장 제출',
  today_timetable: ['종교와 삶Ⅰ', '수학', '음악', '기술·가정', '사회', '과학', '(창)자율·자치활동'],
  tomorrow_prep: ['수학 수 모형 카드', '색연필 12색', '체육복', '알림장 확인', '도움 요청 문장 함께 연습'],
}
const emptyScaffolding = null
const emptyCurriculumResults = { query: '', count: 0, results: [] }
const emptyCareerSearch = { query: '', count: 0, results: [] }
const emptyCareerRecommendation = {
  current_skills: '',
  recommended_careers: [],
  skill_gaps: [],
  career_paths: [],
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

function normalizeCurriculumSubjectOptions(payload) {
  const rawSubjects = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.subjects)
      ? payload.subjects
      : []

  const subjects = rawSubjects
    .map((item) => {
      if (typeof item === 'string') {
        const value = item.trim()
        return value ? { slug: value, label: value } : null
      }
      if (!item || typeof item !== 'object') return null
      const slug = String(item.slug || item.subject || item.code || '').trim()
      const label = String(item.label || item.name || slug).trim()
      if (!slug || !label) return null
      return { ...item, slug, label }
    })
    .filter(Boolean)

  if (!subjects.length) {
    return []
  }

  const deduped = []
  const seen = new Set()
  subjects.forEach((subject) => {
    const key = `${subject.slug}::${subject.label}`
    if (seen.has(key)) return
    seen.add(key)
    deduped.push(subject)
  })
  return deduped
}

function toGradeCode(grade) {
  if (!grade) return grade
  const match = String(grade).match(/[1-6]/)
  return match ? match[0] : grade
}

export function getStudent() {
  return withFallback(async () => (await apiClient.get('/student/')).data, emptyStudent)
}

export function patchStudentTraits(payload) {
  return withFallback(async () => (await apiClient.patch('/student/', payload)).data, payload)
}

export function getStudentProgress() {
  return withFallback(async () => {
    const data = (await apiClient.get('/student/progress')).data
    return normalizeProgressPayload(data)
  }, emptyProgress)
}

export async function deleteStudentFeedbacks({ feedback_ids = [], delete_all = false } = {}) {
  const data = (await apiClient.delete('/student/feedbacks', {
    data: { feedback_ids, delete_all },
  })).data
  return data
}

export function getSchoolLife() {
  return withFallback(async () => {
    const data = (await apiClient.get('/student/school-life')).data
    return data && typeof data === 'object' ? data : {}
  }, emptySchoolLife)
}

export function getScaffoldingRecommendation(payload) {
  return withFallback(async () => {
    const data = (await apiClient.post('/rag/scaffolding-recommendation', payload)).data
    return normalizeScaffoldingApiResponse(data)
  }, emptyScaffolding)
}

export function getCurriculumSubjects() {
  return withFallback(
    async () => normalizeCurriculumSubjectOptions((await apiClient.get('/rag/curriculum-subjects')).data),
    DEFAULT_CURRICULUM_SUBJECTS.map((subject) => ({ ...subject })),
  )
}

export function searchCurriculum(query, params = {}) {
  const normalizedParams = {
    ...params,
    subject: params.subject ? toCurriculumSubjectCode(params.subject) : params.subject,
    grade: params.grade ? toGradeCode(params.grade) : params.grade,
  }
  return withFallback(
    async () => (await apiClient.get('/rag/curriculum-search', { params: { query, ...normalizedParams } })).data,
    { ...emptyCurriculumResults, query },
  )
}

export function searchCareer(query, params = {}) {
  return withFallback(
    async () => (await apiClient.get('/rag/career-search', { params: { query, ...params } })).data,
    { ...emptyCareerSearch, query },
  )
}

export function getCareerRecommendation(payload) {
  return withFallback(async () => {
    const data = (await apiClient.post('/rag/career-recommendation', payload)).data
    return normalizeCareerRecommendationPayload(data)
  }, { ...emptyCareerRecommendation, current_skills: payload?.current_skills || '' })
}
