<template>
  <div class="space-y-6 animate-fade-in h-full flex flex-col">
    <div class="frosted-card p-8 rounded-2xl border border-white/60 shrink-0 shadow-sm">
        <h3 class="text-lg font-bold text-gray-800 mb-6">数据报表导出</h3>
        <div class="flex gap-4">
            <button @click="exportData('PDF')" :disabled="isExporting === 'PDF'" class="flex items-center gap-2 px-6 py-4 bg-red-50 text-red-600 rounded-xl hover:bg-red-100 transition border border-red-100 shadow-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed">
                <Loader2 v-if="isExporting === 'PDF'" class="animate-spin" size="20"/>
                <FileText v-else size="20" /> 导出 PDF 成绩单
            </button>
            <button @click="exportData('Excel')" :disabled="isExporting === 'Excel'" class="flex items-center gap-2 px-6 py-4 bg-green-50 text-green-600 rounded-xl hover:bg-green-100 transition border border-green-100 shadow-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed">
                <Loader2 v-if="isExporting === 'Excel'" class="animate-spin" size="20"/>
                <Sheet v-else size="20" /> 导出 Excel 数据
            </button>
        </div>
    </div>
    
    <div class="frosted-card p-8 rounded-2xl flex-1 border border-white/60 flex flex-col overflow-hidden shadow-sm">
        <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
                <Activity size="20" class="text-blue-500" /> 系统操作日志
            </h3>
            <button @click="fetchLogs" class="text-gray-400 hover:text-blue-500 transition-colors">
                <RefreshCw :class="{'animate-spin': isLoadingLogs}" size="18"/>
            </button>
        </div>
        
        <div v-if="isLoadingLogs && logs.length === 0" class="flex-1 flex justify-center items-center">
            <Loader2 class="animate-spin text-blue-500" size="32"/>
        </div>
        
        <div v-else class="flex-1 overflow-y-auto font-mono text-xs bg-gray-900/95 text-green-400 p-5 rounded-xl shadow-inner custom-scrollbar relative">
            <div v-for="(log, idx) in logs" :key="idx" class="mb-2 opacity-80 hover:opacity-100 hover:bg-white/10 p-1.5 rounded transition break-all">
                <span class="text-blue-400">[{{ log.timestamp }}]</span> 
                User <span class="text-yellow-400">'{{ log.username }}'</span> accessed <span class="text-purple-400">{{ log.path }}</span> 
                - Action: <span class="text-white font-bold">{{ log.action }}</span>
                <span v-if="log.details" class="text-gray-400 ml-2">// {{ log.details }}</span>
            </div>
            
            <div v-if="logs.length === 0" class="text-center text-gray-500 mt-10 flex flex-col items-center">
                <Inbox size="32" class="mb-2 opacity-50"/>
                暂无操作日志记录
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';
import { FileText, Sheet, Loader2, Activity, RefreshCw, Inbox } from 'lucide-vue-next';

const logs = ref([]);
const isLoadingLogs = ref(true);
const isExporting = ref(null);

// 真实调用：获取系统日志
const fetchLogs = async () => {
    isLoadingLogs.value = true;
    try {
        const res = await api.get('/api/analytics/stats/system-logs/');
        logs.value = res.results || res.data || res || [];
    } catch (e) {
        ElMessage.error('获取系统日志失败，后端接口未实现');
    } finally {
        isLoadingLogs.value = false;
    }
};

// 真实调用：接收后端的文件流 (Blob) 并触发下载
const exportData = async (type) => {
    isExporting.value = type;
    try {
        ElMessage.info(`正在生成 ${type}，请稍候...`);
        const endpoint = type === 'PDF' ? '/api/analytics/stats/export-pdf/' : '/api/analytics/stats/export-excel/';
        
        // 🚨 核心：必须指定 responseType 为 blob，否则下载的 Excel/PDF 会是乱码损坏的文件
        const response = await api.get(endpoint, { responseType: 'blob' });
        
        const url = window.URL.createObjectURL(new Blob([response]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `教学报表_${new Date().toISOString().slice(0,10)}.${type === 'Excel' ? 'csv' : 'pdf'}`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        
        ElMessage.success(`${type} 文件导出成功！`);
    } catch (e) {
        ElMessage.error(`${type} 文件导出失败，后端接口可能未实现`);
    } finally {
        isExporting.value = null;
    }
};

onMounted(() => {
    fetchLogs();
});
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
}
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.5);
}
</style>