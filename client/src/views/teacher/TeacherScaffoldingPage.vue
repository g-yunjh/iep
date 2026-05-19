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
          <div class="result-level-header">
            <div>
              <p class="result-kicker">감지된 지원 수준</p>
              <strong class="result-level-mark">{{ levelLabel(recommendation.recommended_level) }}</strong>
            </div>
          </div>

          <div class="result-report-grid">
            <article class="result-report-block result-report-block-primary">
              <span>평가 요약</span>
              <p>{{ detailLevelSemantics }}</p>
              <p v-if="detailRationaleSections.assessment">{{ detailRationaleSections.assessment }}</p>
            </article>
            <article v-if="detailRationaleSections.gap" class="result-report-block">
              <span>주요 학습 격차</span>
              <p>{{ detailRationaleSections.gap }}</p>
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
          <article v-for="activity in activities" :key="activity.name || activity" class="strategy-card">
            <strong>{{ activity.name || activity }}</strong>
            <p>{{ activity.description || '학생 반응에 따라 도움 강도를 조절하며 진행합니다.' }}</p>
          </article>
        </div>
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
const detailLevelSemantics = computed(() => levelSemantics(recommendation.value?.recommended_level))
const detailRationaleSections = computed(() =>
  parseRationaleSections(recommendation.value?.rationale, detailLevelSemantics.value),
)
const relatedStandards = computed(() =>
  recommendation.value?.related_achievement_standards?.length
    ? recommendation.value.related_achievement_standards
    : ['추천과 함께 참고할 성취기준이 여기에 표시됩니다.'],
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

function parseRationaleSections(text, semanticText = '') {
  const sections = {
    assessment: '',
    gap: '',
    standard: '',
  }
  let current = 'assessment'

  String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line && !/^신뢰도\s*[:：]/.test(line))
    .forEach((line) => {
      if (semanticText && line === semanticText.trim()) return

      const gapMatch = line.match(/^주요 학습 격차\s*[:：]\s*(.*)$/)
      if (gapMatch) {
        current = 'gap'
        sections.gap = appendSentence(sections.gap, gapMatch[1])
        return
      }

      const standardMatch = line.match(/^관련 성취기준\s*[:：]\s*(.*)$/)
      if (standardMatch) {
        current = 'standard'
        sections.standard = appendSentence(sections.standard, standardMatch[1])
        return
      }

      if (/^[상중하]\s*[:：]/.test(line)) return
      sections[current] = appendSentence(sections[current], line)
    })

  return sections
}

function appendSentence(base, next) {
  const value = String(next || '').trim()
  if (!value) return base
  return base ? `${base} ${value}` : value
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
