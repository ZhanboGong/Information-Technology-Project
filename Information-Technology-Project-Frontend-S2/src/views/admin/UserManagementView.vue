<template>
  <div class="space-y-6 animate-fade-in pt-4 pb-10">
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

    <div class="flex justify-between items-center">
      <div class="flex gap-4 bg-white/40 p-1.5 rounded-2xl border border-white/60 w-fit">
        <button v-for="role in ['all', 'admin', 'teacher', 'student']" :key="role" 
          @click="handleRoleChange(role)"
          :class="['px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all', activeRole === role ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-400 hover:text-gray-600']">
          {{ role }}
        </button>
      </div>
      
      <div class="flex gap-2">
        <button 
          @click="handleStatusFilter('pending_approval')"
          :class="['px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all border', 
                   activeStatus === 'pending_approval' ? 'bg-orange-500 text-white border-orange-500 shadow-lg shadow-orange-100' : 'bg-white text-orange-500 border-orange-100 hover:bg-orange-50']"
        >
          Pending Approvals
        </button>
      </div>
    </div>

    <div class="frosted-card rounded-[2rem] border border-white/60 overflow-hidden shadow-sm">
      <el-table 
        v-loading="loading" 
        :data="pagedUserList" 
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
        
        <el-table-column label="STATUS" width="180">
          <template #default="scope">
            <div @click.stop class="flex flex-col gap-1">
              <div class="flex items-center">
                <el-switch
                  v-model="scope.row.is_active"
                  @change="(val) => handleToggleStatus(scope.row, val)"
                  style="--el-switch-on-color: #10b981; --el-switch-off-color: #d1d5db"
                />
                <span class="text-[10px] font-bold ml-2 uppercase" :class="scope.row.is_active ? 'text-emerald-600' : 'text-gray-400'">
                  {{ scope.row.is_active ? 'Active' : 'Disabled' }}
                </span>
              </div>
              <div v-if="scope.row.role === 'teacher' && scope.row.approval_status !== 'approved'">
                <el-tag size="small" :type="getStatusTag(scope.row.approval_status)" class="text-[9px] h-4 leading-3 border-none px-1.5 font-bold">
                  {{ scope.row.approval_status.toUpperCase() }}
                </el-tag>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="ACTIONS" width="220" align="right">
          <template #default="scope">
            <div class="flex justify-end items-center gap-1" @click.stop>
              <template v-if="scope.row.approval_status === 'pending_approval'">
                <el-tooltip content="Approve Teacher" placement="top">
                  <button @click="handleApprove(scope.row)" class="p-2 text-emerald-500 hover:bg-emerald-50 rounded-xl transition-colors">
                    <CheckCircle size="18"/>
                  </button>
                </el-tooltip>
                <el-tooltip content="Reject Teacher" placement="top">
                  <button @click="handleReject(scope.row)" class="p-2 text-rose-500 hover:bg-rose-50 rounded-xl transition-colors">
                    <XCircle size="18"/>
                  </button>
                </el-tooltip>
                <div class="w-px h-4 bg-gray-200 mx-1"></div>
              </template>

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

      <div class="p-6 flex justify-center border-t border-gray-100 bg-white/30">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          :total="userList.length"
          background
          class="custom-pagination"
        />
      </div>
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

        <div v-if="isEdit && userForm.role === 'teacher'" class="mt-4 p-4 rounded-2xl border" 
             :class="userForm.approval_status === 'approved' ? 'bg-emerald-50 border-emerald-100' : 'bg-orange-50 border-orange-100'">
          <div class="flex justify-between items-center">
            <span class="text-xs font-bold text-gray-600 uppercase tracking-wider">Approval Status</span>
            <el-tag :type="getStatusTag(userForm.approval_status)">{{ userForm.approval_status }}</el-tag>
          </div>
          <p v-if="userForm.rejected_reason" class="mt-2 text-[11px] text-red-500 italic">
            Last Rejection Reason: {{ userForm.rejected_reason }}
          </p>
        </div>

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
import { ref, onMounted, reactive, computed } from 'vue';
import { UserPlus, Trash2, KeyRound, CheckCircle, XCircle } from 'lucide-vue-next';
import { ElMessage, ElMessageBox } from 'element-plus';
import api from '../../utils/request'; 

const activeRole = ref('all');
const activeStatus = ref(''); // 🚀 新增状态筛选
const search = ref('');
const userList = ref([]);
const loading = ref(false);
const submitting = ref(false);

const currentPage = ref(1);
const pageSize = ref(10);

const pagedUserList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return userList.value.slice(start, end);
});

const showDialog = ref(false);
const isEdit = ref(false);
const currentUserId = ref(null);

const userForm = reactive({
  username: '',
  student_id_num: '',
  first_name: '',
  email: '',
  class_name: '',
  role: 'student',
  approval_status: '',
  rejected_reason: ''
});

const openCreateDialog = () => {
  isEdit.value = false;
  currentUserId.value = null;
  Object.assign(userForm, {
    username: '', student_id_num: '', first_name: '', email: '', class_name: '', role: 'student',
    approval_status: 'approved', rejected_reason: ''
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
    role: row.role,
    approval_status: row.approval_status,
    rejected_reason: row.rejected_reason
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

// 🚀 新增：获取审批状态标签
const getStatusTag = (status) => {
  const map = {
    'approved': 'success',
    'pending_approval': 'warning',
    'pending_email': 'info',
    'rejected': 'danger'
  };
  return map[status] || 'info';
};

const fetchUsers = async () => {
  loading.value = true;
  try {
    const params = { 
      role: activeRole.value, 
      search: search.value,
      status: activeStatus.value // 🚀 传递状态过滤
    };
    const res = await api.get('/api/auth/admin/users/', { params });
    userList.value = res.results || res.data || res;
    currentPage.value = 1;
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

// 🚀 新增：批准审批逻辑
const handleApprove = async (user) => {
  try {
    await ElMessageBox.confirm(`Approve instructor account for ${user.username}? An activation email will be sent.`, 'Approval', { type: 'success' });
    await api.post(`/api/auth/admin/users/${user.id}/approve/`);
    ElMessage.success('Instructor approved successfully');
    fetchUsers();
  } catch (err) { if (err !== 'cancel') ElMessage.error('Action failed'); }
};

// 🚀 新增：驳回审批逻辑
const handleReject = async (user) => {
  try {
    const { value } = await ElMessageBox.prompt('Provide rejection reason:', 'Reject Request', {
      confirmButtonText: 'Reject',
      cancelButtonText: 'Cancel',
      inputPattern: /.+/,
      inputErrorMessage: 'Reason is required'
    });
    await api.post(`/api/auth/admin/users/${user.id}/reject/`, { reason: value });
    ElMessage.warning('Request rejected');
    fetchUsers();
  } catch (err) { if (err !== 'cancel') ElMessage.error('Action failed'); }
};

const handleToggleStatus = async (user, val) => {
  try {
    await api.patch(`/api/auth/admin/users/${user.id}/`, { is_active: val });
    ElMessage.success(`User ${user.username} is now ${val ? 'Active' : 'Disabled'}`);
  } catch (error) {
    user.is_active = !val; 
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
  activeStatus.value = ''; // 切换角色时清空状态过滤
  fetchUsers();
};

// 🚀 新增：处理状态快捷筛选
const handleStatusFilter = (status) => {
  activeStatus.value = activeStatus.value === status ? '' : status;
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

.custom-pagination :deep(.el-pager li) {
  background: transparent !important;
  border-radius: 8px;
  font-weight: 700;
  transition: all 0.3s;
}
.custom-pagination :deep(.el-pager li.is-active) {
  background-color: #2563eb !important;
  color: white !important;
}

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