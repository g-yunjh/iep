<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Strengths</p>
            <h2 class="panel-title">강점 입력</h2>
            <p class="panel-subtitle">아이의 좋아하는 활동을 부담 없는 진로 힌트로 바꿉니다.</p>
          </div>
          <div class="panel-icon">
            <HeartHandshake />
          </div>
        </div>

        <label class="spaced">
          <span class="section-label">현재 보이는 강점</span>
          <textarea v-model="currentSkills" class="textarea-like spaced-sm" rows="6" />
        </label>

        <label class="spaced-sm">
          <span class="section-label">좋아하는 활동</span>
          <input v-model="interests" class="input-like spaced-sm" type="text" />
        </label>

        <div class="button-row spaced">
          <button class="btn" type="button" :disabled="loading" @click="recommendCareer">
            {{ loading ? '탐색 중' : '진로 힌트 보기' }}
          </button>
        </div>
      </section>

      <section class="panel dark">
        <p class="eyebrow">Parent Tone</p>
        <h2 class="panel-title">대화 중심</h2>
        <p class="panel-subtitle">
          직업을 빨리 정하는 화면이 아니라, 아이의 강점을 알아차리고 대화하는 화면입니다.
        </p>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Career Hints</p>
            <h2 class="panel-title">추천 진로 후보</h2>
            <p class="panel-subtitle">아이의 강점과 좋아하는 활동에서 이어볼 수 있는 진로 힌트입니다.</p>
          </div>
          <span class="badge primary">진로 힌트</span>
        </div>

        <div v-if="loading" class="status-banner spaced-sm">
          <strong>새 진로 힌트를 생성 중입니다.</strong>
          <p>강점과 좋아하는 활동을 바탕으로 진로 후보와 대화 힌트를 정리하고 있습니다.</p>
        </div>

        <div class="list-stack spaced">
          <article v-for="career in recommendedCareers" :key="career.job_title" class="career-result">
            <div>
              <strong>{{ career.job_title }}</strong>
              <p>{{ career.category || '기타' }} · 적합도 {{ percentText(career.match_score ?? career.score) }}</p>
            </div>
            <span class="mono">{{ percentText(career.match_score ?? career.score) }}</span>
          </article>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Conversation</p>
        <h2 class="panel-title">오늘 해볼 대화</h2>
        <div class="strategy-grid spaced">
          <article v-for="(sentence, index) in conversationPrompts" :key="sentence" class="strategy-card strategy-card-labeled">
            <strong class="strategy-card-heading">대화 힌트 {{ index + 1 }}</strong>
            <p class="strategy-card-copy">{{ sentence }}</p>
          </article>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel">
        <p class="eyebrow">Skill Growth</p>
        <h2 class="panel-title">키우면 좋은 부분</h2>
        <div class="list-stack spaced">
          <div v-for="gap in skillGaps" :key="gap.job_title || gap" class="mini-card">
            <strong>{{ gap.job_title || '역량' }}</strong>
            <p>{{ listText(gap.gap_skills || [gap]) }}</p>
          </div>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Small Path</p>
        <h2 class="panel-title">작은 단계</h2>
        <div v-if="pathStages.length" class="list-stack spaced">
          <div
            v-for="(stage, index) in pathStages"
            :key="`${stage.stage}-${stage.focus || ''}-${stage.description}`"
            class="path-stage parent-path-stage"
          >
            <span class="step-dot">{{ index + 1 }}</span>
            <strong>{{ stage.stage }}</strong>
            <p v-if="stage.focus" class="path-stage-focus">{{ stage.focus }}</p>
            <p :class="['path-stage-description', !stage.focus && 'is-alone']">{{ stage.description }}</p>
          </div>
        </div>
        <div v-else class="empty-state spaced">
          <strong>경로 대기</strong>
          <p>진로 힌트를 실행하면 작은 단계가 여기에 표시됩니다.</p>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { HeartHandshake } from 'lucide-vue-next'
import { getCareerRecommendation, searchCareer } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()
const route = useRoute()

const loading = ref(false)
const currentSkills = ref('')
const interests = ref('')
const careerRecommendation = ref(null)
const searchResults = ref([])
const routeSearchQuery = computed(() => (typeof route.query.q === 'string' ? route.query.q.trim() : ''))

const recommendedCareers = computed(() =>
  careerRecommendation.value?.recommended_careers?.length
    ? careerRecommendation.value.recommended_careers
    : searchResults.value.slice(0, 3),
)

const skillGaps = computed(() =>
  careerRecommendation.value?.skill_gaps?.length
    ? careerRecommendation.value.skill_gaps.slice(0, 3)
    : [],
)

const pathStages = computed(() => careerRecommendation.value?.career_paths?.[0]?.stages || [])

const conversationPrompts = [
  '오늘 어떤 순서로 했을 때 편했어?',
  '그림을 보고 하니까 뭐가 쉬웠어?',
  '다음에는 어떤 도구를 써보고 싶어?',
  '도움이 필요할 때 어떤 말로 알려줄까?',
]

function listText(items = []) {
  return items.length ? items.slice(0, 4).join(', ') : '정보 없음'
}

function percentText(score) {
  if (typeof score !== 'number') return '-'
  return `${Math.round(score * 100)}%`
}

async function recommendCareer() {
  loading.value = true
  try {
    careerRecommendation.value = await getCareerRecommendation({
      current_skills: currentSkills.value,
      grade: '초등학교 3학년',
      disability_type: studentStore.student?.disability_type || undefined,
      interests: interests.value.split(',').map((item) => item.trim()).filter(Boolean),
    })
  } finally {
    loading.value = false
  }
}

async function refreshCareerSearch() {
  const response = await searchCareer(currentSkills.value, { current_skills: currentSkills.value, k: 3 })
  searchResults.value = response.results || []
}

watch(routeSearchQuery, async (query) => {
  if (!query || query === currentSkills.value) return
  currentSkills.value = query
  await refreshCareerSearch()
  await recommendCareer()
})

onMounted(async () => {
  if (routeSearchQuery.value) currentSkills.value = routeSearchQuery.value
  await refreshCareerSearch()
})
</script>
