<template>
  <div class="space-y-6">
    <StudentProfileHeader :student="student" />

    <section class="grid lg:grid-cols-2 gap-6">
      <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-800 mb-4">학생 프로필 카드</h3>
        <div class="grid sm:grid-cols-2 gap-3 text-sm">
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-slate-500">이름</p>
            <p class="font-semibold text-slate-800">{{ student?.name }}</p>
          </div>
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-slate-500">장애 유형</p>
            <p class="font-semibold text-slate-800">{{ student?.disability_type || '-' }}</p>
          </div>
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-slate-500">ADHD 여부</p>
            <p class="font-semibold text-slate-800">{{ hasAdhd ? '예' : '아니오' }}</p>
          </div>
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-slate-500">중복 진단</p>
            <p class="font-semibold text-slate-800">{{ student?.additional_diagnoses || '-' }}</p>
          </div>
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          <span class="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-medium">
            {{ student?.current_level }}
          </span>
          <span class="px-3 py-1 bg-rose-100 text-rose-700 rounded-full text-xs font-medium">
            {{ student?.behavioral_traits }}
          </span>
        </div>
      </article>

      <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-800 mb-3">AI 스캐폴딩 도구</h3>
        <textarea
          v-model="observationText"
          rows="5"
          class="w-full rounded-xl border border-slate-300 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          placeholder="오늘의 관찰 기록을 작성하세요."
        />
        <button
          class="mt-3 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:bg-slate-400"
          :disabled="isScaffoldLoading || !observationText.trim()"
          @click="onRecommendScaffolding"
        >
          {{ isScaffoldLoading ? '분석 중...' : 'AI 추천 받기' }}
        </button>

        <div v-if="scaffoldingResult" class="mt-4 space-y-2">
          <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-3">
            <p class="text-xs text-indigo-500">추천 레벨</p>
            <p class="font-semibold text-indigo-800">{{ scaffoldingResult.recommended_level }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 p-3">
            <p class="text-xs text-slate-500">지도 전략</p>
            <ul class="text-sm text-slate-700 list-disc pl-5 mt-1">
              <li v-for="strategy in scaffoldingResult.scaffolding_details?.strategies || []" :key="strategy">
                {{ strategy }}
              </li>
            </ul>
          </div>
          <div class="rounded-xl border border-slate-200 p-3">
            <p class="text-xs text-slate-500">활동</p>
            <p class="text-sm text-slate-700">
              {{ scaffoldingResult.scaffolding_details?.activities?.[0]?.name || '추천 활동 없음' }}
            </p>
          </div>
        </div>
      </article>
    </section>

    <section class="grid lg:grid-cols-2 gap-6">
      <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-800 mb-3">성취기준 검색</h3>
        <div class="flex gap-2">
          <input
            v-model="curriculumQuery"
            type="text"
            class="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            placeholder="필요한 교육 정보를 검색하세요."
          />
          <button
            class="px-4 py-2 rounded-xl bg-slate-800 text-white text-sm hover:bg-slate-900"
            @click="onSearchCurriculum"
          >
            검색
          </button>
        </div>
        <ul class="mt-4 space-y-2">
          <li
            v-for="(item, index) in curriculumResults"
            :key="`${item.content}-${index}`"
            class="rounded-xl border border-slate-200 p-3"
          >
            <p class="text-sm text-slate-700">{{ item.content }}</p>
            <p class="text-xs text-slate-500 mt-1">
              {{ item.metadata?.subject || '-' }} / {{ item.metadata?.grade || '-' }}
            </p>
          </li>
        </ul>
      </article>

      <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-800 mb-3">성장 타임라인</h3>
        <ul class="space-y-3">
          <li
            v-for="feedback in progressFeedbacks"
            :key="feedback.id"
            class="relative pl-4 border-l-2 border-indigo-200"
          >
            <p class="text-xs text-slate-500">{{ formatDate(feedback.created_at) }}</p>
            <p class="text-sm text-slate-700 mt-1">{{ feedback.teacher_description }}</p>
            <p class="text-xs text-indigo-600 mt-1">
              분석 레벨: {{ feedback.llm_analysis?.detected_level || '-' }}
            </p>
          </li>
        </ul>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StudentProfileHeader from '../components/StudentProfileHeader.vue'
import {
  getScaffoldingRecommendation,
  searchCurriculum,
  getStudentProgress,
} from '../api'

const props = defineProps({
  student: {
    type: Object,
    default: null,
  },
})

const observationText = ref('')
const isScaffoldLoading = ref(false)
const scaffoldingResult = ref(null)

const curriculumQuery = ref('')
const curriculumResults = ref([])

const progressFeedbacks = ref([])

const hasAdhd = computed(() =>
  (props.student?.additional_diagnoses || '').toLowerCase().includes('adhd'),
)

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('ko-KR')
}

async function onRecommendScaffolding() {
  isScaffoldLoading.value = true
  scaffoldingResult.value = await getScaffoldingRecommendation({
    grade: '초등학교 3학년',
    subject: '통합',
    teacher_description: observationText.value,
  })
  isScaffoldLoading.value = false
}

async function onSearchCurriculum() {
  const result = await searchCurriculum(curriculumQuery.value || '기초 학습 집중')
  curriculumResults.value = result.results || []
}

onMounted(async () => {
  const progressData = await getStudentProgress()
  progressFeedbacks.value = progressData.feedbacks || []
  const searchResult = await searchCurriculum('읽기와 수학 기초')
  curriculumResults.value = searchResult.results || []
})
</script>
