<template>
  <div class="max-w-[1200px] mx-auto space-y-6 animate-fade-in pt-4 pb-20">
    
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-black text-gray-800">System Configuration</h2>
        <p class="text-sm text-gray-500 mt-1">AI engine, sandbox resources, and real-time system health.</p>
      </div>
      <div class="flex items-center gap-2 px-4 py-2 bg-white/60 backdrop-blur-md border border-white rounded-xl shadow-sm">
        <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
        <span class="text-[10px] font-black text-gray-500 uppercase tracking-widest">System Online</span>
      </div>
    </div>

    <!-- 上半部分：配置区（左右两栏） -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <!-- 左栏：AI 引擎配置 -->
      <div v-loading="loading" class="frosted-card p-6 rounded-2xl border border-white/60 shadow-sm">
        <h3 class="text-base font-bold text-gray-800 mb-5 flex items-center gap-2.5">
          <div class="p-2 bg-blue-50 text-blue-600 rounded-xl"><Cpu size="18"/></div>
          LLM Engine Settings
        </h3>

        <div class="space-y-4">
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">API Key</label>
            <el-input v-model="config.deepseek_api_key" type="password" show-password placeholder="sk-..." class="custom-input" />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Model</label>
              <el-select v-model="config.deepseek_model_name" filterable allow-create default-first-option placeholder="Model" class="w-full custom-select">
                <el-option label="deepseek-chat" value="deepseek-chat" />
                <el-option label="deepseek-reasoner" value="deepseek-reasoner" />
                <el-option label="deepseek-coder" value="deepseek-coder" />
              </el-select>
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Base URL</label>
              <el-input v-model="config.deepseek_base_url" placeholder="https://api.deepseek.com" class="custom-input" />
            </div>
          </div>

          <!-- 连接测试结果 -->
          <transition name="el-zoom-in-top">
            <div v-if="testResult" class="p-3 bg-emerald-50 border border-emerald-100 rounded-xl flex items-center justify-between">
              <div class="flex items-center gap-2">
                <CheckCircle2 size="16" class="text-emerald-500" />
                <span class="text-xs font-bold text-emerald-700">Connected</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-[10px] text-emerald-600 font-bold">{{ testResult.balance }}</span>
                <div class="flex gap-1">
                  <span v-for="m in (testResult.models || []).slice(0, 2)" :key="m" class="px-1.5 py-0.5 bg-white/60 rounded text-[9px] font-bold text-emerald-600 border border-emerald-100">{{ m }}</span>
                </div>
              </div>
            </div>
          </transition>

          <div class="flex gap-2">
            <button @click="handleSave('llm')" :disabled="saving" class="flex-1 py-2.5 bg-blue-600 text-white text-sm font-bold rounded-xl shadow-md flex items-center justify-center gap-1.5 hover:bg-blue-700 transition-all active:scale-[0.98] disabled:opacity-50">
              <Loader2 v-if="saving" class="animate-spin" size="16" />
              <Save v-else size="16" />
              Save
            </button>
            <button @click="testConnection" :disabled="testing" class="px-5 py-2.5 bg-white border border-gray-200 text-gray-600 text-sm font-bold rounded-xl hover:bg-gray-50 transition-all flex items-center gap-1.5 active:scale-[0.98]">
              <Loader2 v-if="testing" class="animate-spin" size="16" />
              <Zap v-else size="16" />
              Test
            </button>
          </div>
        </div>
      </div>

      <!-- 右栏：Docker 沙箱配额 -->
      <div v-loading="loading" class="frosted-card p-6 rounded-2xl border border-white/60 shadow-sm">
        <h3 class="text-base font-bold text-gray-800 mb-5 flex items-center gap-2.5">
          <div class="p-2 bg-indigo-50 text-indigo-600 rounded-xl"><ShieldCheck size="18"/></div>
          Sandbox Resource Quotas
        </h3>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Memory Limit</label>
            <el-input v-model="config.docker_mem_limit" placeholder="512m" class="custom-input">
              <template #suffix><span class="text-[10px] font-bold text-gray-400">RAM</span></template>
            </el-input>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Timeout</label>
            <el-input v-model="config.docker_timeout" placeholder="30" class="custom-input">
              <template #suffix><span class="text-[10px] font-bold text-gray-400">SEC</span></template>
            </el-input>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">CPU Quota (Nano)</label>
            <el-input-number v-model="config.docker_cpu_quota" :step="100000000" :min="100000000" class="w-full custom-number-input" />
            <p class="text-[9px] text-gray-400 italic">1,000,000,000 = 1 Core</p>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Max Processes</label>
            <el-input-number v-model="config.docker_pids_limit" :min="10" :max="500" class="w-full custom-number-input" />
          </div>
        </div>

        <div class="mt-4 p-3 bg-indigo-50/50 border border-indigo-100 rounded-xl flex gap-2 items-start">
          <ShieldCheck class="text-indigo-400 shrink-0 mt-0.5" size="14" />
          <p class="text-[11px] text-indigo-600 leading-relaxed">Prevents resource exhaustion and fork bomb attacks.</p>
        </div>

        <button @click="handleSave('docker')" :disabled="saving" class="w-full mt-4 py-2.5 bg-indigo-600 text-white text-sm font-bold rounded-xl shadow-md flex items-center justify-center gap-1.5 hover:bg-indigo-700 transition-all active:scale-[0.98] disabled:opacity-50">
          <Loader2 v-if="saving" class="animate-spin" size="16" />
          <Save v-else size="16" />
          Apply Quotas
        </button>
      </div>
    </div>

    <!-- 下半部分：监控区（左右两栏） -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Docker 容器监控（占 2 列） -->
      <div class="lg:col-span-2 frosted-card p-6 rounded-2xl border border-white/60 shadow-sm">
        <div class="flex justify-between items-center mb-5">
          <h3 class="text-base font-bold text-gray-800 flex items-center gap-2.5">
            <div class="p-2 bg-cyan-50 text-cyan-600 rounded-xl"><Container size="18"/></div>
            Docker Containers
          </h3>
          <button @click="fetchHealth" :disabled="healthLoading" class="px-3 py-1.5 bg-cyan-50 text-cyan-600 rounded-lg text-[11px] font-bold border border-cyan-100 hover:bg-cyan-600 hover:text-white transition-all flex items-center gap-1">
            <Loader2 v-if="healthLoading" size="12" class="animate-spin" />
            <RefreshCw v-else size="12" />
            Refresh
          </button>
        </div>

        <div v-if="healthLoading" class="py-12 text-center text-gray-400 text-sm">Loading...</div>
        <div v-else-if="dockerContainers.length === 0" class="py-12 text-center text-gray-300 text-sm">No containers found</div>
        <div v-else class="space-y-2">
          <div v-for="c in dockerContainers" :key="c.name" class="p-3 bg-gray-50/80 rounded-xl border border-gray-100 flex items-center justify-between hover:bg-gray-50 transition-colors">
            <div class="flex items-center gap-3">
              <div class="w-2 h-2 rounded-full shrink-0" :class="c.status === 'running' ? 'bg-emerald-500' : c.status === 'exited' ? 'bg-red-400' : 'bg-amber-400'"></div>
              <div class="min-w-0">
                <p class="text-sm font-bold text-gray-800 truncate">{{ c.name }}</p>
                <p class="text-[10px] text-gray-400 truncate">{{ c.image }}</p>
              </div>
            </div>
            <div v-if="c.status === 'running' && c.stats" class="flex items-center gap-5 shrink-0 ml-4">
              <div class="text-center w-12">
                <p class="text-[9px] font-bold text-gray-400 uppercase">CPU</p>
                <p class="text-sm font-black" :class="c.stats.cpu_percent > 80 ? 'text-red-500' : 'text-gray-700'">{{ c.stats.cpu_percent }}%</p>
              </div>
              <div class="w-20">
                <div class="flex justify-between items-center mb-1">
                  <p class="text-[9px] font-bold text-gray-400 uppercase">MEM</p>
                  <p class="text-[10px] font-black text-gray-600">{{ c.stats.mem_percent }}%</p>
                </div>
                <div class="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-500" :class="c.stats.mem_percent > 80 ? 'bg-red-500' : c.stats.mem_percent > 60 ? 'bg-amber-500' : 'bg-emerald-500'" :style="{ width: Math.min(c.stats.mem_percent, 100) + '%' }"></div>
                </div>
              </div>
            </div>
            <span v-else class="text-[10px] text-gray-400 font-bold uppercase shrink-0 ml-4">{{ c.status }}</span>
          </div>
        </div>
      </div>

      <!-- Redis 缓存（占 1 列） -->
      <div class="frosted-card p-6 rounded-2xl border border-white/60 shadow-sm flex flex-col">
        <h3 class="text-base font-bold text-gray-800 mb-5 flex items-center gap-2.5">
          <div class="p-2 bg-red-50 text-red-600 rounded-xl"><Database size="18"/></div>
          Redis Cache
        </h3>

        <div v-if="redisStats.status === 'offline'" class="flex-1 flex flex-col items-center justify-center py-6">
          <div class="w-10 h-10 bg-red-50 rounded-full flex items-center justify-center mb-2">
            <WifiOff size="18" class="text-red-400" />
          </div>
          <p class="text-sm font-bold text-red-400">Offline</p>
        </div>

        <div v-else class="flex-1 space-y-3">
          <!-- Hit Rate 大数字 -->
          <div class="text-center py-3 bg-emerald-50 rounded-xl border border-emerald-100">
            <p class="text-[10px] font-black text-emerald-500 uppercase tracking-widest">Hit Rate</p>
            <p class="text-3xl font-black text-emerald-700 mt-1">{{ redisStats.hit_rate }}<span class="text-lg">%</span></p>
          </div>
          
          <div class="grid grid-cols-2 gap-2">
            <div class="p-3 bg-blue-50 rounded-xl border border-blue-100 text-center">
              <p class="text-[9px] font-black text-blue-400 uppercase">Hits</p>
              <p class="text-lg font-black text-blue-700 mt-0.5">{{ formatNum(redisStats.hits) }}</p>
            </div>
            <div class="p-3 bg-amber-50 rounded-xl border border-amber-100 text-center">
              <p class="text-[9px] font-black text-amber-400 uppercase">Misses</p>
              <p class="text-lg font-black text-amber-700 mt-0.5">{{ formatNum(redisStats.misses) }}</p>
            </div>
          </div>

          <div class="p-3 bg-purple-50 rounded-xl border border-purple-100 flex items-center justify-between">
            <span class="text-[10px] font-black text-purple-400 uppercase">Memory</span>
            <span class="text-sm font-black text-purple-700">{{ redisStats.used_memory }}</span>
          </div>
          <div class="p-3 bg-gray-50 rounded-xl border border-gray-100 flex items-center justify-between">
            <span class="text-[10px] font-black text-gray-400 uppercase">Clients</span>
            <span class="text-sm font-black text-gray-700">{{ redisStats.connected_clients }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { 
  Cpu, Save, Loader2, Zap, ShieldCheck, Container, 
  RefreshCw, Database, WifiOff, CheckCircle2
} from 'lucide-vue-next';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';

const saving = ref(false);
const loading = ref(false);
const testing = ref(false);
const testResult = ref(null);
const healthLoading = ref(false);
const dockerContainers = ref([]);
const redisStats = ref({ status: 'offline' });

const config = reactive({
  deepseek_api_key: '',
  deepseek_base_url: '',
  deepseek_model_name: '',
  docker_mem_limit: '512m',
  docker_cpu_quota: 1000000000,
  docker_pids_limit: 50,
  docker_timeout: 30
});

const formatNum = (n) => {
  if (!n && n !== 0) return '0';
  return n.toLocaleString();
};

const fetchHealth = async () => {
  healthLoading.value = true;
  try {
    const res = await api.get('/api/auth/admin/system-health/');
    const data = res.data || res;
    dockerContainers.value = data.docker_containers || [];
    redisStats.value = data.redis || { status: 'offline' };
  } catch (e) {
    console.error('Health check failed:', e);
  } finally {
    healthLoading.value = false;
  }
};

const validateInput = (type) => {
  if (type === 'llm') {
    if (!config.deepseek_api_key || !config.deepseek_api_key.trim()) {
      ElMessage.warning('API Key cannot be empty.');
      return false;
    }
  }
  if (type === 'docker') {
    const memRegex = /^\d+[kmg]?$/i;
    if (!memRegex.test(config.docker_mem_limit)) {
      ElMessage.error('Invalid Memory format. Use e.g., "512m", "1g".');
      return false;
    }
    const timeout = parseInt(config.docker_timeout);
    if (isNaN(timeout) || timeout <= 0 || timeout > 300) {
      ElMessage.error('Timeout must be 1-300 seconds.');
      return false;
    }
  }
  return true;
};

const fetchConfig = async () => {
  loading.value = true;
  try {
    const res = await api.get('/api/auth/admin/system-config/get_settings/');
    const data = res.data || res;
    Object.assign(config, data);
    if (config.deepseek_api_key) silentCheck();
  } catch (err) {
    ElMessage.error('Failed to load config.');
  } finally {
    loading.value = false;
  }
};

const silentCheck = async () => {
  try {
    const res = await api.post('/api/auth/admin/system-config/test-connection/', config);
    testResult.value = res.data;
  } catch (err) {
    console.warn('Silent check failed.');
  }
};

const handleSave = async (type) => {
  if (!validateInput(type)) return;
  saving.value = true;
  try {
    await api.post('/api/auth/admin/system-config/update_settings/', config);
    ElMessage.success(type === 'llm' ? 'AI Engine saved.' : 'Sandbox quotas applied.');
    if (type === 'llm') testConnection();
  } catch (err) {
    ElMessage.error('Save failed.');
  } finally {
    saving.value = false;
  }
};

const testConnection = async () => {
  if (!config.deepseek_api_key) return ElMessage.warning('API Key required');
  testing.value = true;
  testResult.value = null;
  try {
    const res = await api.post('/api/auth/admin/system-config/test-connection/', config);
    testResult.value = res.data;
    ElMessage.success('Connected!');
  } catch (err) {
    ElMessage.error(err.response?.data?.message || 'Connection failed.');
  } finally {
    testing.value = false;
  }
};

onMounted(() => {
  fetchConfig();
  fetchHealth();
});
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
:deep(.custom-input .el-input__wrapper),
:deep(.custom-select .el-input__wrapper),
:deep(.custom-number-input .el-input__wrapper) {
  border-radius: 10px;
  background-color: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  padding: 4px 10px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
}
:deep(.custom-number-input) { width: 100%; }
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #2563eb !important;
  border-color: #2563eb !important;
}
.animate-fade-in { animation: fadeIn 0.4s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>