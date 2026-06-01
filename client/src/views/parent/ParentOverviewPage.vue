<template>
  <div class="page-grid">
    <aside class="column-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Today</p>
            <h2 class="panel-title">오늘의 학교생활</h2>
            <p class="panel-subtitle">오늘 학교에서 확인해야 할 일정과 준비 정보를 모아 보여줍니다.</p>
          </div>
          <div class="panel-icon">
            <CalendarDays />
          </div>
        </div>

        <div class="list-stack spaced">
          <div v-for="item in todayCards" :key="item.label" class="mini-card">
            <strong>{{ item.label }}</strong>
            <p>{{ item.value }}</p>
          </div>
        </div>

        <RouterLink to="/parent/school" class="btn ghost spaced-sm">학교생활 상세</RouterLink>
      </section>
    </aside>

    <main class="column-stack">
      <section class="panel elevated">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Home Support</p>
            <h2 class="panel-title">오늘 집에서 이어갈 일</h2>
            <p class="panel-subtitle">학교에서 효과가 있었던 지원을 집에서도 이어갈 수 있게 정리했습니다.</p>
          </div>
          <span class="badge primary">가정 지원</span>
        </div>

        <div class="callout spaced">
          <strong>{{ homeSupportTitle }}</strong>
          <p>{{ homeSupportCopy }}</p>
        </div>

        <div class="list-stack spaced">
          <div v-for="(step, index) in supportSteps" :key="step.title" class="home-step">
            <span class="step-dot">{{ index + 1 }}</span>
            <strong>{{ step.title }}</strong>
            <p>{{ step.copy }}</p>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Recent Feedback</p>
            <h2 class="panel-title">최근 변화</h2>
            <p class="panel-subtitle">{{ progressSummary }}</p>
          </div>
          <RouterLink to="/parent/traits" class="btn ghost">특성 수정</RouterLink>
        </div>

        <div class="strategy-grid spaced">
          <article v-for="(change, index) in recentChanges" :key="change" class="strategy-card strategy-card-labeled">
            <strong class="strategy-card-heading">변화 기록 {{ index + 1 }}</strong>
            <p class="strategy-card-copy">{{ change }}</p>
          </article>
        </div>
      </section>
    </main>

    <aside class="column-stack">
      <section class="panel dark">
        <p class="eyebrow">Parent View</p>
        <h2 class="panel-title">학부모에게 필요한 정보</h2>
        <p class="panel-subtitle">
          학교생활, 최근 변화, 집에서 이어갈 지원을 먼저 확인할 수 있도록 정리했습니다.
        </p>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">School Memo</p>
            <h2 class="panel-title">내일 준비</h2>
          </div>
          <div class="panel-icon">
            <Backpack />
          </div>
        </div>
        <div class="chip-row spaced">
          <span v-for="prep in prepList" :key="prep" class="chip active">{{ prep }}</span>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Career Talk</p>
            <h2 class="panel-title">진로 대화 힌트</h2>
          </div>
          <div class="panel-icon">
            <BriefcaseBusiness />
          </div>
        </div>
        <div class="callout spaced">
          <strong>“어떤 순서로 하면 편했어?”</strong>
          <p>좋아하는 활동을 직업 이름으로 바로 묻기보다, 강점이 드러난 순간을 대화로 이어갑니다.</p>
        </div>
        <RouterLink to="/parent/career" class="btn ghost spaced-sm">강점과 진로 보기</RouterLink>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Backpack, BriefcaseBusiness, CalendarDays } from 'lucide-vue-next'
import { getSchoolLife, getStudentProgress } from '../../api'
import { useStudentStore } from '../../composables/useStudentStore'

const { state: studentStore } = useStudentStore()

const schoolLife = ref({})
const progress = ref({ feedbacks: [] })

const todayCards = computed(() => [
  { label: '점심', value: schoolLife.value.lunch_menu || '정보 없음' },
  { label: '하교 시간', value: schoolLife.value.dismissal_time || '정보 없음' },
  { label: '오늘 시간표', value: (schoolLife.value.today_timetable || []).join(', ') || '정보 없음' },
  { label: '학사 일정', value: schoolLife.value.academic_calendar || '일정 없음' },
])

const profileRows = computed(() => [
  { label: '현재 수준', value: studentStore.student?.current_level || '정보 없음' },
  { label: '장애 유형', value: studentStore.student?.disability_type || '정보 없음' },
  { label: '특성', value: studentStore.student?.behavioral_traits || '가정 특성 입력 필요' },
])

const feedbacks = computed(() => progress.value.feedbacks || [])
const progressSummary = computed(() => {
  const count = feedbacks.value.length
  return count > 0 ? `총 ${count}개의 피드백 기록이 있습니다.` : '아직 누적된 피드백 기록이 없습니다.'
})
const recentChanges = computed(() => {
  if (!feedbacks.value.length) return []
  return feedbacks.value
    .slice(-4)
    .reverse()
    .map((feedback) => feedback.teacher_description || feedback.performance || '최근 기록이 저장되었습니다.')
})

const prepList = computed(() => schoolLife.value.tomorrow_prep || [])

const homeSupportTitle = computed(() =>
  feedbacks.value.length ? '최근 피드백을 확인해 주세요.' : '가정 지원 정보 대기',
)
const homeSupportCopy = computed(() =>
  feedbacks.value.length
    ? '저장된 피드백을 바탕으로 집에서 이어갈 지원을 확인할 수 있습니다.'
    : 'mock API 또는 실제 API에서 피드백을 받아오면 가정 지원 내용이 표시됩니다.',
)

const supportSteps = [
  { title: '보여주기', copy: '말로 길게 설명하기보다 그림 또는 짧은 목록을 먼저 보여주세요.' },
  { title: '나누기', copy: '활동은 두 단계 이하로 나누고 끝난 항목을 체크합니다.' },
  { title: '칭찬하기', copy: '완료보다 “도움 요청”과 “시작한 행동”을 먼저 칭찬합니다.' },
]

onMounted(async () => {
  const [schoolData, progressData] = await Promise.all([getSchoolLife(), getStudentProgress()])
  schoolLife.value = schoolData
  progress.value = progressData
})
</script>
