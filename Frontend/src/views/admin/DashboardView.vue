<template>
  <div class="space-y-8 animate-fade-in pt-4">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-black text-gray-800 tracking-tight">Admin Dashboard</h2>
        <p class="text-sm text-gray-500 mt-1">System Back-end Management Center</p>
      </div>
      <div class="px-4 py-2 bg-white/60 backdrop-blur-md border border-white rounded-2xl shadow-sm flex items-center gap-3">
        <div class="w-2 h-2" :class="loading ? 'bg-amber-500 animate-spin' : 'bg-emerald-500 animate-pulse'"></div>
        <span class="text-xs font-bold text-gray-600 uppercase tracking-widest">{{ loading ? 'Loading...' : 'Live Monitoring' }}</span>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div v-for="stat in stats" :key="stat.label" class="frosted-card p-6 rounded-[2rem] border border-white/60 shadow-sm hover:shadow-xl transition-all group">
        <div :class="`w-12 h-12 rounded-2xl flex items-center justify-center mb-4 transition-transform group-hover:scale-110 ${getIconColor(stat.label)}`">
          <component :is="getIcon(stat.label)" class="text-white" size="24" />
        </div>
        <p class="text-xs font-black text-gray-400 uppercase tracking-widest">{{ stat.label }}</p>
        <div class="flex items-end gap-2 mt-1">
          <h3 class="text-3xl font-black text-gray-800">{{ stat.value }}</h3>
          <span class="text-xs font-bold mb-1.5" :class="stat.trendClass">{{ stat.trend }}</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2 frosted-card p-8 rounded-[2.5rem] border border-white/60 min-h-[420px] flex flex-col">
        <h3 class="font-bold text-gray-800 mb-6 flex items-center gap-2">
          <Activity size="20" class="text-blue-500" /> Recent 7-day trend of assignments submissions
        </h3>
        <div id="submissionChart" class="w-full flex-1 min-h-[300px]"></div>
      </div>

      <div class="frosted-card p-6 rounded-[2.5rem] border border-white/60 flex flex-col max-h-[420px]">
        <h3 class="font-bold text-gray-800 mb-6 flex items-center gap-2">
          <FileText size="20" class="text-indigo-500" /> 最近动态
        </h3>
        <div class="space-y-6 flex-1 overflow-y-auto pr-2">
          <div v-for="(log, i) in recentLogs" :key="i" class="flex gap-4 relative">
            <div v-if="i !== recentLogs.length - 1" class="absolute left-[11px] top-6 bottom-[-24px] w-[2px] bg-slate-100"></div>
            <div class="w-6 h-6 rounded-full bg-slate-50 border-2 border-white shadow-sm flex items-center justify-center z-10">
              <div class="w-2 h-2 rounded-full" :class="log.color"></div>
            </div>
            <div class="flex-1">
              <p class="text-sm font-bold text-gray-700 leading-snug">{{ log.action }}</p>
              <p class="text-[11px] text-gray-400 mt-1">{{ formatTime(log.time) }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
// 【关键修改】引用你项目自定义的请求工具
import api from '../../utils/request'; 
import * as echarts from 'echarts';
import { Users, BookOpen, CheckCircle, AlertTriangle, Activity, FileText } from 'lucide-vue-next';

const stats = ref([]);
const recentLogs = ref([]);
const loading = ref(true);
let myChart = null;

const getIcon = (label) => ({
  'Total Users': Users, 'Active Courses': BookOpen, 'Submissions': CheckCircle, 'System Alerts': AlertTriangle 
}[label] || Activity);

const getIconColor = (label) => ({
  'Total Users': 'bg-blue-600 shadow-blue-200',
  'Active Courses': 'bg-indigo-500 shadow-indigo-200',
  'Submissions': 'bg-emerald-500 shadow-emerald-200',
  'System Alerts': 'bg-amber-500 shadow-amber-200'
}[label] || 'bg-slate-500') + ' shadow-lg';

const formatTime = (isoStr) => {
  if(!isoStr) return '';
  const date = new Date(isoStr);
  return date.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const initChart = (data) => {
  const chartDom = document.getElementById('submissionChart');
  if (!chartDom) return;
  if (myChart) myChart.dispose();
  myChart = echarts.init(chartDom);
  myChart.setOption({
    tooltip: { trigger: 'axis', borderRadius: 12 },
    xAxis: { 
      type: 'category', 
      data: data.map(d => d.day),
      axisLine: { show: false },
      axisTick: { show: false }
    },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [{
      data: data.map(d => d.count),
      type: 'line',
      smooth: true,
      lineStyle: { width: 4, color: '#3b82f6' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
          { offset: 1, color: 'rgba(59, 130, 246, 0)' }
        ])
      },
      symbol: 'circle', symbolSize: 8, itemStyle: { color: '#3b82f6' }
    }],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true }
  });
};

const fetchData = async () => {
  loading.value = true;
  try {
    // 使用 api 替代原生 axios，它会自动处理 Token
    const res = await api.get('/api/auth/admin/dashboard-stats/');
    
    // 兼容处理：有些封装会直接返回 data，有些会返回整个 response
    const data = res.data || res;
    
    stats.value = data.stats;
    recentLogs.value = data.recentLogs;

    await nextTick();
    if (data.chartData) initChart(data.chartData);
  } catch (err) {
    console.error("Dashboard API Error:", err);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchData();
  window.addEventListener('resize', () => myChart?.resize());
});
</script>