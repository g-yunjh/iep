<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">기준 찾기</p>
            <h2 class="panel-title">성취기준 검색</h2>
            <p class="panel-subtitle">관찰 문장이나 수업 키워드를 입력해 오늘 수업과 가까운 기준을 찾습니다.</p>
          </div>
          <div class="panel-icon">
            <SlidersHorizontal />
          </div>
        </div>

        <div v-if="loading" class="status-banner spaced-sm">
          <strong>관련 성취기준을 찾는 중입니다.</strong>
          <p>입력한 키워드와 선택 과목을 바탕으로 가까운 기준을 다시 정리하고 있습니다.</p>
        </div>

        <label class="spaced">
          <span class="section-label">검색어</span>
          <textarea v-model="filters.query" class="textarea-like spaced-sm" rows="4" />
        </label>

        <div class="mini-grid spaced-sm">
          <label>
            <span class="section-label">과목</span>
            <select v-model="filters.subject" class="input-like spaced-sm">
              <option value="">전체</option>
              <option v-for="subject in subjectOptions" :key="subject.slug" :value="subject.label">
                {{ subject.label }}
              </option>
            </select>
          </label>
          <label>
            <span class="section-label">학년</span>
            <input v-model="filters.grade" class="input-like spaced-sm" type="text" />
          </label>
        </div>

        <label class="spaced-sm">
          <span class="section-label">장애 유형</span>
          <input v-model="filters.disability_type" class="input-like spaced-sm" type="text" />
        </label>

        <button class="btn spaced" type="button" :disabled="loading" @click="runSearch">
          {{ loading ? '검색 중' : '기준 검색' }}
        </button>
      </section>

      <section class="panel dark">
        <p class="eyebrow">수업 연결</p>
        <h2 class="panel-title">기준을 목표로 좁히기</h2>
        <p class="panel-subtitle">
          찾은 기준을 그대로 쓰기보다 학생이 오늘 보일 수 있는 행동으로 작게 나누어 활용합니다.
        </p>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">찾은 성취기준</p>
            <h2 class="panel-title">검색 결과 {{ results.length }}개</h2>
            <p class="panel-subtitle">가장 가까운 기준을 선택해 수업 목표와 관찰 포인트를 정리합니다.</p>
          </div>
        </div>

        <div v-if="results.length" class="list-stack spaced">
          <button
            v-for="(item, index) in results"
            :key="`${item.content}-${index}`"
            type="button"
            :class="['standard-result', selectedIndex === index && 'is-selected']"
            @click="selectedIndex = index"
          >
            <code>{{ standardCode(item, index) }}</code>
            <div>
              <strong>{{ standardText(item) }}</strong>
              <p>{{ subjectLabel(item.metadata?.subject) }} · {{ item.metadata?.grade || '학년 정보 없음' }}</p>
            </div>
            <span class="mono">{{ scoreText(item.score) }}</span>
          </button>
        </div>

        <div v-else class="empty-state spaced">
          <strong>검색 결과가 없습니다.</strong>
          <p>학생 관찰 문장이나 과목 키워드를 바꿔 다시 검색해보세요.</p>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">기준 상세</p>
            <h2 class="panel-title">선택한 기준</h2>
          </div>
          <div class="panel-icon">
            <BookOpenCheck />
          </div>
        </div>

        <template v-if="selectedResult">
          <div class="selected-standard-card spaced">
            <div class="selected-standard-meta">
              <span>{{ standardCode(selectedResult, selectedIndex) }}</span>
              <span>{{ subjectLabel(selectedResult.metadata?.subject) }}</span>
              <span>{{ selectedResult.metadata?.grade || '학년 정보 없음' }}</span>
            </div>
            <h3>성취기준</h3>
            <p>{{ standardText(selectedResult) }}</p>
          </div>

          <div v-if="selectedFocusItems.length" class="selected-standard-card spaced-sm">
            <h3>수업에서 확인할 행동</h3>
            <ul class="clean-dot-list">
              <li v-for="item in selectedFocusItems" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div class="mini-grid spaced">
            <div class="metric-card">
              <p>관련도</p>
              <strong>{{ scoreText(selectedResult.score) }}</strong>
              <small>검색 기준</small>
            </div>
            <div class="metric-card">
              <p>과목</p>
              <strong>{{ subjectLabel(selectedResult.metadata?.subject) }}</strong>
              <small>{{ selectedResult.metadata?.grade || '-' }}</small>
            </div>
          </div>
        </template>

        <div v-else class="empty-state spaced">
          <strong>선택 기준 없음</strong>
          <p>검색 결과를 선택하면 기준 원문과 수업에서 볼 행동이 정리됩니다.</p>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">수업 메모</p>
        <h2 class="panel-title">수업 적용 메모</h2>
        <div class="list-stack spaced">
          <div v-for="memo in lessonMemos" :key="memo" class="mini-card">
            <strong>활용 방법</strong>
            <p>{{ memo }}</p>
          </div>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpenCheck, SlidersHorizontal } from 'lucide-vue-next'
import { searchCurriculum } from '../../api'
import { useCurriculumSubjects } from '../../composables/useCurriculumSubjects'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()
const { subjectOptions, loadCurriculumSubjects } = useCurriculumSubjects()
const route = useRoute()

const loading = ref(false)
const results = ref([])
const selectedIndex = ref(0)
const filters = reactive({
  query: '',
  subject: '',
  grade: '',
  disability_type: '',
})

const subjectLabelMap = computed(() => {
  const entries = {}
  subjectOptions.value.forEach((subject) => {
    entries[subject.slug] = subject.label
    entries[subject.label] = subject.label
  })
  return entries
})

const selectedResult = computed(() => results.value[selectedIndex.value] || null)
const routeSearchQuery = computed(() => (typeof route.query.q === 'string' ? route.query.q.trim() : ''))

const lessonMemos = [
  '학생이 오늘 보일 수 있는 행동 하나를 골라 수업 목표로 사용합니다.',
  '기준이 넓게 느껴지면 활동이나 관찰 포인트를 하나만 선택해 기록합니다.',
  '추천 결과와 맞지 않으면 다른 기준을 선택하거나 검색어를 더 구체적으로 바꿉니다.',
]

const selectedFocusItems = computed(() => {
  const content = selectedResult.value?.content || ''
  return [
    ...extractSectionItems(content, '학습 목표'),
    ...extractSectionItems(content, '활동'),
  ].slice(0, 4)
})

function standardText(item) {
  const content = String(item?.content || '')
  const match = content.match(/성취기준\s*:\s*(.+)/)
  return (match?.[1] || content).trim()
}

function standardCode(item, index) {
  return item?.metadata?.standard_id || item?.metadata?.achievement_standard_id || item?.metadata?.id || `STD ${String(index + 1).padStart(2, '0')}`
}

function subjectLabel(subject) {
  return subjectLabelMap.value[subject] || subject || '과목 정보 없음'
}

function subjectInputValue(subject) {
  if (!subject) return ''
  const matched = subjectOptions.value.find((item) => item.label === subject || item.slug === subject)
  return matched?.label || subject
}

function scoreText(score) {
  if (typeof score !== 'number') return '-'
  return score.toFixed(2)
}

function applySearchInputEcho(response) {
  const sampleInput = response?.sample_input || {}
  if (!filters.query && response?.query) filters.query = response.query
  if (!filters.subject && sampleInput.subject) filters.subject = subjectInputValue(sampleInput.subject)
  if (!filters.grade && sampleInput.grade) filters.grade = sampleInput.grade
  if (!filters.disability_type && sampleInput.disability_type) {
    filters.disability_type = sampleInput.disability_type
  }
}

function extractSectionItems(content, sectionTitle) {
  const lines = String(content || '').split('\n')
  const items = []
  let inSection = false

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) continue
    if (line.startsWith(`${sectionTitle}:`)) {
      inSection = true
      continue
    }
    if (inSection && /^[가-힣A-Za-z ]+:$/.test(line) && !line.startsWith('-')) break
    if (inSection && line.startsWith('-')) {
      items.push(line.replace(/^-\s*/, '').trim())
    }
  }

  return items
}

async function runSearch() {
  loading.value = true
  try {
    const response = await searchCurriculum(filters.query, {
      subject: filters.subject || undefined,
      grade: filters.grade || undefined,
      disability_type: filters.disability_type || studentStore.student?.disability_type || undefined,
      k: 6,
    })
    applySearchInputEcho(response)
    results.value = response.results || []
    selectedIndex.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadCurriculumSubjects()
  if (filters.subject) {
    const isValid = subjectOptions.value.some(
      (subject) => subject.label === filters.subject || subject.slug === filters.subject,
    )
    if (!isValid) filters.subject = ''
  }
  if (routeSearchQuery.value) filters.query = routeSearchQuery.value
  filters.disability_type = studentStore.student?.disability_type || ''
  await runSearch()
})

watch(routeSearchQuery, async (query) => {
  if (!query || query === filters.query) return
  filters.query = query
  await runSearch()
})
</script>
