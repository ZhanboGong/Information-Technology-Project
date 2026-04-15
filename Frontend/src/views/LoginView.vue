<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-[#F3F4F9] p-4 font-sans">
    <div class="w-full max-w-[900px] h-auto min-h-[550px] bg-white rounded-[40px] shadow-[0_20px_50px_rgba(0,0,0,0.1)] flex flex-col md:flex-row overflow-hidden border border-white">
      
      <div class="w-full md:w-[45%] bg-[#7795E9] relative flex flex-col items-center justify-center p-12 text-center text-white overflow-hidden">
        <div class="absolute top-0 right-0 w-full h-full bg-[#7795E9] rounded-br-[180px] z-0"></div>
        
        <div class="relative z-10 space-y-6">
          <h1 class="text-4xl md:text-5xl font-bold tracking-tight">Hello, Welcome!</h1>
          <p class="text-blue-50/80 font-medium"></p>
          
          <div class="py-8 flex justify-center">
            <svg width="60" height="60" class="rounded-2xl bg-white/20 p-2 backdrop-blur-md" viewBox="0 0 100 120">
              <path d="M50 115 C50 115 90 95 90 30 V 10 L 50 0 L 10 10 V 30 C 10 95 50 115 50 115 Z" fill="white"/>
            </svg>
          </div>
          
          <div class="pt-4">
            <p class="text-sm text-blue-100 mb-4 opacity-70">Intelligent Programming System</p>
            <div class="w-32 h-1 bg-white/30 mx-auto rounded-full"></div>
          </div>
        </div>
      </div>

      <div class="w-full md:w-[55%] p-10 md:p-16 flex flex-col justify-center bg-white">
        <div class="mb-10 text-center">
          <h2 class="text-4xl font-black text-gray-800 tracking-tight">Login</h2>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-6">
          <div class="space-y-1">
            <div class="relative group">
              <div class="absolute inset-y-0 right-4 flex items-center pointer-events-none">
                <User size="18" class="text-gray-400 group-focus-within:text-[#7795E9] transition-colors" />
              </div>
              <input 
                v-model="form.username" 
                type="text" 
                required 
                placeholder="Username"
                class="w-full bg-[#EFEFEF] border-none rounded-xl px-6 py-4 text-[15px] font-medium text-gray-700 placeholder-gray-400 focus:ring-2 focus:ring-[#7795E9]/50 transition-all outline-none"
              >
            </div>
          </div>
          
          <div class="space-y-1">
            <div class="relative group">
              <div class="absolute inset-y-0 right-4 flex items-center pointer-events-none">
                <Lock size="18" class="text-gray-400 group-focus-within:text-[#7795E9] transition-colors" />
              </div>
              <input 
                v-model="form.password" 
                type="password" 
                required 
                placeholder="Password"
                class="w-full bg-[#EFEFEF] border-none rounded-xl px-6 py-4 text-[15px] font-medium text-gray-700 placeholder-gray-400 focus:ring-2 focus:ring-[#7795E9]/50 transition-all outline-none"
              >
            </div>
            <div class="text-right pt-2">
              <button 
                type="button" 
                @click="handleForgotPassword"
                class="text-xs font-semibold text-gray-500 hover:text-[#7795E9] transition-colors"
              >
                Forgot password?
              </button>
            </div>
          </div>

          <button 
            :disabled="loading" 
            type="submit" 
            class="w-full py-4 bg-[#7795E9] hover:bg-[#6684D8] text-white rounded-xl font-bold text-lg shadow-lg shadow-blue-200 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-70"
          >
            <Loader2 v-if="loading" class="animate-spin" size="22" />
            <span v-else>Login</span>
          </button>

          <div class="pt-8">
            <div class="relative flex items-center justify-center mb-6">
              <div class="absolute inset-0 flex items-center">
                <div class="w-full border-t border-gray-100"></div>
              </div>
              <span class="relative px-4 text-xs font-medium text-gray-400 bg-white">or login with social platforms</span>
            </div>
            
            <div class="flex justify-center gap-4">
              <button type="button" class="w-12 h-12 flex items-center justify-center border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors">
                <Github size="20" class="text-gray-700" />
              </button>
              <button type="button" class="w-12 h-12 flex items-center justify-center border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors">
                <Chrome size="20" class="text-gray-700" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../store/authStore';
import { Validators } from '../utils/validators'; 
// 修改点：引入了 ElMessageBox
import { ElMessage, ElMessageBox } from 'element-plus';
import { User, Lock, Loader2, Github, Chrome } from 'lucide-vue-next';

const router = useRouter();
const authStore = useAuthStore();
const loading = ref(false);

const form = reactive({ 
  username: '', 
  password: '' 
});

// 修改点：新增处理忘记密码的弹窗逻辑
const handleForgotPassword = () => {
  ElMessageBox.alert(
    'Please contact the administrator to reset your password.',
    'Forgot Password',
    {
      confirmButtonText: 'OK',
      type: 'info',
      center: true
    }
  );
};

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('Please fill in both account and password');
    return;
  }

  if (Validators && typeof Validators.username === 'function') {
    if (!Validators.username(form.username)) {
      ElMessage.warning('The account format is incorrect');
      return;
    }
  }

  loading.value = true;
  try {
    await authStore.login(form);
    
    ElMessage.success({
      message: 'Welcome back!',
      type: 'success',
      duration: 2000
    });
    
    const role = authStore.user?.role;
    
    if (role === 'admin') {
      router.push('/admin/dashboard'); 
    } else if (role === 'teacher') {
      router.push('/teacher/dashboard'); 
    } else {
      router.push('/student/dashboard'); 
    }
    
  } catch (error) {
    console.error('Login Failure:', error);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* 针对小屏幕优化布局 */
@media (max-width: 768px) {
  .rounded-br-\[180px\] {
    border-bottom-right-radius: 0;
  }
}
</style>