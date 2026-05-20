<template>
  <div class="p-8 max-w-5xl mx-auto animate-fade-in">
    
    <div class="flex items-center gap-4 mb-10 border-b border-gray-200 pb-6">
      <div class="p-3.5 rounded-2xl bg-white shadow-sm border border-gray-100">
        <Settings class="text-blue-600" :size="28" />
      </div>
      <div>
        <h2 class="text-3xl font-extrabold text-[#1E3A8A] tracking-tighter">System Settings</h2>
        <p class="text-gray-500 mt-1 font-medium">Configure your personal preferences for notifications and reports.</p>
      </div>
    </div>

    <div v-if="loadingData" class="space-y-6">
      <el-skeleton animated class="setting-card-frosted p-8 rounded-3xl" />
    </div>

    <el-card v-else-if="form" shadow="never" class="setting-card-frosted rounded-3xl border-none p-2">
      
      <el-form :model="form" label-position="top" class="p-6 space-y-10">
        
        <div class="flex items-center justify-between gap-10 bg-gray-50/50 p-6 rounded-2xl border border-gray-100 hover:bg-white hover:shadow-sm transition-all">
          <div class="flex items-start gap-4 flex-1">
            <el-icon class="mt-1 text-blue-500 bg-blue-100 p-2.5 rounded-full" size="20"><Bell /></el-icon>
            <div>
              <h4 class="font-bold text-gray-800">Deadline Statistical Reports</h4>
              <p class="text-gray-500 text-sm mt-1 leading-relaxed">
                Automatically send a comprehensive summary report to your email when an assignment expires.
              </p>
            </div>
          </div>
          <div class="shrink-0">
            <el-switch 
              v-model="form.enable_report" 
              class="custom-switch"
              inline-prompt
              active-text="ON"
              inactive-text="OFF"
            />
          </div>
        </div>

        <transition name="setting-fade">
          <div v-if="form?.enable_report" class="space-y-10 pt-4 pl-4 border-l-4 border-blue-100">
            
            <div class="grid grid-cols-1 md:grid-cols-3 items-center gap-6">
              <div class="md:col-span-2">
                <h5 class="font-bold text-gray-800 flex items-center gap-2">
                  <Clock size="16" class="text-orange-500" />
                  Notification Timing
                </h5>
                <p class="text-sm text-gray-400 mt-1">Set how many hours before the deadline to receive the report.</p>
              </div>
              
              <div class="flex items-center gap-3 bg-gray-100/50 p-3 rounded-xl border border-gray-200 shadow-inner justify-between">
                <el-input-number 
                  v-model="form.remind_before_hours" 
                  :min="0" 
                  :max="72" 
                  class="custom-input-number"
                  controls-position="right"
                />
                <span class="text-xs font-bold uppercase tracking-wider text-orange-600 px-2.5 py-1 bg-orange-100 rounded-lg text-nowrap">
                  {{ form.remind_before_hours === 0 ? 'ON TIME' : `${form.remind_before_hours}H Before` }}
                </span>
              </div>
            </div>

            <div>
              <h5 class="font-bold text-gray-800 mb-3 flex items-center gap-2">
                <MailWarning size="16" class="text-blue-500" />
                Email Subject Template
              </h5>
              <div class="relative custom-input-group">
                <el-input 
                  v-model="form.subject_template" 
                  placeholder="e.g. [Notification] Assignment Report: {title}"
                  class="custom-input"
                >
                </el-input>
                <span class="absolute right-3 top-2.5 text-xs font-mono font-bold text-gray-400 bg-gray-100 px-2 py-1 rounded">
                  {title}
                </span>
              </div>
              <div class="flex items-center gap-2 mt-3 text-xs bg-blue-50 text-blue-600 p-3 rounded-lg border border-blue-100">
                <Info size="14" />
                <span>
                  The system automatically replaces 
                  <code class="font-mono bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-bold"> {title} </code> 
                  with the actual assignment name. Do not remove it.
                </span>
              </div>
            </div>

          </div>
        </transition>

        <div class="mt-12 pt-8 border-t border-gray-100 flex justify-end gap-3">
          <el-button @click="fetchSettings" class="custom-btn-secondary">
            <RefreshCcw size="16" class="mr-2" /> Reset
          </el-button>
          <el-button type="primary" :loading="loading" @click="saveSettings" class="custom-btn-primary">
            <Check size="18" class="mr-2" /> Save All Changes
          </el-button>
        </div>
      </el-form>
    </el-card>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import { Settings, Clock, Info, Check, RefreshCcw, MailWarning } from 'lucide-vue-next' // 升级图标库以匹配侧边栏
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// 1. 初始化防守
const form = ref({
  enable_report: true,
  remind_before_hours: 0,
  subject_template: '【系统通知】作业截止统计报告：《{title}》'
})
const loading = ref(false)
const loadingData = ref(true) // 数据加载状态

// 2. 初始化：获取老师的全局配置
const fetchSettings = async () => {
  loadingData.value = true
  try {
    const res = await request.get('/api/auth/notification-config/me/')
    if (res && res.data) {
      form.value = { ...form.value, ...res.data }
    }
  } catch (err) {
    console.error('Fetch Config Error:', err)
    ElMessage.error('Failed to load settings from server.')
  } finally {
    loadingData.value = false
  }
}

// 3. 提交修改
const saveSettings = async () => {
  if (form.value.enable_report && !form.value.subject_template.includes('{title}')) {
    ElMessage.warning('The subject template must contain the {title} placeholder.')
    return
  }

  loading.value = true
  try {
    await request.put('/api/auth/notification-config/me/', form.value)
    ElMessage.success('Settings updated successfully!')
  } catch (err) {
    console.error('Update Config Error:', err)
    ElMessage.error('Failed to save settings. Please try again.')
  } finally {
    loading.value = false
  }
}

onMounted(fetchSettings)
</script>

<style scoped>
/* 🚀 自定义 CSS - 延续系统的毛玻璃风格 */

/* 卡片玻璃质感 */
.setting-card-frosted {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.03) !important;
}

/* 进场动画 */
.animate-fade-in {
  animation: fadeIn 0.4s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 高级设置展开动画 */
.setting-fade-enter-active, .setting-fade-leave-active {
  transition: all 0.3s ease-out;
}
.setting-fade-enter-from, .setting-fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

/* --- Element Plus 组件美化 --- */

/* Switch 开关颜色 */
:deep(.custom-switch.el-switch.is-checked .el-switch__core) {
  background-color: #2563eb; /* blue-600 */
}

/* 输入框组合样式 */
:deep(.custom-input .el-input__wrapper) {
  border-radius: 12px;
  padding: 10px 15px;
  background-color: #f9fafb; /* gray-50 */
  box-shadow: none !important;
  border: 1px solid #e5e7eb; /* gray-200 */
  transition: all 0.2s;
}
:deep(.custom-input .el-input__wrapper.is-focus) {
  background-color: white;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
}

/* 数字输入框样式 */
:deep(.custom-input-number) {
  width: 140px;
}
:deep(.custom-input-number .el-input__wrapper) {
  border-radius: 10px;
  background-color: transparent;
  box-shadow: none !important;
  border: none !important;
}

/* 按钮样式 */
.custom-btn-primary {
  @apply px-6 py-5 rounded-xl font-bold transition-all shadow-md hover:scale-105;
  background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%);
  border: none;
}
.custom-btn-secondary {
  @apply px-6 py-5 rounded-xl font-bold text-gray-600 hover:bg-gray-100 transition-all border border-gray-200 bg-white;
}
</style>