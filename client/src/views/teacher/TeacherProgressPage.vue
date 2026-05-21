<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Progress Summary</p>
            <h2 class="panel-title">성장 흐름</h2>
            <p class="panel-subtitle">{{ progressSummary }}</p>
          </div>
          <div class="panel-icon">
            <TrendingUp />
          </div>
        </div>

        <div class="mini-grid spaced">
          <div v-for="metric in metrics" :key="metric.label" class="metric-card">
            <p>{{ metric.label }}</p>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.caption }}</small>
          </div>
        </div>
      </section>

      <section class="panel dark">
        <p class="eyebrow">Learning Memory</p>
        <h2 class="panel-title">누적 관찰 메모</h2>
        <p class="panel-subtitle">
          저장된 피드백은 다음 추천을 만들 때 학생의 반응 패턴과 지원 이력으로 함께 반영됩니다.
        </p>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Feedback Timeline</p>
            <h2 class="panel-title">피드백 기록</h2>
            <p class="panel-subtitle">
              {{ searchQuery ? `'${searchQuery}' 검색 결과 ${filteredFeedbacks.length}개` : '최근 기록을 선택하면 오른쪽에서 추천 원문을 확인합니다.' }}
            </p>
          </div>
          <div class="feedback-action-row">
            <button class="btn ghost" type="button" :disabled="loading || deleting" @click="loadProgress">새로고침</button>
            <button
              :class="['btn ghost', deleteMode && 'danger']"
              type="button"
              :disabled="!feedbacks.length || deleting"
              @click="toggleDeleteMode"
            >
              {{ deleteMode ? '취소' : '기록 지우기' }}
            </button>
          </div>
        </div>

        <div v-if="deleteMode && filteredFeedbacks.length" class="feedback-delete-panel spaced">
          <div class="feedback-delete-copy">
            <p class="eyebrow">Delete Feedback</p>
            <h3>삭제할 기록 선택</h3>
            <p :title="deleteModeSummary">{{ deleteModeSummary }}</p>
          </div>
          <div class="feedback-delete-actions">
            <label class="feedback-select-all">
              <input
                type="checkbox"
                :checked="areVisibleFeedbacksSelected"
                :disabled="deleting"
                @change="toggleVisibleFeedbacks($event.target.checked)"
              >
              <span>현재 목록 선택</span>
            </label>
            <button
              class="btn ghost"
              type="button"
              :disabled="!selectedFeedbackIds.length || deleting"
              @click="deleteSelectedFeedbacks"
            >
              선택 삭제
            </button>
            <button
              class="btn ghost danger"
              type="button"
              :disabled="!feedbacks.length || deleting"
              @click="deleteAllFeedbacks"
            >
              전체 지우기
            </button>
          </div>
        </div>

        <p v-if="deleteNotice" class="feedback-notice">{{ deleteNotice }}</p>

        <template v-if="visibleFeedbacks.length">
          <div class="list-stack spaced">
            <article
              v-for="(feedback, index) in visibleFeedbacks"
              :key="feedback.id || index"
              :class="[
                'timeline-row',
                'feedback-select-row',
                deleteMode && 'is-delete-mode',
                deleteMode && selectedFeedbackIds.includes(feedback.id) && 'is-marked-delete',
                selectedId === feedback.id && 'is-selected',
              ]"
            >
              <label v-if="deleteMode" class="feedback-row-check" @click.stop>
                <input
                  type="checkbox"
                  :checked="selectedFeedbackIds.includes(feedback.id)"
                  :disabled="!feedback.id || deleting"
                  @change="toggleFeedbackSelection(feedback.id, $event.target.checked)"
                >
              </label>
              <button
                type="button"
                class="feedback-row-content"
                @click="handleFeedbackRowClick(feedback)"
              >
                <small>{{ formatDate(feedback.created_at) }}</small>
                <strong>{{ feedback.teacher_description || feedback.performance || '기록 내용 없음' }}</strong>
                <span class="badge soft">{{ levelLabel(feedback.llm_analysis?.detected_level) }}</span>
                <span class="mono">{{ feedback.id ? `#${feedback.id}` : '-' }}</span>
              </button>
            </article>
          </div>

          <div v-if="hiddenFeedbackCount" class="feedback-more-row">
            <button class="btn ghost" type="button" @click="showAllFeedbacks = !showAllFeedbacks">
              {{ showAllFeedbacks ? '접기' : `${hiddenFeedbackCount}개 더보기` }}
            </button>
          </div>
        </template>

        <div v-else class="empty-state spaced">
          <strong>{{ searchQuery ? '검색 결과가 없습니다.' : '아직 저장된 피드백이 없습니다.' }}</strong>
          <p>{{ searchQuery ? '다른 날짜, 수준, 피드백 문장으로 다시 검색해보세요.' : '추천 화면에서 AI 추천을 실행하면 이곳에 기록이 쌓입니다.' }}</p>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Selected Feedback</p>
            <h2 class="panel-title">기록 상세</h2>
          </div>
          <div class="panel-icon">
            <ClipboardList />
          </div>
        </div>

        <template v-if="selectedFeedback">
          <div class="callout spaced">
            <strong>{{ levelLabel(selectedFeedback.llm_analysis?.detected_level) }} 수준 분석</strong>
            <p>{{ selectedFeedback.teacher_description || selectedFeedback.performance }}</p>
          </div>

          <div class="list-stack spaced">
            <div v-for="item in feedbackDetails" :key="item.label" class="card-row">
              <strong>{{ item.label }}</strong>
              <span>{{ item.value }}</span>
            </div>
          </div>
        </template>

        <div v-else class="empty-state spaced">
          <strong>선택된 기록 없음</strong>
          <p>왼쪽 타임라인에서 기록을 선택하세요.</p>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Recommendation Snapshot</p>
        <h2 class="panel-title">저장된 추천</h2>
        <div v-if="recommendationText" class="mini-card spaced">
          <strong>스캐폴딩 요약</strong>
          <p>{{ recommendationText }}</p>
        </div>
        <div v-else class="empty-state spaced">
          <strong>추천 원문 없음</strong>
          <p>예전 기록이거나 추천 저장 전 기록일 수 있습니다.</p>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ClipboardList, TrendingUp } from 'lucide-vue-next'
import { deleteStudentFeedbacks, getStudentProgress, mapLevelToKorean } from '../../api'

const FEEDBACK_PREVIEW_LIMIT = 7
const loading = ref(false)
const deleting = ref(false)
const deleteMode = ref(false)
const deleteNotice = ref('')
const feedbacks = ref([])
const selectedId = ref(null)
const selectedFeedbackIds = ref([])
const showAllFeedbacks = ref(false)
const route = useRoute()

const orderedFeedbacks = computed(() => [...feedbacks.value].reverse())
const searchQuery = computed(() => (typeof route.query.q === 'string' ? route.query.q.trim() : ''))
const filteredFeedbacks = computed(() => {
  const q = searchQuery.value.toLowerCase()
  if (!q) return orderedFeedbacks.value
  return orderedFeedbacks.value.filter((feedback) => feedbackMatches(feedback, q))
})
const hiddenFeedbackCount = computed(() => Math.max(filteredFeedbacks.value.length - FEEDBACK_PREVIEW_LIMIT, 0))
const visibleFeedbacks = computed(() =>
  showAllFeedbacks.value ? filteredFeedbacks.value : filteredFeedbacks.value.slice(0, FEEDBACK_PREVIEW_LIMIT),
)
const visibleFeedbackIds = computed(() => visibleFeedbacks.value.map((feedback) => feedback.id).filter(Boolean))
const areVisibleFeedbacksSelected = computed(() =>
  visibleFeedbackIds.value.length > 0 &&
  visibleFeedbackIds.value.every((id) => selectedFeedbackIds.value.includes(id)),
)
const selectionSummary = computed(() => {
  if (selectedFeedbackIds.value.length) return `${selectedFeedbackIds.value.length}개 선택됨`
  if (hiddenFeedbackCount.value && !showAllFeedbacks.value) {
    return `최근 ${FEEDBACK_PREVIEW_LIMIT}개 표시 · ${hiddenFeedbackCount.value}개 숨김`
  }
  return `총 ${filteredFeedbacks.value.length}개 기록`
})
const deleteModeSummary = computed(() => {
  if (selectedFeedbackIds.value.length) return `${selectedFeedbackIds.value.length}개 선택됨`
  if (hiddenFeedbackCount.value && !showAllFeedbacks.value) {
    return `최근 ${FEEDBACK_PREVIEW_LIMIT}개 표시 · 더보기로 추가 선택`
  }
  return '선택 삭제 또는 전체 지우기'
})
const selectedFeedback = computed(() =>
  feedbacks.value.find((feedback) => feedback.id === selectedId.value) ||
  visibleFeedbacks.value[0] ||
  orderedFeedbacks.value[0] ||
  null,
)
const latestLevel = computed(() => selectedFeedback.value?.llm_analysis?.detected_level || '중')
const progressSummary = computed(() => {
  const count = feedbacks.value.length
  return count > 0 ? `총 ${count}개의 피드백 기록이 있습니다.` : '아직 누적된 피드백 기록이 없습니다.'
})

const metrics = computed(() => [
  { label: '총 기록', value: feedbacks.value.length, caption: 'Feedback rows' },
  { label: '최근 수준', value: levelLabel(latestLevel.value), caption: 'LLM analysis' },
])

const feedbackDetails = computed(() => {
  const feedback = selectedFeedback.value
  if (!feedback) return []
  return [
    { label: '수행 기록', value: feedback.performance || '수행도 기록 없음' },
    { label: '효과', value: feedback.scaffolding_effectiveness || '적용 전' },
    { label: '장애 유형', value: feedback.disability_type || '정보 없음' },
    { label: '생성일', value: formatDateTime(feedback.created_at) },
  ]
})

const recommendationText = computed(() => {
  const rec = selectedFeedback.value?.scaffolding_recommendations
  if (!rec) return ''
  if (typeof rec === 'string') return rec
  return rec.rationale || rec.additional_notes || rec.scaffolding_details?.description || ''
})

function feedbackMatches(feedback, query) {
  const fields = [
    feedback.teacher_description,
    feedback.performance,
    feedback.scaffolding_effectiveness,
    feedback.disability_type,
    feedback.llm_analysis?.detected_level,
    feedback.llm_analysis?.analysis_summary,
    ...(feedback.llm_analysis?.learning_gaps || []),
    feedback.scaffolding_recommendations?.rationale,
    feedback.created_at,
  ]
  return fields.some((field) => String(field || '').toLowerCase().includes(query))
}

function toggleFeedbackSelection(feedbackId, checked) {
  if (!feedbackId) return
  const next = new Set(selectedFeedbackIds.value)
  if (checked) next.add(feedbackId)
  else next.delete(feedbackId)
  selectedFeedbackIds.value = [...next]
}

function toggleVisibleFeedbacks(checked) {
  const next = new Set(selectedFeedbackIds.value)
  visibleFeedbackIds.value.forEach((id) => {
    if (checked) next.add(id)
    else next.delete(id)
  })
  selectedFeedbackIds.value = [...next]
}

function handleFeedbackRowClick(feedback) {
  if (deleteMode.value) {
    toggleFeedbackSelection(feedback.id, !selectedFeedbackIds.value.includes(feedback.id))
    return
  }
  selectedId.value = feedback.id
}

function toggleDeleteMode() {
  deleteMode.value = !deleteMode.value
  deleteNotice.value = ''
  if (!deleteMode.value) selectedFeedbackIds.value = []
}

function levelLabel(level) {
  const mapped = mapLevelToKorean(level)
  return mapped != null && mapped !== '' ? mapped : '대기'
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadProgress() {
  loading.value = true
  try {
    const previousSelectedId = selectedId.value
    const progress = await getStudentProgress()
    feedbacks.value = progress.feedbacks || []
    const validIds = new Set(feedbacks.value.map((feedback) => feedback.id).filter(Boolean))
    selectedFeedbackIds.value = selectedFeedbackIds.value.filter((id) => validIds.has(id))
    selectedId.value = validIds.has(previousSelectedId)
      ? previousSelectedId
      : visibleFeedbacks.value[0]?.id || orderedFeedbacks.value[0]?.id || null
  } finally {
    loading.value = false
  }
}

async function deleteSelectedFeedbacks() {
  const ids = selectedFeedbackIds.value
  if (!ids.length || deleting.value) return
  if (!window.confirm(`${ids.length}개의 피드백 기록을 삭제할까요?`)) return

  deleting.value = true
  deleteNotice.value = ''
  try {
    const result = await deleteStudentFeedbacks({ feedback_ids: ids })
    selectedFeedbackIds.value = []
    deleteMode.value = false
    deleteNotice.value = `${result.deleted_count}개의 기록을 삭제했습니다.`
    await loadProgress()
  } catch (error) {
    deleteNotice.value = '삭제 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.'
  } finally {
    deleting.value = false
  }
}

async function deleteAllFeedbacks() {
  if (!feedbacks.value.length || deleting.value) return
  if (!window.confirm('모든 피드백 기록을 삭제할까요? 이 작업은 되돌릴 수 없습니다.')) return

  deleting.value = true
  deleteNotice.value = ''
  try {
    const result = await deleteStudentFeedbacks({ delete_all: true })
    selectedFeedbackIds.value = []
    deleteMode.value = false
    showAllFeedbacks.value = false
    deleteNotice.value = `${result.deleted_count}개의 기록을 모두 삭제했습니다.`
    await loadProgress()
  } catch (error) {
    deleteNotice.value = '전체 삭제 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.'
  } finally {
    deleting.value = false
  }
}

watch(searchQuery, () => {
  showAllFeedbacks.value = false
  selectedFeedbackIds.value = []
  deleteMode.value = false
  selectedId.value = visibleFeedbacks.value[0]?.id || orderedFeedbacks.value[0]?.id || null
})

onMounted(loadProgress)
</script>
