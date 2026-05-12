<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">School Life</p>
            <h2 class="panel-title">학교생활 요약</h2>
            <p class="panel-subtitle">NEIS 연동 정보와 fallback 데이터를 같은 화면에서 표시합니다.</p>
          </div>
          <div class="panel-icon">
            <School />
          </div>
        </div>

        <button class="btn spaced" type="button" :disabled="loading" @click="loadSchoolLife">
          {{ loading ? '불러오는 중' : '정보 새로고침' }}
        </button>
      </section>

      <section class="panel dark">
        <p class="eyebrow">Plain View</p>
        <h2 class="panel-title">학부모 화면 기준</h2>
        <p class="panel-subtitle">
          급식, 시간표, 하교, 준비물처럼 오늘 행동에 필요한 정보만 전면에 둡니다.
        </p>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Today Cards</p>
            <h2 class="panel-title">오늘 확인</h2>
            <p class="panel-subtitle">아침에 가장 먼저 볼 정보입니다.</p>
          </div>
          <span class="badge primary">GET /student/school-life</span>
        </div>

        <div class="metric-grid spaced">
          <div v-for="card in mainCards" :key="card.label" class="metric-card">
            <p>{{ card.label }}</p>
            <strong>{{ card.value }}</strong>
            <small>{{ card.caption }}</small>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Timetable</p>
            <h2 class="panel-title">오늘 시간표</h2>
          </div>
          <span class="badge soft">{{ timetable.length }}교시</span>
        </div>

        <div class="list-stack spaced">
          <div v-for="(subject, index) in timetable" :key="`${subject}-${index}`" class="home-step">
            <span class="step-dot">{{ index + 1 }}</span>
            <strong>{{ `${index + 1}교시` }}</strong>
            <p>{{ subject }}</p>
          </div>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Lunch</p>
            <h2 class="panel-title">급식</h2>
          </div>
          <div class="panel-icon">
            <Soup />
          </div>
        </div>
        <div class="callout spaced">
          <strong>{{ lunch }}</strong>
          <p>아이에게 익숙하지 않은 메뉴가 있으면 미리 짧게 알려주세요.</p>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Tomorrow Prep</p>
        <h2 class="panel-title">내일 준비</h2>
        <div class="chip-row spaced">
          <span v-for="item in prepList" :key="item" class="chip active">{{ item }}</span>
        </div>
      </section>

      <section class="panel">
        <p class="eyebrow">Calendar</p>
        <h2 class="panel-title">학사 일정</h2>
        <div class="mini-card spaced">
          <strong>오늘 일정</strong>
          <p>{{ schoolLife.academic_calendar || '일정 없음' }}</p>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { School, Soup } from 'lucide-vue-next'
import { getSchoolLife } from '../../api'

const loading = ref(false)
const schoolLife = ref({})

const lunch = computed(() => schoolLife.value.lunch_menu || '정보 없음')
const timetable = computed(() => {
  const items = schoolLife.value.today_timetable || []
  return items.length ? items : ['국어', '수학', '미술']
})
const prepList = computed(() => schoolLife.value.tomorrow_prep || ['체육복', '색연필', '국어 공책'])

const mainCards = computed(() => [
  { label: '점심', value: shortText(lunch.value), caption: '급식' },
  { label: '하교', value: schoolLife.value.dismissal_time || '정보 없음', caption: '예상 시간' },
  { label: '일정', value: shortText(schoolLife.value.academic_calendar || '일정 없음'), caption: '오늘' },
  { label: '준비', value: `${prepList.value.length}개`, caption: prepList.value.join(', ') },
])

function shortText(value = '') {
  return value.length > 8 ? `${value.slice(0, 8)}...` : value
}

async function loadSchoolLife() {
  loading.value = true
  try {
    schoolLife.value = await getSchoolLife()
  } finally {
    loading.value = false
  }
}

onMounted(loadSchoolLife)
</script>
