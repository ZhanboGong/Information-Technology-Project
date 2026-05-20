<template>
  <div class="space-y-6 animate-fade-in pt-4 pb-10">
    <div class="flex justify-between items-end">
      <div>
        <h2 class="text-2xl font-black text-gray-800">AI Usage Analytics</h2>
        <p class="text-sm text-gray-500">Monitor token consumption, response performance, and API stability.</p>
      </div>
      <div class="flex gap-2">
        <button v-for="d in [7, 14, 30]" :key="d" @click="fetchData(d)"
          :class="['px-4 py-2 rounded-xl text-xs font-black transition-all border', selectedDays === d ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-500 border-gray-200 hover:border-blue-300']">
          {{ d }}D
        </button>
      </div>
    </div>

    <!-- 顶部统计卡片 -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-5">
      <div v-for="card in statCards" :key="card.label" class="frosted-card p-5 rounded-2xl border border-white/60 hover:shadow-lg transition-all">
        <div class="flex items-center gap-3 mb-3">
          <div :class="`w-10 h-10 rounded-xl flex items-center justify-center ${card.bg}`">
            <component :is="card.icon" size="18" class="text-white" />
          </div>
          <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">{{ card.label }}</span>
        </div>
        <h3 class="text-2xl font-black text-gray-800">{{ card.value }}</h3>
        <p class="text-[11px] text-gray-400 mt-1">{{ card.sub }}</p>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <Loader2 class="animate-spin text-blue-500" size="36" />
    </div>

    <template v-else>
      <!-- Token 趋势 + 调用次数 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 frosted-card p-6 rounded-2xl border border-white/60">
          <h3 class="font-bold text-gray-800 mb-4 flex items-center gap-2">
            <TrendingUp size="18" class="text-blue-500" /> Daily Token Consumption
          </h3>
          <div ref="tokenChartRef" class="w-full h-[300px]"></div>
        </div>
        <div class="frosted-card p-6 rounded-2xl border border-white/60">
          <h3 class="font-bold text-gray-800 mb-4 flex items-center gap-2">
            <PieChart size="18" class="text-indigo-500" /> Endpoint Distribution
          </h3>
          <div ref="pieChartRef" class="w-full h-[300px]"></div>
        </div>
      </div>

      <!-- 响应时间 + 错误率 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="frosted-card p-6 rounded-2xl border border-white/60">
          <h3 class="font-bold text-gray-800 mb-4 flex items-center gap-2">
            <Clock size="18" class="text-amber-500" /> Avg Response Time by Endpoint
          </h3>
          <div ref="latencyChartRef" class="w-full h-[280px]"></div>
        </div>
        <div class="frosted-card p-6 rounded-2xl border border-white/60">
          <h3 class="font-bold text-gray-800 mb-4 flex items-center gap-2">
            <AlertTriangle size="18" class="text-red-500" /> Daily Error Count
          </h3>
          <div ref="errorChartRef" class="w-full h-[280px]"></div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue';
import api from '../../utils/request';
import * as echarts from 'echarts';
import { TrendingUp, PieChart, Clock, AlertTriangle, Activity, Coins, Timer, Loader2 } from 'lucide-vue-next';

const loading = ref(true);
const selectedDays = ref(30);
const totals = ref({});
const dailyTrend = ref([]);
const endpointDist = ref([]);
const endpointLatency = ref([]);

const tokenChartRef = ref(null);
const pieChartRef = ref(null);
const latencyChartRef = ref(null);
const errorChartRef = ref(null);

let charts = [];

const statCards = ref([]);

const updateStatCards = () => {
  const t = totals.value;
  statCards.value = [
    { label: 'Total Tokens', value: (t.total_tokens || 0).toLocaleString(), sub: `Prompt: ${(t.prompt_tokens || 0).toLocaleString()} / Completion: ${(t.completion_tokens || 0).toLocaleString()}`, icon: Coins, bg: 'bg-blue-600' },
    { label: 'Total Calls', value: (t.total_calls || 0).toLocaleString(), sub: `Last ${selectedDays.value} days`, icon: Activity, bg: 'bg-emerald-500' },
    { label: 'Avg Response', value: `${t.avg_response || 0}s`, sub: 'Per API call', icon: Timer, bg: 'bg-amber-500' },
    { label: 'Error Rate', value: `${t.error_rate || 0}%`, sub: `${t.error_count || 0} failed calls`, icon: AlertTriangle, bg: 'bg-red-500' }
  ];
};

const fetchData = async (days = 30) => {
  selectedDays.value = days;
  loading.value = true;
  try {
    const res = await api.get(`/api/auth/admin/ai-usage/?days=${days}`);
    const data = res.data || res;
    totals.value = data.totals || {};
    dailyTrend.value = data.daily_trend || [];
    endpointDist.value = data.endpoint_distribution || [];
    endpointLatency.value = data.endpoint_latency || [];
    updateStatCards();
    setTimeout(() => renderCharts(), 100);
    renderCharts();
  } catch (e) {
    console.error('AI Usage API Error:', e);
  } finally {
    loading.value = false;
  }
};

const renderCharts = () => {
  charts.forEach(c => c.dispose());
  charts = [];

  // 1. Token 趋势折线图
  if (tokenChartRef.value) {
    const c = echarts.init(tokenChartRef.value);
    charts.push(c);
    c.setOption({
      tooltip: { trigger: 'axis', borderRadius: 12 },
      legend: { data: ['Tokens', 'Calls'], bottom: 0 },
      xAxis: { type: 'category', data: dailyTrend.value.map(d => d.date), axisLine: { show: false }, axisTick: { show: false } },
      yAxis: [
        { type: 'value', name: 'Tokens', splitLine: { lineStyle: { type: 'dashed' } } },
        { type: 'value', name: 'Calls', splitLine: { show: false } }
      ],
      series: [
        { name: 'Tokens', type: 'bar', data: dailyTrend.value.map(d => d.total_tokens), itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 20 },
        { name: 'Calls', type: 'line', yAxisIndex: 1, data: dailyTrend.value.map(d => d.calls), smooth: true, lineStyle: { color: '#10b981', width: 3 }, itemStyle: { color: '#10b981' } }
      ],
      grid: { left: '3%', right: '3%', bottom: '12%', top: '8%', containLabel: true }
    });
  }

  // 2. 接口分布饼图
  if (pieChartRef.value) {
    const c = echarts.init(pieChartRef.value);
    charts.push(c);
    const nameMap = { 'chat.completions/evaluate': 'AI Grading', 'chat.completions/ask': 'AI Assist', 'suggest-kps': 'KP Suggest', 'suggest-rubric': 'Rubric Gen' };
    c.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      series: [{
        type: 'pie', radius: ['40%', '70%'], center: ['50%', '50%'],
        label: { fontSize: 11 },
        data: endpointDist.value.map(e => ({ name: nameMap[e.endpoint] || e.endpoint, value: e.count })),
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' } }
      }]
    });
  }

  // 3. 响应时间柱状图
  if (latencyChartRef.value) {
    const c = echarts.init(latencyChartRef.value);
    charts.push(c);
    const nameMap = { 'chat.completions/evaluate': 'AI Grading', 'chat.completions/ask': 'AI Assist', 'suggest-kps': 'KP Suggest', 'suggest-rubric': 'Rubric Gen' };
    c.setOption({
      tooltip: { trigger: 'axis', formatter: '{b}: {c}s' },
      xAxis: { type: 'category', data: endpointLatency.value.map(e => nameMap[e.endpoint] || e.endpoint), axisLabel: { rotate: 20, fontSize: 11 } },
      yAxis: { type: 'value', name: 'Seconds', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [{
        type: 'bar', barMaxWidth: 40,
        data: endpointLatency.value.map(e => Math.round(e.avg_time * 100) / 100),
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#f59e0b' }, { offset: 1, color: '#fbbf24' }]), borderRadius: [6, 6, 0, 0] }
      }],
      grid: { left: '3%', right: '5%', bottom: '15%', top: '10%', containLabel: true }
    });
  }

  // 4. 错误率趋势
  if (errorChartRef.value) {
    const c = echarts.init(errorChartRef.value);
    charts.push(c);
    c.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: dailyTrend.value.map(d => d.date), axisLine: { show: false }, axisTick: { show: false } },
      yAxis: { type: 'value', name: 'Errors', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [{
        type: 'bar', barMaxWidth: 20,
        data: dailyTrend.value.map(d => d.errors),
        itemStyle: { color: '#ef4444', borderRadius: [4, 4, 0, 0] }
      }],
      grid: { left: '3%', right: '5%', bottom: '3%', top: '10%', containLabel: true }
    });
  }
};

const handleResize = () => charts.forEach(c => c.resize());

onMounted(() => {
  fetchData();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  charts.forEach(c => c.dispose());
});
</script>

<style scoped>
.frosted-card { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); }
</style>