<template>
  <div class="min-h-screen flex font-sans bg-[#F0F4F8]">
    <nav class="w-64 sidebar-frosted flex flex-col py-8 z-50 fixed h-full overflow-y-auto custom-scrollbar">
      <div class="px-8 mb-8 flex items-center gap-4 shrink-0">
        <div class="relative group">
          <svg width="48" height="48" class="relative h-12 w-12 rounded-lg bg-white shadow-lg p-1" viewBox="0 0 100 120">
              <defs>
                  <linearGradient id="scuYellow" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#FFC72C"/><stop offset="100%" stop-color="#EAAA00"/></linearGradient>
                  <linearGradient id="scuTeal" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#00939D"/><stop offset="100%" stop-color="#00555A"/></linearGradient>
              </defs>
              <path d="M50 115 C50 115 90 95 90 30 V 10 L 50 0 L 10 10 V 30 C 10 95 50 115 50 115 Z" fill="white"/>
              <path d="M50 55 L 50 5 L 15 15 C 15 35 25 50 50 55 Z" fill="url(#scuYellow)"/>
              <path d="M50 55 L 50 5 L 85 15 C 85 35 75 50 50 55 Z" fill="url(#scuTeal)"/>
              <path d="M50 65 L 50 110 C 25 100 15 80 15 40 C 15 60 25 65 50 65 Z" fill="url(#scuYellow)"/>
              <path d="M50 65 L 50 110 C 75 100 85 80 85 40 C 85 60 75 65 50 65 Z" fill="url(#scuTeal)"/>
          </svg>
        </div>
        <div>
            <h1 class="text-lg font-bold tracking-tight text-white">Southern Cross</h1>
            <p class="text-xs text-blue-200 font-medium tracking-wide uppercase">University</p>
        </div>
      </div>
      
      <div class="flex-1 px-4 space-y-1">
        <div class="pt-2 pb-2 px-4 text-[10px] font-bold text-blue-300/60 uppercase tracking-widest">DASHBOARD</div>
        <router-link to="/teacher/dashboard" class="nav-item" active-class="active">
            <LayoutDashboard size="18" /><span>Workbench</span>
        </router-link>

        <div class="pt-6 pb-2 px-4 text-[10px] font-bold text-blue-300/60 uppercase tracking-widest">TEACHING</div>
        <router-link to="/teacher/courses" class="nav-item" active-class="active">
            <Library size="18" /><span>Courses & Classes</span>
        </router-link>

        <router-link to="/teacher/grading" class="nav-item justify-between" :class="{'active': route.path.includes('/teacher/grading')}" active-class="active">
            <div class="flex items-center gap-3">
              <BookOpenCheck size="18" /><span>Submissions</span>
            </div>
            <span v-if="reminders.length > 0" class="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-md shadow-sm animate-pulse">
              {{ reminders.length }}
            </span>
        </router-link>

        <div class="pt-6 pb-2 px-4 text-[10px] font-bold text-blue-300/60 uppercase tracking-widest">ACCOUNT</div>
        <router-link to="/teacher/profile" class="nav-item" active-class="active">
            <User size="18" /><span>My Profile</span>
        </router-link>
      </div>

      <div class="mt-auto px-6 py-6 border-t border-white/10">
        <div class="flex items-center gap-3 cursor-pointer hover:bg-white/10 p-2 rounded-xl transition-all" @click="handleLogout">
            <div class="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-500 to-blue-700 border-2 border-white/20 flex items-center justify-center font-bold text-sm text-white shadow-md">
                {{ authStore.user?.username?.[0]?.toUpperCase() || 'T' }}
            </div>
            <div class="min-w-0">
                <p class="text-sm font-bold text-white truncate w-32">{{ authStore.user?.username }}</p>
                <p class="text-xs text-blue-300 capitalize flex items-center gap-1">
                  <LogOut size="12" />Sign Out
                </p>
            </div>
        </div>
      </div>
    </nav>
    
    <main class="flex-1 ml-64 p-10 relative overflow-y-auto h-screen custom-scrollbar">
      <header class="flex justify-between items-center mb-10 w-full gap-4">
        <div class="flex items-center gap-4 flex-1 min-w-0">
          <button v-if="route.path.includes('workspace')" @click="router.push('/teacher/grading')" 
                  class="shrink-0 group px-4 py-2 rounded-xl bg-white border border-gray-200 text-gray-600 font-bold hover:bg-blue-50 hover:text-blue-600 transition-all shadow-sm flex items-center gap-2">
              <ArrowLeft size="18" class="group-hover:-translate-x-1 transition-transform" />
              <span>Back</span>
          </button>

          <div class="flex-1 min-w-0">
              <h2 class="text-2xl font-bold text-[#1E3A8A] tracking-tight truncate">{{ pageTitle }}</h2>
              <p class="text-sm text-gray-500 mt-1 flex items-center gap-2 font-medium">
                  <span class="flex h-2.5 w-2.5 relative">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
                  </span>
                  <span>System Status: Normal</span>
              </p>
          </div>
        </div>
        
        <div class="flex items-center gap-4 shrink-0 relative">
          <div v-if="route.path.includes('workspace')" class="px-4 py-2 rounded-full bg-blue-100 text-blue-700 flex items-center gap-2 text-xs font-bold border border-blue-200 shadow-sm animate-fade-in">
              <div class="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></div>
              Grading Mode
          </div>

          <button 
            @click.stop="toggleNotifications"
            class="shrink-0 p-3 rounded-full text-gray-500 hover:text-[#1E3A8A] border border-white/60 shadow-sm bg-white/50 transition-all hover:scale-105 active:scale-95 relative"
          >
              <Bell size="20" />
              <span v-if="reminders.length > 0" class="absolute top-2.5 right-2.5 h-2 w-2 bg-red-500 rounded-full border border-white"></span>
          </button>

          <transition name="fade">
            <div 
              v-if="showNotifications" 
              class="absolute right-0 top-14 w-80 bg-white rounded-2xl shadow-2xl border border-gray-100 z-[100] overflow-hidden"
            >
              <div class="p-4 border-b border-gray-50 bg-gray-50/50 flex justify-between items-center">
                <span class="font-bold text-gray-800 text-sm">Approaching Deadlines</span>
                <span class="text-[10px] bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-full font-bold uppercase text-nowrap">Teacher Alert</span>
              </div>
              
              <div class="max-h-96 overflow-y-auto custom-scrollbar">
                <div v-if="reminders.length === 0" class="p-8 text-center">
                  <p class="text-gray-400 text-sm">No assignments closing soon</p>
                </div>

                <div 
                  v-for="item in reminders" 
                  :key="item.assignment_id"
                  @click="goToGrading(item.assignment_id)"
                  class="p-4 border-b border-gray-50 hover:bg-indigo-50/50 cursor-pointer transition-colors group"
                >
                  <div class="flex flex-col gap-1">
                    <h4 class="font-bold text-gray-800 text-sm group-hover:text-indigo-600 transition-colors">
                      {{ item.title }}
                    </h4>
                    <p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider">{{ item.course_name }}</p>
                    
                    <div class="mt-2 space-y-1">
                      <div class="flex justify-between text-[10px] font-bold">
                        <span class="text-emerald-600">Submitted: {{ item.submitted_count || 0 }}</span>
                        <span class="text-gray-400">Total: {{ item.total_students || 0 }}</span>
                      </div>
                      <div class="w-full bg-gray-100 h-1 rounded-full overflow-hidden">
                        <div class="bg-emerald-500 h-full transition-all duration-500" 
                             :style="{ width: ((item.submitted_count / item.total_students) * 100 || 0) + '%' }"></div>
                      </div>
                    </div>

                    <div class="flex items-center gap-2 mt-2 text-xs" :class="item.days_left < 2 ? 'text-red-500 font-bold' : 'text-orange-500'">
                      <Clock size="12" />
                      <span>
                        {{ item.days_left > 0 ? `Closes in ${item.days_left} days` : `Closing in ${item.hours_left}h!` }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <router-link 
                to="/teacher/grading" 
                @click="showNotifications = false"
                class="block p-3 text-center text-[11px] font-bold text-indigo-600 hover:bg-indigo-50 transition-colors uppercase"
              >
                Go to Grading Center
              </router-link>
            </div>
          </transition>
        </div>
      </header>

      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../store/authStore';
import axios from 'axios';
import { 
  LayoutDashboard, Library, BookOpenCheck, 
  LogOut, Bell, User, ArrowLeft, Clock 
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const showNotifications = ref(false);
const reminders = ref([]);

// 获取提醒数据
const fetchReminders = async () => {
  try {
    const token = authStore.token;
    if (!token) return;

    // 假设后端复用此接口，但在老师角色下返回：作业标题、已交人数、总人数、截止时间
    const response = await axios.get('/api/auth/home/reminders/', {
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (Array.isArray(response.data)) {
        reminders.value = response.data;
    }
  } catch (error) {
    console.error("[Teacher Layout] Reminders failed:", error.message);
    reminders.value = [];
  }
};

const toggleNotifications = () => {
  showNotifications.value = !showNotifications.value;
};

const closeNotifications = (e) => {
  if (showNotifications.value && !e.target.closest('.relative')) {
    showNotifications.value = false;
  }
};

const goToGrading = (id) => {
  showNotifications.value = false;
  // 跳转到该作业的批改页面，或者批改列表并高亮该项
  router.push('/teacher/grading');
};

const pageTitle = computed(() => {
  if (route.path.includes('workspace')) return 'Grading Workspace';
  const map = {
    '/teacher/dashboard': 'Workbench',
    '/teacher/courses': 'Courses & Classes',
    '/teacher/grading': 'Submissions & Grading',
    '/teacher/profile': 'Profile Settings'
  };
  return map[route.path] || 'Teacher Center';
});

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};

onMounted(() => {
  fetchReminders();
  window.addEventListener('click', closeNotifications);
});

onUnmounted(() => {
  window.removeEventListener('click', closeNotifications);
});
</script>

<style scoped>
.nav-item {
  @apply w-full flex items-center gap-3 px-5 py-3.5 rounded-xl transition-all text-sm font-medium text-blue-100 hover:bg-white/5;
}
.active {
  @apply bg-white/15 text-white shadow-lg backdrop-blur-sm border border-white/10;
}
.sidebar-frosted {
  background: rgba(30, 58, 138, 0.95);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 10px; }
.animate-fade-in { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(-5px); } to { opacity: 1; transform: translateY(0); } }
</style>