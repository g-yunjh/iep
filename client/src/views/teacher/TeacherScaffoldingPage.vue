<template>
  <div class="space-y-6">
    <StudentProfileHeader :student="studentStore.student" />

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
      </div>
    </article>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import StudentProfileHeader from '../../components/StudentProfileHeader.vue'
import { getScaffoldingRecommendation } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()
const observationText = ref('')
const isScaffoldLoading = ref(false)
const scaffoldingResult = ref(null)

async function onRecommendScaffolding() {
  isScaffoldLoading.value = true
  scaffoldingResult.value = await getScaffoldingRecommendation({
    grade: '초등학교 3학년',
    subject: '통합',
    teacher_description: observationText.value,
  })
  isScaffoldLoading.value = false
}
</script>
