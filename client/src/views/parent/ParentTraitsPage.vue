<template>
  <div class="space-y-6">
    <StudentProfileHeader :student="studentStore.student" />

    <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <h3 class="text-lg font-semibold text-slate-800 mb-3">아이 특성 관리</h3>
      <div class="space-y-3">
        <label class="block">
          <span class="text-xs text-slate-500">현재 수준</span>
          <input
            v-model="traitForm.current_level"
            type="text"
            class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </label>
        <label class="block">
          <span class="text-xs text-slate-500">장애 유형</span>
          <input
            v-model="traitForm.disability_type"
            type="text"
            class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </label>
        <label class="block">
          <span class="text-xs text-slate-500">장애 중복 정보</span>
          <input
            v-model="traitForm.additional_diagnoses"
            type="text"
            class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            placeholder="예: ADHD"
          />
        </label>
        <label class="block">
          <span class="text-xs text-slate-500">행동 트리거/행동 특성</span>
          <textarea
            v-model="traitForm.behavioral_traits"
            rows="4"
            class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            placeholder="예: 어려운 걸 보면 화를 냄"
          />
        </label>
        <button
          class="w-full px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:bg-slate-400"
          :disabled="savingTraits"
          @click="onSaveTraits"
        >
          {{ savingTraits ? '저장 중...' : '특성 저장' }}
        </button>
      </div>
    </article>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import StudentProfileHeader from '../../components/StudentProfileHeader.vue'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore, updateTraits } = useStudentStore()
const savingTraits = ref(false)

const traitForm = reactive({
  current_level: '',
  disability_type: '',
  additional_diagnoses: '',
  behavioral_traits: '',
})

watch(
  () => studentStore.student,
  (student) => {
    traitForm.current_level = student?.current_level || ''
    traitForm.disability_type = student?.disability_type || ''
    traitForm.additional_diagnoses = student?.additional_diagnoses || ''
    traitForm.behavioral_traits = student?.behavioral_traits || ''
  },
  { immediate: true },
)

async function onSaveTraits() {
  savingTraits.value = true
  await updateTraits({ ...traitForm })
  savingTraits.value = false
}
</script>
