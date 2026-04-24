import { createRouter, createWebHistory } from 'vue-router'

import TeacherOverviewPage from '../views/teacher/TeacherOverviewPage.vue'
import TeacherScaffoldingPage from '../views/teacher/TeacherScaffoldingPage.vue'
import TeacherCurriculumPage from '../views/teacher/TeacherCurriculumPage.vue'
import TeacherProgressPage from '../views/teacher/TeacherProgressPage.vue'

import ParentOverviewPage from '../views/parent/ParentOverviewPage.vue'
import ParentTraitsPage from '../views/parent/ParentTraitsPage.vue'
import ParentCareerPage from '../views/parent/ParentCareerPage.vue'

const routes = [
  { path: '/', redirect: '/teacher/overview' },
  { path: '/teacher/overview', component: TeacherOverviewPage },
  { path: '/teacher/scaffolding', component: TeacherScaffoldingPage },
  { path: '/teacher/curriculum', component: TeacherCurriculumPage },
  { path: '/teacher/progress', component: TeacherProgressPage },
  { path: '/parent/overview', component: ParentOverviewPage },
  { path: '/parent/traits', component: ParentTraitsPage },
  { path: '/parent/career', component: ParentCareerPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
