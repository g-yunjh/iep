<template>
  <section class="rounded-[24px] border border-white/80 bg-white/90 p-5 shadow-sm">
    <div class="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">Student Profile</p>
        <h2 class="mt-2 text-2xl font-black tracking-normal text-slate-950">
          {{ student?.name || '이지훈' }}
        </h2>
        <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          {{ student?.current_level || '현재 수준을 입력하면 추천과 요약이 더 정확해집니다.' }}
        </p>
      </div>

      <div class="grid gap-2 sm:grid-cols-2 lg:min-w-[420px]">
        <div class="rounded-[16px] border border-slate-100 bg-slate-50 p-3">
          <p class="text-xs font-semibold text-slate-400">장애 유형</p>
          <p class="mt-1 text-sm font-bold text-slate-800">{{ student?.disability_type || '-' }}</p>
        </div>
        <div class="rounded-[16px] border border-slate-100 bg-slate-50 p-3">
          <p class="text-xs font-semibold text-slate-400">행동 특성</p>
          <p class="mt-1 text-sm font-bold text-slate-800">{{ student?.behavioral_traits || '-' }}</p>
        </div>
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
