<template>
  <div class="space-y-6 animate-fade-in pt-4">
    <div class="flex justify-between items-end">
      <div>
        <h2 class="text-2xl font-black text-gray-800">User Management</h2>
        <p class="text-sm text-gray-500">Manage the account permissions and statuses of administrators, teachers and students across all platforms.</p>
      </div>
      <div class="flex gap-3">
        <el-input 
          v-model="search" 
          @input="handleSearch" 
          placeholder="Search by name/ID..." 
          class="w-64 custom-input" 
          clearable 
        />
        <button @click="openCreateDialog" class="px-6 py-2.5 bg-blue-600 text-white font-bold rounded-xl shadow-lg shadow-blue-200 hover:bg-blue-700 transition-all flex items-center gap-2">
          <UserPlus size="18" /> Create User
        </button>
      </div>
    </div>

    <div class="flex gap-4 bg-white/40 p-1.5 rounded-2xl border border-white/60 w-fit">
      <button v-for="role in ['all', 'admin', 'teacher', 'student']" :key="role" 
        @click="handleRoleChange(role)"
        :class="['px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all', activeRole === role ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-400 hover:text-gray-600']">
        {{ role }}
      </button>
    </div>

    <div class="frosted-card rounded-[2rem] border border-white/60 overflow-hidden shadow-sm">
      <el-table 
        v-loading="loading" 
        :data="userList" 
        style="width: 100%" 
        class="admin-table cursor-pointer"
        @row-click="openEditDialog"
      >
        <el-table-column label="USER INFO" min-width="200">
          <template #default="scope">
            <div class="flex items-center gap-3 py-1">
              <div class="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center font-bold text-blue-600 border border-white uppercase shadow-sm">
                {{ (scope.row.username || '?').charAt(0) }}
              </div>
              <div>
                <p class="font-bold text-gray-800 leading-tight">{{ scope.row.first_name || scope.row.username || 'Unknown' }}</p>
                <p class="text-[10px] font-mono text-gray-400 mt-0.5">{{ scope.row.student_id_num || 'SYSTEM_ADMIN' }}</p>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="ROLE" width="130">
          <template #default="scope">
            <el-tag :type="getRoleTag(scope.row.role)" effect="light" class="font-black border-none px-3 rounded-lg">
              {{ (scope.row.role || 'student').toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="STATUS" width="140">
          <template #default="scope">
            <div @click.stop class="flex items-center">
              <el-switch
                v-model="scope.row.is_active"
                @change="(val) => handleToggleStatus(scope.row, val)"
                style="--el-switch-on-color: #10b981; --el-switch-off-color: #d1d5db"
              />
              <span class="text-[11px] font-bold ml-2" :class="scope.row.is_active ? 'text-emerald-600' : 'text-gray-400'">
                {{ scope.row.is_active ? 'ACTIVE' : 'DISABLED' }}
              </span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="ACTIONS" width="160" align="right">
          <template #default="scope">
            <div class="flex justify-end gap-2" @click.stop>
              <el-tooltip content="Reset Password" placement="top">
                <button @click="handleResetPassword(scope.row)" class="p-2 text-amber-500 hover:bg-amber-50 rounded-xl transition-colors">
                  <KeyRound size="16"/>
                </button>
              </el-tooltip>
              <el-tooltip content="Delete User" placement="top">
                <button @click="handleDelete(scope.row)" class="p-2 text-red-400 hover:bg-red-50 rounded-xl transition-colors">
                  <Trash2 size="16"/>
                </button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog 
      v-model="showDialog" 
      :title="isEdit ? 'Edit User Details' : 'Create New System User'" 
      width="680px" 
      class="custom-dialog"
      destroy-on-close
    >
      <el-form :model="userForm" label-position="top">
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="Login Username (Account)" required>
              <el-input v-model="userForm.username" placeholder="e.g. jsmith" :disabled="isEdit" />
            </el-form-item>
            
            <el-form-item label="Student / Staff ID" required>
              <el-input v-model="userForm.student_id_num" placeholder="e.g. 20240001" />
            </el-form-item>

            <el-form-item label="System Role" required>
              <el-select v-model="userForm.role" placeholder="Select role" class="w-full">
                <el-option label="Student" value="student" />
                <el-option label="Teacher" value="teacher" />
                <el-option label="Administrator" value="admin" />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="Full Name (Display Name)" required>
              <el-input v-model="userForm.first_name" placeholder="Enter real name" />
            </el-form-item>

            <el-form-item label="Email Address">
              <el-input v-model="userForm.email" placeholder="example@univ.edu" />
            </el-form-item>

            <el-form-item label="Class / Department">
              <el-input v-model="userForm.class_name" placeholder="e.g. Computer Science B1" />
            </el-form-item>
          </el-col>
        </el-row>

        <div v-if="!isEdit" class="mt-4 p-4 bg-slate-50 rounded-2xl border border-slate-100">
          <p class="text-[11px] text-slate-500 leading-relaxed italic">
            <span class="font-bold text-blue-600">Tip:</span> 新用户的初始密码默认与其输入的<b>学号/工号</b>一致。
          </p>
        </div>
      </el-form>
      
      <template #footer>
        <div class="flex gap-3 justify-end px-2 pt-2">
          <el-button @click="showDialog = false" class="rounded-xl px-6">Cancel</el-button>
          <el-button 
            @click="handleSaveUser" 
            type="primary" 
            :loading="submitting" 
            class="rounded-xl bg-blue-600 border-none px-10 font-black shadow-lg shadow-blue-200"
          >
            {{ isEdit ? 'Update Changes' : 'Confirm Create' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue';
import { UserPlus, Trash2, KeyRound } from 'lucide-vue-next';
import { ElMessage, ElMessageBox } from 'element-plus';
import api from '../../utils/request'; 

const activeRole = ref('all');
const search = ref('');
const userList = ref([]);
const loading = ref(false);
const submitting = ref(false);

// 弹窗状态管理
const showDialog = ref(false);
const isEdit = ref(false);
const currentUserId = ref(null);

const userForm = reactive({
  username: '',
  student_id_num: '',
  first_name: '',
  email: '',
  class_name: '',
  role: 'student'
});

const openCreateDialog = () => {
  isEdit.value = false;
  currentUserId.value = null;
  Object.assign(userForm, {
    username: '', student_id_num: '', first_name: '', email: '', class_name: '', role: 'student'
  });
  showDialog.value = true;
};

const openEditDialog = (row) => {
  isEdit.value = true;
  currentUserId.value = row.id;
  Object.assign(userForm, {
    username: row.username,
    student_id_num: row.student_id_num,
    first_name: row.first_name,
    email: row.email,
    class_name: row.class_name,
    role: row.role
  });
  showDialog.value = true;
};

const getRoleTag = (role) => {
  if (!role) return 'info';
  const r = role.toLowerCase();
  if (r === 'admin') return 'danger';
  if (r === 'teacher') return 'warning';
  return 'info';
};

const fetchUsers = async () => {
  loading.value = true;
  try {
    const res = await api.get('/api/auth/admin/users/', {
      params: { role: activeRole.value, search: search.value }
    });
    userList.value = res.results || res.data || res;
  } catch (error) {
    ElMessage.error('Failed to sync user records');
  } finally {
    loading.value = false;
  }
};

const handleSaveUser = async () => {
  if (!userForm.username || !userForm.student_id_num || !userForm.first_name) {
    ElMessage.warning('Please complete the required information');
    return;
  }
  
  submitting.value = true;
  try {
    if (isEdit.value) {
      await api.patch(`/api/auth/admin/users/${currentUserId.value}/`, userForm);
      ElMessage.success('User updated successfully');
    } else {
      await api.post('/api/auth/admin/users/', userForm);
      ElMessage.success('User created successfully');
    }
    showDialog.value = false;
    fetchUsers(); 
  } catch (error) {
    ElMessage.error(error.response?.data?.username ? 'Username already exists' : 'Action failed');
  } finally {
    submitting.value = false;
  }
};

const handleToggleStatus = async (user, val) => {
  try {
    await api.patch(`/api/auth/admin/users/${user.id}/`, { is_active: val });
    ElMessage.success(`User ${user.username} is now ${val ? 'Active' : 'Disabled'}`);
  } catch (error) {
    user.is_active = !val; // 失败回滚
    ElMessage.error('Failed to change user status');
  }
};

let searchTimer = null;
const handleSearch = () => {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => fetchUsers(), 400);
};

const handleRoleChange = (role) => {
  activeRole.value = role;
  fetchUsers();
};

const handleResetPassword = async (user) => {
  try {
    await ElMessageBox.confirm(`Reset password for ${user.username}?`, 'Security Check', { type: 'warning' });
    await api.post(`/api/auth/admin/users/${user.id}/reset-password/`);
    ElMessage.success('Password updated successfully');
  } catch (err) { if (err !== 'cancel') ElMessage.error('Reset failed'); }
};

const handleDelete = async (user) => {
  try {
    await ElMessageBox.confirm('Permanent deletion. Proceed?', 'Critical', { type: 'error' });
    await api.delete(`/api/auth/admin/users/${user.id}/`);
    ElMessage.success('User removed');
    fetchUsers();
  } catch (err) { if (err !== 'cancel') ElMessage.error('Delete failed'); }
};

onMounted(fetchUsers);
</script>

<style scoped>
/* 表格行美化 */
.admin-table :deep(.el-table__row) {
  transition: all 0.2s;
}
.admin-table :deep(.el-table__row:hover) {
  background-color: rgba(255, 255, 255, 0.6) !important;
  transform: scale(1.002);
}

:deep(.admin-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
}
.custom-input :deep(.el-input__wrapper) {
  border-radius: 0.75rem;
  background-color: rgba(255, 255, 255, 0.6);
  box-shadow: none;
  border: 1px solid rgba(226, 232, 240, 0.8);
}

/* 磨砂效果弹窗 */
:deep(.custom-dialog) {
  border-radius: 32px;
  overflow: hidden;
  backdrop-filter: blur(20px);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}
:deep(.el-dialog__header) {
  margin-right: 0;
  padding: 24px 32px;
  border-bottom: 1px solid rgba(0,0,0,0.03);
}
:deep(.el-dialog__title) {
  font-weight: 900;
  letter-spacing: -0.02em;
  color: #1e293b;
}
:deep(.el-dialog__body) {
  padding: 32px;
}
:deep(.el-form-item__label) {
  font-weight: 700;
  color: #64748b;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px !important;
}
:deep(.el-input__wrapper) {
  border-radius: 12px;
  background: white;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
</style>