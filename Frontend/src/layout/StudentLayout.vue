<template>
  <div class="min-h-screen flex font-sans bg-[#F0F4F8]">
    <nav class="w-64 sidebar-frosted flex flex-col py-8 z-50 fixed h-full overflow-y-auto custom-scrollbar">
      <div class="px-8 mb-8 flex items-center gap-4 shrink-0">
        <div class="py-8 flex justify-center">
  <svg width="60" height="60" class="rounded-2xl bg-white/20 p-2.5 backdrop-blur-md" viewBox="0 0 120 120">
    <path
      d="M36 24 C31 24 26 29 26 34 V 49 C 26 54 21 54 21 54 C 21 54 26 54 26 59 V 74 C 26 79 31 84 36 84 M84 24 C89 24 94 29 94 34 V 49 C 94 54 99 54 99 54 C 99 54 94 54 94 59 V 74 C 94 79 89 84 84 84 Z"
      fill="white"
      opacity="0.15"
      class="group-hover:opacity-20 transition-opacity"
    />

    <path
      d="M36 24 C31 24 26 29 26 34 V 49 C 26 54 21 54 21 54 C 21 54 26 54 26 59 V 74 C 26 79 31 84 36 84 M84 24 C89 24 94 29 94 34 V 49 C 94 54 99 54 99 54 C 99 54 94 54 94 59 V 74 C 94 79 89 84 84 84 M68 18 L52 90"
      fill="none"
      stroke="white"
      stroke-width="7"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="group-hover:stroke-[white] transition-colors"
    />
  </svg>
</div>
        <div>
            <h1 class="text-lg font-bold tracking-tight text-white">Intelligent Programming Education</h1>
            <p class="text-xs text-blue-200 font-medium tracking-wide uppercase">System</p>
        </div>
      </div>
      
      <div class="flex-1 px-4 space-y-1">
        <div class="pt-2 pb-2 px-4 text-[10px] font-bold text-blue-300/60 uppercase tracking-widest">DASHBOARD</div>
        <router-link to="/student/dashboard" class="nav-item" active-class="active">
            <LayoutDashboard size="18" /><span>Overview</span>
        </router-link>

        <div class="pt-6 pb-2 px-4 text-[10px] font-bold text-blue-300/60 uppercase tracking-widest">LEARNING</div>
        <router-link to="/student/assignments" class="nav-item justify-between" active-class="active">
            <div class="flex items-center gap-3">
              <BookOpen size="18" /><span>Assignments</span>
            </div>
            <span v-if="reminders.length > 0" class="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-md shadow-sm">
              {{ reminders.length }}
            </span>
        </router-link>

        <router-link to="/student/grades" class="nav-item" active-class="active">
            <Award size="18" /><span>Gradebook</span>
        </router-link>
        
        <router-link to="/student/analysis" class="nav-item" active-class="active">
            <BarChart3 size="18" /><span>Analytics</span>
        </router-link>

        <div class="pt-6 pb-2 px-4 text-[10px] font-bold text-blue-300/60 uppercase tracking-widest">ACCOUNT</div>
        <router-link to="/student/profile" class="nav-item" active-class="active">
            <User size="18" /><span>My Profile</span>
        </router-link>
      </div>

      <div class="mt-auto px-6 py-6 border-t border-white/10">
        <div class="flex items-center gap-3 cursor-pointer hover:bg-white/10 p-2 rounded-xl transition-all" @click="handleLogout">
            <div class="h-10 w-10 rounded-full bg-gradient-to-br from-blue-600 to-blue-800 border-2 border-white/20 flex items-center justify-center font-bold text-sm text-white shadow-md">
                {{ authStore.user?.username?.[0]?.toUpperCase() || 'S' }}
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
        
        <div class="flex items-center gap-4 shrink-0 relative">
          <button 
            @click.stop="toggleNotifications"
            class="shrink-0 p-3 rounded-full text-gray-500 hover:text-[#1E3A8A] relative transition-all hover:scale-105 active:scale-95 border border-white/60 shadow-sm bg-white/50"
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
                <span class="font-bold text-gray-800 text-sm">Upcoming Deadlines</span>
                <span class="text-[10px] bg-blue-100 text-blue-600 px-2 py-0.5 rounded-full font-bold uppercase">7 Days</span>
              </div>
              
              <div class="max-h-96 overflow-y-auto custom-scrollbar">
                <div v-if="reminders.length === 0" class="p-8 text-center">
                  <p class="text-gray-400 text-sm">No assignments due soon</p>
                </div>

                <div 
                  v-for="item in reminders" 
                  :key="item.assignment_id"
                  @click="goToAssignment(item.assignment_id)"
                  class="p-4 border-b border-gray-50 hover:bg-blue-50/50 cursor-pointer transition-colors group"
                >
                  <div class="flex flex-col gap-1">
                    <h4 class="font-bold text-gray-800 text-sm group-hover:text-blue-600 transition-colors">
                      {{ item.title }}
                    </h4>
                    <p class="text-[11px] text-gray-400 font-medium uppercase tracking-wider">{{ item.course_name }}</p>
                    <div class="flex items-center gap-2 mt-1 text-xs" :class="item.days_left < 2 ? 'text-red-500 font-bold' : 'text-orange-500'">
                      <Clock size="12" />
                      <span>
                        {{ item.days_left > 0 ? `Due in ${item.days_left} days` : `Urgent: ${item.hours_left}h left!` }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <router-link 
                to="/student/assignments" 
                @click="showNotifications = false"
                class="block p-3 text-center text-[11px] font-bold text-blue-600 hover:bg-blue-50 transition-colors uppercase"
              >
                View All Assignments
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
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../store/authStore';
import axios from 'axios';
import { 
  LayoutDashboard, BookOpen, Award, BarChart3, 
  LogOut, Bell, User, Clock 
} from 'lucide-vue-next';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const showNotifications = ref(false);
const reminders = ref([]);

const fetchReminders = async () => {
  try {
    const token = authStore.token;
    if (!token) return;

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
    console.error("[Layout] Warning of loading failure:", error.message);
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

/**
 * According to the index of path in js: / student/assignments/submit / : assignId
 */
const goToAssignment = (id) => {
  showNotifications.value = false;

  router.push({
    name: 'StudentSubmission',
    params: { assignId: id }
  });
};

onMounted(() => {
  fetchReminders();
  window.addEventListener('click', closeNotifications);
});

onUnmounted(() => {
  window.removeEventListener('click', closeNotifications);
});

const pageTitle = computed(() => {
  const map = {
    '/student/dashboard': 'Overview',
    '/student/assignments': 'My Assignments',
    '/student/courses': 'Course Center',
    '/student/grades': 'Gradebook',
    '/student/analysis': 'Analytics',
    '/student/profile': 'Profile Settings'
  };
  
  // Match the header logic of the dynamic route
  if (route.path.includes('/student/assignments/submit/')) return 'Submit Assignment';
  
  return map[route.path] || 'Student Space';
});

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};
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
</style>