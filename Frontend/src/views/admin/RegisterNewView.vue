<template>
  <div class="space-y-8 animate-fade-in pt-4 pb-12">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-black text-gray-800 tracking-tight">Provision Accounts</h2>
        <p class="text-sm text-gray-500 mt-1">Create a new standalone account or import user data in batches through files</p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2 space-y-6">
        <div class="frosted-card p-8 rounded-[2.5rem] border border-white/60 shadow-sm">
          <div class="flex items-center gap-3 mb-8">
            <div class="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600">
              <UserPlus size="24" />
            </div>
            <h3 class="text-xl font-bold text-gray-800">Single User Registration</h3>
          </div>

          <el-form :model="singleForm" label-position="top" class="register-form">
            <el-row :gutter="32">
              <el-col :span="12">
                <el-form-item label="Username (Unique ID)" required>
                  <el-input v-model="singleForm.username" placeholder="e.g. smith_2024" />
                </el-form-item>
                
                <el-form-item label="Student / Staff ID" required>
                  <el-input v-model="singleForm.student_id_num" placeholder="e.g. 20240001" />
                </el-form-item>

                <el-form-item label="Full Name" required>
                  <el-input v-model="singleForm.first_name" placeholder="Enter real name" />
                </el-form-item>
              </el-col>

              <el-col :span="12">
                <el-form-item label="System Role" required>
                  <el-select v-model="singleForm.role" class="w-full">
                    <el-option label="Student" value="student" />
                    <el-option label="Teacher" value="teacher" />
                    <el-option label="Administrator" value="admin" />
                  </el-select>
                </el-form-item>

                <el-form-item label="Class / Department">
                  <el-input v-model="singleForm.class_name" placeholder="e.g. Year 2 - Class A" />
                </el-form-item>

                <el-form-item label="Email Address">
                  <el-input v-model="singleForm.email" placeholder="example@univ.edu" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="mt-6 flex justify-end pt-4 border-t border-slate-50">
              <button 
                @click="handleSingleRegister" 
                :disabled="loading"
                class="px-10 py-3.5 bg-blue-600 text-white font-black rounded-2xl shadow-lg shadow-blue-100 hover:bg-blue-700 hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-50"
              >
                {{ loading ? 'Provisioning...' : 'Confirm Registration' }}
              </button>
            </div>
          </el-form>
        </div>
      </div>

      <div class="space-y-6">
        <div class="frosted-card p-8 rounded-[2.5rem] border border-white/60 shadow-sm flex flex-col h-full">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600">
              <Layers size="24" />
            </div>
            <h3 class="text-xl font-bold text-gray-800">Bulk Import</h3>
          </div>

          <p class="text-xs text-gray-400 mb-8 leading-relaxed">
            支持一键导入 Excel 或 CSV 文件。请确保文件包含：<b>username, id_num, name, role</b> 等字段。
          </p>

          <el-upload
            class="bulk-uploader"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
          >
            <div class="py-4">
              <UploadCloud class="mx-auto text-blue-400 mb-2" size="48" />
              <div class="text-sm font-bold text-gray-600">Drop file here or <span class="text-blue-600">browse</span></div>
              <p class="text-[10px] text-gray-400 mt-1">Support .xlsx, .csv (Max 10MB)</p>
            </div>
          </el-upload>

          <div class="mt-auto pt-8">
            <button 
              @click="handleBulkImport"
              :disabled="!uploadFile || loading"
              class="w-full py-4 bg-slate-900 text-white font-black rounded-2xl shadow-xl hover:bg-black transition-all flex items-center justify-center gap-2 disabled:bg-gray-200"
            >
              <FileSpreadsheet size="18" /> Start Batch Processing
            </button>
            
            <p class="text-[10px] text-center text-gray-400 mt-4">
              * 批量导入的用户默认密码与其 ID 一致
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { UserPlus, Layers, UploadCloud, FileSpreadsheet } from 'lucide-vue-next';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';

const loading = ref(false);
const uploadFile = ref(null);

// 单个注册表单
const singleForm = reactive({
  username: '',
  student_id_num: '',
  first_name: '',
  class_name: '',
  role: 'student',
  email: ''
});

/**
 * 处理单个注册
 */
const handleSingleRegister = async () => {
  if (!singleForm.username || !singleForm.student_id_num || !singleForm.first_name) {
    ElMessage.warning('Required fields are missing');
    return;
  }

  loading.value = true;
  try {
    // 调用的还是我们之前写的 admin/users 接口，后端 perform_create 会自动处理密码
    await api.post('/api/auth/admin/users/', singleForm);
    ElMessage.success(`User ${singleForm.username} created!`);
    
    // 重置表单
    Object.assign(singleForm, {
      username: '', student_id_num: '', first_name: '', class_name: '', role: 'student', email: ''
    });
  } catch (err) {
    console.error(err);
    const msg = err.response?.data?.username ? 'Username/ID already exists' : 'Registration failed';
    ElMessage.error(msg);
  } finally {
    loading.value = false;
  }
};

/**
 * 处理文件选择
 */
const handleFileChange = (file) => {
  uploadFile.value = file.raw;
};

/**
 * 执行批量导入 (需对应后端接口支持)
 */
const handleBulkImport = async () => {
  if (!uploadFile.value) return;

  const formData = new FormData();
  formData.append('file', uploadFile.value);

  loading.value = true;
  try {
    // 注意：这个接口需要你在后端 TeacherStudentManagementViewSet 中已经实现的逻辑
    // 或者你可以专门为 Admin 写一个批量导入接口
    await api.post('/api/auth/teacher/students/import-students/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    ElMessage.success('Batch import task triggered successfully');
    uploadFile.value = null;
  } catch (err) {
    ElMessage.error('Import failed: Check file format');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

:deep(.register-form .el-form-item__label) {
  font-weight: 800;
  color: #475569;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px !important;
}

:deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 4px 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}

:deep(.bulk-uploader .el-upload-dragger) {
  border-radius: 24px;
  border: 2px dashed #e2e8f0;
  background: rgba(248, 250, 252, 0.5);
  transition: all 0.3s ease;
}

:deep(.bulk-uploader .el-upload-dragger:hover) {
  border-color: #3b82f6;
  background: white;
}
</style>