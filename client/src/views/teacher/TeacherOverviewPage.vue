<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Student Context</p>
            <h2 class="panel-title">{{ studentName }}</h2>
            <p class="panel-subtitle">추천 생성에 반영되는 학생 기본 맥락입니다.</p>
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
        <div class="panel-header">
          <div>
            <p class="eyebrow">School Feed</p>
            <h2 class="panel-title">오늘 학교 정보</h2>
          </div>
          <div class="panel-icon">
            <CalendarDays />
          </div>
        </div>

        <div class="list-stack spaced">
          <div v-for="item in schoolCards" :key="item.label" class="mini-card">
            <strong>{{ item.label }}</strong>
            <p>{{ item.value }}</p>
          </div>
        </div>
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

        <div class="chip-row spaced">
          <button
            v-for="subject in subjects"
            :key="subject"
            type="button"
            :class="['chip', selectedSubject === subject && 'active']"
            @click="selectedSubject = subject"
          >
            {{ subject }}
          </button>
        </div>

        <textarea
          v-model="observationDraft"
          class="textarea-like spaced-sm"
          rows="5"
          placeholder="수업 중 관찰한 행동, 반응한 지원, 어려웠던 조건을 짧게 입력하세요."
        />

        <div class="button-row spaced-sm">
          <button class="btn" type="button" :disabled="loadingRecommendation" @click="createQuickRecommendation">
            {{ loadingRecommendation ? '분석 중' : '빠른 추천 생성' }}
          </button>
          <RouterLink to="/teacher/scaffolding" class="btn ghost">상세 입력으로 이동</RouterLink>
        </div>
      </section>

      <section class="panel" v-if="quickRecommendation">
        <div class="result-level">
          <p>추천 지원 수준</p>
          <strong>{{ levelLabel(quickRecommendation.recommended_level) }}</strong>
          <p>{{ quickRecommendation.rationale }}</p>
        </div>

        <div class="strategy-grid spaced">
          <article v-for="strategy in quickStrategies" :key="strategy" class="strategy-card">
            <strong>{{ strategy }}</strong>
            <p>수업 중 바로 적용하고, 적용 반응은 기록 화면에서 이어서 확인합니다.</p>
          </article>
        </div>
      </section>

      <section class="panel" v-else>
        <p class="eyebrow">Recommendation Preview</p>
        <h2 class="panel-title">추천 결과 대기</h2>
        <p class="panel-subtitle">
          관찰 기록을 실행하면 추천 수준, 전략, 활동, 근거 성취기준이 이 영역에 정리됩니다.
        </p>
        <div class="strategy-grid spaced">
          <article v-for="item in previewStrategies" :key="item" class="strategy-card">
            <strong>{{ item }}</strong>
            <p>피그마 화면처럼 한눈에 읽히는 실행 단위로 표시됩니다.</p>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Evidence</p>
            <h2 class="panel-title">근거 성취기준</h2>
            <p class="panel-subtitle">AI 추천과 연결되는 성취기준 후보를 교사가 검토합니다.</p>
          </div>
          <RouterLink to="/teacher/curriculum" class="btn ghost">기준 검색</RouterLink>
        </div>

        <div class="list-stack spaced">
          <article v-for="(standard, index) in evidenceList" :key="standard" class="standard-result">
            <code>{{ `MATCH ${String(index + 1).padStart(2, '0')}` }}</code>
            <div>
              <strong>{{ standard }}</strong>
              <p>{{ selectedSubject }} 수업 맥락과 학생 현재 수준을 함께 반영합니다.</p>
            </div>
            <span class="mono">{{ index === 0 ? '0.82' : '0.77' }}</span>
          </article>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel dark">
        <p class="eyebrow">Today Priority</p>
        <h2 class="panel-title">교사가 지금 봐야 할 것</h2>
        <p class="panel-subtitle">
          학생의 상태, 추천 전략, 성취기준 근거, 기록 흐름만 전면에 두었습니다.
        </p>

        <div class="list-stack spaced">
          <div v-for="item in priorityList" :key="item" class="dark-list-item">{{ item }}</div>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Feedback Loop</p>
        <h2 class="panel-title">최근 피드백</h2>
        <div class="list-stack spaced">
          <article v-for="feedback in feedbackPreview" :key="feedback.id" class="timeline-row">
            <small>{{ formatDate(feedback.created_at) }}</small>
            <strong>{{ feedback.teacher_description || feedback.performance || '기록 내용 없음' }}</strong>
            <span class="badge soft">{{ levelLabel(feedback.llm_analysis?.detected_level) }}</span>
            <RouterLink to="/teacher/progress" class="mono">보기</RouterLink>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Career Hint</p>
            <h2 class="panel-title">강점 기반 진로</h2>
          </div>
          <div class="panel-icon">
            <BriefcaseBusiness />
          </div>
        </div>
        <div class="callout spaced">
          <strong>손작업과 순서 기억</strong>
          <p>반복 루틴과 시각 자료에 안정적으로 반응하는 강점은 직무 체험 후보로 연결됩니다.</p>
        </div>
        <RouterLink to="/teacher/career" class="btn ghost spaced-sm">진로 추천 보기</RouterLink>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  BriefcaseBusiness,
  CalendarDays,
  UserRoundCheck,
} from 'lucide-vue-next'
import { getScaffoldingRecommendation, getSchoolLife, getStudentProgress } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()

const subjects = ['수학', '국어']
const selectedSubject = ref('수학')
const observationDraft = ref(
  '수학 활동에서 수 모형을 보여주면 문제 풀이를 시작하지만, 말로만 설명하면 첫 단계에서 멈추고 도움을 요청하지 못합니다.',
)
const schoolLife = ref({})
const progress = ref({ feedbacks: [], progress_summary: '' })
const quickRecommendation = ref(null)
const loadingRecommendation = ref(false)

const studentName = computed(() => studentStore.student?.name || '나의 아이')

const studentCards = computed(() => [
  { label: '현재 수준', value: studentStore.student?.current_level || '초등 3학년 수준 입력 대기' },
  { label: '장애 유형', value: studentStore.student?.disability_type || '정보 없음' },
  { label: '중복 정보', value: studentStore.student?.additional_diagnoses || '없음' },
  { label: '행동 특성', value: studentStore.student?.behavioral_traits || '가정/학교 특성 입력 필요' },
])

const schoolCards = computed(() => [
  { label: '점심', value: schoolLife.value.lunch_menu || '정보 없음' },
  { label: '하교 시간', value: schoolLife.value.dismissal_time || '정보 없음' },
  { label: '오늘 시간표', value: (schoolLife.value.today_timetable || []).join(', ') || '정보 없음' },
  { label: '학사 일정', value: schoolLife.value.academic_calendar || '일정 없음' },
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

const quickStrategies = computed(() =>
  quickRecommendation.value?.scaffolding_details?.strategies?.length
    ? quickRecommendation.value.scaffolding_details.strategies
    : previewStrategies,
)

const previewStrategies = [
  '한 번에 한 단계만 제시',
  '수 모형 또는 그림 단서 먼저 제공',
  '완료 직후 구체적인 강화',
  '도움 요청 문장 카드 제공',
]

const evidenceList = computed(() => {
  const result = quickRecommendation.value
  const standards = [
    result?.achievement_standard?.standard_text,
    ...(result?.related_achievement_standards || []),
  ].filter(Boolean).slice(0, 3)
  return standards.length
    ? standards
    : [
        '수학: 수 모형을 활용해 덧셈과 뺄셈 과정을 나타낸다.',
        '국어: 핵심 낱말의 의미를 문맥에서 파악한다.',
      ]
})

const priorityList = [
  '오늘 관찰 기록을 먼저 남기기',
  '추천 수준과 실제 지원 강도 비교',
  '성취기준 근거를 수업 목표에 연결',
  '적용 후 반응을 피드백으로 누적',
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
      grade: '초등학교 3학년',
      subject: selectedSubject.value,
      teacher_description: observationDraft.value,
    })
    progress.value = await getStudentProgress()
  } finally {
    loadingRecommendation.value = false
  }
}

onMounted(async () => {
  const [schoolData, progressData] = await Promise.all([getSchoolLife(), getStudentProgress()])
  schoolLife.value = schoolData
  progress.value = progressData
})
</script>
