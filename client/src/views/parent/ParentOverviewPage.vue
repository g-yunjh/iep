<template>
  <div class="space-y-6">
    <StudentProfileHeader :student="studentStore.student" />

    <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <h3 class="text-lg font-semibold text-slate-800 mb-3">학교 생활 요약</h3>
      <div class="grid sm:grid-cols-2 gap-3">
        <div class="rounded-xl bg-slate-50 p-3">
          <p class="text-xs text-slate-500">점심 급식</p>
          <p class="text-sm text-slate-800 mt-1">{{ schoolLife.meal_info?.lunch || '-' }}</p>
        </div>
        <div class="rounded-xl bg-slate-50 p-3">
          <p class="text-xs text-slate-500">간식</p>
          <p class="text-sm text-slate-800 mt-1">{{ schoolLife.meal_info?.snack || '-' }}</p>
        </div>
        <div class="rounded-xl bg-slate-50 p-3">
          <p class="text-xs text-slate-500">하교 시간</p>
          <p class="text-sm text-slate-800 mt-1">{{ schoolLife.dismissal_time || '-' }}</p>
        </div>
        <div class="rounded-xl bg-slate-50 p-3">
          <p class="text-xs text-slate-500">내일 준비물</p>
          <p class="text-sm text-slate-800 mt-1">{{ prepList }}</p>
        </div>
      </div>
    </article>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StudentProfileHeader from '../../components/StudentProfileHeader.vue'
import { getSchoolLife } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()
const schoolLife = ref({})
const prepList = computed(() => (schoolLife.value.tomorrow_prep || []).join(', '))

onMounted(async () => {
  schoolLife.value = await getSchoolLife()
})
</script>
