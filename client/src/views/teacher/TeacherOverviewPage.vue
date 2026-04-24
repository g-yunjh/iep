<template>
  <div class="space-y-6">
    <StudentProfileHeader :student="studentStore.student" />

    <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <h3 class="text-lg font-semibold text-slate-800 mb-4">학생 프로필 카드</h3>
      <div class="grid sm:grid-cols-2 gap-3 text-sm">
        <div class="rounded-xl bg-slate-50 p-3">
          <p class="text-slate-500">이름</p>
          <p class="font-semibold text-slate-800">{{ studentStore.student?.name }}</p>
        </div>
        <div class="rounded-xl bg-slate-50 p-3">
          <p class="text-slate-500">장애 유형</p>
          <p class="font-semibold text-slate-800">{{ studentStore.student?.disability_type || '-' }}</p>
        </div>
        <div class="rounded-xl bg-slate-50 p-3">
          <p class="text-slate-500">ADHD 여부</p>
          <p class="font-semibold text-slate-800">{{ hasAdhd ? '예' : '아니오' }}</p>
        </div>
        <div class="rounded-xl bg-slate-50 p-3">
          <p class="text-slate-500">중복 진단</p>
          <p class="font-semibold text-slate-800">{{ studentStore.student?.additional_diagnoses || '-' }}</p>
        </div>
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <span class="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-medium">
          {{ studentStore.student?.current_level }}
        </span>
        <span class="px-3 py-1 bg-rose-100 text-rose-700 rounded-full text-xs font-medium">
          {{ studentStore.student?.behavioral_traits }}
        </span>
      </div>
    </article>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StudentProfileHeader from '../../components/StudentProfileHeader.vue'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()
const hasAdhd = computed(() =>
  (studentStore.student?.additional_diagnoses || '').toLowerCase().includes('adhd'),
)
</script>
