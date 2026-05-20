<template>
  <div class="space-y-6 animate-fade-in pt-4 pb-10">
    <div class="flex justify-between items-end">
      <div>
        <h2 class="text-2xl font-black text-gray-800">Knowledge Point Library</h2>
        <p class="text-sm text-gray-500">Manage system-wide L1 and course-specific L2 knowledge points.</p>
      </div>
      <div class="flex gap-2">
        <button @click="handleExport" class="px-4 py-2.5 bg-white border border-gray-200 text-gray-600 text-sm font-bold rounded-xl hover:bg-gray-50 transition-all flex items-center gap-1.5">
          <Download size="16" /> Export CSV
        </button>
        <label class="px-4 py-2.5 bg-white border border-gray-200 text-gray-600 text-sm font-bold rounded-xl hover:bg-gray-50 transition-all flex items-center gap-1.5 cursor-pointer">
          <Upload size="16" /> Import CSV
          <input type="file" accept=".csv" class="hidden" @change="handleImport" />
        </label>
        <button @click="openCreateDialog" class="px-5 py-2.5 bg-blue-600 text-white text-sm font-bold rounded-xl shadow-md hover:bg-blue-700 transition-all flex items-center gap-1.5">
          <Plus size="16" /> Add KP
        </button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="flex gap-3 items-center">
      <div class="flex gap-1 bg-white/40 p-1 rounded-xl border border-white/60">
        <button v-for="t in ['all', 'L1', 'L2']" :key="t" @click="filterType = t; currentPage = 1; fetchKPList()"
          :class="['px-4 py-1.5 rounded-lg text-xs font-black uppercase transition-all', filterType === t ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-400 hover:text-gray-600']">
          {{ t === 'all' ? 'All' : t }}
        </button>
      </div>
      <div class="flex gap-1 bg-white/40 p-1 rounded-xl border border-white/60">
        <button v-for="l in ['all', 'python', 'java']" :key="l" @click="filterLang = l === 'all' ? '' : l; currentPage = 1; fetchKPList()"
          :class="['px-4 py-1.5 rounded-lg text-xs font-black capitalize transition-all', (l === 'all' && !filterLang) || filterLang === l ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-400 hover:text-gray-600']">
          {{ l === 'all' ? 'All' : l }}
        </button>
      </div>
      <span class="text-xs text-gray-400 font-bold ml-2">{{ kpList.length }} items</span>
    </div>

    <!-- 表格 -->
    <div class="frosted-card rounded-2xl border border-white/60 overflow-hidden shadow-sm">
      <el-table v-loading="loading" :data="pagedKPList" style="width: 100%" row-class-name="hover:bg-blue-50/30 transition-colors">
        <el-table-column label="NAME" min-width="180">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <div class="w-1.5 h-5 rounded-full" :class="row.is_system ? 'bg-blue-500' : 'bg-emerald-500'"></div>
              <span class="font-bold text-gray-800 text-sm">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="DESCRIPTION" min-width="250">
          <template #default="{ row }">
            <p class="text-xs text-gray-500 line-clamp-2">{{ row.description || '-' }}</p>
          </template>
        </el-table-column>
        <el-table-column label="BLOOM" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.bloom_level" class="px-2 py-0.5 bg-indigo-50 text-indigo-600 border border-indigo-100 rounded text-[10px] font-black uppercase">
              {{ row.bloom_level }}
            </span>
            <span v-else class="text-xs text-gray-300">-</span>
          </template>
        </el-table-column>
        <el-table-column label="TYPE" width="80" align="center">
          <template #default="{ row }">
            <span :class="['px-2 py-0.5 rounded text-[10px] font-black', row.is_system ? 'bg-blue-50 text-blue-600 border border-blue-100' : 'bg-emerald-50 text-emerald-600 border border-emerald-100']">
              {{ row.is_system ? 'L1' : 'L2' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="LANG" width="80" align="center">
          <template #default="{ row }">
            <span class="text-xs font-bold text-gray-500 uppercase">{{ row.language || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="REFS" width="70" align="center">
          <template #default="{ row }">
            <span class="text-sm font-black" :class="row.reference_count > 0 ? 'text-blue-600' : 'text-gray-300'">{{ row.reference_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="" width="100" align="right">
          <template #default="{ row }">
            <div class="flex gap-1 justify-end">
              <button @click="openEditDialog(row)" class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all"><Edit size="14" /></button>
              <button @click="handleDelete(row)" class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"><Trash2 size="14" /></button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div v-if="kpList.length > 10" class="p-4 flex justify-center border-t border-gray-100 bg-white/30">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          :total="kpList.length"
          background
          class="custom-pagination"
        />
      </div>
    </div>

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingKP ? 'Edit Knowledge Point' : 'Create Knowledge Point'" width="520px" destroy-on-close>
      <div class="space-y-4">
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Name *</label>
          <el-input v-model="kpForm.name" placeholder="e.g., Exception Handling" />
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Description</label>
          <el-input v-model="kpForm.description" type="textarea" :rows="3" placeholder="Assessment logic description..." />
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Type</label>
            <el-select v-model="kpForm.is_system" class="w-full">
              <el-option :value="true" label="L1 (System)" />
              <el-option :value="false" label="L2 (Course)" />
            </el-select>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Language</label>
            <el-select v-model="kpForm.language" class="w-full">
              <el-option value="python" label="Python" />
              <el-option value="java" label="Java" />
            </el-select>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Category</label>
            <el-select v-model="kpForm.category" class="w-full">
              <el-option value="L1" label="L1" />
              <el-option value="L2" label="L2" />
            </el-select>
          </div>
          <div class="space-y-1.5">
            <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Bloom Level</label>
            <el-select v-model="kpForm.bloom_level" class="w-full">
              <el-option value="remember" label="Remember" />
              <el-option value="understand" label="Understand" />
              <el-option value="apply" label="Apply" />
              <el-option value="analyze" label="Analyze" />
              <el-option value="evaluate" label="Evaluate" />
              <el-option value="create" label="Create" />
            </el-select>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" color="#2563eb" @click="handleSaveKP" :loading="saving">{{ editingKP ? 'Update' : 'Create' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import api from '../../utils/request';
import { Download, Upload, Plus, Edit, Trash2 } from 'lucide-vue-next';

const loading = ref(false);
const saving = ref(false);
const kpList = ref([]);
const filterType = ref('all');
const filterLang = ref('');
const dialogVisible = ref(false);
const editingKP = ref(null);
const currentPage = ref(1);
const pageSize = ref(10);

const kpForm = reactive({ name: '', description: '', is_system: false, language: 'python', category: 'L2', bloom_level: 'apply' });

const pagedKPList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return kpList.value.slice(start, start + pageSize.value);
});

const fetchKPList = async () => {
  loading.value = true;
  try {
    const res = await api.get('/api/auth/admin/knowledge-points/with-refs/', {
      params: { type: filterType.value, language: filterLang.value }
    });
    kpList.value = res.data || res;
  } catch (e) {
    ElMessage.error('Failed to load knowledge points');
  } finally {
    loading.value = false;
  }
};

const openCreateDialog = () => {
  editingKP.value = null;
  Object.assign(kpForm, { name: '', description: '', is_system: false, language: 'python', category: 'L2', bloom_level: 'apply' });
  dialogVisible.value = true;
};

const openEditDialog = (kp) => {
  editingKP.value = kp;
  Object.assign(kpForm, { name: kp.name, description: kp.description, is_system: kp.is_system, language: kp.language, category: kp.category, bloom_level: kp.bloom_level || 'apply' });
  dialogVisible.value = true;
};

const handleSaveKP = async () => {
  if (!kpForm.name.trim()) return ElMessage.warning('Name is required');
  saving.value = true;
  try {
    if (editingKP.value) {
      await api.patch(`/api/auth/knowledge-points/${editingKP.value.id}/`, kpForm);
      ElMessage.success('Updated');
    } else {
      await api.post('/api/auth/knowledge-points/', kpForm);
      ElMessage.success('Created');
    }
    dialogVisible.value = false;
    fetchKPList();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Save failed');
  } finally {
    saving.value = false;
  }
};

const handleDelete = async (kp) => {
  if (kp.reference_count > 0) {
    return ElMessage.warning(`Cannot delete: referenced by ${kp.reference_count} assignment(s)`);
  }
  try {
    await ElMessageBox.confirm(`Delete "${kp.name}"?`, 'Confirm', { type: 'warning' });
    await api.delete(`/api/auth/knowledge-points/${kp.id}/`);
    ElMessage.success('Deleted');
    fetchKPList();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Delete failed');
  }
};

const handleExport = () => {
  window.open('/api/auth/admin/knowledge-points/export/', '_blank');
};

const handleImport = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await api.post('/api/auth/admin/knowledge-points/import/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    ElMessage.success(`Imported: ${res.created || 0} created, ${res.skipped || 0} skipped`);
    fetchKPList();
  } catch (err) {
    ElMessage.error('Import failed');
  }
  e.target.value = '';
};

onMounted(fetchKPList);
</script>

<style scoped>
.frosted-card { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); }

.custom-pagination :deep(.el-pager li) {
  background: transparent !important;
  border-radius: 8px;
  font-weight: 700;
  transition: all 0.3s;
}
.custom-pagination :deep(.el-pager .is-active) {
  background-color: #2563eb !important;
  color: white !important;
}
</style>