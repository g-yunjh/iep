<template>
  <div class="space-y-6">
    <StudentProfileHeader :student="student" />

    <section class="grid lg:grid-cols-3 gap-4">
      <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm lg:col-span-2">
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
    </section>

    <section class="grid lg:grid-cols-2 gap-6">
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
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import StudentProfileHeader from '../components/StudentProfileHeader.vue'
import { getSchoolLife, searchCareer } from '../api'

const props = defineProps({
  student: {
    type: Object,
    default: null,
  },
  updateTraits: {
    type: Function,
    required: true,
  },
})

const schoolLife = ref({})
const savingTraits = ref(false)
const careerInterest = ref('')
const careerResults = ref([])

const traitForm = reactive({
  current_level: '',
  disability_type: '',
  additional_diagnoses: '',
  behavioral_traits: '',
})

const prepList = computed(() => (schoolLife.value.tomorrow_prep || []).join(', '))

watch(
  () => props.student,
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
  await props.updateTraits({ ...traitForm })
  savingTraits.value = false
}

async function onSearchCareer() {
  const result = await searchCareer(careerInterest.value || '창작 활동과 손작업')
  careerResults.value = result.results || []
}

onMounted(async () => {
  schoolLife.value = await getSchoolLife()
  const result = await searchCareer('시각 활동과 의사소통')
  careerResults.value = result.results || []
})
</script>
