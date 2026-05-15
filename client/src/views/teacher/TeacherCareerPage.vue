<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Skill Context</p>
            <h2 class="panel-title">현재 역량 입력</h2>
            <p class="panel-subtitle">강점과 관심 활동을 입력하면 AI가 맞춤 진로를 추천합니다.</p>
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
          <input v-model="interestText" class="input-like spaced-sm" type="text" placeholder="쉼표로 구분" />
        </label>

        <div class="button-row spaced">
          <button class="btn" type="button" :disabled="loading" @click="createRecommendation">
            {{ loading ? '분석 중' : '진로 추천 받기' }}
          </button>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Student</p>
        <h2 class="panel-title">학생 맥락</h2>
        <div class="list-stack spaced">
          <div v-for="item in profileRows" :key="item.label" class="card-row">
            <strong>{{ item.label }}</strong>
            <span>{{ item.value }}</span>
          </div>
        </div>
      </section>

      <section class="panel dark">
        <p class="eyebrow">Career Recommendation</p>
        <h2 class="panel-title">강점 기반 진로</h2>
        <p class="panel-subtitle">
          추천 직업, 역량 격차, 단계별 경로를 한 번에 받습니다. 수업·상담에 바로 연결할 수 있도록 정리했습니다.
        </p>
        <span class="badge primary spaced-sm">POST /rag/career-recommendation</span>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Recommended Careers</p>
            <h2 class="panel-title">추천 직업</h2>
            <p class="panel-subtitle">직업을 선택하면 오른쪽에서 격차와 경로를 확인합니다.</p>
          </div>
          <span v-if="recommendedCareers.length" class="badge soft">{{ recommendedCareers.length }}건</span>
        </div>

        <div v-if="loading && !recommendedCareers.length" class="empty-state spaced">
          <strong>진로 추천을 불러오는 중입니다.</strong>
        </div>

        <div v-else-if="recommendedCareers.length" class="list-stack spaced">
          <button
            v-for="(career, index) in recommendedCareers"
            :key="career.job_title"
            type="button"
            :class="['career-result', selectedIndex === index && 'is-selected']"
            @click="selectedIndex = index"
          >
            <div>
              <strong>{{ career.job_title }}</strong>
              <p>{{ career.category || '기타' }}</p>
            </div>
            <span class="mono">{{ percentText(career.match_score) }}</span>
          </button>
        </div>

        <div v-else class="empty-state spaced">
          <strong>진로 추천 결과 없음</strong>
          <p>역량과 관심 활동을 입력한 뒤 진로 추천을 실행해 보세요.</p>
          <button class="btn ghost spaced-sm" type="button" :disabled="loading" @click="createRecommendation">
            {{ loading ? '불러오는 중' : '다시 요청' }}
          </button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Development</p>
            <h2 class="panel-title">키우기 제안</h2>
          </div>
          <span class="badge soft">{{ selectedCareerTitle }}</span>
        </div>

        <div v-if="developmentSuggestions.length" class="list-stack spaced">
          <article v-for="suggestion in developmentSuggestions" :key="suggestion" class="strategy-card">
            <p>{{ suggestion }}</p>
          </article>
        </div>
        <div v-else class="empty-state spaced">
          <strong>제안 대기</strong>
          <p>진로 추천을 실행하면 선택한 직업에 맞는 발달 제안이 표시됩니다.</p>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Skill Gap</p>
            <h2 class="panel-title">수업으로 키울 역량</h2>
          </div>
          <span class="badge soft">{{ selectedCareerTitle }}</span>
        </div>

        <div v-if="selectedGapSkills.length" class="strategy-grid spaced">
          <article v-for="gap in selectedGapSkills" :key="gap" class="strategy-card">
            <strong>{{ gap }}</strong>
            <p>직무 탐색 전에 수업·가정 활동으로 작게 연습할 수 있는 역량입니다.</p>
          </article>
        </div>
        <div v-else class="empty-state spaced">
          <strong>격차 정보 없음</strong>
          <p>추천 직업을 선택하거나 진로 추천을 다시 실행해 보세요.</p>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Career Path</p>
        <h2 class="panel-title">단계별 경로</h2>
        <p v-if="pathTarget" class="panel-subtitle text-sm">{{ pathTarget }} · {{ pathTimeline }}</p>

        <div v-if="pathStages.length" class="list-stack spaced">
          <div
            v-for="(stage, index) in pathStages"
            :key="`${stage.stage}-${stage.focus || ''}-${stage.description}`"
            class="path-stage"
          >
            <span class="step-dot">{{ index + 1 }}</span>
            <strong>{{ stage.stage }}</strong>
            <p v-if="stage.focus" class="text-sm text-[var(--color-text-secondary)]">{{ stage.focus }}</p>
            <p>{{ stage.description }}</p>
          </div>
        </div>
        <div v-else class="empty-state spaced">
          <strong>경로 대기</strong>
          <p>진로 추천을 실행하면 현재 학습에서 직무 체험까지의 단계가 표시됩니다.</p>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Sparkles } from 'lucide-vue-next'
import { getCareerRecommendation } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()

const currentSkills = ref('손작업과 순서 기억이 안정적이며, 시각 자료를 활용한 활동에 오래 참여합니다.')
const interestText = ref('그림 카드, 요리 활동, 반복 루틴')
const careerRecommendation = ref(null)
const selectedIndex = ref(0)
const loading = ref(false)

const profileRows = computed(() => [
  { label: '현재 수준', value: studentStore.student?.current_level || '입력 대기' },
  { label: '장애 유형', value: studentStore.student?.disability_type || '정보 없음' },
  { label: '행동 특성', value: studentStore.student?.behavioral_traits || '관찰 필요' },
])

const recommendedCareers = computed(() => careerRecommendation.value?.recommended_careers || [])

const selectedCareer = computed(() => recommendedCareers.value[selectedIndex.value] || null)

const selectedCareerTitle = computed(() => selectedCareer.value?.job_title || '대기')

const selectedSkillGap = computed(() => {
  const job = selectedCareer.value?.job_title
  if (!job || !careerRecommendation.value?.skill_gaps?.length) return null
  return (
    careerRecommendation.value.skill_gaps.find((g) => g.job_title === job) ||
    careerRecommendation.value.skill_gaps[0]
  )
})

const selectedGapSkills = computed(() => selectedSkillGap.value?.gap_skills || [])

const developmentSuggestions = computed(() => selectedSkillGap.value?.development_suggestions || [])

const selectedCareerPath = computed(() => {
  const job = selectedCareer.value?.job_title
  const paths = careerRecommendation.value?.career_paths || []
  if (!paths.length) return null
  if (!job) return paths[0]
  return paths.find((p) => p.target_career === job) || paths[0]
})

const pathStages = computed(() => selectedCareerPath.value?.stages || [])

const pathTarget = computed(() => selectedCareerPath.value?.target_career || '')

const pathTimeline = computed(() => selectedCareerPath.value?.estimated_timeline || '')

function percentText(score) {
  if (typeof score !== 'number') return '-'
  return `${Math.round(score * 100)}%`
}

async function createRecommendation() {
  loading.value = true
  try {
    careerRecommendation.value = await getCareerRecommendation({
      current_skills: currentSkills.value,
      grade: '초등학교 3학년',
      disability_type: studentStore.student?.disability_type || undefined,
      interests: interestText.value.split(',').map((item) => item.trim()).filter(Boolean),
    })
    selectedIndex.value = 0
  } finally {
    loading.value = false
  }
}

watch(recommendedCareers, (list) => {
  if (selectedIndex.value >= list.length) selectedIndex.value = 0
})

onMounted(createRecommendation)
</script>
