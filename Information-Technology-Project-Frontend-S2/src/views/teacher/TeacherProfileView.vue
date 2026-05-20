<template>
  <div class="space-y-6 animate-fade-in max-w-6xl mx-auto pt-2 pb-20">
    
    <div class="frosted-card p-6 rounded-2xl border border-white/60 bg-gradient-to-r from-indigo-50/50 to-blue-50/30 shadow-sm">
      <div class="flex items-center gap-5">
        <div class="relative">
          <div class="absolute -inset-1 bg-gradient-to-tr from-indigo-600 to-blue-600 rounded-full opacity-20 blur-sm"></div>
          <div class="relative h-16 w-16 rounded-full bg-white border-2 border-white shadow-sm flex items-center justify-center text-2xl font-bold text-indigo-600">
            {{ user?.first_name?.[0] || user?.username?.[0]?.toUpperCase() || 'T' }}
          </div>
        </div>
        <div>
          <h2 class="text-2xl font-bold text-gray-800 tracking-tight">
            {{ user?.first_name || 'Teacher' }} {{ user?.last_name || '' }}
          </h2>
          <p class="text-xs text-gray-500 mt-1 flex items-center gap-2 font-medium">
            <span class="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-md uppercase tracking-wider text-[10px]">Teacher Account</span>
            <span class="text-gray-300">|</span>
            <span>Staff ID: {{ user?.student_id_num || 'N/A' }}</span>
          </p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      <div class="space-y-6">
        <div class="frosted-card p-6 rounded-2xl border border-white/60 bg-white/40">
          <h3 class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-5">Security Status</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between p-3 rounded-xl bg-white/50 border border-white/20">
              <div class="flex items-center gap-3 text-gray-700">
                <Mail size="16" class="text-indigo-500" />
                <span class="text-xs font-semibold">Email Verified</span>
              </div>
              <CheckCircle2 size="16" class="text-emerald-500" />
            </div>
            <div class="flex items-center justify-between p-3 rounded-xl bg-white/50 border border-white/20">
              <div class="flex items-center gap-3 text-gray-700">
                <ShieldCheck size="16" class="text-purple-500" />
                <span class="text-xs font-semibold">Teacher Verification</span>
              </div>
              <CheckCircle2 size="16" class="text-emerald-500" />
            </div>
          </div>
        </div>
      </div>

      <div class="lg:col-span-2 space-y-6">
        <div class="frosted-card p-6 rounded-2xl border border-white/60 bg-white/40 shadow-sm relative overflow-hidden">
          <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center gap-3">
            <div class="p-2 bg-indigo-100 text-indigo-600 rounded-lg"><UserSquare size="18" /></div>
            Personal Information
          </h3>

          <form @submit.prevent="handleUpdateInfo" class="space-y-5">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div class="space-y-1.5">
                <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider ml-1">First Name</label>
                <div class="relative group">
                  <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-500 transition-colors">
                    <UserSquare size="16" />
                  </span>
                  <input v-model="infoForm.first_name" type="text" 
                         class="w-full pl-11 pr-4 py-2.5 text-sm rounded-xl border border-gray-200 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all bg-white/80" />
                </div>
              </div>

              <div class="space-y-1.5">
                <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider ml-1">Last Name</label>
                <div class="relative group">
                  <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-500 transition-colors">
                    <UserSquare size="16" />
                  </span>
                  <input v-model="infoForm.last_name" type="text"
                         class="w-full pl-11 pr-4 py-2.5 text-sm rounded-xl border border-gray-200 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all bg-white/80" />
                </div>
              </div>

              <div class="md:col-span-2 space-y-1.5">
                <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider ml-1">Email Address (Read-only)</label>
                <div class="relative group">
                  <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
                    <Mail size="16" />
                  </span>
                  <input :value="user?.email" readonly 
                         class="w-full pl-11 pr-4 py-2.5 text-sm rounded-xl border border-gray-100 bg-gray-50/50 text-gray-500 cursor-default outline-none" />
                </div>
                <p class="text-[10px] text-orange-500 flex items-center gap-1 mt-1 ml-1 font-medium">
                  <AlertCircle size="12" /> For security reasons, please contact the IT department to change your email.
                </p>
              </div>
            </div>

            <div class="pt-5 border-t border-gray-100 flex justify-end">
              <button type="submit" :disabled="infoSubmitting" 
                      class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-xs shadow-md transition-all flex items-center gap-2 active:scale-95 disabled:opacity-50">
                <Loader2 v-if="infoSubmitting" size="14" class="animate-spin" />
                <Save v-else size="14" />
                Save Changes
              </button>
            </div>
          </form>
        </div>

        <div class="frosted-card p-6 rounded-2xl border border-white/60 bg-white/40 shadow-sm relative overflow-hidden">
          <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center gap-3">
            <div class="p-2 bg-orange-100 text-orange-600 rounded-lg"><Lock size="18" /></div>
            Security & Password
          </h3>

          <form @submit.prevent="handleChangePassword" class="space-y-5">
            <div class="space-y-4">
              <div class="space-y-1.5">
                <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider ml-1">Current Password</label>
                <div class="relative group">
                  <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-orange-500 transition-colors">
                    <KeyRound size="16" />
                  </span>
                  <input v-model="pwdForm.old_password" type="password" placeholder="••••••••"
                         class="w-full pl-11 pr-4 py-2.5 text-sm rounded-xl border border-gray-200 focus:ring-4 focus:ring-orange-500/10 focus:border-orange-500 outline-none transition-all bg-white/80" />
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div class="space-y-1.5">
                  <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider ml-1">New Password</label>
                  <div class="relative group">
                    <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-orange-500 transition-colors">
                      <Lock size="16" />
                    </span>
                    <input v-model="pwdForm.new_password" type="password"
                           class="w-full pl-11 pr-4 py-2.5 text-sm rounded-xl border border-gray-200 focus:ring-4 focus:ring-orange-500/10 focus:border-orange-500 outline-none transition-all bg-white/80" />
                  </div>
                </div>
                <div class="space-y-1.5">
                  <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider ml-1">Confirm Password</label>
                  <div class="relative group">
                    <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-orange-500 transition-colors">
                      <Lock size="16" />
                    </span>
                    <input v-model="pwdForm.confirm_password" type="password"
                           class="w-full pl-11 pr-4 py-2.5 text-sm rounded-xl border border-gray-200 focus:ring-4 focus:ring-orange-500/10 focus:border-orange-500 outline-none transition-all bg-white/80" />
                  </div>
                </div>
              </div>
            </div>

            <div class="pt-5 border-t border-gray-100 flex justify-end">
              <button type="submit" :disabled="pwdSubmitting" 
                      class="px-6 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-bold text-xs shadow-md transition-all flex items-center gap-2 active:scale-95 disabled:opacity-50">
                <Loader2 v-if="pwdSubmitting" size="14" class="animate-spin" />
                <RefreshCw v-else size="14" />
                Update Password
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useAuthStore } from '../../store/authStore';
import api from '../../utils/request';
import { ElMessage } from 'element-plus';
import { 
  Loader2, Lock, Mail, CheckCircle2, AlertCircle,
  ShieldCheck, UserSquare, Save, KeyRound, RefreshCw
} from 'lucide-vue-next';

const authStore = useAuthStore();
const user = computed(() => authStore.user);

const infoSubmitting = ref(false);
const infoForm = ref({ first_name: '', last_name: '' });

const pwdSubmitting = ref(false);
const pwdForm = ref({ old_password: '', new_password: '', confirm_password: '' });

// 🚀 获取最新完整信息，确保邮箱和工号同步
const fetchLatestProfile = async () => {
  try {
    const res = await api.get('/api/auth/profile/me/');
    const latestData = res.data || res;
    authStore.setUser(latestData);
    
    infoForm.value.first_name = latestData.first_name || '';
    infoForm.value.last_name = latestData.last_name || '';
  } catch (error) {
    console.error('Fetch profile failed:', error);
    if (user.value) {
      infoForm.value.first_name = user.value.first_name || '';
      infoForm.value.last_name = user.value.last_name || '';
    }
  }
};

onMounted(() => {
  fetchLatestProfile();
});

const handleUpdateInfo = async () => {
  if (!infoForm.value.first_name) {
    return ElMessage.warning('First name is required');
  }

  infoSubmitting.value = true;
  try {
    const res = await api.patch('/api/auth/profile/me/', {
      first_name: infoForm.value.first_name,
      last_name: infoForm.value.last_name
    });
    ElMessage.success('Information updated successfully');
    authStore.setUser(res.data || res); 
  } catch (error) {
    console.error('Update failed');
    ElMessage.error('Update failed');
  } finally {
    infoSubmitting.value = false;
  }
};

const handleChangePassword = async () => {
  if (pwdForm.value.new_password !== pwdForm.value.confirm_password) {
    return ElMessage.error('Passwords do not match');
  }
  if (!pwdForm.value.old_password || pwdForm.value.new_password.length < 6) {
    return ElMessage.warning('New password must be at least 6 characters');
  }

  pwdSubmitting.value = true;
  try {
    await api.post('/api/auth/profile/change-password/', {
      old_password: pwdForm.value.old_password,
      new_password: pwdForm.value.new_password
    });
    ElMessage.success('Password changed successfully');
    pwdForm.value = { old_password: '', new_password: '', confirm_password: '' };
  } catch (error) {
    console.error('Change password failed');
  } finally {
    pwdSubmitting.value = false;
  }
};
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.animate-fade-in { animation: fadeIn 0.4s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
input::placeholder { color: #cbd5e1; font-size: 0.75rem; }
</style>