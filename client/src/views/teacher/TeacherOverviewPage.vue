<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Student Profile</p>
            <h2 class="panel-title">{{ studentName }}</h2>
            <p class="panel-subtitle">AI가 반영할 학생에 대한 기본 정보입니다.</p>
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
          <article v-for="feedback in feedbackPreview" :key="feedback.id" class="timeline-row">
            <small>{{ formatDate(feedback.created_at) }}</small>
            <strong>{{ feedback.teacher_description || feedback.performance || '기록 내용 없음' }}</strong>
            <span class="badge soft">{{ levelLabel(feedback.llm_analysis?.detected_level) }}</span>
            <RouterLink to="/teacher/progress" class="mono">보기</RouterLink>
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
            <p class="panel-subtitle">백엔드의 RAG 스캐폴딩 추천 API와 바로 연결됩니다.</p>
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
            {{ loadingRecommendation ? '분석 중' : '빠른 추천 생성' }}
          </button>
          <RouterLink to="/teacher/scaffolding" class="btn ghost">상세 입력으로 이동</RouterLink>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Scaffolding Results</p>
            <h2 class="panel-title">추천 수준과 전략</h2>
            <p class="panel-subtitle">지훈이의 현재 상태를 반영한 즉시 적용 전략입니다.</p>
          </div>
        </div>

        <template v-if="quickRecommendation">
          <div class="result-level">
            <p>감지된 지원 수준</p>
            <strong>{{ levelLabel(quickRecommendation.recommended_level) }}</strong>
            <p>{{ quickRecommendation.rationale }}</p>
          </div>

          <div class="strategy-grid spaced">
            <article v-for="strategy in strategies" :key="strategy" class="strategy-card">
              <strong>{{ strategy }}</strong>
              <p>수업 장면에서 바로 실행할 수 있는 단위로 정리했습니다.</p>
            </article>
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
          <div class="strategy-grid spaced">
            <article v-for="activity in activities" :key="activity.name || activity" class="strategy-card">
              <strong>{{ activity.name || activity }}</strong>
              <p>{{ activity.description || '학생 반응에 따라 도움 강도를 조절하며 진행합니다.' }}</p>
            </article>
          </div>
        </template>

        <div v-else class="empty-state spaced">
          <strong>추천 결과 대기</strong>
          <p>추천이 생성되면 지훈이가 바로 실행할 수 있는 활동이 표시됩니다.</p>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel dark">
        <p class="eyebrow">Today Priority</p>
        <h2 class="panel-title">교사가 지금 봐야 할 것</h2>
        <p class="panel-subtitle">오늘 수업에서 가장 우선순위가 높은 실행 포인트입니다.</p>

        <div class="list-stack spaced">
          <div v-for="item in priorityList" :key="item" class="dark-list-item">{{ item }}</div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Achievement Evidence</p>
            <h2 class="panel-title">근거 성취기준</h2>
            <p class="panel-subtitle">추천 생성 결과와 함께 본 기준을 확인합니다.</p>
          </div>
        </div>

        <div v-if="standard" class="callout spaced">
          <strong>{{ standard.standard_id || '기준 ID 없음' }} · {{ standard.subject || recommendationForm.subject }}</strong>
          <p>{{ standard.standard_text }}</p>
        </div>
        <div v-else class="empty-state spaced">
          <strong>추천 결과 대기</strong>
          <p>추천 실행 후 가장 관련도 높은 기준이 표시됩니다.</p>
        </div>

        <div class="list-stack spaced">
          <article v-for="(standardText, index) in relatedStandards" :key="`${standardText}-${index}`" class="standard-result">
            <code>{{ `RELATED ${String(index + 1).padStart(2, '0')}` }}</code>
            <div>
              <strong>{{ standardText }}</strong>
              <p>추천 생성 시 함께 참고한 기준입니다.</p>
            </div>
            <span class="mono">{{ index === 0 ? '0.79' : '0.73' }}</span>
          </article>
        </div>
      </section>

      <!-- <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Recent Feedback</p>
            <h2 class="panel-title">최근 피드백</h2>
          </div>
        </div>
        <div class="list-stack spaced">
          <article v-for="feedback in feedbackPreview" :key="feedback.id" class="timeline-row">
            <small>{{ formatDate(feedback.created_at) }}</small>
            <strong>{{ feedback.teacher_description || feedback.performance || '기록 내용 없음' }}</strong>
            <span class="badge soft">{{ levelLabel(feedback.llm_analysis?.detected_level) }}</span>
            <RouterLink to="/teacher/progress" class="mono">보기</RouterLink>
          </article>
        </div>
      </section> -->
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
  { label: '현재 수준', value: studentStore.student?.current_level || '초등 3학년 수준 입력 대기' },
  { label: '장애 유형', value: studentStore.student?.disability_type || '정보 없음' },
  { label: '중복 정보', value: studentStore.student?.additional_diagnoses || '없음' },
  { label: '행동 특성', value: studentStore.student?.behavioral_traits || '가정/학교 특성 입력 필요' },
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
const relatedStandards = computed(() =>
  quickRecommendation.value?.related_achievement_standards?.length
    ? quickRecommendation.value.related_achievement_standards
    : ['추천 생성 후 관련 성취기준 후보가 여기에 표시됩니다.'],
)

const previewStrategies = [
  '한 번에 한 단계만 제시',
  '수 모형 또는 그림 단서 먼저 제공',
  '완료 직후 구체적인 강화',
  '도움 요청 문장 카드 제공',
]

const priorityList = [
  '지훈이의 시작 단계를 낮추고 즉시 성공 경험 만들기',
  '도움 요청 문장을 먼저 제시해 멈춤 시간을 줄이기',
  '수업 후 피드백에 적용 반응을 바로 기록하기',
  '근거 성취기준을 오늘 수업 목표 문장으로 연결하기',
]

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
