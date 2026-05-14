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
        <p class="eyebrow">Stored in Database</p>
        <h2 class="panel-title">기록 출처</h2>
        <p class="panel-subtitle">
          스캐폴딩 추천을 실행하면 데이터 베이스에 관찰 기록 및 추천 활동이 저장됩니다. 이 내역들은 추후 스캐폴딩 제공에 반영됩니다.
        </p>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Feedback Timeline</p>
            <h2 class="panel-title">피드백 기록</h2>
            <p class="panel-subtitle">최근 기록을 선택하면 오른쪽에서 추천 원문을 확인합니다.</p>
          </div>
          <button class="btn ghost" type="button" :disabled="loading" @click="loadProgress">새로고침</button>
        </div>

        <div v-if="feedbacks.length" class="list-stack spaced">
          <button
            v-for="(feedback, index) in orderedFeedbacks"
            :key="feedback.id || index"
            type="button"
            :class="['timeline-row', selectedId === feedback.id && 'is-selected']"
            @click="selectedId = feedback.id"
          >
            <small>{{ formatDate(feedback.created_at) }}</small>
            <strong>{{ feedback.teacher_description || feedback.performance || '기록 내용 없음' }}</strong>
            <span class="badge soft">{{ levelLabel(feedback.llm_analysis?.detected_level) }}</span>
            <span class="mono">{{ feedback.id ? `#${feedback.id}` : '-' }}</span>
          </button>
        </div>

        <div v-else class="empty-state spaced">
          <strong>아직 저장된 피드백이 없습니다.</strong>
          <p>추천 화면에서 AI 추천을 실행하면 이곳에 기록이 쌓입니다.</p>
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
import { computed, onMounted, ref } from 'vue'
import { ClipboardList, TrendingUp } from 'lucide-vue-next'
import { getStudentProgress } from '../../api'

const loading = ref(false)
const feedbacks = ref([])
const progressSummary = ref('최근 피드백을 불러오는 중입니다.')
const selectedId = ref(null)

const orderedFeedbacks = computed(() => [...feedbacks.value].reverse())
const selectedFeedback = computed(() => feedbacks.value.find((feedback) => feedback.id === selectedId.value) || orderedFeedbacks.value[0] || null)
const latestLevel = computed(() => selectedFeedback.value?.llm_analysis?.detected_level || 'medium')

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

function levelLabel(level) {
  const map = { high: '높음', medium: '중간', low: '낮음', 상: '높음', 중: '중간', 하: '낮음' }
  return map[level] || level || '대기'
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
    const progress = await getStudentProgress()
    feedbacks.value = progress.feedbacks || []
    progressSummary.value = progress.progress_summary || '아직 피드백 데이터가 없습니다.'
    selectedId.value = orderedFeedbacks.value[0]?.id || null
  } finally {
    loading.value = false
  }
}

onMounted(loadProgress)
</script>
