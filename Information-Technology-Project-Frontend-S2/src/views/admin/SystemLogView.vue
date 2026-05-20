<template>
  <div class="space-y-6 animate-fade-in pt-4 pb-10">
    <div class="flex justify-between items-end">
      <div>
        <h2 class="text-2xl font-black text-gray-800 flex items-center gap-2">
          <FileText class="text-indigo-500" /> System Audit Logs
        </h2>
        <p class="text-sm text-gray-500 mt-1">
          Record all system AI interface calls, Token consumption, and administrator operation records.
        </p>
      </div>
      <div class="flex gap-3">
        <el-input 
          v-model="search" 
          :placeholder="activeTab === 'ai' ? 'Filter by endpoint...' : 'Filter by operator or detail...'" 
          class="w-64 custom-input" 
          clearable 
        />
        <button @click="fetchLogs" :disabled="loading" class="p-2.5 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-all">
          <RefreshCw :class="{'animate-spin': loading}" size="20" class="text-gray-500" />
        </button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="resetPagination">
      <el-tab-pane name="ai">
        <template #label>
          <div class="flex items-center gap-2 px-2">
            <Activity size="16" />
            <span class="font-bold">AI Service Traffic</span>
          </div>
        </template>
        
        <div class="frosted-card rounded-[2.5rem] border border-white/60 overflow-hidden shadow-sm mt-2">
          <el-table 
            v-loading="loading" 
            :data="pagedAiLogs" 
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
                    <p class="text-sm font-bold text-gray-700">{{ scope.row.endpoint || 'Chat Completion' }}</p>
                    <p class="text-[10px] text-gray-400 font-black uppercase">{{ scope.row.service }}</p>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="USAGE (TOKENS)" width="150">
              <template #default="scope">
                <div class="flex items-center gap-2">
                  <Zap size="14" class="text-amber-500" />
                  <span class="text-sm font-black text-gray-600">{{ (scope.row.tokens || 0).toLocaleString() }}</span>
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

          <div class="p-6 flex justify-center border-t border-gray-100 bg-white/30">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              layout="prev, pager, next, total"
              :total="filteredAiLogs.length"
              background
              class="custom-pagination"
            />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="ops">
        <template #label>
          <div class="flex items-center gap-2 px-2">
            <ShieldCheck size="16" />
            <span class="font-bold">Operation Audit</span>
          </div>
        </template>

        <div class="frosted-card rounded-[2.5rem] border border-white/60 overflow-hidden shadow-sm mt-2">
          <el-table 
            v-loading="loading" 
            :data="pagedOpsLogs" 
            style="width: 100%" 
            class="admin-table"
          >
            <el-table-column label="TIMESTAMP" width="180">
              <template #default="scope">
                <span class="text-xs font-mono text-gray-500">{{ formatTime(scope.row.time) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="OPERATOR" width="150">
              <template #default="scope">
                <div class="flex items-center gap-2">
                  <div class="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-black text-[10px]">
                    {{ scope.row.user ? scope.row.user.charAt(0).toUpperCase() : 'U' }}
                  </div>
                  <span class="text-sm font-bold text-gray-700">{{ scope.row.user }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="ACTION" width="120">
              <template #default="scope">
                <el-tag :type="getActionType(scope.row.action)" effect="dark" size="small" class="rounded-lg font-black italic">
                  {{ scope.row.action }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="TARGET" width="140">
              <template #default="scope">
                <span class="text-xs font-mono bg-gray-100 px-2 py-1 rounded text-gray-600">{{ scope.row.target }}</span>
              </template>
            </el-table-column>
            <el-table-column label="DETAILS">
              <template #default="scope">
                <p class="text-sm text-gray-600">{{ scope.row.detail }}</p>
              </template>
            </el-table-column>
          </el-table>

          <div class="p-6 flex justify-center border-t border-gray-100 bg-white/30">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              layout="prev, pager, next, total"
              :total="filteredOpsLogs.length"
              background
              class="custom-pagination"
            />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { FileText, RefreshCw, Zap, Activity, ShieldCheck } from 'lucide-vue-next';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';

// 基础状态
const loading = ref(false);
const search = ref('');
const activeTab = ref('ai');

// 🚀 新增分页状态
const currentPage = ref(1);
const pageSize = ref(10); // 每页显示 10 条

const logData = ref({
  ai_logs: [],
  ops_logs: []
});

const fetchLogs = async () => {
  loading.value = true;
  try {
    const res = await api.get('/api/auth/admin/system-logs/');
    const responseData = res.data || res;
    if (responseData && responseData.ai_logs) {
      logData.value = responseData;
    } else if (Array.isArray(responseData)) {
      logData.value.ai_logs = responseData;
      logData.value.ops_logs = [];
    }
  } catch (err) {
    ElMessage.error('Failed to load system logs');
  } finally {
    loading.value = false;
  }
};

// 切换 Tab 时重置页码
const resetPagination = () => {
  currentPage.value = 1;
};

// --- 计算属性：过滤数据 ---
const filteredAiLogs = computed(() => {
  const data = logData.value.ai_logs || [];
  if (!search.value) return data;
  return data.filter(log => 
    (log.endpoint || '').toLowerCase().includes(search.value.toLowerCase()) ||
    (log.service || '').toLowerCase().includes(search.value.toLowerCase())
  );
});

const filteredOpsLogs = computed(() => {
  const data = logData.value.ops_logs || [];
  if (!search.value) return data;
  return data.filter(log => 
    (log.detail || '').toLowerCase().includes(search.value.toLowerCase()) ||
    (log.user || '').toLowerCase().includes(search.value.toLowerCase())
  );
});

// --- 🚀 核心逻辑：分页切片数据 ---
const pagedAiLogs = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredAiLogs.value.slice(start, end);
});

const pagedOpsLogs = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredOpsLogs.value.slice(start, end);
});

// --- 工具函数 ---
const formatTime = (timeStr) => {
  if (!timeStr) return '--';
  const d = new Date(timeStr);
  return d.toLocaleString('zh-CN', { hour12: false });
};

const getRowClass = ({ row }) => {
  return row.status !== 200 ? 'error-row' : '';
};

const getActionType = (action) => {
  const map = { 'UPDATE': 'warning', 'DELETE': 'danger', 'CREATE': 'success', 'RESOLVE': 'primary' };
  return map[action] || 'info';
};

const viewDetails = (row) => {
  ElMessage.info(`Log ID: ${row.id}`);
};

onMounted(fetchLogs);
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(16px);
}

/* Tabs 样式美化 */
.custom-tabs :deep(.el-tabs__nav-wrap::after) { display: none; }
.custom-tabs :deep(.el-tabs__item) { color: #94a3b8; font-size: 0.9rem; transition: all 0.3s; height: 45px; }
.custom-tabs :deep(.el-tabs__item.is-active) { color: #4f46e5; }
.custom-tabs :deep(.el-tabs__active-bar) { background-color: #4f46e5; height: 3px; border-radius: 3px; }

/* 分页器美化 */
.custom-pagination :deep(.el-pager li) {
  background: transparent !important;
  border-radius: 8px;
  font-weight: 700;
}
.custom-pagination :deep(.el-pager li.is-active) {
  background-color: #4f46e5 !important;
  color: white !important;
}

:deep(.admin-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(248, 250, 252, 0.5);
}

:deep(.error-row) { background-color: rgba(254, 242, 242, 0.5) !important; }
.custom-input :deep(.el-input__wrapper) { border-radius: 0.75rem; background-color: white; box-shadow: none; border: 1px solid #e2e8f0; }
</style>