<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex justify-between items-end mb-2">
      <div>
        <h3 class="text-lg font-bold text-gray-800">Workbench Overview</h3>
        <p class="text-xs text-gray-500 mt-1">
          Real-time monitoring {{ currentCourse?.name || 'Course' }} 's Teaching schedule
        </p>
      </div>
      
      <div class="relative z-20">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <BookOpen size="16" class="text-blue-600" />
        </div>
        <select 
          v-model="selectedCourseId" 
          @change="handleCourseChange"
          class="pl-10 pr-10 py-2.5 bg-white border border-blue-200 rounded-xl text-sm font-bold text-gray-700 focus:border-blue-500 outline-none shadow-sm appearance-none cursor-pointer min-w-[260px]"
        >
          <option v-for="c in courseOptions" :key="c.id" :value="c.id">
            {{ c.name }}
          </option>
        </select>
        <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
          <ChevronDown size="16" class="text-gray-400" />
        </div>
      </div>
    </div>

    <div v-if="loading" class="grid grid-cols-4 gap-6">
      <div v-for="i in 4" :key="i" class="h-32 bg-gray-100 animate-pulse rounded-2xl"></div>
    </div>
    
    <div v-else class="grid grid-cols-4 gap-6">
      <div v-for="(stat, index) in summaryStats" :key="index" class="frosted-card p-7 rounded-2xl relative overflow-hidden group">
        <div class="absolute -right-6 -top-6 w-24 h-24 rounded-full opacity-10" :style="{ backgroundColor: stat.colorHex }"></div>
        <div class="flex justify-between items-start mb-5 relative z-10">
          <div>
            <p class="text-gray-500 text-xs font-bold uppercase mb-1">{{ stat.label }}</p>
            <h3 class="text-4xl font-bold text-gray-800">{{ stat.value }}<span class="text-base ml-1.5 font-medium text-gray-500">{{ stat.unit }}</span></h3>
          </div>
          <div class="p-3.5 rounded-xl bg-white/50 border border-white shadow-sm">
            <component :is="stat.icon" size="24" :style="{ color: stat.colorHex }" />
          </div>
        </div>
        <div class="relative z-10 mt-2 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
          <div class="h-full rounded-full transition-all duration-1000" :style="{ width: stat.progress + '%', backgroundColor: stat.colorHex }"></div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-6 min-h-[500px]">
      <div class="col-span-2 frosted-card rounded-2xl p-7 flex flex-col">
        <h3 class="text-xl font-bold text-gray-800 mb-6 flex items-center gap-3">
          <BarChart3 size="20" class="text-blue-600" /> Distribution of average marks for coursework
        </h3>
        <div id="nebulaChart" class="flex-1 w-full min-h-[380px]"></div>
      </div>

      <div class="col-span-1 frosted-card rounded-2xl p-7 flex flex-col">
        <h3 class="text-xl font-bold text-gray-800 mb-6 flex items-center gap-3">
          <Target size="20" class="text-orange-500" /> Skill point distribution
        </h3>
        <div id="dimensionChart" class="flex-1 w-full min-h-[380px]"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';
import * as echarts from 'echarts';
import api from '../../utils/request';
import { 
  FileStack, 
  Bot, 
  AlertCircle, 
  CheckSquare, 
  BarChart4, 
  Settings,
  // ... 保留原来的其他图标，确保每个名字只出现一次
} from 'lucide-vue-next';

const loading = ref(true);
const courseOptions = ref([]);
const selectedCourseId = ref(null);
const assignments = ref([]);
const dashboardData = ref(null);

const currentCourse = computed(() => courseOptions.value.find(c => c.id === selectedCourseId.value));

let nebulaChart = null;
let dimensionChart = null;

const initData = async () => {
  try {
    loading.value = true;
    const res = await api.get('/api/auth/teacher/courses/'); 
    courseOptions.value = res.results || res.data || res;
    if (courseOptions.value.length > 0) {
      selectedCourseId.value = courseOptions.value[0].id;
      await handleCourseChange();
    } else {
      loading.value = false;
    }
  } catch (e) {
    console.error('Failed to fetch course list', e);
    loading.value = false;
  }
};

const handleCourseChange = async () => {
  if (!selectedCourseId.value) return;
  try {
    loading.value = true;
    
    const [statsRes, assignRes] = await Promise.all([
      api.get(`/api/analytics/stats/${selectedCourseId.value}/course-dashboard/`),
      api.get('/api/auth/teacher/assignments/')
    ]);

    dashboardData.value = statsRes.results || statsRes.data || statsRes;
    
    const allData = assignRes.results || assignRes.data || assignRes;
    assignments.value = allData.filter(a => 
      (typeof a.course === 'object' ? a.course.id : a.course) === selectedCourseId.value
    );
    
    loading.value = false;

    nextTick(() => {
      setTimeout(() => drawCharts(), 200);
    });
  } catch (e) {
    console.error('Failed to sync course statistics', e);
    loading.value = false;
  }
};

const summaryStats = computed(() => {
  const data = dashboardData.value;
  return [
    { 
      label: 'Assignments', 
      value: assignments.value.length, 
      unit: '', 
      icon: FileStack, 
      colorHex: '#4A90E2', 
      progress: 100 
    },
    { 
      label: 'Students', 
      value: currentCourse.value?.student_count || 0, 
      unit: '', 
      icon: Bot, 
      colorHex: '#805AD5', 
      progress: 100 
    },
    { 
      label: 'Submissions', 
      value: data && data.summary ? data.summary.total_submissions : 0, 
      unit: '', 
      icon: CheckSquare, 
      colorHex: '#48BB78', 
      progress: 100 
    },
    { 
      label: 'Avg. Score', 
      value: data && data.summary ? Math.round(data.summary.average_score) : 0, 
      unit: '%', 
      icon: AlertCircle, 
      colorHex: '#ED8936', 
      progress: data && data.summary ? data.summary.average_score : 0 
    }
  ];
});
const drawCharts = () => {
  const nDom = document.getElementById('nebulaChart');
  const dDom = document.getElementById('dimensionChart');
  
  if (!nDom || !dDom || nDom.clientWidth === 0 || dDom.clientWidth === 0) return;

  if (nebulaChart) nebulaChart.dispose();
  if (dimensionChart) dimensionChart.dispose();

  const chartLabels = assignments.value.length > 0 
    ? assignments.value.map(a => a.title.length > 5 ? a.title.substring(0,5)+'..' : a.title) 
    : ['No assignment for now.'];
    
  const chartData = assignments.value.length > 0 
    ? assignments.value.map(() => Math.floor(Math.random() * 15 + 75)) // 模拟平均分
    : [0];

  nebulaChart = echarts.init(nDom);
  nebulaChart.setOption({
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.65)',
      extraCssText: 'backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.05);',
      borderColor: 'transparent',
      textStyle: { color: '#2D3748', fontWeight: 'bold' }
    },
    grid: { left: '2%', right: '4%', bottom: '5%', top: '15%', containLabel: true },
    xAxis: { 
      type: 'category', 
      data: chartLabels,
      axisLabel: { color: '#718096', fontWeight: '500', margin: 12 },
      axisLine: { lineStyle: { color: '#E2E8F0', width: 2 } },
      axisTick: { show: false }
    },
    yAxis: { 
      type: 'value', 
      max: 100, 
      axisLabel: { color: '#A0AEC0' },
      splitLine: { lineStyle: { type: 'dashed', color: '#EDF2F7' } } 
    },
    series: [
      {
        name: 'Average Score',
        data: chartData,
        type: 'bar',
        barWidth: 45, 
        showBackground: true,
        backgroundStyle: {
          color: 'rgba(243, 244, 246, 0.4)',
          borderRadius: [8, 8, 0, 0]
        },
        itemStyle: {
          color: 'rgba(30, 64, 175, 0.65)', 
          borderColor: 'rgba(255, 255, 255, 0.7)', 
          borderWidth: 1.5,
          shadowColor: 'rgba(30, 64, 175, 0.4)',
          shadowBlur: 12,
          borderRadius: [8, 8, 0, 0] 
        }
      },
      {
        name: 'Trends',
        data: chartData,
        type: 'line',
        smooth: false,
        symbol: 'circle',
        symbolSize: 10,
        itemStyle: {
          color: '#F6AD55',
          borderColor: '#FFF',
          borderWidth: 2,
          shadowColor: 'rgba(246, 173, 85, 0.5)',
          shadowBlur: 8
        },
        lineStyle: {
          color: '#F6AD55',
          width: 3,
          shadowColor: 'rgba(246, 173, 85, 0.3)',
          shadowBlur: 8,
          shadowOffsetY: 4
        }
      }
    ]
  });

  dimensionChart = echarts.init(dDom);
  const radarData = dashboardData.value?.l2_knowledge_radar || {};
  const indicators = Object.keys(radarData).map(k => ({ name: k, max: 100 }));
  const radarValues = Object.values(radarData);

  dimensionChart.setOption({
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.65)',
      extraCssText: 'backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 12px;',
      textStyle: { color: '#2D3748', fontWeight: 'bold' }
    },
    radar: {
      indicator: indicators.length > 0 ? indicators : [
        { name: 'Coding Standards', max: 100 },
        { name: 'logical consistency', max: 100 },
        { name: 'Robustness', max: 100 }
      ],
      shape: 'circle',
      splitNumber: 4,
      axisName: { color: '#4A5568', fontWeight: 'bold' },
      splitLine: { lineStyle: { color: ['#E2E8F0'].reverse() } },
      splitArea: { areaStyle: { color: ['rgba(237, 137, 54, 0.02)', 'rgba(237, 137, 54, 0.05)'] } },
      axisLine: { lineStyle: { color: '#E2E8F0' } }
    },
    series: [{
      type: 'radar',
      data: [{ 
        value: radarValues.length > 0 ? radarValues : [0, 0, 0], 
        name: 'Mastery',
        areaStyle: { color: 'rgba(237, 137, 54, 0.3)' }, 
        itemStyle: { color: '#ED8936' },
        lineStyle: { width: 2, color: '#ED8936' }
      }]
    }]
  });
};

const handleResize = () => {
  nebulaChart?.resize();
  dimensionChart?.resize();
};

onMounted(() => {
  initData();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  nebulaChart?.dispose();
  dimensionChart?.dispose();
});
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  transition: all 0.3s ease;
}
.frosted-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px -8px rgba(0,0,0,0.05);
}
</style>