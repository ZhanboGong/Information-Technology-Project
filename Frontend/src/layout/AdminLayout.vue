<template>
  <div class="min-h-screen bg-[#f8fafc] flex overflow-hidden">
    <aside class="w-64 bg-white/70 backdrop-blur-xl border-r border-white/60 flex flex-col z-50">
      <div class="p-6 flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-indigo-600 to-blue-500 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200">
          <ShieldAlert class="text-white" size="24" />
        </div>
        <div>
          <h1 class="text-lg font-black text-gray-800 tracking-tighter leading-none">ADMIN</h1>
          <p class="text-[10px] text-blue-600 font-bold uppercase tracking-widest mt-1">Control Center</p>
        </div>
      </div>

      <nav class="flex-1 px-4 py-4 space-y-2 overflow-y-auto scrollbar-hide">
        <div class="text-[10px] font-black text-gray-400 uppercase px-4 mb-2 tracking-[0.2em]">Management</div>
        
        <router-link v-for="item in menuItems" :key="item.path" :to="item.path" 
          class="flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-300 group"
          :class="activeRoute === item.path ? 'bg-blue-600 text-white shadow-lg shadow-blue-200 active-nav' : 'text-gray-500 hover:bg-blue-50 hover:text-blue-600'">
          <component :is="item.icon" size="20" :class="activeRoute === item.path ? 'text-white' : 'group-hover:scale-110 transition-transform'"/>
          <span class="text-sm font-bold">{{ item.name }}</span>
        </router-link>

        <div class="pt-6 text-[10px] font-black text-gray-400 uppercase px-4 mb-2 tracking-[0.2em]">System</div>
        
        <router-link to="/admin/config" 
          class="flex items-center gap-3 px-4 py-3 rounded-2xl transition-all text-gray-500 hover:bg-purple-50 hover:text-purple-600 group"
          active-class="bg-purple-600 !text-white shadow-lg shadow-purple-200">
          <Settings size="20" />
          <span class="text-sm font-bold">API & AI Config</span>
        </router-link>

        <router-link to="/admin/monitor" 
          class="flex items-center gap-3 px-4 py-3 rounded-2xl transition-all text-gray-500 hover:bg-amber-50 hover:text-amber-600 group"
          active-class="bg-amber-600 !text-white shadow-lg shadow-amber-200">
          <Activity size="20" />
          <span class="text-sm font-bold">Task Monitor</span>
        </router-link>
      </nav>

      <div class="p-4 border-t border-gray-100">
        <button @click="handleLogout" class="w-full flex items-center gap-3 px-4 py-3 text-red-500 hover:bg-red-50 rounded-2xl transition-all font-bold text-sm group">
          <LogOut size="20" class="group-hover:translate-x-1 transition-transform"/>
          Logout
        </button>
      </div>
    </aside>

    <main class="flex-1 flex flex-col h-screen overflow-hidden relative">
      <div class="absolute top-[-10%] right-[-5%] w-[40%] h-[40%] bg-blue-100/50 rounded-full blur-[120px] -z-10"></div>
      <div class="absolute bottom-[-10%] left-[-5%] w-[30%] h-[30%] bg-purple-100/50 rounded-full blur-[100px] -z-10"></div>

      <header class="h-20 flex items-center justify-between px-10 shrink-0">
        <div class="flex items-center gap-2">
          <span class="text-sm font-bold text-gray-400 uppercase tracking-widest">Server Status:</span>
          <div class="flex items-center gap-1.5 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-100">
            <div class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
            <span class="text-[10px] font-black text-emerald-600 uppercase">Operational</span>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <div class="text-right">
            <p class="text-sm font-black text-gray-800 leading-none">{{ adminName }}</p>
            <p class="text-[10px] text-gray-400 font-bold mt-1 uppercase">Root Administrator</p>
          </div>
          <div class="w-10 h-10 rounded-full bg-gray-200 border-2 border-white shadow-sm overflow-hidden">
            <img :src="`https://api.dicebear.com/7.x/bottts/svg?seed=${adminName}`" alt="avatar">
          </div>
        </div>
      </header>

      <section class="flex-1 overflow-y-auto px-10 pb-10 custom-scrollbar">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../store/authStore'; // 引入 authStore
import { 
  ShieldAlert, Users, UserPlus, LayoutDashboard, 
  Settings, Activity, LogOut, FileText 
} from 'lucide-vue-next';
import { ElMessageBox, ElMessage } from 'element-plus';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore(); // 初始化 authStore

// 优先从 store 获取用户名，保证状态实时同步
const adminName = computed(() => authStore.user?.username || localStorage.getItem('username') || 'Admin');
const activeRoute = computed(() => route.path);

const menuItems = [
  { name: 'Overview', path: '/admin/dashboard', icon: LayoutDashboard },
  { name: 'Users List', path: '/admin/users', icon: Users },
  { name: 'Register New', path: '/admin/register', icon: UserPlus },
  { name: 'System Logs', path: '/admin/logs', icon: FileText },
];

/**
 * 退出登录逻辑
 */
const handleLogout = () => {
  ElMessageBox.confirm('Are you sure you want to exit the admin console?', 'Logout', {
    confirmButtonText: 'Logout',
    cancelButtonText: 'Cancel',
    type: 'warning',
    roundButton: true
  }).then(() => {
    // 关键修复：统一调用 store 的登出方法
    // 这样会自动清理 localStorage 以及重置 store 内的认证状态
    authStore.logout(); 
    
    // 跳转回登录页面
    router.push('/login');
    ElMessage.success('Logged out successfully');
  }).catch(() => {
    // 处理取消操作，避免控制台报错
    console.log('Logout cancelled');
  });
};
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 10px;
}

/* 视图切换动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 侧边栏活动项状态条 */
.active-nav {
  position: relative;
}

.active-nav::after {
  content: '';
  position: absolute;
  right: -16px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 20px;
  background: #2563eb;
  border-radius: 4px 0 0 4px;
}
</style>