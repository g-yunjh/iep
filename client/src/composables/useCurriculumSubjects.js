import { computed, reactive, readonly } from 'vue'
import { getCurriculumSubjects } from '../api'

const FALLBACK_SUBJECTS = [
  { slug: 'math', label: '수학' },
  { slug: 'korean', label: '국어' },
]

const state = reactive({
  subjects: FALLBACK_SUBJECTS.map((subject) => ({ ...subject })),
  loading: false,
  loaded: false,
  error: '',
})

async function loadCurriculumSubjects(force = false) {
  if (state.loaded && !force) return state.subjects

  state.loading = true
  state.error = ''
  try {
    const subjects = await getCurriculumSubjects()
    state.subjects = Array.isArray(subjects) && subjects.length
      ? subjects
      : FALLBACK_SUBJECTS.map((subject) => ({ ...subject }))
    state.loaded = true
    return state.subjects
  } catch (error) {
    state.error = '과목 목록을 불러오지 못했습니다.'
    state.subjects = FALLBACK_SUBJECTS.map((subject) => ({ ...subject }))
    console.error(error)
    return state.subjects
  } finally {
    state.loading = false
  }
}

export function useCurriculumSubjects() {
  const subjectOptions = computed(() =>
    state.subjects.length ? state.subjects : FALLBACK_SUBJECTS,
  )

  return {
    state: readonly(state),
    subjectOptions,
    loadCurriculumSubjects,
  }
}
