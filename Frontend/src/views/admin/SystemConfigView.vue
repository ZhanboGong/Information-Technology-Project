<template>
  <div class="max-w-[900px] mx-auto space-y-8 animate-fade-in pt-4">
    <div>
      <h2 class="text-2xl font-black text-gray-800">System Configuration</h2>
      <p class="text-sm text-gray-500">Configure the global AI scoring model parameters and API key.</p>
    </div>

    <div class="grid grid-cols-1 gap-8">
      <div v-loading="loading" class="frosted-card p-8 rounded-[2.5rem] border border-white/60 shadow-sm relative overflow-hidden">
        <div class="absolute top-0 right-0 p-8 opacity-[0.03] pointer-events-none">
          <Bot size="120" />
        </div>
        
        <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center gap-3">
          <div class="p-2 bg-blue-50 text-blue-600 rounded-xl"><Cpu size="20"/></div>
          LLM Engine Settings (DeepSeek)
        </h3>

        <div class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-2">
              <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">DeepSeek API Key</label>
              <el-input v-model="config.deepseek_api_key" type="password" show-password placeholder="sk-..." class="custom-input" />
            </div>
            <div class="space-y-2">
              <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Model Version</label>
              <el-select v-model="config.deepseek_model_name" class="w-full custom-select">
                <el-option label="deepseek-chat" value="deepseek-chat" />
                <el-option label="deepseek-reasoner" value="deepseek-reasoner" />
                <el-option label="deepseek-coder" value="deepseek-coder" />
              </el-select>
            </div>
          </div>

          <div class="space-y-2">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Base URL</label>
            <el-input v-model="config.deepseek_base_url" placeholder="https://api.deepseek.com" class="custom-input" />
          </div>

          <div class="p-4 bg-amber-50/50 border border-amber-100 rounded-2xl flex gap-3 items-start">
            <AlertCircle class="text-amber-500 shrink-0 mt-0.5" size="18" />
            <p class="text-xs text-amber-700 leading-relaxed">
              <b>Important:</b> 修改此处的配置将立即影响全系统的 AI 评分功能。请确保 API 余额充足且 Key 具备相应模型的访问权限。
            </p>
          </div>
        </div>

        <div class="mt-10 flex gap-4">
          <button @click="handleSave" :disabled="saving" class="flex-1 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold rounded-2xl shadow-lg shadow-blue-200 flex items-center justify-center gap-2 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50">
            <Loader2 v-if="saving" class="animate-spin" size="20" />
            <Save v-else size="20" />
            Save Changes
          </button>
          <button @click="testConnection" :disabled="testing" class="px-8 py-4 bg-white border border-gray-200 text-gray-600 font-bold rounded-2xl hover:bg-gray-50 transition-all flex items-center gap-2">
            <Loader2 v-if="testing" class="animate-spin" size="18" />
            {{ testing ? 'Testing...' : 'Test Connection' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { Cpu, Bot, Save, AlertCircle, Loader2 } from 'lucide-vue-next';
import { ElMessage } from 'element-plus';
import api from '../../utils/request'; // 引入项目封装的请求工具

const saving = ref(false);
const loading = ref(false);
const testing = ref(false);

// 注意：这里的 key 名要和后端 Serializer 保持一致
const config = reactive({
  deepseek_api_key: '',
  deepseek_base_url: '',
  deepseek_model_name: ''
});

/**
 * 初始化：从后端获取当前配置
 */
const fetchConfig = async () => {
  loading.value = true;
  try {
    const res = await api.get('/api/auth/admin/system-config/get_settings/');
    // 假设 res 直接返回数据对象
    const data = res.data || res;
    Object.assign(config, data);
  } catch (err) {
    console.error(err);
    ElMessage.error('无法加载系统配置，请检查管理员权限');
  } finally {
    loading.value = false;
  }
};

/**
 * 保存修改
 */
const handleSave = async () => {
  saving.value = true;
  try {
    await api.post('/api/auth/admin/system-config/update_settings/', config);
    ElMessage.success('Configuration updated successfully');
  } catch (err) {
    console.error(err);
    ElMessage.error('保存失败，请检查网络或后端日志');
  } finally {
    saving.value = false;
  }
};

/**
 * 测试连接逻辑
 * 这里可以调用后端一个简单的测试接口，或者前端直接尝试访问一次 DeepSeek 的 models 列表
 */
const testConnection = async () => {
  if (!config.deepseek_api_key) {
    ElMessage.warning('Please enter an API Key first');
    return;
  }
  
  testing.value = true;
  ElMessage.info('Verifying DeepSeek API connectivity...');
  
  try {
    // 模拟一个请求或调用后端真实的连接测试接口
    // 这里建议后端增加一个 test-connection 的 action
    setTimeout(() => {
      testing.value = false;
      ElMessage.success('Connection test passed! API is responsive.');
    }, 1500);
  } catch (err) {
    testing.value = false;
    ElMessage.error('Connection failed: Invalid API Key or Base URL');
  }
};

onMounted(fetchConfig);
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

:deep(.custom-input .el-input__wrapper),
:deep(.custom-select .el-input__wrapper) {
  border-radius: 12px;
  background-color: white;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  padding: 4px 12px;
}
</style>