import { reactive, readonly } from 'vue'
import { getStudent, patchStudentTraits } from '../api'

const state = reactive({
  student: null,
  loading: false,
  error: '',
})

async function loadStudent() {
  state.loading = true
  state.error = ''
  try {
    state.student = await getStudent()
  } catch (error) {
    state.error = '학생 정보를 불러오지 못했습니다.'
    console.error(error)
  } finally {
    state.loading = false
  }
}

async function updateTraits(payload) {
  state.loading = true
  state.error = ''
  try {
    const updated = await patchStudentTraits(payload)
    state.student = { ...state.student, ...updated }
    return updated
  } catch (error) {
    state.error = '학생 특성 저장에 실패했습니다.'
    console.error(error)
    throw error
  } finally {
    state.loading = false
  }
}

export function useStudentStore() {
  return {
    state: readonly(state),
    loadStudent,
    updateTraits,
  }
}
