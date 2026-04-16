<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-[#F3F4F9] p-4 font-sans">
    <div class="w-full max-w-[900px] h-auto min-h-[550px] bg-white rounded-[40px] shadow-[0_20px_50px_rgba(0,0,0,0.1)] flex flex-col md:flex-row overflow-hidden border border-white">
      
      <div class="w-full md:w-[45%] bg-[#7795E9] relative flex flex-col items-center justify-center p-12 text-center text-white overflow-hidden">
        <div class="absolute top-0 right-0 w-full h-full bg-[#7795E9] rounded-br-[180px] z-0"></div>
        <div class="relative z-10 space-y-6">
          <h1 class="text-4xl md:text-5xl font-bold tracking-tight">Hello, Welcome!</h1>
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
          <div class="pt-4">
            <p class="text-sm text-blue-100 mb-4 opacity-70">Intelligent Programming Education System</p>
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
              <input v-model="form.username" type="text" required placeholder="Username / Student ID"
                class="w-full bg-[#EFEFEF] border-none rounded-xl px-6 py-4 text-[15px] font-medium text-gray-700 placeholder-gray-400 focus:ring-2 focus:ring-[#7795E9]/50 transition-all outline-none">
            </div>
          </div>

          <div class="space-y-1">
            <div class="relative group">
              <div class="absolute inset-y-0 right-4 flex items-center pointer-events-none">
                <Lock size="18" class="text-gray-400 group-focus-within:text-[#7795E9] transition-colors" />
              </div>
              <input v-model="form.password" type="password" required placeholder="Password"
                class="w-full bg-[#EFEFEF] border-none rounded-xl px-6 py-4 text-[15px] font-medium text-gray-700 placeholder-gray-400 focus:ring-2 focus:ring-[#7795E9]/50 transition-all outline-none">
            </div>
            <div class="text-right pt-2">
              <button type="button" @click="handleForgotPassword" class="text-xs font-semibold text-gray-500 hover:text-[#7795E9] transition-colors">
                Forgot password?
              </button>
            </div>
          </div>

          <button :disabled="loading" type="submit" class="w-full py-4 bg-[#7795E9] hover:bg-[#6684D8] text-white rounded-xl font-bold text-lg shadow-lg shadow-blue-200 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-70">
            <Loader2 v-if="loading" class="animate-spin" size="22" />
            <span v-else>Login</span>
          </button>

          <div class="pt-6 text-center">
            <p class="text-sm text-gray-500">
              Don't have an account?
              <button type="button" @click="showRegisterInfo = true" class="text-[#7795E9] font-bold hover:underline">
                Contact Admin
              </button>
            </p>
          </div>

          <div class="pt-8">
            <div class="relative flex items-center justify-center mb-6">
              <div class="absolute inset-0 flex items-center">
                <div class="w-full border-t border-gray-100"></div>
              </div>
              <span class="relative px-4 text-xs font-medium text-gray-400 bg-white tracking-tight">System Resources</span>
            </div>
            <div class="flex justify-center gap-4">
              <a href="https://github.com/ZhanboGong/Information-Technology-Project" target="_blank" class="w-12 h-12 flex items-center justify-center border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors">
                <Github size="20" class="text-gray-700" />
              </a>
              <button type="button" @click="handleApplyPrivilege" class="w-12 h-12 flex items-center justify-center border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors text-gray-700">
                <ShieldCheck size="20" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>

    <el-dialog v-model="showRegisterInfo" title="Registration Guide" width="450px" center align-center class="custom-dialog">
      <div class="text-center py-4">
        <div class="w-16 h-16 bg-blue-50 text-blue-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <UserPlus size="32" />
        </div>
        <p class="text-gray-600 leading-relaxed mb-6 font-medium">
          To maintain academic integrity, accounts are pre-assigned by the department.<br>
          Please reach out to the <strong>Lab Administrator</strong> for enrollment.
        </p>
        <div class="bg-gray-50 p-4 rounded-2xl border border-gray-100 text-left space-y-3">
          <div class="flex items-center gap-3">
            <Mail size="16" class="text-[#7795E9]" />
            <span class="text-sm font-mono text-gray-700">admin_support@scu.edu.au</span>
          </div>
          <div class="flex items-center gap-3">
            <MapPin size="16" class="text-[#7795E9]" />
            <span class="text-sm text-gray-700">Room 4.12, Engineering Building</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" class="w-full rounded-xl py-6 bg-[#7795E9]" @click="showRegisterInfo = false">Got it</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../store/authStore';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  User, Lock, Loader2, Github, ShieldCheck,
  UserPlus, Mail, MapPin
} from 'lucide-vue-next';

const router = useRouter();
const authStore = useAuthStore();
const loading = ref(false);
const showRegisterInfo = ref(false); // 控制注册弹窗

const form = reactive({
  username: '',
  password: ''
});

// 处理忘记密码
const handleForgotPassword = () => {
  ElMessageBox.confirm(
    'Please contact the system administrator to reset your password. Would you like to see the contact info?',
    'Forgot Password',
    {
      confirmButtonText: 'View Contact',
      cancelButtonText: 'Cancel',
      type: 'info',
      roundButton: true
    }
  ).then(() => {
    showRegisterInfo.value = true;
  });
};

// 🚀 核心功能：申请管理员权限（显示联系方式）
const handleApplyPrivilege = () => {
  ElMessageBox.alert(
    '<div style="text-align: left;">If you are an instructor or a lab coordinator, please provide your Staff ID and Department info to: <br><br><b>Email:</b> admin_support@scu.edu.au<br><b>Subject:</b> Role Upgrade Request - [Your Name]</div>',
    'Privilege Application',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: 'I am a Teacher',
      center: true
    }
  );
};

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('Account and password are required');
    return;
  }

  loading.value = true;
  try {
    await authStore.login(form);
    ElMessage.success('Welcome back!');

    const role = authStore.user?.role;
    if (role === 'admin') router.push('/admin/dashboard');
    else if (role === 'teacher') router.push('/teacher/dashboard');
    else router.push('/student/dashboard');

  } catch (error) {
    // 错误处理由拦截器或 store 处理
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
@media (max-width: 768px) {
  .rounded-br-\[180px\] {
    border-bottom-right-radius: 0;
  }
}
:deep(.el-dialog) {
  border-radius: 24px;
}
</style>