<template>
  <main class="min-h-screen bg-slate-50 p-6 md:p-8">
    <div class="max-w-7xl mx-auto space-y-6">
      <header>
        <div>
          <h1 class="text-2xl md:text-3xl font-bold text-slate-800">나의 아이 대시보드</h1>
          <p class="text-sm text-slate-500 mt-1">역할 분리형 단일 학생 지원 앱</p>
        </div>
      </header>

      <nav class="flex flex-wrap gap-2">
        <RouterLink
          v-for="item in roleLinks"
          :key="item.to"
          :to="item.to"
          class="px-3 py-2 rounded-xl text-sm font-medium border"
          :class="route.path === item.to ? 'bg-white text-indigo-700 border-indigo-200' : 'text-slate-600 border-slate-200'"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <p v-if="studentStore.error" class="text-sm text-rose-600">{{ studentStore.error }}</p>
      <RouterView />
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useStudentStore } from './composables/useStudentStore'

const route = useRoute()
const { state: studentStore, loadStudent } = useStudentStore()

const isTeacherRoute = computed(() => route.path.startsWith('/teacher'))
const roleLinks = computed(() =>
  isTeacherRoute.value
    ? [
        { to: '/teacher/overview', label: '프로필' },
        { to: '/teacher/scaffolding', label: 'AI 스캐폴딩' },
        { to: '/teacher/curriculum', label: '성취기준 검색' },
        { to: '/teacher/progress', label: '성장 타임라인' },
      ]
    : [
        { to: '/parent/overview', label: '학교 생활 요약' },
        { to: '/parent/traits', label: '특성 관리' },
        { to: '/parent/career', label: '미래 진로 탐색' },
      ],
)

onMounted(() => {
  loadStudent()
})
</script>
