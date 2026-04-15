<template>
  <div class="space-y-6 animate-fade-in pt-4 pb-10">
    <div class="flex justify-between items-end">
      <div>
        <h2 class="text-2xl font-black text-gray-800 flex items-center gap-2">
          <FileText class="text-indigo-500" /> System Audit Logs
        </h2>
        <p class="text-sm text-gray-500 mt-1">Record all system AI interface calls, Token consumption and performance data.</p>
      </div>
      <div class="flex gap-3">
        <el-input v-model="search" placeholder="Filter by endpoint..." class="w-64 custom-input" clearable />
        <button @click="fetchLogs" :disabled="loading" class="p-2.5 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-all">
          <RefreshCw :class="{'animate-spin': loading}" size="20" class="text-gray-500" />
        </button>
      </div>
    </div>

    <div class="frosted-card rounded-[2.5rem] border border-white/60 overflow-hidden shadow-sm">
      <el-table 
        v-loading="loading" 
        :data="filteredLogs" 
        style="width: 100%" 
        class="admin-table"
        :row-class-name="getRowClass"
      >
        <el-table-column label="TIMESTAMP" width="180">
          <template #default="scope">
            <span class="text-xs font-mono text-gray-500">{{ formatTime(scope.row.time) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="SERVICE / ENDPOINT" min-width="250">
          <template #default="scope">
            <div class="flex items-center gap-3">
              <div :class="['w-2 h-2 rounded-full', scope.row.status === 200 ? 'bg-emerald-500' : 'bg-red-500']"></div>
              <div>
                <p class="text-sm font-bold text-gray-700">{{ scope.row.endpoint }}</p>
                <p class="text-[10px] text-gray-400 font-black uppercase">{{ scope.row.service }}</p>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="USAGE (TOKENS)" width="150">
          <template #default="scope">
            <div class="flex items-center gap-2">
              <Zap size="14" class="text-amber-500" />
              <span class="text-sm font-black text-gray-600">{{ scope.row.tokens.toLocaleString() }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="LATENCY" width="120">
          <template #default="scope">
            <el-tag size="small" :type="parseFloat(scope.row.latency) > 2000 ? 'danger' : 'info'" class="rounded-lg font-bold">
              {{ scope.row.latency }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="STATUS" width="120">
          <template #default="scope">
            <span :class="['text-xs font-black px-2 py-1 rounded', scope.row.status === 200 ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600']">
              HTTP {{ scope.row.status }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="DETAILS" width="100" align="right">
          <template #default="scope">
            <button @click="viewDetails(scope.row)" class="text-blue-500 hover:text-blue-700 font-bold text-xs">VIEW</button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { FileText, RefreshCw, Zap } from 'lucide-vue-next';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';

const loading = ref(false);
const search = ref('');
const logs = ref([]);

const fetchLogs = async () => {
  loading.value = true;
  try {
    const res = await api.get('/api/auth/admin/system-logs/');
    logs.value = res.data || res;
  } catch (err) {
    console.error(err);
    ElMessage.error('Failed to load system logs');
  } finally {
    loading.value = false;
  }
};

const filteredLogs = computed(() => {
  if (!search.value) return logs.value;
  return logs.value.filter(log => 
    log.endpoint.toLowerCase().includes(search.value.toLowerCase())
  );
});

const formatTime = (timeStr) => {
  const d = new Date(timeStr);
  return d.toLocaleString('zh-CN', { hour12: false });
};

const getRowClass = ({ row }) => {
  return row.status !== 200 ? 'error-row' : '';
};

const viewDetails = (row) => {
  // 这里可以扩展一个弹窗展示具体的 Request/Response Payload
  ElMessage.info(`Log ID: ${row.id} - 详细原始报文需对接日志存储服务。`);
};

onMounted(fetchLogs);
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(16px);
}

:deep(.admin-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(248, 250, 252, 0.5);
}

:deep(.error-row) {
  background-color: rgba(254, 242, 242, 0.5) !important;
}

.custom-input :deep(.el-input__wrapper) {
  border-radius: 0.75rem;
  background-color: white;
  box-shadow: none;
  border: 1px solid #e2e8f0;
}
</style>