<template>
  <div class="space-y-6 animate-fade-in pb-12">

    <div class="welcome-banner rounded-xl p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
      <div class="flex-1 min-w-0">
        <h2 class="text-2xl font-bold text-gray-800 tracking-tight">
          {{ greetingText }}, {{ authStore.user?.username || 'Teacher' }}
        </h2>
        <p class="text-sm text-gray-500 mt-1.5">
          {{ todayText }} &mdash; Intelligent Programming Education System
        </p>
      </div>
      <div class="flex items-center gap-3 shrink-0 flex-wrap">
        <button @click="router.push('/teacher/grading')" class="action-btn-primary">
          <BookOpenCheck size="16" /> Start Grading
        </button>
        <button @click="router.push('/teacher/courses')" class="action-btn-primary">
          <FilePlus size="16" /> Publish Assignment
        </button>
        <button @click="router.push('/teacher/appeals')" class="action-btn-primary">
          <ShieldAlert size="16" /> Grade Appeals
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">

      <div class="lg:col-span-3 workbench-panel rounded-xl p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-sm font-bold text-gray-800 flex items-center gap-2 uppercase tracking-wider">
            <BellRing size="16" class="text-amber-500" /> Action Center
          </h3>
          <span class="text-[10px] text-gray-400 font-medium">Items requiring your attention</span>
        </div>

        <div v-if="loading" class="space-y-3">
          <div v-for="i in 4" :key="i" class="h-14 bg-gray-100 animate-pulse rounded-xl"></div>
        </div>

        <div v-else class="space-y-3">
          <div v-for="task in pendingTasks" :key="task.label" @click="task.route && router.push(task.route)" class="task-item">
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <div class="w-2 h-2 rounded-full shrink-0" :class="task.dotColor"></div>
              <div class="min-w-0 flex-1">
                <p class="text-sm font-semibold text-gray-700 truncate">{{ task.label }}</p>
                <p class="text-xs text-gray-400 mt-0.5">{{ task.description }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <span class="text-lg font-black tabular-nums" :class="task.countColor">{{ task.count }}</span>
              <ChevronRight size="16" class="text-gray-300" />
            </div>
          </div>
          <div v-if="pendingTasks.length === 0" class="text-center py-8 text-gray-400">
            <CheckCircle2 size="32" class="mx-auto mb-2 opacity-40" />
            <p class="text-sm font-medium">All clear! No pending tasks.</p>
          </div>
        </div>
      </div>

      <div class="lg:col-span-2 workbench-panel rounded-xl p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-sm font-bold text-gray-800 flex items-center gap-2 uppercase tracking-wider">
            <Library size="16" class="text-blue-500" /> My Courses
          </h3>
          <button @click="router.push('/teacher/courses')" class="text-xs text-blue-600 hover:text-blue-700 font-semibold transition-colors">
            Manage All
          </button>
        </div>

        <div v-if="loading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-16 bg-gray-100 animate-pulse rounded-xl"></div>
        </div>

        <div v-else class="space-y-3">
          <div v-for="course in paginatedCourses" :key="course.id" @click="router.push('/teacher/courses')" class="course-card">
            <div class="flex items-center justify-between">
              <h4 class="text-sm font-bold text-gray-700 truncate flex-1 mr-3">{{ course.name }}</h4>
              <span class="inline-flex items-center gap-1 text-[10px] font-bold bg-gray-100/80 text-gray-400 px-2.5 py-1 rounded-full shrink-0 tracking-wide">
                ID:{{ course.id }}
              </span>
            </div>
            <div class="flex items-center gap-4 mt-2 text-xs text-gray-400">
              <span class="flex items-center gap-1"><Users size="12" /> {{ course.student_count || 0 }} students</span>
              <span class="flex items-center gap-1"><FileStack size="12" /> {{ getCourseAssignmentCount(course.id) }} assignments</span>
            </div>
          </div>

          <div v-if="courses.length === 0" class="text-center py-8 text-gray-400">
            <Inbox size="32" class="mx-auto mb-2 opacity-40" />
            <p class="text-sm font-medium">No courses found in your account.</p>
          </div>

          <div v-if="totalCoursePages > 1" class="flex items-center justify-center gap-3 mt-4 pt-3 border-t border-gray-100">
            <button @click="coursePage--" :disabled="coursePage === 0" class="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
              <ChevronLeft size="16" />
            </button>
            <span class="text-xs text-gray-400 font-semibold">{{ coursePage + 1 }} / {{ totalCoursePages }}</span>
            <button @click="coursePage++" :disabled="coursePage >= totalCoursePages - 1" class="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
              <ChevronRight size="16" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 workbench-panel rounded-xl p-6">
        <div class="flex items-center justify-between mb-5 gap-4 flex-wrap">
          <h3 class="text-sm font-bold text-gray-800 flex items-center gap-2 uppercase tracking-wider min-w-0">
            <BarChart3 size="16" class="text-blue-500 shrink-0" /> Distribution of Average Marks
          </h3>
          <el-dropdown trigger="click" @command="handleCourseChange" placement="bottom-end">
            <button class="course-pill">
              <BookOpen size="14" class="text-blue-500 shrink-0" />
              <span class="course-pill-text">{{ currentCourseName }}</span>
              <ChevronDown size="14" class="text-gray-400 shrink-0" />
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="c in courses" :key="c.id" :command="c.id" :class="{ 'is-active': c.id === selectedCourseId }">
                  {{ c.name }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div id="avgMarksChart" class="w-full" style="height: 300px;"></div>
      </div>

      <div class="workbench-panel rounded-xl p-6 flex flex-col">
        <h3 class="text-sm font-bold text-gray-800 flex items-center gap-2 uppercase tracking-wider mb-4">
          <Radar size="16" class="text-orange-500" /> Skill Distribution
        </h3>
        <div id="skillRadarChart" class="w-full flex-1" style="min-height: 260px;"></div>
      </div>
    </div>

    <div class="workbench-panel rounded-xl p-6">
      <h3 class="text-sm font-bold text-gray-800 flex items-center gap-2 uppercase tracking-wider mb-5">
        <TrendingUp size="16" class="text-emerald-500" /> Submission Trend (Recent 14 Days)
      </h3>
      <div id="submissionTrendChart" class="w-full" style="height: 240px;"></div>
    </div>

    <div class="workbench-panel rounded-xl p-6">
      <h3 class="text-sm font-bold text-gray-800 flex items-center gap-2 uppercase tracking-wider mb-5">
        <LayoutGrid size="16" class="text-indigo-500" /> Quick Access
      </h3>
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div v-for="action in quickActions" :key="action.label" @click="router.push(action.route)" class="quick-action-card">
          <div class="p-3 rounded-xl" :class="action.iconBg">
            <component :is="action.icon" size="20" :class="action.iconColor" />
          </div>
          <span class="text-xs font-semibold text-gray-600 mt-2 text-center leading-tight">{{ action.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../../store/authStore';
import api from '../../utils/request';
import * as echarts from 'echarts';
import {
  BookOpenCheck, FilePlus, ShieldAlert, BellRing, ChevronRight, ChevronDown, ChevronLeft,
  CheckCircle2, Library, Users, FileStack, Inbox, TrendingUp, Target,
  LayoutGrid, BarChart3, Settings, FileText, Sparkles, Radar, BookOpen
} from 'lucide-vue-next';

const router = useRouter();
const authStore = useAuthStore();

const loading = ref(true);
const courses = ref([]);
const assignments = ref([]);
const appeals = ref([]);
const selectedCourseId = ref(null);
const dashboardData = ref(null);

const coursePage = ref(0);
const pageSize = 3;

let submissionChart = null;
let skillRadarChart = null;
let avgMarksChart = null;

// --- Computed ---

const greetingText = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
});

const todayText = computed(() => {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });
});

const currentCourseName = computed(() => {
  const course = courses.value.find(c => c.id === selectedCourseId.value);
  return course?.name || 'Select Course';
});

const totalCoursePages = computed(() => Math.ceil(courses.value.length / pageSize));
const paginatedCourses = computed(() => {
  const start = coursePage.value * pageSize;
  return courses.value.slice(start, start + pageSize);
});

const pendingTasks = computed(() => {
  const tasks = [];
  // 1. Ungraded assignments
  const ungraded = assignments.value.filter(a => (a.submitted_count || 0) > (a.graded_count || 0));
  if (ungraded.length > 0) {
    tasks.push({
      label: `${ungraded.length} assignment(s) need grading`,
      description: 'Pending student submissions',
      count: ungraded.length,
      countColor: 'text-red-500', dotColor: 'bg-red-500', route: '/teacher/grading'
    });
  }
  // 2. Pending appeals
  const pendingAppeals = appeals.value.filter(a => ['pending_teacher', 'pending_ai'].includes(a.status));
  if (pendingAppeals.length > 0) {
    tasks.push({
      label: `${pendingAppeals.length} appeals pending`,
      description: 'Review student concerns',
      count: pendingAppeals.length,
      countColor: 'text-amber-500', dotColor: 'bg-amber-500', route: '/teacher/appeals'
    });
  }
  return tasks;
});

const quickActions = computed(() => [
  { label: 'Grading Center', icon: BookOpenCheck, route: '/teacher/grading', iconBg: 'bg-blue-50', iconColor: 'text-blue-600' },
  { label: 'Course Management', icon: Library, route: '/teacher/courses', iconBg: 'bg-indigo-50', iconColor: 'text-indigo-600' },
  { label: 'AI Insights', icon: Sparkles, route: '/teacher/grading', iconBg: 'bg-purple-50', iconColor: 'text-purple-600' },
  { label: 'Grade Appeals', icon: ShieldAlert, route: '/teacher/appeals', iconBg: 'bg-amber-50', iconColor: 'text-amber-600' },
  { label: 'Export Reports', icon: FileText, route: '/teacher/settings', iconBg: 'bg-emerald-50', iconColor: 'text-emerald-600' },
  { label: 'System Settings', icon: Settings, route: '/teacher/settings', iconBg: 'bg-gray-100', iconColor: 'text-gray-600' }
]);

const getCourseAssignmentCount = (courseId) => {
  return assignments.value.filter(a => (typeof a.course === 'object' ? a.course.id : a.course) === courseId).length;
};

// --- Data Fetching (Strictly from API) ---

const fetchAllData = async () => {
  loading.value = true;
  try {
    const [coursesRes, assignmentsRes, appealsRes] = await Promise.all([
      api.get('/api/auth/teacher/courses/'),
      api.get('/api/auth/teacher/assignments/'),
      api.get('/api/auth/teacher/assignments/all-appeals/')
    ]);

    courses.value = coursesRes?.results || coursesRes || [];
    assignments.value = assignmentsRes?.results || assignmentsRes || [];
    appeals.value = appealsRes?.results || appealsRes || [];

    if (courses.value.length > 0) {
      selectedCourseId.value = courses.value[0].id;
      await fetchCourseDashboard(courses.value[0].id);
    }
  } catch (e) {
    console.error('Critical data fetch failed:', e);
  } finally {
    loading.value = false;
  }
};

const fetchCourseDashboard = async (courseId) => {
  try {
    const res = await api.get(`/api/analytics/stats/${courseId}/course-dashboard/`);
    dashboardData.value = res.results || res.data || res;
    nextTick(() => drawCharts());
  } catch (e) {
    console.error('Dashboard stats unavailable:', e);
    dashboardData.value = null; // Clear data on failure
    nextTick(() => drawCharts());
  }
};

const handleCourseChange = async (courseId) => {
  selectedCourseId.value = courseId;
  await fetchCourseDashboard(courseId);
};

// --- Charts Logic (Real Data Driven) ---

const drawCharts = () => {
  drawAvgMarks();
  drawSkillRadar();
  drawSubmissionTrend();
};

const drawAvgMarks = () => {
  const dom = document.getElementById('avgMarksChart');
  if (!dom) return;
  if (avgMarksChart) avgMarksChart.dispose();
  avgMarksChart = echarts.init(dom);

  const history = dashboardData.value?.history || [];
  const labels = history.length > 0 ? history.map(h => h.task.length > 10 ? h.task.substring(0, 10) + '..' : h.task) : ['No Data'];
  const values = history.length > 0 ? history.map(h => h.score) : [0];

  avgMarksChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Average Score', 'Trend'], right: 0, top: 0 },
    grid: { left: '3%', right: '4%', bottom: '10%', top: '15%', containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { color: '#9ca3af', fontSize: 10 } },
    yAxis: { type: 'value', max: 100, axisLabel: { color: '#9ca3af' } },
    series: [
      { name: 'Average Score', type: 'bar', data: values, barWidth: 35, itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] } },
      { name: 'Trend', type: 'line', data: values, smooth: true, itemStyle: { color: '#F6AD55' } }
    ]
  });
};

const drawSubmissionTrend = () => {
  const dom = document.getElementById('submissionTrendChart');
  if (!dom) return;
  if (submissionChart) submissionChart.dispose();
  submissionChart = echarts.init(dom);

  const trend = dashboardData.value?.submission_trend || [];
  const labels = trend.length > 0 ? trend.map(d => d.date) : ['No Data'];
  const values = trend.length > 0 ? trend.map(d => d.count) : [0];

  submissionChart.setOption({
    tooltip: { trigger: 'axis', formatter: '{b}<br/>Submissions: <b>{c}</b>' },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '15%', containLabel: true },
    xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { color: '#9ca3af', fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { color: '#9ca3af' } },
    series: [{
      name: 'Submissions', type: 'line', data: values, smooth: true,
      areaStyle: { color: 'rgba(16, 185, 129, 0.2)' }, itemStyle: { color: '#10b981' }, lineStyle: { width: 3 }
    }]
  });
};

const drawSkillRadar = () => {
  const dom = document.getElementById('skillRadarChart');
  if (!dom) return;
  if (skillRadarChart) skillRadarChart.dispose();
  skillRadarChart = echarts.init(dom);

  const radar = dashboardData.value?.l2_knowledge_radar || {};
  const indicators = Object.keys(radar).map(k => ({ name: k, max: 100 }));
  const values = Object.values(radar);

  skillRadarChart.setOption({
    tooltip: {},
    radar: {
      indicator: indicators.length > 0 ? indicators : [{ name: 'No Skill Data', max: 100 }],
      shape: 'circle',
      axisName: { color: '#4a5568', fontSize: 10 }
    },
    series: [{
      type: 'radar',
      data: [{ value: values, areaStyle: { color: 'rgba(237, 137, 54, 0.2)' }, itemStyle: { color: '#ED8936' } }]
    }]
  });
};

const handleResize = () => {
  avgMarksChart?.resize();
  skillRadarChart?.resize();
  submissionChart?.resize();
};

onMounted(async () => {
  await fetchAllData();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  avgMarksChart?.dispose();
  skillRadarChart?.dispose();
  submissionChart?.dispose();
});
</script>

<style scoped>
.welcome-banner {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(219, 234, 254, 0.4) 100%);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
}
.workbench-panel {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.action-btn-primary {
  @apply flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm
         hover:bg-blue-700 active:scale-[0.97] transition-all;
}
.task-item {
  @apply flex items-center justify-between p-4 rounded-xl border border-transparent
         hover:bg-white hover:border-gray-200 cursor-pointer transition-all;
}
.course-card {
  @apply p-4 rounded-xl border border-transparent
         hover:bg-white hover:border-blue-200 cursor-pointer transition-all;
}
.course-pill {
  @apply flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold
         bg-white border border-gray-200 text-gray-700 cursor-pointer shadow-sm;
}
.quick-action-card {
  @apply flex flex-col items-center justify-center p-4 rounded-xl border border-transparent
         hover:bg-white hover:border-gray-200 cursor-pointer transition-all;
}
.animate-fade-in { animation: fadeIn 0.4s ease-out; }
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>