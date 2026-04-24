<template>
  <div class="space-y-6">
    <StudentProfileHeader :student="studentStore.student" />

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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import StudentProfileHeader from '../../components/StudentProfileHeader.vue'
import { searchCurriculum } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()
const curriculumQuery = ref('')
const curriculumResults = ref([])

async function onSearchCurriculum() {
  const result = await searchCurriculum(curriculumQuery.value || '기초 학습 집중')
  curriculumResults.value = result.results || []
}

onMounted(onSearchCurriculum)
</script>
