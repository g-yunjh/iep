<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Search Filters</p>
            <h2 class="panel-title">성취기준 검색</h2>
            <p class="panel-subtitle">수학과 국어 기준을 같은 형식으로 검색합니다.</p>
          </div>
          <div class="panel-icon">
            <SlidersHorizontal />
          </div>
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
              <option>수학</option>
              <option>국어</option>
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
        <p class="eyebrow">What Matters</p>
        <h2 class="panel-title">교사용 화면에 남긴 기능</h2>
        <p class="panel-subtitle">
          기준 원문, 과목/학년, 관련도, 선택 기준만 보여주고 벡터스토어 내부 정보는 숨겼습니다.
        </p>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Curriculum Results</p>
            <h2 class="panel-title">검색 결과 {{ results.length }}개</h2>
            <p class="panel-subtitle">결과를 선택하면 오른쪽에서 수업 목표로 정리됩니다.</p>
          </div>
          <span class="badge primary">GET /rag/curriculum-search</span>
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
              <strong>{{ compactContent(item.content) }}</strong>
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
            <p class="eyebrow">Selected Standard</p>
            <h2 class="panel-title">선택 기준</h2>
          </div>
          <div class="panel-icon">
            <BookOpenCheck />
          </div>
        </div>

        <template v-if="selectedResult">
          <div class="callout spaced">
            <strong>{{ standardCode(selectedResult, selectedIndex) }}</strong>
            <p>{{ selectedResult.content }}</p>
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
          <p>검색 결과를 선택하면 이곳에 기준 원문과 메타정보가 표시됩니다.</p>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Classroom Use</p>
        <h2 class="panel-title">수업 적용 메모</h2>
        <div class="list-stack spaced">
          <div v-for="memo in lessonMemos" :key="memo" class="mini-card">
            <strong>적용 포인트</strong>
            <p>{{ memo }}</p>
          </div>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { BookOpenCheck, SlidersHorizontal } from 'lucide-vue-next'
import { searchCurriculum } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()

const loading = ref(false)
const results = ref([])
const selectedIndex = ref(0)
const filters = reactive({
  query: '수 모형을 활용한 덧셈과 받아올림 단계 지원',
  subject: '수학',
  grade: '',
  disability_type: '',
})

const selectedResult = computed(() => results.value[selectedIndex.value] || null)

const lessonMemos = [
  '기준 원문을 그대로 목표 문장에 쓰기보다 오늘 수업 행동으로 좁혀 사용합니다.',
  '추천 결과와 맞지 않는 기준은 교사가 선택하지 않고 다시 검색합니다.',
  '국어와 수학 기준은 같은 카드 구조로 보여 비교가 쉽도록 했습니다.',
]

function compactContent(content = '') {
  return content.length > 96 ? `${content.slice(0, 96)}...` : content
}

function standardCode(item, index) {
  return item?.metadata?.standard_id || item?.metadata?.achievement_standard_id || item?.metadata?.id || `STD ${String(index + 1).padStart(2, '0')}`
}

function subjectLabel(subject) {
  const map = { math: '수학', korean: '국어' }
  return map[subject] || subject || '과목 정보 없음'
}

function scoreText(score) {
  if (typeof score !== 'number') return '-'
  return score.toFixed(2)
}

async function runSearch() {
  loading.value = true
  try {
    const response = await searchCurriculum(filters.query || '기초 학습 지원', {
      subject: filters.subject || undefined,
      grade: filters.grade || undefined,
      disability_type: filters.disability_type || studentStore.student?.disability_type || undefined,
      k: 6,
    })
    results.value = response.results || []
    selectedIndex.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  filters.disability_type = studentStore.student?.disability_type || ''
  await runSearch()
})
</script>
