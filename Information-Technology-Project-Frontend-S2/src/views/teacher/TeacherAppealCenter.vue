<template>
  <div class="max-w-6xl mx-auto p-6 space-y-6 animate-fade-in">

    <!-- Header -->
    <div>
      <h1 class="text-3xl font-black tracking-tight text-gray-900 flex items-center gap-3">
        <ShieldAlert class="text-blue-600" size="32"/>
        Grade Appeal Center
      </h1>
      <p class="text-gray-500 font-medium mt-1">Review and resolve student concerns with AI-assisted auditing.</p>
    </div>

    <!-- Stats bar -->
    <div class="frosted-card rounded-2xl border-2 border-gray-100 p-1 flex divide-x divide-gray-100">
      <div class="flex-1 flex items-center justify-center gap-3 py-3 px-4 cursor-pointer hover:bg-gray-50 transition-all rounded-xl"
           @click="activeStatus = 'all'">
        <div class="w-2 h-2 rounded-full bg-blue-400"></div>
        <p class="text-xl font-black text-gray-800">{{ stats.total }}</p>
        <p class="text-[10px] font-black uppercase tracking-widest" :class="activeStatus === 'all' ? 'text-blue-600' : 'text-gray-400'">All</p>
      </div>
      <div class="flex-1 flex items-center justify-center gap-3 py-3 px-4 cursor-pointer hover:bg-gray-50 transition-all rounded-xl"
           @click="activeStatus = 'pending_teacher'">
        <div class="w-2 h-2 rounded-full bg-amber-400"></div>
        <p class="text-xl font-black text-gray-800">{{ stats.pending }}</p>
        <p class="text-[10px] font-black uppercase tracking-widest" :class="activeStatus === 'pending_teacher' ? 'text-amber-600' : 'text-gray-400'">Pending</p>
      </div>
      <div class="flex-1 flex items-center justify-center gap-3 py-3 px-4 cursor-pointer hover:bg-gray-50 transition-all rounded-xl"
           @click="activeStatus = 'rejected_by_ai'">
        <div class="w-2 h-2 rounded-full bg-gray-400"></div>
        <p class="text-xl font-black text-gray-800">{{ stats.rejected }}</p>
        <p class="text-[10px] font-black uppercase tracking-widest" :class="activeStatus === 'rejected_by_ai' ? 'text-gray-600' : 'text-gray-400'">AI Rejected</p>
      </div>
      <div class="flex-1 flex items-center justify-center gap-3 py-3 px-4 cursor-pointer hover:bg-gray-50 transition-all rounded-xl"
           @click="activeStatus = 'pending_ai'">
        <div class="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></div>
        <p class="text-xl font-black text-gray-800">{{ stats.auditing }}</p>
        <p class="text-[10px] font-black uppercase tracking-widest" :class="activeStatus === 'pending_ai' ? 'text-blue-600' : 'text-gray-400'">Auditing</p>
      </div>
      <div class="flex-1 flex items-center justify-center gap-3 py-3 px-4 cursor-pointer hover:bg-gray-50 transition-all rounded-xl"
           @click="activeStatus = 'completed'">
        <div class="w-2 h-2 rounded-full bg-emerald-400"></div>
        <p class="text-xl font-black text-gray-800">{{ stats.completed }}</p>
        <p class="text-[10px] font-black uppercase tracking-widest" :class="activeStatus === 'completed' ? 'text-emerald-600' : 'text-gray-400'">Resolved</p>
      </div>
    </div>

    <!-- Course filter -->
    <div v-if="courseNames.length > 1" class="flex items-center gap-2 overflow-x-auto pb-1">
      <button 
        @click="activeCourse = null"
        :class="activeCourse === null ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300'"
        class="px-4 py-1.5 rounded-lg text-xs font-black border-2 transition-all whitespace-nowrap"
      >
        All Courses
      </button>
      <button 
        v-for="name in courseNames" 
        :key="name"
        @click="activeCourse = name"
        :class="activeCourse === name ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300'"
        class="px-4 py-1.5 rounded-lg text-xs font-black border-2 transition-all whitespace-nowrap"
      >
        {{ name }}
        <span class="ml-1 opacity-60">{{ courseCount[name] || 0 }}</span>
      </button>
    </div>

    <!-- Content -->
    <div class="space-y-3">
      <div v-if="loading" class="space-y-3">
        <div v-for="i in 4" :key="i" class="frosted-card rounded-xl border-2 border-gray-100 p-5 animate-pulse">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gray-200 rounded-xl"></div>
              <div class="space-y-2">
                <div class="h-4 bg-gray-200 rounded w-24"></div>
                <div class="h-3 bg-gray-200 rounded w-16"></div>
              </div>
            </div>
            <div class="h-8 w-20 bg-gray-200 rounded-lg"></div>
          </div>
        </div>
      </div>

      <div v-else-if="filteredAppeals.length === 0" class="text-center py-16 bg-white rounded-2xl border-2 border-dashed border-gray-200">
        <Inbox size="40" class="mx-auto text-gray-300 mb-3"/>
        <p class="text-sm font-bold text-gray-400">No appeals found for this filter</p>
      </div>

      <div v-else class="space-y-2">
        <div 
          v-for="appeal in displayedAppeals" 
          :key="appeal.id"
          class="frosted-card rounded-xl border-2 border-gray-100 hover:border-blue-300 hover:shadow-md transition-all overflow-hidden"
        >
          <!-- Row 1 -->
          <div class="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-sm shrink-0">
                {{ appeal.student_name[0] }}
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <h3 class="font-black text-gray-900 truncate">{{ appeal.student_name }}</h3>
                  <span 
                    class="px-2 py-0.5 rounded text-[10px] font-black shrink-0"
                    :class="getStatusTheme(appeal.status)"
                  >
                    {{ appeal.status_display }}
                  </span>
                </div>
                <p class="text-xs text-gray-400 font-mono mt-0.5 truncate">{{ appeal.assignment_title }} · {{ appeal.student_id_num }}</p>
              </div>
            </div>

            <div class="flex items-center gap-4 shrink-0">
              <div class="text-right">
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Current Score</p>
                <p class="text-2xl font-black text-blue-600">{{ appeal.original_score }}</p>
              </div>
              <button 
                @click="openResolveModal(appeal)"
                :disabled="appeal.status === 'completed'"
                class="px-6 py-2.5 rounded-xl font-black text-sm shadow-lg transition-all active:scale-95 disabled:opacity-40"
                :class="appeal.status === 'completed' ? 'bg-gray-100 text-gray-400 border border-gray-200' : 'bg-gray-900 text-white hover:bg-blue-600'"
              >
                {{ appeal.status === 'completed' ? 'Resolved' : 'Handle Appeal' }}
              </button>
            </div>
          </div>

          <!-- Row 2 -->
          <div class="px-5 pb-5 grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="p-3 bg-gray-50 rounded-xl border border-gray-100">
              <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 flex items-center gap-1">
                <MessageSquare size="10" /> Student Reason
              </p>
              <p class="text-xs text-gray-600 leading-relaxed line-clamp-2 italic">"{{ appeal.student_reason }}"</p>
            </div>
            <div class="p-3 bg-blue-50/30 rounded-xl border border-blue-100/50">
              <p class="text-[10px] font-black text-blue-500 uppercase tracking-widest mb-1 flex items-center gap-1">
                <Bot size="10" /> AI Auditor Opinion
              </p>
              <p class="text-xs text-blue-700/80 leading-relaxed line-clamp-2">{{ appeal.ai_judgment }}</p>
            </div>
          </div>
        </div>

        <!-- Load More -->
        <div v-if="displayedAppeals.length < filteredAppeals.length" class="flex justify-center pt-4">
          <button 
            @click="loadMore"
            class="px-8 py-2.5 bg-white border-2 border-gray-200 text-gray-600 rounded-xl font-black text-sm hover:border-blue-300 hover:text-blue-600 transition-all flex items-center gap-2"
          >
            Load More ({{ filteredAppeals.length - displayedAppeals.length }} remaining)
          </button>
        </div>
      </div>
    </div>

    <AppealResolveModal 
      v-if="modalVisible" 
      :appeal="selectedAppeal" 
      @close="modalVisible = false"
      @refresh="fetchAppeals"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { ShieldAlert, Inbox, MessageSquare, Bot } from 'lucide-vue-next';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';
import AppealResolveModal from './AppealResolveModal.vue';

const appeals = ref([]);
const loading = ref(false);
const modalVisible = ref(false);
const selectedAppeal = ref(null);
const activeStatus = ref('all');
const activeCourse = ref(null);
const pageSize = 5;
const displayCount = ref(pageSize);

const fetchAppeals = async () => {
  loading.value = true;
  try {
    const res = await api.get('/api/auth/teacher/assignments/all-appeals/');
    let finalData = [];
    if (Array.isArray(res)) {
      finalData = res;
    } else if (res.data && Array.isArray(res.data)) {
      finalData = res.data;
    } else if (res.data && res.data.results && Array.isArray(res.data.results)) {
      finalData = res.data.results;
    } else if (res.results && Array.isArray(res.results)) {
      finalData = res.results;
    }
    appeals.value = finalData;
  } catch (e) {
    ElMessage.error(e.response?.data?.error || 'Failed to load appeals');
  } finally {
    loading.value = false;
  }
};

// Stats
const stats = computed(() => {
  const list = Array.isArray(appeals.value) ? appeals.value : [];
  return {
    pending: list.filter(a => a?.status === 'pending_teacher').length,
    rejected: list.filter(a => a?.status === 'rejected_by_ai').length,
    auditing: list.filter(a => a?.status === 'pending_ai').length,
    completed: list.filter(a => a?.status === 'completed').length,
    total: list.length
  };
});

// Course names extracted from assignment titles
const courseNames = computed(() => {
  const names = new Set();
  appeals.value.forEach(a => {
    if (a.assignment_title) names.add(a.assignment_title);
  });
  return [...names];
});

const courseCount = computed(() => {
  const counts = {};
  appeals.value.forEach(a => {
    if (a.assignment_title) {
      counts[a.assignment_title] = (counts[a.assignment_title] || 0) + 1;
    }
  });
  return counts;
});

// Filtered by status + course
const filteredAppeals = computed(() => {
  let list = Array.isArray(appeals.value) ? appeals.value : [];
  if (activeStatus.value !== 'all') {
    list = list.filter(a => a?.status === activeStatus.value);
  }
  if (activeCourse.value) {
    list = list.filter(a => a?.assignment_title === activeCourse.value);
  }
  return list;
});

// Paginated display
const displayedAppeals = computed(() => {
  return filteredAppeals.value.slice(0, displayCount.value);
});

const loadMore = () => {
  displayCount.value += pageSize;
};

// Reset pagination when filter changes
const resetPagination = () => {
  displayCount.value = pageSize;
};

// Watch filter changes - use a simple approach
import { watch } from 'vue';
watch([activeStatus, activeCourse], resetPagination);

const getStatusTheme = (status) => {
  const themes = {
    'pending_teacher': 'bg-amber-50 text-amber-600 border border-amber-200',
    'rejected_by_ai': 'bg-gray-100 text-gray-500 border border-gray-200',
    'completed': 'bg-emerald-50 text-emerald-600 border border-emerald-200',
    'pending_ai': 'bg-blue-50 text-blue-600 border border-blue-200'
  };
  return themes[status] || themes['pending_teacher'];
};

const openResolveModal = (appeal) => {
  selectedAppeal.value = appeal;
  modalVisible.value = true;
};

onMounted(fetchAppeals);
</script>

<style scoped>
.frosted-card {
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
</style>