<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Skill Context</p>
            <h2 class="panel-title">현재 역량 입력</h2>
            <p class="panel-subtitle">학생의 강점과 관심 단서를 직업 후보 검색에 연결합니다.</p>
          </div>
          <div class="panel-icon">
            <Sparkles />
          </div>
        </div>

        <label class="spaced">
          <span class="section-label">현재 역량</span>
          <textarea v-model="currentSkills" class="textarea-like spaced-sm" rows="6" />
        </label>

        <label class="spaced-sm">
          <span class="section-label">관심 활동</span>
          <input v-model="interestText" class="input-like spaced-sm" type="text" />
        </label>

        <div class="button-row spaced">
          <button class="btn" type="button" :disabled="loadingSearch" @click="searchCareers">
            {{ loadingSearch ? '검색 중' : '직업 검색' }}
          </button>
          <button class="btn ghost" type="button" :disabled="loadingRecommendation" @click="createRecommendation">
            {{ loadingRecommendation ? '분석 중' : '경로 분석' }}
          </button>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Student</p>
        <h2 class="panel-title">{{ studentStore.student?.name || '나의 아이' }}</h2>
        <div class="list-stack spaced">
          <div v-for="item in profileRows" :key="item.label" class="card-row">
            <strong>{{ item.label }}</strong>
            <span>{{ item.value }}</span>
          </div>
        </div>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Career Search</p>
            <h2 class="panel-title">직업 후보</h2>
            <p class="panel-subtitle">검색 결과를 선택하면 역량 격차와 수업 연결점을 봅니다.</p>
          </div>
          <span class="badge primary">GET /rag/career-search</span>
        </div>

        <div v-if="careerResults.length" class="list-stack spaced">
          <button
            v-for="(career, index) in careerResults"
            :key="`${career.job_title}-${index}`"
            type="button"
            :class="['career-result', selectedIndex === index && 'is-selected']"
            @click="selectedIndex = index"
          >
            <div>
              <strong>{{ career.job_title || '직업 정보 없음' }}</strong>
              <p>필요 역량: {{ listText(career.required_skills) }}</p>
            </div>
            <span class="mono">{{ scoreText(career.score) }}</span>
          </button>
        </div>

        <div v-else class="empty-state spaced">
          <strong>직업 후보가 없습니다.</strong>
          <p>현재 역량을 입력하고 직업 검색을 실행하세요.</p>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Skill Gap</p>
            <h2 class="panel-title">수업으로 키울 역량</h2>
          </div>
          <span class="badge soft">{{ selectedCareer?.job_title || '대기' }}</span>
        </div>

        <div class="strategy-grid spaced">
          <article v-for="gap in selectedGaps" :key="gap" class="strategy-card">
            <strong>{{ gap }}</strong>
            <p>직무 탐색 전에 수업·가정 활동으로 작게 연습할 수 있는 역량입니다.</p>
          </article>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel dark">
        <p class="eyebrow">Recommendation API</p>
        <h2 class="panel-title">강점 기반 경로</h2>
        <p class="panel-subtitle">
          경로 분석을 실행하면 추천 직업, 격차, 단계별 커리어 경로를 서버에서 받아옵니다.
        </p>
      </section>

      <section class="panel">
        <p class="eyebrow">Recommended Careers</p>
        <h2 class="panel-title">추천 직업</h2>
        <div class="list-stack spaced">
          <article v-for="career in recommendedCareers" :key="career.job_title" class="mini-card">
            <strong>{{ career.job_title }}</strong>
            <p>{{ career.category || '기타' }} · 적합도 {{ percentText(career.match_score ?? career.score) }}</p>
          </article>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Career Path</p>
        <h2 class="panel-title">단계별 경로</h2>
        <div v-if="pathStages.length" class="list-stack spaced">
          <div v-for="stage in pathStages" :key="`${stage.stage}-${stage.description}`" class="path-stage">
            <strong>{{ stage.stage }}</strong>
            <p>{{ stage.description }}</p>
          </div>
        </div>
        <div v-else class="empty-state spaced">
          <strong>경로 대기</strong>
          <p>경로 분석 버튼을 누르면 현재 학습에서 직무 체험까지의 단계가 표시됩니다.</p>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Sparkles } from 'lucide-vue-next'
import { getCareerRecommendation, searchCareer } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()

const currentSkills = ref('손작업과 순서 기억이 안정적이며, 시각 자료를 활용한 활동에 오래 참여합니다.')
const interestText = ref('그림 카드, 요리 활동, 반복 루틴')
const careerResults = ref([])
const careerRecommendation = ref(null)
const selectedIndex = ref(0)
const loadingSearch = ref(false)
const loadingRecommendation = ref(false)

const profileRows = computed(() => [
  { label: '현재 수준', value: studentStore.student?.current_level || '입력 대기' },
  { label: '장애 유형', value: studentStore.student?.disability_type || '정보 없음' },
  { label: '행동 특성', value: studentStore.student?.behavioral_traits || '관찰 필요' },
])

const selectedCareer = computed(() => careerResults.value[selectedIndex.value] || null)
const selectedGaps = computed(() => {
  const gapSkills =
    selectedCareer.value?.skill_alignment?.missing_skills ||
    selectedCareer.value?.skill_gap?.gap_skills ||
    []
  return gapSkills.length ? gapSkills : ['도구 활용', '작업 순서 언어화', '상황에 맞는 도움 요청']
})

const recommendedCareers = computed(() =>
  careerRecommendation.value?.recommended_careers?.length
    ? careerRecommendation.value.recommended_careers
    : careerResults.value.slice(0, 3),
)

const pathStages = computed(() => careerRecommendation.value?.career_paths?.[0]?.stages || [])

function listText(items = []) {
  return items.length ? items.slice(0, 4).join(', ') : '정보 없음'
}

function scoreText(score) {
  if (typeof score !== 'number') return '-'
  return score.toFixed(2)
}

function percentText(score) {
  if (typeof score !== 'number') return '-'
  return `${Math.round(score * 100)}%`
}

async function searchCareers() {
  loadingSearch.value = true
  try {
    const response = await searchCareer(currentSkills.value || '손작업과 시각 자료', {
      current_skills: currentSkills.value,
      k: 5,
    })
    careerResults.value = response.results || []
    selectedIndex.value = 0
  } finally {
    loadingSearch.value = false
  }
}

async function createRecommendation() {
  loadingRecommendation.value = true
  try {
    careerRecommendation.value = await getCareerRecommendation({
      current_skills: currentSkills.value,
      grade: '초등학교 3학년',
      disability_type: studentStore.student?.disability_type || undefined,
      interests: interestText.value.split(',').map((item) => item.trim()).filter(Boolean),
    })
  } finally {
    loadingRecommendation.value = false
  }
}

onMounted(async () => {
  await searchCareers()
})
</script>
