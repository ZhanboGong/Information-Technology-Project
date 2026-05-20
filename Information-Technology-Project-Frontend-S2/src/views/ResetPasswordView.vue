<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-[#F3F4F9] p-4 font-sans">
    <div class="w-full max-w-[900px] h-auto min-h-[550px] bg-white rounded-[40px] shadow-[0_20px_50px_rgba(0,0,0,0.1)] flex flex-col md:flex-row overflow-hidden border border-white">
      
      <div class="w-full md:w-[45%] bg-[#7795E9] relative flex flex-col items-center justify-center p-12 text-center text-white overflow-hidden">
        <div class="absolute top-0 right-0 w-full h-full bg-[#7795E9] rounded-br-[180px] z-0"></div>
        <div class="relative z-10 space-y-6">
          <h1 class="text-4xl md:text-5xl font-bold tracking-tight">Reset Password</h1>
          <div class="py-8 flex justify-center">
            <svg width="60" height="60" class="rounded-2xl bg-white/20 p-2.5 backdrop-blur-md" viewBox="0 0 120 120">
              <circle cx="60" cy="45" r="20" fill="none" stroke="white" stroke-width="7" />
              <rect x="35" y="65" width="50" height="35" rx="5" fill="none" stroke="white" stroke-width="7" />
              <circle cx="60" cy="82" r="6" fill="white" opacity="0.8" />
            </svg>
          </div>
          <div class="pt-4">
            <p class="text-sm text-blue-100 mb-4 opacity-70">Enter your new password below</p>
            <div class="w-32 h-1 bg-white/30 mx-auto rounded-full"></div>
          </div>
        </div>
      </div>

      <div class="w-full md:w-[55%] p-10 md:p-16 flex flex-col justify-center bg-white">
        <div class="mb-10 text-center">
          <h2 class="text-4xl font-black text-gray-800 tracking-tight">New Password</h2>
        </div>

        <form @submit.prevent="handleReset" class="space-y-6">
          <div class="space-y-5">
            <div class="relative group">
              <div class="absolute inset-y-0 right-4 flex items-center pointer-events-none">
                <Lock size="18" class="text-gray-400 group-focus-within:text-[#7795E9] transition-colors" />
              </div>
              <input v-model="password" type="password" required placeholder="New password"
                class="w-full bg-[#EFEFEF] border-none rounded-xl px-6 py-4 text-[15px] font-medium text-gray-700 placeholder-gray-400 focus:ring-2 focus:ring-[#7795E9]/50 transition-all outline-none">
            </div>
            <div class="relative group">
              <div class="absolute inset-y-0 right-4 flex items-center pointer-events-none">
                <Lock size="18" class="text-gray-400 group-focus-within:text-[#7795E9] transition-colors" />
              </div>
              <input v-model="confirmPwd" type="password" required placeholder="Confirm new password"
                class="w-full bg-[#EFEFEF] border-none rounded-xl px-6 py-4 text-[15px] font-medium text-gray-700 placeholder-gray-400 focus:ring-2 focus:ring-[#7795E9]/50 transition-all outline-none">
            </div>
          </div>

          <button :disabled="loading" type="submit" class="w-full py-4 bg-[#7795E9] hover:bg-[#6684D8] text-white rounded-xl font-bold text-lg shadow-lg shadow-blue-200 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-70">
            <Loader2 v-if="loading" class="animate-spin" size="22" />
            <span v-else>Reset Password</span>
          </button>

          <p v-if="message" class="text-sm text-center pt-4" :class="success ? 'text-emerald-500' : 'text-red-400'">
            {{ message }}
          </p>

          <div class="pt-4 text-center">
            <router-link to="/login" class="text-sm text-[#7795E9] font-bold hover:underline">
              &larr; Back to Login
            </router-link>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRoute } from 'vue-router';
import api from '../utils/request';
import { ElMessage } from 'element-plus';
import { Lock, Loader2 } from 'lucide-vue-next';

const route = useRoute();
const password = ref('');
const confirmPwd = ref('');
const loading = ref(false);
const message = ref('');
const success = ref(false);

const handleReset = async () => {
  const token = route.query.token;
  if (!token) {
    message.value = 'Invalid or missing reset token.';
    return;
  }
  if (!password.value || password.value.length < 6) {
    ElMessage.warning('Password must be at least 6 characters.');
    return;
  }
  if (password.value !== confirmPwd.value) {
    ElMessage.warning('Passwords do not match.');
    return;
  }
  loading.value = true;
  try {
    await api.post('/api/auth/password-reset/confirm/', {
      token,
      password: password.value
    });
    success.value = true;
    message.value = 'Password reset successfully. Redirecting to login...';
    setTimeout(() => { window.location.href = '/login'; }, 2000);
  } catch {
    message.value = 'Reset failed. The link may have expired.';
  } finally {
    loading.value = false;
  }
};
</script>