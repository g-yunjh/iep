<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Student</p>
            <h2 class="panel-title">{{ studentName }}</h2>
            <p class="panel-subtitle">학생 맥락은 추천 요청과 함께 서버에서 반영됩니다.</p>
          </div>
          <div class="panel-icon">
            <UserRoundCog />
          </div>
        </div>

        <div class="list-stack spaced">
          <div v-for="item in studentProfile" :key="item.label" class="card-row">
            <strong>{{ item.label }}</strong>
            <span>{{ item.value }}</span>
          </div>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Past Feedback</p>
        <h2 class="panel-title">최근 기록 반영</h2>
        <p class="panel-subtitle">선택한 피드백 ID는 추천 요청의 맥락으로 보낼 수 있습니다.</p>

        <div class="list-stack spaced">
          <label v-for="feedback in feedbacks.slice(-3).reverse()" :key="feedback.id" class="card-row">
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
            <p class="panel-subtitle">관찰 문장과 과목 정보를 서버의 추천 API로 전송합니다.</p>
          </div>
          <span class="badge primary">POST /rag</span>
        </div>

        <div class="mini-grid spaced">
          <label>
            <span class="section-label">학년</span>
            <input v-model="form.grade" class="input-like spaced-sm" type="text" />
          </label>
          <label>
            <span class="section-label">과목</span>
            <select v-model="form.subject" class="input-like spaced-sm">
              <option>수학</option>
              <option>국어</option>
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
          <p>감지된 지원 수준</p>
          <strong>{{ levelLabel(recommendation.recommended_level) }}</strong>
          <p>{{ recommendation.rationale }}</p>
        </div>

        <div class="strategy-grid spaced">
          <article v-for="strategy in strategies" :key="strategy" class="strategy-card">
            <strong>{{ strategy }}</strong>
            <p>수업 장면에서 바로 실행할 수 있는 단위로 정리했습니다.</p>
          </article>
        </div>
      </section>

      <section class="panel" v-else>
        <div class="empty-state">
          <strong>추천 결과가 아직 없습니다.</strong>
          <p>관찰 기록을 입력하고 추천을 실행하면 수준, 전략, 활동, 근거가 이 화면에 나타납니다.</p>
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
          <article v-for="activity in activities" :key="activity.name || activity" class="strategy-card">
            <strong>{{ activity.name || activity }}</strong>
            <p>{{ activity.description || '학생 반응에 따라 도움 강도를 조절하며 진행합니다.' }}</p>
          </article>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel dark">
        <p class="eyebrow">Recommendation Logic</p>
        <h2 class="panel-title">서버 연계 흐름</h2>
        <p class="panel-subtitle">이 화면에서 실행하면 백엔드가 추천을 만들고 피드백 기록에도 저장합니다.</p>

        <div class="list-stack spaced">
          <div class="dark-list-item">1. 학생 프로필 조회</div>
          <div class="dark-list-item">2. 관찰 기록 RAG 분석</div>
          <div class="dark-list-item">3. 성취기준 근거 연결</div>
          <div class="dark-list-item">4. 추천 결과 피드백 저장</div>
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
          <p>추천 실행 후 가장 관련도 높은 기준이 표시됩니다.</p>
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
import { getScaffoldingRecommendation, getStudentProgress, mapLevelToKorean } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()

const loading = ref(false)
const recommendation = ref(null)
const feedbacks = ref([])
const form = reactive({
  grade: '초등학교 3학년',
  subject: '수학',
  teacher_description:
    '수 모형을 보여주면 덧셈 활동을 시작하지만, 받아올림 단계에서 멈추고 도움 요청을 하지 못합니다.',
})

const studentName = computed(() => studentStore.student?.name || '이지훈')
const studentProfile = computed(() => [
  { label: '현재 수준', value: studentStore.student?.current_level || '초등 3학년 수준 입력 대기' },
  { label: '장애 유형', value: studentStore.student?.disability_type || '정보 없음' },
  { label: '행동 특성', value: studentStore.student?.behavioral_traits || '관찰 필요' },
])

const strategies = computed(() =>
  recommendation.value?.scaffolding_details?.strategies?.length
    ? recommendation.value.scaffolding_details.strategies
    : ['한 번에 한 단계만 제시', '시각 단서를 먼저 제시', '완료 직후 강화'],
)

const activities = computed(() =>
  recommendation.value?.scaffolding_details?.activities?.length
    ? recommendation.value.scaffolding_details.activities
    : [
        { name: '단계 카드 정렬', description: '풀이 순서를 카드로 먼저 놓고 한 단계씩 수행합니다.' },
        { name: '도움 요청 문장 연습', description: '멈춘 지점에서 사용할 짧은 요청 문장을 선택하게 합니다.' },
      ],
)

const standard = computed(() => recommendation.value?.achievement_standard || null)
const relatedStandards = computed(() =>
  recommendation.value?.related_achievement_standards?.length
    ? recommendation.value.related_achievement_standards
    : ['추천 실행 후 관련 성취기준 후보가 여기에 표시됩니다.'],
)

function levelLabel(level) {
  const mapped = mapLevelToKorean(level)
  return mapped != null && mapped !== '' ? mapped : '대기'
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
}

function resetDraft() {
  form.teacher_description = ''
  recommendation.value = null
}

async function requestRecommendation() {
  loading.value = true
  try {
    recommendation.value = await getScaffoldingRecommendation({ ...form })
    const progressData = await getStudentProgress()
    feedbacks.value = progressData.feedbacks || []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const progressData = await getStudentProgress()
  feedbacks.value = progressData.feedbacks || []
})
</script>
