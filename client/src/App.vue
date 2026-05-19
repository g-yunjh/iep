<template>
  <main :class="['app-shell', isTeacherRoute ? 'theme-teacher' : 'theme-parent']">
    <header class="topbar">
      <div class="brand-lockup">
        <div class="brand-mark" aria-label="IEP">
          <img :src="brandLogo" alt="" />
        </div>
        <div>
          <p class="eyebrow">{{ header.eyebrow }}</p>
          <h1>{{ header.title }}</h1>
          <p class="topbar-copy">{{ header.copy }}</p>
        </div>
      </div>

      <div class="topbar-actions">
        <label class="global-search">
          <Search class="search-icon" />
          <input type="search" :placeholder="header.search" />
        </label>
        <RouterLink
          v-for="mode in roleModes"
          :key="mode.to"
          :to="mode.to"
          :class="['mode-button', mode.active && 'is-active']"
        >
          {{ mode.label }}
        </RouterLink>
        <RouterLink :to="header.ctaTo" class="primary-action">
          {{ header.cta }}
        </RouterLink>
      </div>
    </header>

    <div class="workspace">
      <aside class="side-rail" aria-label="주요 메뉴">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :class="['rail-item', route.path === item.to && 'is-active']"
        >
          <component :is="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
        <div class="rail-avatar">{{ isTeacherRoute ? '지훈' : '지훈' }}</div>
      </aside>

      <nav class="mobile-tabs" aria-label="모바일 탭">
        <RouterLink
          v-for="item in navItems"
          :key="`mobile-${item.to}`"
          :to="item.to"
          :class="['mobile-tab', route.path === item.to && 'is-active']"
        >
          <span v-if="item.mobileSvg" class="mobile-tab-icon" v-html="item.mobileSvg" />
          {{ item.label }}
        </RouterLink>
      </nav>

      <section class="workspace-main">
        <p v-if="studentStore.error" class="inline-alert">{{ studentStore.error }}</p>
        <RouterView />
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import {
  BarChart3,
  BookOpenCheck,
  BriefcaseBusiness,
  ClipboardPenLine,
  HeartHandshake,
  Home,
  NotebookTabs,
  Search,
  Settings2,
  Sparkles,
  UserRoundCog,
} from 'lucide-vue-next'
import { useStudentStore } from './composables/useStudentStore'
import brandLogo from './assets/icons/bgddd.svg'
import todaySvg from './assets/icons/today.svg?raw'
import schoolSvg from './assets/icons/school.svg?raw'
import characteristicSvg from './assets/icons/characteristic.svg?raw'
import courseSvg from './assets/icons/course.svg?raw'
import teacherHomeSvg from './assets/icons/home.svg?raw'
import teacherRecommendSvg from './assets/icons/recommand.svg?raw'
import teacherCriteriaSvg from './assets/icons/criteria.svg?raw'
import teacherRecordSvg from './assets/icons/record.svg?raw'

const route = useRoute()
const { state: studentStore, loadStudent } = useStudentStore()

const isTeacherRoute = computed(() => route.path.startsWith('/teacher'))

const teacherItems = [
  { to: '/teacher/overview', label: '홈', icon: NotebookTabs, mobileSvg: teacherHomeSvg },
  { to: '/teacher/scaffolding', label: '추천', icon: Sparkles, mobileSvg: teacherRecommendSvg },
  { to: '/teacher/curriculum', label: '기준', icon: BookOpenCheck, mobileSvg: teacherCriteriaSvg },
  { to: '/teacher/progress', label: '기록', icon: BarChart3, mobileSvg: teacherRecordSvg },
  { to: '/teacher/career', label: '진로', icon: BriefcaseBusiness, mobileSvg: courseSvg },
]

const parentItems = [
  { to: '/parent/overview', label: '오늘', icon: Home, mobileSvg: todaySvg },
  { to: '/parent/school', label: '생활', icon: ClipboardPenLine, mobileSvg: schoolSvg },
  { to: '/parent/traits', label: '특성', icon: UserRoundCog, mobileSvg: characteristicSvg },
  { to: '/parent/career', label: '진로', icon: BriefcaseBusiness, mobileSvg: courseSvg },
]

const navItems = computed(() => (isTeacherRoute.value ? teacherItems : parentItems))

const headers = {
  '/teacher/overview': {
    eyebrow: '교사용 워크벤치',
    title: '대시보드',
    copy: '관찰 기록을 바탕으로 한 AI 스캐폴딩 추천과 근거 기준, 학생 성장 흐름을 한눈에 확인합니다.',
    search: '학생, 성취기준, 피드백 검색',
    cta: '추천 작성',
    ctaTo: '/teacher/scaffolding',
  },
  '/teacher/scaffolding': {
    eyebrow: '교사용 워크벤치 · 추천 상세 화면',
    title: 'AI 스캐폴딩 추천',
    copy: '관찰 기록을 입력하고 학생 맥락과 과거 피드백을 반영해 지원 전략을 생성합니다.',
    search: '학생, 피드백, 추천 기록 검색',
    cta: '추천 생성',
    ctaTo: '/teacher/scaffolding',
  },
  '/teacher/curriculum': {
    eyebrow: '교사용 워크벤치 · 기준 상세 화면',
    title: '성취기준 근거 검색',
    copy: '국어와 수학 성취기준을 검색하고 AI 추천의 근거로 사용할 기준을 선택합니다.',
    search: '성취기준, 과목, 키워드 검색',
    cta: '기준 검색',
    ctaTo: '/teacher/curriculum',
  },
  '/teacher/progress': {
    eyebrow: '교사용 워크벤치 · 기록 상세 화면',
    title: '피드백 기록과 성장 흐름',
    copy: 'AI 추천 실행 후 저장된 피드백을 학생별 타임라인과 요약으로 확인합니다.',
    search: '날짜, 수준, 피드백 검색',
    cta: '기록 보기',
    ctaTo: '/teacher/progress',
  },
  '/teacher/career': {
    eyebrow: '교사용 워크벤치 · 진로 상세 화면',
    title: '강점 기반 진로 추천',
    copy: '학생의 현재 역량과 관심 단서를 바탕으로 진로 후보와 역량 격차를 확인합니다.',
    search: '직업, 강점, 역량 검색',
    cta: '진로 탐색',
    ctaTo: '/teacher/career',
  },
  '/parent/overview': {
    eyebrow: '학부모용 워크벤치',
    title: '대시보드',
    copy: '학교생활 정보와 최근 피드백을 쉬운 문장으로 보고, 집에서 바로 해볼 일을 확인합니다.',
    search: '학교생활, 강점, 진로 검색',
    cta: '기록 보기',
    ctaTo: '/parent/overview',
  },
  '/parent/school': {
    eyebrow: '학부모용 워크벤치',
    title: '학교생활 상세',
    copy: '급식, 시간표, 하교 시간, 내일 준비를 빠르게 확인합니다.',
    search: '급식, 시간표, 일정 검색',
    cta: '새로고침',
    ctaTo: '/parent/school',
  },
  '/parent/traits': {
    eyebrow: '학부모용 워크벤치',
    title: '아이 특성 관리',
    copy: '가정에서 보이는 강점과 어려움을 기록해 학교와 같은 지원 방향을 맞춥니다.',
    search: '특성, 행동, 수준 검색',
    cta: '특성 저장',
    ctaTo: '/parent/traits',
  },
  '/parent/career': {
    eyebrow: '학부모용 워크벤치',
    title: '강점과 진로',
    copy: '아이의 강점과 좋아하는 활동을 부담 없는 진로 대화로 연결합니다.',
    search: '관심 활동, 직업 검색',
    cta: '탐색',
    ctaTo: '/parent/career',
  },
}

const header = computed(() => headers[route.path] || headers['/teacher/overview'])

const roleModes = computed(() => [
  { to: '/teacher/overview', label: '교사용', active: isTeacherRoute.value },
  { to: '/parent/overview', label: '학부모용', active: !isTeacherRoute.value },
])

onMounted(loadStudent)
</script>
