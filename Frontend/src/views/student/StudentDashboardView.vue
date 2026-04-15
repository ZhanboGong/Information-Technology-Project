<template>
  <div class="space-y-8 animate-fade-in max-w-6xl mx-auto pt-2">
    
    <div class="frosted-card p-8 rounded-2xl border border-white/60 bg-gradient-to-r from-blue-50/50 to-transparent">
      <h2 class="text-3xl font-bold text-gray-800 tracking-tight">
        Welcome back, {{ user?.username || 'Student' }} 👋
      </h2>
      <p class="text-sm text-gray-500 mt-2">It's a great day to improve yourself. Here is your learning overview; please handle pending tasks in time.</p>
    </div>

    <div class="grid grid-cols-3 gap-6">
      
      <div 
        @click="router.push('/student/assignments')"
        class="frosted-card p-6 rounded-2xl border border-white/60 flex flex-col justify-between hover:-translate-y-1 transition-transform cursor-pointer relative overflow-hidden group shadow-sm hover:shadow-md"
      >
        <div class="absolute right-0 top-0 w-24 h-24 bg-blue-500/5 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
        <div class="flex justify-between items-start mb-6">
          <div class="p-3.5 bg-blue-100 text-blue-600 rounded-xl"><BookOpen size="24" /></div>
          <span v-if="stats.pending_count > 0" class="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-md shadow-sm animate-pulse">
            {{ stats.pending_count }} Pending
          </span>
        </div>
        <div>
          <h3 class="text-lg font-bold text-gray-800 group-hover:text-blue-600 transition-colors">My Assignments</h3>
          <p class="text-xs text-gray-500 mt-1">View and submit course tasks</p>
        </div>
      </div>

      <div 
        @click="router.push('/student/grades')"
        class="frosted-card p-6 rounded-2xl border border-white/60 flex flex-col justify-between hover:-translate-y-1 transition-transform cursor-pointer relative overflow-hidden group shadow-sm hover:shadow-md"
      >
        <div class="absolute right-0 top-0 w-24 h-24 bg-orange-500/5 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
        <div class="mb-6">
          <div class="inline-block p-3.5 bg-orange-100 text-orange-600 rounded-xl"><Award size="24" /></div>
        </div>
        <div>
          <h3 class="text-lg font-bold text-gray-800 group-hover:text-orange-600 transition-colors">Gradebook</h3>
          <p class="text-xs text-gray-500 mt-1">Check your assessment records</p>
        </div>
      </div>

      <div 
        @click="router.push('/student/analysis')"
        class="frosted-card p-6 rounded-2xl border border-white/60 flex flex-col justify-between hover:-translate-y-1 transition-transform cursor-pointer relative overflow-hidden group shadow-sm hover:shadow-md"
      >
        <div class="absolute right-0 top-0 w-24 h-24 bg-purple-500/5 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
        <div class="mb-6">
          <div class="inline-block p-3.5 bg-purple-100 text-purple-600 rounded-xl"><BarChart3 size="24" /></div>
        </div>
        <div>
          <h3 class="text-lg font-bold text-gray-800 group-hover:text-purple-600 transition-colors">Capability Analysis</h3>
          <p class="text-xs text-gray-500 mt-1">AI-powered knowledge diagnosis</p>
        </div>
      </div>
    </div>

    <div class="frosted-card p-8 rounded-3xl border border-white/60 bg-white/40 mt-10">
      <div class="flex items-center gap-3 mb-6">
        <Activity size="20" class="text-blue-500" />
        <h3 class="text-lg font-bold text-gray-800">Recent Activities</h3>
      </div>
      
      <div v-if="activities.length > 0" class="space-y-4">
        <div v-for="item in activities" :key="item.id" class="flex items-center p-4 bg-white/50 rounded-xl border border-white/20">
          <div class="w-2 h-2 rounded-full bg-blue-500 mr-4"></div>
          <span class="text-sm text-gray-700 flex-1">{{ item.content }}</span>
          <span class="text-xs text-gray-400">{{ item.time }}</span>
        </div>
      </div>

      <div v-else class="text-center py-10 text-gray-400 border-2 border-dashed border-gray-200 rounded-xl">
        <p class="text-sm font-medium">No recent activities. Go to "My Assignments" to start learning!</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../../store/authStore';
import api from '../../utils/request'; 
import { BookOpen, Award, BarChart3, Activity } from 'lucide-vue-next';

const router = useRouter();
const authStore = useAuthStore();
const user = computed(() => authStore.user);

const stats = reactive({
  pending_count: 0
});

const activities = ref([]);

const fetchDashboardData = async () => {
  try {
    // Calling the actual assignment API
    const res = await api.get('/api/auth/student/assignments/');
    const data = res.data || res;
    
    if (Array.isArray(data)) {
      // Filter out tasks that haven't been submitted yet
      const pending = data.filter(item => !item.is_submitted);
      stats.pending_count = pending.length;
      
      // Populate activities for a richer UI
      if (pending.length > 0) {
        activities.value = [
          { id: 1, content: `You have ${pending.length} assignment(s) approaching deadline.`, time: 'Just now' },
          { id: 2, content: 'The system has updated your learning overview.', time: '5 mins ago' }
        ];
      }
    }
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error);
  }
};

onMounted(() => {
  fetchDashboardData();
});
</script>