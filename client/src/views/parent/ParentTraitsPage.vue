<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Child Profile</p>
            <h2 class="panel-title">아이 특성 관리</h2>
            <p class="panel-subtitle">저장된 정보는 교사용 추천 맥락에도 반영됩니다.</p>
          </div>
          <div class="panel-icon">
            <UserRoundCog />
          </div>
        </div>

        <div class="callout spaced">
          <strong>가정에서만 아는 단서가 중요합니다.</strong>
          <p>어려워하는 상황, 안정되는 방식, 좋아하는 활동을 짧게 적어두면 추천 품질이 좋아집니다.</p>
        </div>
      </section>

      <section class="panel dark">
        <p class="eyebrow">Backend</p>
        <h2 class="panel-title">저장 위치</h2>
        <p class="panel-subtitle">
          저장 버튼은 `PATCH /student`로 학생 프로필을 갱신합니다.
        </p>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Editable Fields</p>
            <h2 class="panel-title">프로필 입력</h2>
            <p class="panel-subtitle">민감한 진단명보다 실제 지원에 필요한 표현을 우선합니다.</p>
          </div>
          <span class="badge primary">PATCH /student</span>
        </div>

        <div class="mini-grid spaced">
          <label>
            <span class="section-label">이름</span>
            <input v-model="traitForm.name" class="input-like spaced-sm" type="text" />
          </label>
          <label>
            <span class="section-label">장애 유형</span>
            <input v-model="traitForm.disability_type" class="input-like spaced-sm" type="text" />
          </label>
        </div>

        <label class="spaced">
          <span class="section-label">현재 수준</span>
          <input v-model="traitForm.current_level" class="input-like spaced-sm" type="text" />
        </label>

        <label class="spaced-sm">
          <span class="section-label">중복 진단 또는 참고 정보</span>
          <input v-model="traitForm.additional_diagnoses" class="input-like spaced-sm" type="text" />
        </label>

        <label class="spaced-sm">
          <span class="section-label">행동 트리거와 안정되는 지원</span>
          <textarea v-model="traitForm.behavioral_traits" class="textarea-like spaced-sm" rows="7" />
        </label>

        <div class="button-row spaced">
          <button class="btn" type="button" :disabled="saving" @click="saveTraits">
            {{ saving ? '저장 중' : '특성 저장' }}
          </button>
          <span v-if="savedMessage" class="badge soft">{{ savedMessage }}</span>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel">
        <p class="eyebrow">Plain Summary</p>
        <h2 class="panel-title">입력 정보 요약</h2>
        <div class="list-stack spaced">
          <div v-for="item in summaryCards" :key="item.label" class="mini-card">
            <strong>{{ item.label }}</strong>
            <p>{{ item.value }}</p>
          </div>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Useful Examples</p>
        <h2 class="panel-title">좋은 입력 예시</h2>
        <div class="list-stack spaced">
          <div v-for="example in examples" :key="example" class="strategy-card">
            <strong>{{ example }}</strong>
            <p>교사와 가정이 같은 지원 전략을 쓰는 데 도움이 됩니다.</p>
          </div>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { UserRoundCog } from 'lucide-vue-next'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore, updateTraits } = useStudentStore()

const saving = ref(false)
const savedMessage = ref('')
const traitForm = reactive({
  name: '',
  current_level: '',
  disability_type: '',
  additional_diagnoses: '',
  behavioral_traits: '',
})

const summaryCards = computed(() => [
  { label: '현재 수준', value: traitForm.current_level || '현재 학습 수준을 입력해주세요.' },
  { label: '장애 유형', value: traitForm.disability_type || '지원 방식 선택의 기본 정보입니다.' },
  { label: '참고 정보', value: traitForm.additional_diagnoses || '추가 참고 정보가 있으면 입력해주세요.' },
  { label: '행동 특성', value: traitForm.behavioral_traits || '가정에서 보이는 반응을 적어주세요.' },
])

const examples = [
  '말로만 안내하면 멈추지만, 그림 순서를 보면 시작합니다.',
  '어려운 문제를 만나면 짜증을 내지만 선택지가 두 개면 고릅니다.',
  '반복되는 손작업과 정리 활동을 오래 유지합니다.',
]

watch(
  () => studentStore.student,
  (student) => {
    traitForm.name = student?.name || ''
    traitForm.current_level = student?.current_level || ''
    traitForm.disability_type = student?.disability_type || ''
    traitForm.additional_diagnoses = student?.additional_diagnoses || ''
    traitForm.behavioral_traits = student?.behavioral_traits || ''
  },
  { immediate: true },
)

async function saveTraits() {
  saving.value = true
  savedMessage.value = ''
  try {
    await updateTraits({ ...traitForm })
    savedMessage.value = '저장 완료'
  } finally {
    saving.value = false
  }
}
</script>
