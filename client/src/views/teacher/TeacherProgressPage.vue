<template>
  <div class="space-y-6">
    <StudentProfileHeader :student="studentStore.student" />

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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import StudentProfileHeader from '../../components/StudentProfileHeader.vue'
import { getStudentProgress } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()
const progressFeedbacks = ref([])

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('ko-KR')
}

onMounted(async () => {
  const progressData = await getStudentProgress()
  progressFeedbacks.value = progressData.feedbacks || []
})
</script>
