import { computed, reactive, readonly } from 'vue'
import { getCurriculumSubjects } from '../api'

const state = reactive({
  subjects: [],
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
    state.subjects = Array.isArray(subjects) ? subjects : []
    state.loaded = true
    return state.subjects
  } catch (error) {
    state.error = '과목 목록을 불러오지 못했습니다.'
    state.subjects = []
    console.error(error)
    return state.subjects
  } finally {
    state.loading = false
  }
}

export function useCurriculumSubjects() {
  const subjectOptions = computed(() => state.subjects)

  return {
    state: readonly(state),
    subjectOptions,
    loadCurriculumSubjects,
  }
}
