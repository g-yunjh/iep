<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Student Profile</p>
            <h2 class="panel-title">{{ studentName }}</h2>
          </div>
          <div class="panel-icon">
            <UserRoundCog />
          </div>
        </div>
        <p class="panel-subtitle student-profile-subtitle">학생의 기본 특성과 현재 수준을 바탕으로 추천 방향을 잡습니다.</p>

        <div class="list-stack spaced student-context-list">
          <div v-for="item in studentProfile" :key="item.label" class="card-row student-context-row">
            <strong>{{ item.label }}</strong>
            <span>{{ item.value }}</span>
          </div>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Past Feedback</p>
        <h2 class="panel-title">최근 기록 반영</h2>
        <p class="panel-subtitle">최근 관찰 기록을 함께 참고해 반복되는 어려움과 반응을 반영합니다.</p>

        <div class="list-stack spaced">
          <label
            v-for="feedback in feedbacks.slice(-3).reverse()"
            :key="feedback.id"
            class="card-row feedback-context-row"
          >
            <strong>{{ formatDate(feedback.created_at) }}</strong>
            <span>{{ feedback.teacher_description || feedback.performance || '기록 내용 없음' }}</span>
          </label>
        </div>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Observation Input</p>
            <h2 class="panel-title">스캐폴딩 추천 입력</h2>
            <p class="panel-subtitle">수업 중 관찰한 상황을 적으면 바로 적용할 지원 방향을 정리합니다.</p>
          </div>
          <span class="badge primary">맞춤 추천</span>
        </div>

        <div v-if="loading" class="status-banner spaced-sm">
          <strong>새 스캐폴딩 추천을 생성 중입니다.</strong>
          <p>학생 상태와 선택 과목을 바탕으로 근거 기준과 활동까지 함께 정리하고 있습니다.</p>
        </div>

        <div class="mini-grid spaced">
          <label>
            <span class="section-label">학년</span>
            <input v-model="form.grade" class="input-like spaced-sm" type="text" />
          </label>
          <label>
            <span class="section-label">과목</span>
            <select v-model="form.subject" class="input-like spaced-sm">
              <option v-for="subject in subjectOptions" :key="subject.slug" :value="subject.label">
                {{ subject.label }}
              </option>
            </select>
          </label>
        </div>

        <label class="spaced">
          <span class="section-label">학생 상태 서술</span>
          <textarea
            v-model="form.teacher_description"
            class="textarea-like spaced-sm"
            rows="8"
            placeholder="예: 덧셈 활동에서 구체물을 보면 시작하지만, 받아올림 단계에서 멈추고 도움 요청을 하지 못합니다."
          />
        </label>

        <div class="button-row spaced-sm">
          <button class="btn" type="button" :disabled="loading || !form.teacher_description.trim()" @click="requestRecommendation">
            {{ loading ? '추천 생성 중' : 'AI 추천 받기' }}
          </button>
          <button class="btn ghost" type="button" @click="resetDraft">입력 초기화</button>
        </div>
      </section>

      <section class="panel" v-if="recommendation">
        <div class="result-level">
          <div class="result-level-header">
            <div>
              <p class="result-kicker">감지된 지원 수준</p>
              <strong class="result-level-mark">{{ levelLabel(recommendation.recommended_level) }}</strong>
            </div>
            <span v-if="detailConfidence" class="result-confidence">
              신뢰도 {{ detailConfidence }}
            </span>
          </div>

          <div class="result-report-grid">
            <article class="result-report-block result-report-block-primary">
              <span>평가 요약</span>
              <p>{{ detailLevelSemantics }}</p>
              <p v-if="detailRationaleSections.assessment">{{ detailRationaleSections.assessment }}</p>
            </article>
            <article v-if="detailRationaleSections.gap" class="result-report-block">
              <span>주요 학습 격차</span>
              <template v-if="gapItems.length">
                <ul class="compact-list result-compact-list">
                  <li v-for="item in visibleGapItems" :key="item">{{ item }}</li>
                </ul>
                <button
                  v-if="gapItems.length > SUMMARY_LIMIT"
                  type="button"
                  class="inline-more-button result-more-button"
                  @click="showAllGaps = !showAllGaps"
                >
                  {{ showAllGaps ? '접기' : `+ ${gapItems.length - SUMMARY_LIMIT}개 더 보기` }}
                </button>
              </template>
              <p v-else>{{ detailRationaleSections.gap }}</p>
            </article>
            <article v-if="detailRationaleSections.standard" class="result-report-block result-report-block-wide">
              <span>근거 성취기준</span>
              <p>{{ detailRationaleSections.standard }}</p>
            </article>
          </div>
        </div>

        <div class="strategy-grid spaced">
          <article v-for="(strategy, index) in strategies" :key="strategy" class="strategy-card strategy-card-labeled">
            <strong class="strategy-card-heading">추천 전략 {{ index + 1 }}</strong>
            <p class="strategy-card-copy">{{ strategy }}</p>
          </article>
        </div>
      </section>

      <section class="panel" v-else>
        <div class="empty-state">
          <strong>추천 결과가 아직 없습니다.</strong>
          <p>관찰 기록을 입력하면 추천 수준, 지원 전략, 활동, 근거 기준을 한 번에 확인할 수 있습니다.</p>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Activity Set</p>
            <h2 class="panel-title">추천 활동</h2>
          </div>
          <span class="badge soft">{{ activities.length }}개</span>
        </div>

        <div class="strategy-grid spaced">
          <article v-for="activity in visibleActivities" :key="activity.name || activity" class="strategy-card">
            <strong>{{ activity.name || activity }}</strong>
            <p>{{ activity.description || '학생 반응에 따라 도움 강도를 조절하며 진행합니다.' }}</p>
          </article>
        </div>
        <button
          v-if="activities.length > ACTIVITY_PREVIEW_LIMIT"
          type="button"
          class="inline-more-button spaced-sm"
          @click="showAllActivities = !showAllActivities"
        >
          {{ showAllActivities ? '추천 활동 접기' : `추천 활동 ${activities.length - ACTIVITY_PREVIEW_LIMIT}개 더 보기` }}
        </button>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel dark">
        <p class="eyebrow">Recommendation Flow</p>
        <h2 class="panel-title">추천 구성 방식</h2>
        <p class="panel-subtitle">입력한 관찰 기록을 학생 특성, 지난 피드백, 성취기준과 함께 보며 수업 지원 방향을 정리합니다.</p>

        <div class="list-stack spaced">
          <div class="dark-list-item">1. 학생 특성 확인</div>
          <div class="dark-list-item">2. 최근 관찰 기록 반영</div>
          <div class="dark-list-item">3. 관련 성취기준 확인</div>
          <div class="dark-list-item">4. 수업 전략과 활동 제안</div>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Achievement Evidence</p>
        <h2 class="panel-title">근거 성취기준</h2>
        <div v-if="standard" class="callout spaced">
          <strong>{{ standard.standard_id || '기준 ID 없음' }} · {{ standard.subject || form.subject }}</strong>
          <p>{{ standard.standard_text }}</p>
        </div>
        <div v-else class="empty-state spaced">
          <strong>기준 대기</strong>
          <p>학생 상태와 가장 가까운 성취기준이 여기에 표시됩니다.</p>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Related Standards</p>
        <h2 class="panel-title">함께 본 기준</h2>
        <div class="list-stack spaced">
          <div v-for="standardText in relatedStandards" :key="standardText" class="mini-card">
            <strong>관련 기준</strong>
            <p>{{ standardText }}</p>
          </div>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { UserRoundCog } from 'lucide-vue-next'
import {
  buildScaffoldingPresentation,
  getScaffoldingRecommendation,
  getStudentProgress,
  mapLevelToKorean,
} from '../../api'
import { useCurriculumSubjects } from '../../composables/useCurriculumSubjects'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()
const { subjectOptions, loadCurriculumSubjects } = useCurriculumSubjects()

const loading = ref(false)
const recommendation = ref(null)
const feedbacks = ref([])
const showAllGaps = ref(false)
const showAllActivities = ref(false)
const SUMMARY_LIMIT = 3
const ACTIVITY_PREVIEW_LIMIT = 4
const form = reactive({
  grade: '초등학교 3학년',
  subject: '수학',
  teacher_description: '',
})

function ensureSelectedSubject(currentValue) {
  if (!subjectOptions.value.length) return currentValue
  const isValid = subjectOptions.value.some(
    (subject) => subject.label === currentValue || subject.slug === currentValue,
  )
  return isValid ? currentValue : subjectOptions.value[0].label
}

const studentName = computed(() => studentStore.student?.name || '학생 정보 없음')
const studentProfile = computed(() => [
  { label: '현재 수준', value: studentStore.student?.current_level || '정보 없음' },
  { label: '장애 유형', value: studentStore.student?.disability_type || '정보 없음' },
  { label: '행동 특성', value: studentStore.student?.behavioral_traits || '관찰 필요' },
])

const strategies = computed(() =>
  recommendation.value?.scaffolding_details?.strategies?.length
    ? recommendation.value.scaffolding_details.strategies
    : [],
)

const activities = computed(() =>
  recommendation.value?.scaffolding_details?.activities?.length
    ? recommendation.value.scaffolding_details.activities
    : [],
)

const gapItems = computed(() => splitDisplayItems(detailRationaleSections.value?.gap))
const visibleGapItems = computed(() =>
  showAllGaps.value ? gapItems.value : gapItems.value.slice(0, SUMMARY_LIMIT),
)
const visibleActivities = computed(() =>
  showAllActivities.value ? activities.value : activities.value.slice(0, ACTIVITY_PREVIEW_LIMIT),
)

const standard = computed(() => recommendation.value?.achievement_standard || null)
const detailLevelSemantics = computed(() => levelSemantics(recommendation.value?.recommended_level))
const detailRationaleSections = computed(() =>
  recommendation.value?.presentation ||
  buildScaffoldingPresentation(recommendation.value, recommendation.value?.llm_analysis),
)
const detailConfidence = computed(() => detailRationaleSections.value?.confidence || '')
const relatedStandards = computed(() =>
  recommendation.value?.related_achievement_standards?.length
    ? recommendation.value.related_achievement_standards
    : [],
)

function levelLabel(level) {
  const mapped = mapLevelToKorean(level)
  return mapped != null && mapped !== '' ? mapped : '대기'
}

function levelSemantics(level) {
  const mapped = mapLevelToKorean(level)
  const key = String(mapped || '').trim()
  if (key === '중')
    return '중: 시각적 단서와 단계별 안내를 병행하면 과제를 이어가기 쉬운 수준입니다.'
  if (key === '상')
    return '상: 상대적으로 독립 수행에 가깝고, 확인 질문·선택지 중심의 가벼운 지원으로 충분한 경우가 많습니다.'
  if (key === '하')
    return '하: 세분화된 시각·구체 자료와 짧은 단계의 안내가 필요한 수준입니다.'
  return '추천 수준에 따른 지원 강도입니다.'
}

function splitDisplayItems(text) {
  const value = String(text || '')
    .replace(/\r\n?/g, '\n')
    .replace(/^\s*(?:[-*•·]|\d+[.)])\s*/gm, '|')
    .replace(/\s+(?:[-*•·]|\d+[.)])\s+/g, '|')
    .replace(/\s*([?!])\s*,+\s*/g, '$1|')
    .replace(/([?!])\s+(?=[가-힣A-Za-z0-9])/g, '$1|')
    .replace(/\s*\.\s*,+\s*/g, '.|')
    .replace(/다\.\s+/g, '다.|')
    .replace(/\.\s+(?=[가-힣A-Za-z0-9])/g, '.|')
    .replace(/\s+·\s+/g, '|')
    .replace(/\n+/g, '|')
    .trim()
  if (!value) return []

  const items = value.split('|').flatMap(splitCommaItems).map(cleanListItem).filter(Boolean)
  return [...new Set(items)]
}

function splitCommaItems(item) {
  const value = cleanListItem(item)
  if (!value) return []
  const parts = value.split(/\s*,\s+/).map(cleanListItem).filter(Boolean)
  if (parts.length > 1 && parts.every((part) => part.length >= 6)) return parts
  return [value]
}

function cleanListItem(item) {
  return String(item || '')
    .trim()
    .replace(/^(?:[-*•·]\s*|\d+[.)]\s*)+/, '')
    .replace(/^['"“”‘’]+|['"“”‘’]+$/g, '')
    .replace(/\s*([?!])\s*,+$/g, '$1')
    .replace(/\s*\.\s*,+$/g, '.')
    .replace(/[,;:\s]+$/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
}

function resetDraft() {
  form.teacher_description = ''
  recommendation.value = null
}

function subjectInputValue(subject) {
  if (!subject) return ''
  const matched = subjectOptions.value.find((item) => item.label === subject || item.slug === subject)
  return matched?.label || subject
}

function applyRecommendationInputEcho(response) {
  const sampleInput = response?.sample_input || {}
  if (!form.teacher_description && sampleInput.teacher_description) {
    form.teacher_description = sampleInput.teacher_description
  }
  if (!form.grade && sampleInput.grade) {
    form.grade = sampleInput.grade
  }
  if (!form.subject && sampleInput.subject) {
    form.subject = subjectInputValue(sampleInput.subject)
  }
}

async function requestRecommendation() {
  loading.value = true
  try {
    showAllGaps.value = false
    showAllActivities.value = false
    recommendation.value = await getScaffoldingRecommendation({ ...form })
    applyRecommendationInputEcho(recommendation.value)
    const progressData = await getStudentProgress()
    feedbacks.value = progressData.feedbacks || []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadCurriculumSubjects()
  form.subject = ensureSelectedSubject(form.subject)
  const progressData = await getStudentProgress()
  feedbacks.value = progressData.feedbacks || []
})
</script>
