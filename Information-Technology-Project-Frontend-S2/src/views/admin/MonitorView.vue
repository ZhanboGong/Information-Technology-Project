<template>
  <div class="space-y-6 animate-fade-in pt-4 pb-10">
    <div class="flex justify-between items-end">
      <div>
        <h2 class="text-2xl font-black text-gray-800 flex items-center gap-2">
          <Activity class="text-amber-500" /> System Monitor
        </h2>
        <p class="text-sm text-gray-500 mt-1">Real-time monitoring of the asynchronous task queue, the AI scoring engine, and the system load.</p>
      </div>
      <button @click="fetchMonitorData" :disabled="loading" class="px-5 py-2 bg-white border border-gray-200 text-gray-700 font-bold rounded-xl hover:bg-gray-50 transition-all flex items-center gap-2 shadow-sm">
        <RefreshCw :class="{'animate-spin': loading}" size="16" />
        Force Refresh
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div v-for="node in nodes" :key="node.name" class="frosted-card p-6 rounded-[2rem] border border-white/60 shadow-sm relative overflow-hidden">
        <div class="flex justify-between items-start mb-4">
          <div :class="`p-3 rounded-2xl ${node.bgClass || 'bg-blue-50'} ${node.textClass || 'text-blue-500'}`">
            <component :is="getIcon(node.name)" size="24" />
          </div>
          <div :class="['px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest', node.status === 'Online' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600']">
            {{ node.status }}
          </div>
        </div>
        <h4 class="font-bold text-gray-800">{{ node.name }}</h4>
        <p class="text-xs text-gray-400 mt-1">{{ node.desc }}</p>
        <div class="mt-4 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
          <div class="h-full bg-blue-500 rounded-full transition-all duration-1000" :style="{width: node.load + '%'}"></div>
        </div>
        <div class="flex justify-between mt-2">
          <span class="text-[10px] font-black text-gray-400 uppercase">Load</span>
          <span class="text-[10px] font-black text-blue-600">{{ node.load }}%</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div class="frosted-card p-8 rounded-[2.5rem] border border-white/60 flex flex-col min-h-[420px]">
        <h3 class="font-bold text-gray-800 mb-6 flex items-center gap-2">
          <Database size="20" class="text-blue-500" /> Recent Task Queue
        </h3>
        
        <div class="space-y-4">
          <div v-for="task in queueTasks" :key="task.id" class="p-4 bg-white/50 border border-gray-100 rounded-2xl flex items-center justify-between group hover:border-blue-200 transition-all">
            <div class="flex items-center gap-4">
              <div class="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center">
                <FileCode size="20" class="text-slate-400" />
              </div>
              <div>
                <p class="text-sm font-bold text-gray-700">Submission #{{ task.id }}</p>
                <p class="text-[10px] text-gray-400 font-mono uppercase">{{ task.type }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span :class="['text-[10px] font-black px-2 py-1 rounded uppercase', getStatusClass(task.status)]">
                {{ task.status }}
              </span>
              <span class="text-xs text-gray-400">{{ formatTaskTime(task.time) }}</span>
            </div>
          </div>
          <div v-if="queueTasks.length === 0" class="text-center py-20 text-gray-400 text-sm">No active tasks found.</div>
        </div>
      </div>

      <div class="frosted-card p-8 rounded-[2.5rem] border border-white/60">
        <h3 class="font-bold text-gray-800 mb-6 flex items-center gap-2">
          <Zap size="20" class="text-purple-500" /> LLM API Performance
        </h3>
        
        <div class="space-y-10">
          <div v-for="api_item in performanceData" :key="api_item.label">
            <div class="flex justify-between items-end mb-3">
              <div>
                <span class="text-sm font-bold text-gray-700 block">{{ api_item.label }}</span>
                <span class="text-[10px] text-purple-500 font-black uppercase tracking-wider">
                  {{ api_item.extra || 'Monitoring Tokens...' }}
                </span>
              </div>
              <div class="text-right">
                <span class="text-2xl font-black text-purple-600 block">{{ api_item.latency }}ms</span>
                <span class="text-[10px] text-gray-400 font-bold uppercase">Avg Response Time</span>
              </div>
            </div>
            
            <div class="flex gap-1 h-16 items-end px-2 bg-slate-50/50 rounded-xl py-2">
              <div v-for="(val, idx) in api_item.history" :key="idx" 
                   class="flex-1 bg-purple-200 rounded-t-sm hover:bg-purple-500 transition-all cursor-pointer relative group"
                   :style="{height: Math.min((val / 30), 100) + '%'}">
                <div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-[9px] px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-20">
                  {{ val }}ms
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-8 grid grid-cols-2 gap-4">
          <div class="p-4 bg-emerald-50/50 border border-emerald-100 rounded-2xl">
            <p class="text-[10px] font-black text-emerald-600 uppercase mb-1">Service Status</p>
            <p class="text-sm font-bold text-emerald-800">Operational</p>
          </div>
          <div class="p-4 bg-blue-50/50 border border-blue-100 rounded-2xl">
            <p class="text-[10px] font-black text-blue-600 uppercase mb-1">Latest Code</p>
            <p class="text-sm font-bold text-blue-800">200 OK</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { Activity, RefreshCw, Server, Database, Zap, Cpu, FileCode } from 'lucide-vue-next';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';

const loading = ref(false);
const nodes = ref([]);
const queueTasks = ref([]);
const performanceData = ref([]);
let refreshTimer = null;

const getIcon = (name) => {
  if (name.includes('Server')) return Server;
  if (name.includes('Worker') || name.includes('Celery')) return Cpu;
  return Database;
};

const getStatusClass = (status) => {
  const map = {
    'Success': 'bg-emerald-50 text-emerald-600',
    'Running': 'bg-blue-50 text-blue-600',
    'Pending': 'bg-amber-50 text-amber-600',
    'Failed': 'bg-red-50 text-red-600'
  };
  return map[status] || 'bg-gray-50 text-gray-600';
};

const formatTaskTime = (timeStr) => {
  if (!timeStr) return '';
  const date = new Date(timeStr);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const fetchMonitorData = async () => {
  loading.value = true;
  try {
    const res = await api.get('/api/auth/admin/system-monitor/');
    const data = res.data || res;
    nodes.value = data.nodes || [];
    queueTasks.value = data.queueTasks || [];
    performanceData.value = data.apiPerformance || [];
  } catch (err) {
    console.error("Monitor fetch error:", err);
    // ElMessage.error('Failed to sync system metrics.');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchMonitorData();
  // 每 30 秒自动刷新一次，确保持续监控
  refreshTimer = setInterval(fetchMonitorData, 30000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(16px);
}

/* 简单的柱状图动画 */
.transition-all {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>