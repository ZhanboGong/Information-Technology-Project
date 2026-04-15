<template>
  <div class="space-y-6 animate-fade-in max-w-5xl mx-auto pt-2 pb-10">
    <div class="flex items-center gap-4 mb-6">
      <button @click="router.back()" class="p-2.5 frosted-card rounded-xl text-gray-500 hover:text-blue-600 transition-all border border-white/60">
        <ArrowLeft size="20" />
      </button>
      <div>
        <h2 class="text-2xl font-bold text-gray-800 tracking-tight">{{ assignment?.title || 'Loading assignment...' }}</h2>
        <p class="text-sm text-gray-500 mt-1">Please upload a ZIP archive containing your source code. The system will perform sandbox testing and AI evaluation automatically.</p>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-6">
      <div class="col-span-2 frosted-card p-6 rounded-2xl border border-white/60 flex items-center justify-between bg-gradient-to-r from-blue-50/50 to-transparent">
        <div>
          <p class="text-sm font-bold text-gray-500 mb-1">Attempts Remaining</p>
          <div class="flex items-baseline gap-2">
            <span class="text-4xl font-black" :class="attemptsLeft > 0 ? 'text-blue-600' : 'text-red-500'">{{ attemptsLeft }}</span>
            <span class="text-lg font-bold text-gray-400">/ {{ assignment?.max_attempts || 10 }}</span>
          </div>
        </div>
        <div class="text-right">
          <p class="text-xs text-gray-400 mb-1">Deadline</p>
          <p class="text-lg font-mono font-bold text-orange-500">{{ formatTime(assignment?.deadline) }}</p>
        </div>
      </div>
      <div class="frosted-card p-6 rounded-2xl border border-white/60 flex flex-col justify-center items-center text-center">
        <div v-if="historyLogs.length > 0" class="flex flex-col items-center">
          <CheckCircle2 size="32" class="text-green-500 mb-2" />
          <p class="font-bold text-gray-700">Submitted</p>
        </div>
        <div v-else class="flex flex-col items-center">
          <AlertCircle size="32" class="text-amber-400 mb-2" />
          <p class="font-bold text-gray-700">No Submission</p>
        </div>
      </div>
    </div>

    <div class="frosted-card p-8 rounded-2xl border border-white/60">
      <h3 class="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
        <UploadCloud size="20" class="text-blue-600"/> Upload Source Code (ZIP)
      </h3>
      
      <div 
        class="border-2 border-dashed rounded-2xl p-10 text-center transition-all"
        :class="[attemptsLeft <= 0 ? 'border-gray-200 bg-gray-50 opacity-60' : (isDragging ? 'border-blue-500 bg-blue-50' : 'border-blue-200 bg-blue-50/30 hover:bg-blue-50')]"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <div v-if="!selectedFile">
          <FileArchive size="48" class="mx-auto text-blue-400 mb-4" />
          <p class="font-bold text-gray-700 text-lg mb-1">Click or drag ZIP file here</p>
          <p class="text-sm text-gray-500 mb-6">Ensure root directory contains 'src' or relevant configuration files</p>
          <button 
            :disabled="attemptsLeft <= 0"
            @click="triggerFileSelect"
            class="px-6 py-2.5 bg-white border border-gray-200 rounded-xl font-bold text-sm text-blue-600 shadow-sm hover:border-blue-300 disabled:opacity-50"
          >
            Select Local File
          </button>
          <input type="file" ref="fileInput" class="hidden" accept=".zip" @change="handleFileSelect">
        </div>
        
        <div v-else class="flex flex-col items-center">
          <div class="w-16 h-16 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
            <FileCode size="32" class="text-blue-600" />
          </div>
          <p class="font-bold text-gray-800 mb-1">{{ selectedFile.name }}</p>
          <p class="text-xs text-gray-500 mb-6">{{ (selectedFile.size / 1024 / 1024).toFixed(2) }} MB</p>
          
          <div class="flex gap-4">
            <button @click="selectedFile = null" :disabled="isSubmitting" class="px-6 py-2.5 bg-gray-100 text-gray-600 rounded-xl font-bold text-sm hover:bg-gray-200 transition-all">Reselect</button>
            <button @click="confirmSubmit" :disabled="isSubmitting" class="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-bold text-sm shadow-md hover:bg-blue-700 transition-all flex items-center gap-2">
              <Loader2 v-if="isSubmitting" size="16" class="animate-spin" />
              {{ isSubmitting ? 'Submitting...' : 'Confirm & Submit' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="frosted-card rounded-2xl border border-white/60 overflow-hidden">
      <div class="p-6 border-b border-gray-100 bg-white/40 flex justify-between items-center">
        <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2"><History size="20" class="text-blue-600"/> Submission History</h3>
        <button @click="fetchHistory" class="text-xs text-blue-600 hover:underline">Refresh</button>
      </div>
      
      <div class="p-0 overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50/50 text-xs text-gray-500 uppercase">
              <th class="p-4 font-bold">Submission Time</th>
              <th class="p-4 font-bold">Attempt</th>
              <th class="p-4 font-bold">Status</th>
              <th class="p-4 font-bold">Action</th>
            </tr>
          </thead>
          <tbody class="text-sm divide-y divide-gray-100">
            <tr v-for="log in historyLogs" :key="log.id" class="hover:bg-blue-50/30 transition-colors">
              <td class="p-4 text-gray-700 font-medium">{{ formatTime(log.created_at) }}</td>
              <td class="p-4 text-gray-500">Attempt #{{ log.attempt_number || '-' }}</td>
              <td class="p-4">
                <span :class="getStatusClass(log.status)" class="px-2.5 py-1 rounded-md font-bold text-xs border">
                  {{ getStatusText(log.status) }}
                </span>
              </td>
              <td class="p-4">
                <button 
                  v-if="log.status === 'completed' || log.status === 'failed'"
                  @click="goToDetail(log)" 
                  class="text-blue-600 font-bold text-xs hover:underline flex items-center gap-1"
                >
                  <Terminal size="14" /> View Feedback Details
                </button>
                <span v-else class="text-gray-400 text-xs italic">Processing...</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';
import { 
  ArrowLeft, UploadCloud, FileArchive, FileCode, Loader2, 
  History, Terminal, CheckCircle2, AlertCircle, X 
} from 'lucide-vue-next';

const router = useRouter();
const route = useRoute();
const assignmentId = route.params.assignId;

const assignment = ref(null);
const historyLogs = ref([]);
const loading = ref(true);
const isSubmitting = ref(false);
const isDragging = ref(false);
const selectedFile = ref(null);
const fileInput = ref(null);

// 修改点：定义跳转函数
const goToDetail = (record) => {
  // 根据你的路由配置跳转到成绩详情页
  if (record && record.id){
    router.push(`/student/grades/detail/${record.id}`);
  }else{
    console.error("Invalid record:", record);
  }

};

const attemptsLeft = computed(() => {
  if (!assignment.value) return 0;
  return Math.max(0, assignment.value.max_attempts - historyLogs.value.length);
});

const initData = async () => {
  try {
    loading.value = true;
    const assignRes = await api.get(`/api/auth/student/assignments/`);
    const allAssigns = assignRes.data || assignRes;
    assignment.value = allAssigns.find(a => String(a.id) === String(assignmentId));
    await fetchHistory();
  } catch (error) {
    ElMessage.error('Failed to initialize page');
  } finally {
    loading.value = false;
  }
};

const fetchHistory = async () => {
  try {
    const subRes = await api.get('/api/auth/student/submissions/');
    const allSubs = subRes.data || subRes;
    historyLogs.value = allSubs
      .filter(s => String(s.assignment) === String(assignmentId))
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  } catch (e) {
    console.error('Failed to fetch submission history');
  }
};

const triggerFileSelect = () => fileInput.value.click();
const handleFileSelect = (e) => {
  const file = e.target.files[0];
  if (file && file.name.endsWith('.zip')) selectedFile.value = file;
  else ElMessage.error('Only ZIP archives are supported');
};
const handleDrop = (e) => {
  isDragging.value = false;
  const file = e.dataTransfer.files[0];
  if (file && file.name.endsWith('.zip')) selectedFile.value = file;
  else ElMessage.error('Only ZIP format is supported');
};

const confirmSubmit = async () => {
  if (!selectedFile.value) return ElMessage.warning('Please select a file');
  
  const formData = new FormData();
  formData.append('assignment', Number(assignmentId)); 
  formData.append('sub_type', 'archive'); 
  formData.append('file', selectedFile.value);

  isSubmitting.value = true;
  try {
    const res = await api.post('/api/auth/student/submissions/', formData);
    ElMessage.success(res.data?.message || 'Submission successful. Automated review started.');
    selectedFile.value = null;
    await fetchHistory();
  } catch (error) {
    console.error('Upload failed:', error);
    ElMessage.error(error.response?.data?.message || 'Server rejected the upload');
  } finally {
    isSubmitting.value = false;
  }
};

const formatTime = (t) => t ? new Date(t).toLocaleString() : '-';

const getStatusText = (status) => {
  const map = { 'pending': 'Queuing', 'running': 'Building', 'completed': 'Completed', 'failed': 'Build Failed' };
  return map[status] || status;
};

const getStatusClass = (status) => {
  if (status === 'completed') return 'bg-green-50 text-green-600 border-green-200';
  if (status === 'failed') return 'bg-red-50 text-red-600 border-red-200';
  return 'bg-blue-50 text-blue-600 border-blue-200';
};

onMounted(initData);
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #cbd5e1;
}

.frosted-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
</style>