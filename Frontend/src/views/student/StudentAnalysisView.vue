<template>
  <div class="space-y-6 animate-fade-in max-w-7xl mx-auto pt-4 pb-12 px-4">
    
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      <div class="md:col-span-2">
        <h2 class="text-3xl font-extrabold text-gray-800 tracking-tight flex items-center gap-3">
          <div class="p-2.5 bg-purple-600 rounded-2xl shadow-lg shadow-purple-200">
            <BarChart3 class="text-white" size="26" />
          </div>
          Ability Profile
        </h2>
        <p class="text-sm text-gray-500 mt-2 ml-1 font-medium">Integrated coding DNA report based on multi-dimensional scoring.</p>
      </div>
      
      <div class="frosted-card p-5 rounded-3xl border border-white/60 flex flex-col justify-center shadow-sm text-center">
        <p class="text-[10px] font-black text-gray-800 uppercase tracking-[0.2em] mb-1">Average Score</p>
        <div class="flex items-baseline justify-center gap-1">
          <span class="text-3xl font-black text-purple-600">{{ summary.average_score }}</span>
          <span class="text-xs text-gray-400 font-bold">pts</span>
        </div>
      </div>

      <div class="frosted-card p-5 rounded-3xl border border-white/60 flex flex-col justify-center shadow-sm text-center">
        <p class="text-[10px] font-black text-gray-800 uppercase tracking-[0.2em] mb-1">Completed Tasks</p>
        <div class="flex items-baseline justify-center gap-2">
          <span class="text-3xl font-black text-blue-600">{{ summary.total_completed }}</span>
          <span class="text-xs text-gray-400 font-bold uppercase">Tasks</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex flex-col justify-center items-center py-32">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-purple-100 border-t-purple-600 mb-4"></div>
      <p class="text-gray-400 font-bold animate-pulse text-xs tracking-widest uppercase">Calculating Skill Matrix...</p>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <div class="lg:col-span-8 frosted-card p-8 rounded-[2.5rem] border border-white/60 shadow-sm hover:shadow-md transition-all flex flex-col">
        <div class="mb-6">
          <h3 class="text-xl font-bold text-gray-800 flex items-center gap-2">
            <Target size="22" class="text-purple-600" /> 
            Comprehensive Skill Mastery
          </h3>
          <p class="text-xs text-gray-600 mt-1 uppercase font-bold tracking-widest">Global view of coding dimensions (Top 8 displayed)</p>
        </div>
        
        <div id="radarChart" class="flex-1 w-full min-h-[450px]"></div>
      </div>

      <div class="lg:col-span-4 space-y-6">
        <div class="frosted-card p-7 rounded-[2.5rem] border border-white/60 bg-gradient-to-br from-purple-50/50 via-white to-white shadow-sm flex flex-col h-full">
          <div class="flex items-center gap-2 mb-8">
            <div class="p-2 bg-yellow-400 rounded-xl shadow-lg shadow-yellow-100">
              <Sparkles size="20" class="text-white" />
            </div>
            <h3 class="text-lg font-bold text-gray-800">AI Intelligence</h3>
          </div>
          
          <div class="space-y-8 flex-1">
            <div v-if="bestKp" class="relative pl-5 border-l-4 border-emerald-400">
              <p class="text-[10px] font-black text-emerald-600 uppercase tracking-widest mb-1">Peak Mastery</p>
              <h4 class="font-bold text-gray-900 text-base">{{ bestKp.name }}</h4>
              <p class="text-xs text-gray-500 mt-1 leading-relaxed italic">"Exceptional logic implementation and code cohesion."</p>
            </div>

            <div v-if="weakestKp" class="bg-orange-50/40 border border-orange-100/60 p-5 rounded-[2rem]">
              <div class="flex items-center gap-2 text-orange-600 font-black text-[10px] mb-3 uppercase tracking-wider">
                <AlertTriangle size="14"/> Action Required
              </div>
              <h4 class="font-bold text-gray-900 text-base mb-1">{{ weakestKp.name }}</h4>
              <p class="text-xs text-gray-600 leading-relaxed mb-6 font-medium">Currently scored at {{ weakestKp.score }}. Focus on reinforcing these core concepts.</p>
              
              <div class="space-y-3">
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest px-1">Study Guide</p>
                <button class="w-full p-4 rounded-2xl bg-white border border-orange-100 text-blue-700 text-xs flex items-center justify-between font-bold shadow-sm hover:translate-x-1 transition-all">
                  <div class="flex items-center gap-2">
                    <BookOpen size="14" class="text-blue-400" /> 
                    <span>Practice {{ weakestKp.name }}</span>
                  </div>
                  <TrendingUp size="14" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="!loading" class="frosted-card p-8 rounded-[2.5rem] border border-white/60 shadow-sm hover:shadow-md transition-all">
      <div class="flex items-center justify-between mb-8">
        <h3 class="text-xl font-bold text-gray-800 flex items-center gap-2">
          <TrendingUp size="22" class="text-blue-600" /> 
          Performance Growth Curve
        </h3>
        <span class="px-4 py-1.5 bg-blue-50 text-blue-600 rounded-full text-[10px] font-black uppercase tracking-widest border border-blue-100">
          Last {{ history.length }} Events
        </span>
      </div>
      <div id="lineChart" class="w-full h-[350px]"></div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';
import * as echarts from 'echarts';
import api from '../../utils/request';
import { 
  BarChart3, Target, Sparkles, TrendingUp, AlertTriangle, 
  BookOpen 
} from 'lucide-vue-next';

const loading = ref(true);
const radarL1 = ref({});
const radarL2 = ref({});
const history = ref([]);
const summary = ref({ total_completed: 0, average_score: 0 });

let radarChartInstance = null;
let lineChartInstance = null;

const fetchAnalysisData = async () => {
  try {
    loading.value = true;
    const res = await api.get('/api/analytics/stats/student-profile/');
    const data = res.data || res;
    
    radarL1.value = data.radar_l1_general || {};
    radarL2.value = data.radar_l2_special || {};
    history.value = data.history || [];
    summary.value = data.summary || { total_completed: 0, average_score: 0 };

    nextTick(() => {
      initRadarChart();
      initLineChart();
    });
  } catch (error) {
    console.error('Data sync failed:', error);
  } finally {
    loading.value = false;
  }
};

// 1. 合并全量数据集 (用于 Tooltip 展示)
const combinedMap = computed(() => ({ ...radarL1.value, ...radarL2.value }));

// 2. 🚀 核心修改：雷达图视觉显示数据集 (仅限 Top 8)
const radarDisplayMap = computed(() => {
  const entries = Object.entries(combinedMap.value);
  // 这里可以根据得分排序显示前8个，也可以按默认顺序
  return Object.fromEntries(entries.slice(0, 8));
});

// 3. 修正：Weakest KP (取最小值)
const weakestKp = computed(() => {
  const entries = Object.entries(combinedMap.value);
  if (entries.length === 0) return null;
  const sorted = [...entries].sort((a, b) => a[1] - b[1]); // 升序
  return { name: sorted[0][0], score: Math.round(sorted[0][1]) };
});

// 4. 修正：Best KP (取最大值)
const bestKp = computed(() => {
  const entries = Object.entries(combinedMap.value);
  if (entries.length === 0) return null;
  const sorted = [...entries].sort((a, b) => b[1] - a[1]); // 降序
  return { name: sorted[0][0], score: Math.round(sorted[0][1]) };
});

const initRadarChart = () => {
  const dom = document.getElementById('radarChart');
  if (!dom) return;
  if (radarChartInstance) radarChartInstance.dispose();
  radarChartInstance = echarts.init(dom);

  const displayKeys = Object.keys(radarDisplayMap.value);
  const fullDataEntries = Object.entries(combinedMap.value);
  if (displayKeys.length === 0) return;

  const indicators = displayKeys.map(key => ({ name: key, max: 100 }));
  const displayValues = displayKeys.map(key => radarDisplayMap.value[key] || 0);

  const option = {
    // 🚀 核心修改：Tooltip 全量展示逻辑
    tooltip: { 
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      padding: [12, 18],
      borderWidth: 1,
      borderColor: '#9333ea',
      shadowBlur: 10,
      shadowColor: 'rgba(0,0,0,0.1)',
      textStyle: { color: '#1e293b', fontSize: 12 },
      formatter: () => {
        let res = `<div style="font-weight:900; color:#9333ea; border-bottom:1px solid #eee; margin-bottom:8px; padding-bottom:4px;">Global Skill Matrix</div>`;
        fullDataEntries.forEach(([key, val]) => {
          res += `<div style="display:flex; justify-content:space-between; gap:30px; margin-bottom:3px;">
                    <span style="color:#64748b;">${key}:</span>
                    <span style="font-weight:800; color:#9333ea;">${Math.round(val)}%</span>
                  </div>`;
        });
        return res;
      }
    },
    radar: {
      indicator: indicators,
      radius: '70%',
      splitNumber: 4,
      axisName: { 
        color: '#94a3b8', 
        fontWeight: 'bold', 
        fontSize: 10,
        formatter: (value) => {
          if (value.length > 10) return value.slice(0, 8) + '...';
          return value;
        }
      },
      splitArea: { show: false },
      splitLine: { lineStyle: { color: 'rgba(226, 232, 240, 0.8)' } },
      axisLine: { lineStyle: { color: 'rgba(226, 232, 240, 0.8)' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: displayValues,
        name: 'Skill Proficiency',
        itemStyle: { color: '#9333ea' },
        lineStyle: { width: 4, color: '#9333ea' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(147, 51, 234, 0.4)' },
            { offset: 1, color: 'rgba(147, 51, 234, 0.05)' }
          ])
        },
        symbolSize: 8
      }]
    }]
  };
  radarChartInstance.setOption(option);
};

const initLineChart = () => {
  const dom = document.getElementById('lineChart');
  if (!dom) return;
  if (lineChartInstance) lineChartInstance.dispose();
  lineChartInstance = echarts.init(dom);

  if (history.value.length === 0) return;

  const option = {
    tooltip: { trigger: 'axis', backgroundColor: '#fff', borderRadius: 12, borderWidth: 0, shadowBlur: 10 },
    grid: { left: '2%', right: '3%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: history.value.map(i => i.task),
      axisLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 }
    },
    yAxis: { type: 'value', min: 0, max: 100, splitLine: { lineStyle: { type: 'dashed', color: '#f1f5f9' } }, axisLabel: { color: '#94a3b8' } },
    series: [{
      data: history.value.map(i => i.score),
      type: 'line',
      smooth: 0.4,
      symbolSize: 10,
      itemStyle: { color: '#3b82f6', borderWidth: 3, borderColor: '#fff' },
      lineStyle: { width: 5, color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#60a5fa' }, { offset: 1, color: '#3b82f6' }]) },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(59, 130, 246, 0.15)' }, { offset: 1, color: 'rgba(59, 130, 246, 0)' }]) }
    }]
  };
  lineChartInstance.setOption(option);
};

const handleResize = () => {
  radarChartInstance?.resize();
  lineChartInstance?.resize();
};

onMounted(() => {
  fetchAnalysisData();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  radarChartInstance?.dispose();
  lineChartInstance?.dispose();
});
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
</style>