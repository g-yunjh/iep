<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Student Profile</p>
            <h2 class="panel-title">{{ studentName }}</h2>
            <p class="panel-subtitle">AI가 답변 생성시 학생의 기본 특성을 반영합니다.</p>
          </div>
          <div class="panel-icon">
            <UserRoundCheck />
          </div>
        </div>

        <div class="list-stack spaced">
          <div v-for="item in studentCards" :key="item.label" class="card-row">
            <strong>{{ item.label }}</strong>
            <span>{{ item.value }}</span>
          </div>
        </div>

        <RouterLink to="/parent/traits" class="btn ghost spaced-sm">프로필 수정</RouterLink>
      </section>

      <section class="panel">
        <p class="eyebrow">Recent Flow</p>
        <h2 class="panel-title">최근 변화</h2>
        <p class="panel-subtitle">{{ progressSummary }}</p>

        <div class="mini-grid spaced">
          <div v-for="metric in sideMetrics" :key="metric.label" class="metric-card">
            <p>{{ metric.label }}</p>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.caption }}</small>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Recent Feedback</p>
            <h2 class="panel-title">최근 피드백</h2>
          </div>
        </div>
        <div class="list-stack spaced">
          <article
            v-for="feedback in feedbackPreview"
            :key="feedback.id"
            class="timeline-row feedback-card rounded-lg border border-[var(--color-border)] p-3"
          >
            <div class="flex items-center gap-3">
              <small class="whitespace-nowrap text-[0.75rem] leading-none text-[var(--color-text-secondary)]">
                {{ formatDate(feedback.created_at) }}
              </small>
              <span class="badge soft shrink-0">{{ levelLabel(feedback.llm_analysis?.detected_level) }}</span>
            </div>
            <strong
              class="feedback-summary min-w-0 text-sm font-semibold leading-snug text-[var(--color-text)]"
              :title="feedback.teacher_description || feedback.performance || '기록 내용 없음'"
            >
              {{ feedback.teacher_description || feedback.performance || '기록 내용 없음' }}
            </strong>
          </article>
        </div>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">AI Scaffolding</p>
            <h2 class="panel-title">관찰 기록을 수업 전략으로 전환</h2>
            <p class="panel-subtitle">학생에 대한 관찰 기록을 바탕으로 AI가 학생 맞춤의 스캐폴딩을 제공합니다.</p>
          </div>
          <span class="badge primary">Live API</span>
        </div>

        <textarea
          v-model="observationDraft"
          class="textarea-like spaced-sm"
          rows="5"
          placeholder="수업 중 관찰한 행동, 반응한 지원, 어려웠던 조건을 짧게 입력하세요."
        />

        <div class="mini-grid spaced-sm">
          <label>
            <span class="section-label">학년</span>
            <input v-model="recommendationForm.grade" class="input-like spaced-sm" type="text" />
          </label>
          <label>
            <span class="section-label">과목</span>
            <select v-model="recommendationForm.subject" class="input-like spaced-sm">
              <option>수학</option>
              <option>국어</option>
            </select>
          </label>
        </div>

        <div class="button-row spaced-sm">
          <button class="btn" type="button" :disabled="loadingRecommendation" @click="createQuickRecommendation">
            {{ loadingRecommendation ? '분석 중' : '추천 생성' }}
          </button>
          <RouterLink to="/teacher/scaffolding" class="btn ghost">상세 입력으로 이동</RouterLink>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Scaffolding Results</p>
            <h2 class="panel-title">추천 수준과 전략</h2>
            <p class="panel-subtitle">학생의 현재 상태를 반영한 즉시 적용 전략입니다.</p>
          </div>
        </div>

        <template v-if="quickRecommendation">
          <div class="space-y-6 pt-1">
            <div class="result-level">
              <p>감지된 지원 수준</p>
              <strong>{{ levelLabel(quickRecommendation.recommended_level) }}</strong>
              <p class="mt-3 text-sm leading-relaxed text-[var(--color-text-secondary)]">
                {{ levelSemantics(quickRecommendation.recommended_level) }}
              </p>
              <p class="mt-4 leading-relaxed">{{ quickRecommendation.rationale }}</p>
            </div>

            <div class="strategy-grid spaced gap-y-6">
              <article v-for="strategy in strategies" :key="strategy" class="strategy-card">
                <strong>{{ strategy }}</strong>
                <p class="mt-2 leading-relaxed">수업 장면에서 바로 실행할 수 있는 단위로 정리했습니다.</p>
              </article>
            </div>
          </div>
        </template>

        <div v-else class="empty-state spaced">
          <strong>추천 결과 대기</strong>
          <p>관찰 기록을 입력하고 추천을 실행하면 수준과 전략이 표시됩니다.</p>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Recommended Activities</p>
            <h2 class="panel-title">추천 활동</h2>
          </div>
          <span class="badge soft">{{ activities.length }}개</span>
        </div>

        <template v-if="quickRecommendation">
          <p
            class="mb-4 border-b border-[var(--color-border)] pb-3 text-xs font-medium uppercase tracking-wide text-[var(--color-text-secondary)]"
          >
            실행 단위 활동 · 지적 처리 부담을 줄이고 한 번에 하나씩 완료할 수 있게 구성했습니다 (지훈이 맞춤).
          </p>
          <div class="strategy-grid spaced gap-y-6">
            <article
              v-for="activity in activities"
              :key="activity.name || activity"
              class="strategy-card space-y-3 py-4 leading-relaxed"
            >
              <strong class="block text-base">{{ activity.name || activity }}</strong>
              <p class="text-[0.9375rem] leading-relaxed text-[var(--color-text-secondary)]">
                {{ activity.description || '학생 반응에 따라 도움 강도를 조절하며 진행합니다.' }}
              </p>
            </article>
          </div>
        </template>

        <div v-else class="empty-state spaced">
          <strong>추천 결과 대기</strong>
          <p>추천이 생성되면 학생에게 바로 적용할 수 있는 활동이 표시됩니다.</p>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel dark">
        <p class="eyebrow">Today Priority</p>
        <h2 class="panel-title">학생 맞춤 수업 포인트</h2>
        <p class="panel-subtitle">학생의 개별 특성을 고려한 오늘 수업 전 체크리스트입니다.</p>

        <div class="list-stack spaced">
          <div v-for="item in priorityList" :key="item" class="dark-list-item">{{ item }}</div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Achievement Evidence</p>
            <h2 class="panel-title">근거 성취기준</h2>
            <p class="panel-subtitle">AI가 스캐폴딩을 제안할 때, 반영한 근거 성취기준입니다.</p>
          </div>
        </div>

        <div v-if="standard" class="callout spaced">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <strong class="min-w-0 flex-1 leading-snug">
              {{ standard.standard_id || '기준 ID 없음' }} · {{ standard.subject || recommendationForm.subject }}
            </strong>
            <span
              class="shrink-0 text-2xl font-bold tabular-nums tracking-tight text-[var(--color-primary,#4f46e5)]"
              title="AI 분석 기준 문헌·검색 일치도"
            >
              {{ primaryMatchPercent }}
            </span>
          </div>
          <p class="mt-3 leading-relaxed">{{ standard.standard_text }}</p>
        </div>
        <div v-else class="empty-state spaced">
          <strong>추천 결과 대기</strong>
          <p>추천 실행 후 가장 관련도 높은 기준이 표시됩니다.</p>
        </div>

        <p v-if="evidenceList.length" class="eyebrow mt-4">함께 본 기준</p>
        <div v-if="evidenceList.length" class="list-stack spaced">
          <article v-for="(row, index) in evidenceList" :key="`${row.text}-${index}`" class="standard-result items-start gap-3">
            <code class="shrink-0">{{ `REL ${String(index + 1).padStart(2, '0')}` }}</code>
            <div class="min-w-0 flex-1">
              <strong class="line-clamp-2">{{ row.text }}</strong>
              <p class="mt-1 text-sm text-[var(--color-text-secondary)]">AI 매칭 스코어 기준 참고 항목입니다.</p>
            </div>
            <span class="mono shrink-0 text-base font-semibold tabular-nums">{{ row.matchPercent }}</span>
          </article>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  UserRoundCheck,
} from 'lucide-vue-next'
import { getScaffoldingRecommendation, getStudentProgress } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()

const observationDraft = ref(
  '수학 활동에서 수 모형을 보여주면 문제 풀이를 시작하지만, 말로만 설명하면 첫 단계에서 멈추고 도움을 요청하지 못합니다.',
)
const progress = ref({ feedbacks: [], progress_summary: '' })
const quickRecommendation = ref(null)
const loadingRecommendation = ref(false)

const recommendationForm = reactive({
  grade: '초등학교 3학년',
  subject: '수학',
})

const studentName = computed(() => studentStore.student?.name || '이지훈')

const studentCards = computed(() => [
  {
    label: '현재 수준',
    value: studentStore.student?.current_level || '초등 3학년 수준 · 구체적 연산 단계에서 개별 지원 필요',
  },
  {
    label: '장애 유형',
    value: studentStore.student?.disability_type || '경도 지적장애 · ADHD (프로필 등록 시 서버에 반영)',
  },
  {
    label: '동반 진단',
    value: studentStore.student?.additional_diagnoses || '없음 또는 미등록',
  },
  {
    label: '과제·주의 특성',
    value:
      studentStore.student?.behavioral_traits ||
      '말로만 된 설명보다 시각·순서 단서가 있을 때 과제 지속 시간이 길어짐 · 전환 시 예고 필요',
  },
])

const feedbacks = computed(() => progress.value.feedbacks || [])
const progressSummary = computed(() => progress.value.progress_summary || '최근 피드백을 불러오는 중입니다.')
const latestFeedback = computed(() => feedbacks.value.at(-1) || null)
const latestLevel = computed(() => latestFeedback.value?.llm_analysis?.detected_level || 'medium')

const sideMetrics = computed(() => [
  { label: '기록 수', value: feedbacks.value.length, caption: '누적 피드백' },
  { label: '최근 수준', value: levelLabel(latestLevel.value), caption: '최근 분석' },
])

const feedbackPreview = computed(() => feedbacks.value.slice(-3).reverse())

const strategies = computed(() =>
  quickRecommendation.value?.scaffolding_details?.strategies?.length
    ? quickRecommendation.value.scaffolding_details.strategies
    : previewStrategies,
)

const activities = computed(() =>
  quickRecommendation.value?.scaffolding_details?.activities?.length
    ? quickRecommendation.value.scaffolding_details.activities
    : [
        { name: '단계 카드 정렬', description: '풀이 순서를 카드로 먼저 놓고 한 단계씩 수행합니다.' },
        { name: '도움 요청 문장 연습', description: '멈춘 지점에서 사용할 짧은 요청 문장을 선택하게 합니다.' },
      ],
)

const standard = computed(() => quickRecommendation.value?.achievement_standard || null)

const primaryMatchPercent = computed(() =>
  scoreToPercent(standard.value?.relevance_score ?? standard.value?.match_score),
)

const evidenceList = computed(() => {
  const rec = quickRecommendation.value
  if (!rec?.related_achievement_standards?.length) return []

  const primaryScoreRaw = rec.achievement_standard?.relevance_score ?? rec.achievement_standard?.match_score ?? 0.82
  const primaryScore = typeof primaryScoreRaw === 'number' ? primaryScoreRaw : Number(primaryScoreRaw) || 0.82

  return rec.related_achievement_standards
    .map((item, index) => {
      const text =
        typeof item === 'string'
          ? item
          : item?.standard_text || item?.text || ''
      if (!text.trim() || isPlaceholderRelatedText(text)) return null

      let matchRaw
      if (typeof item === 'object' && item != null) {
        matchRaw = item.match_score ?? item.relevance_score
      }
      if (matchRaw == null || Number.isNaN(Number(matchRaw))) {
        matchRaw = Math.max(0.48, primaryScore - (index + 1) * 0.055)
      }

      return {
        text,
        matchPercent: scoreToPercent(matchRaw),
      }
    })
    .filter(Boolean)
})

const previewStrategies = [
  '한 번에 한 단계만 제시',
  '수 모형 또는 그림 단서 먼저 제공',
  '완료 직후 구체적인 강화',
  '도움 요청 문장 카드 제공',
]

const priorityList = [
  '1. ADHD 투약 여부 및 아침 컨디션 확인',
  '2. 수업 시작 전 시각적 스케줄러 배치',
  '3. 과제 전환 시 3분 전 예고제 실시',
  '4. 지시는 한 문장·한 단계, 성공 시 즉각 구두 강화',
]

function scoreToPercent(raw) {
  if (raw == null || raw === '') return '—'
  const n = Number(raw)
  if (Number.isNaN(n)) return '—'
  const pct = n <= 1 ? Math.round(n * 100) : Math.round(n)
  return `${pct}%`
}

function isPlaceholderRelatedText(text) {
  return /추천 생성 후|후보가 여기/.test(text)
}

function levelSemantics(level) {
  const key = String(level || '').toLowerCase()
  if (key === 'medium' || key === '중' || level === '중간')
    return '중간(Medium): 시각적 촉진(Visual Prompt)과 부분적 신체 지원이 필요한 단계입니다.'
  if (key === 'high' || key === '상' || level === '높음')
    return '높음(High): 높은 구조화와 반복 모델링이 필요하며, 시작을 대신 제시해 주는 단계입니다.'
  if (key === 'low' || key === '하' || level === '낮음')
    return '낮음(Low): 언어 단서만으로도 과제를 지속할 수 있으며, 확인 질문 위주로 지원합니다.'
  return '추천 수준에 따른 지원 강도입니다. 필요 시 상세 입력 화면에서 조정할 수 있습니다.'
}

function levelLabel(level) {
  const map = {
    high: '높음',
    medium: '중간',
    low: '낮음',
    상: '높음',
    중: '중간',
    하: '낮음',
  }
  return map[level] || level || '대기'
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
}

async function createQuickRecommendation() {
  loadingRecommendation.value = true
  try {
    quickRecommendation.value = await getScaffoldingRecommendation({
      grade: recommendationForm.grade,
      subject: recommendationForm.subject,
      teacher_description: observationDraft.value,
      disability_type: studentStore.student?.disability_type || undefined,
      additional_diagnoses: studentStore.student?.additional_diagnoses || undefined,
    })
    progress.value = await getStudentProgress()
  } finally {
    loadingRecommendation.value = false
  }
}

onMounted(async () => {
  const progressData = await getStudentProgress()
  progress.value = progressData
})
</script>
