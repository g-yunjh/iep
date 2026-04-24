<template>
  <div class="space-y-6">
    <StudentProfileHeader :student="studentStore.student" />

    <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <h3 class="text-lg font-semibold text-slate-800 mb-3">미래 진로 탐색</h3>
      <div class="flex gap-2">
        <input
          v-model="careerInterest"
          type="text"
          class="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          placeholder="관심 분야를 입력하세요."
        />
        <button
          class="px-4 py-2 rounded-xl bg-slate-800 text-white text-sm hover:bg-slate-900"
          @click="onSearchCareer"
        >
          탐색
        </button>
      </div>

      <ul class="mt-4 space-y-3">
        <li
          v-for="career in careerResults"
          :key="career.job_title"
          class="rounded-xl border border-slate-200 p-3"
        >
          <p class="text-sm font-semibold text-slate-800">{{ career.job_title }}</p>
          <p class="text-xs text-slate-500 mt-1">필요 역량: {{ (career.required_skills || []).join(', ') }}</p>
          <p class="text-xs text-rose-600 mt-1">
            Skill Gap: {{ (career.skill_gap?.gap_skills || []).join(', ') || '없음' }}
          </p>
        </li>
      </ul>
    </article>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import StudentProfileHeader from '../../components/StudentProfileHeader.vue'
import { searchCareer } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()
const careerInterest = ref('')
const careerResults = ref([])

async function onSearchCareer() {
  const result = await searchCareer(careerInterest.value || '창작 활동과 손작업')
  careerResults.value = result.results || []
}

onMounted(async () => {
  const result = await searchCareer('시각 활동과 의사소통')
  careerResults.value = result.results || []
})
</script>
