<template>
  <section class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-sm text-slate-500">단일 학생 프로필</p>
        <h2 class="text-2xl font-bold text-slate-800 mt-1">{{ student?.name || '나의 아이' }}</h2>
      </div>
      <div class="flex flex-wrap gap-2">
        <span class="px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-semibold">
          현재 수준: {{ student?.current_level || '-' }}
        </span>
        <span class="px-3 py-1 rounded-full bg-amber-50 text-amber-700 text-xs font-semibold">
          행동 특성: {{ student?.behavioral_traits || '-' }}
        </span>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  student: {
    type: Object,
    default: null,
  },
})
</script>
