<template>
  <div class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm animate-in fade-in duration-300">
    <div class="bg-white w-full max-w-4xl rounded-[40px] shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-300">
      
      <div class="p-8 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <div>
          <h2 class="text-2xl font-black text-gray-900">Resolve Grade Appeal</h2>
          <p class="text-sm text-gray-500 font-medium">Evaluating: {{ appeal.student_name }} - {{ appeal.assignment_title }}</p>
        </div>
        <button @click="$emit('close')" class="p-2 hover:bg-white rounded-full transition-colors">
          <X size="24" class="text-gray-400" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-8 custom-scrollbar">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          <div class="space-y-4">
            <h3 class="flex items-center gap-2 text-sm font-black text-gray-400 uppercase tracking-widest">
              <User size="16"/> Student Reason
            </h3>
            <div class="p-6 rounded-3xl bg-amber-50/50 border border-amber-100 italic text-gray-700 leading-relaxed shadow-inner">
              "{{ appeal.student_reason }}"
            </div>
          </div>

          <div class="space-y-4">
            <h3 class="flex items-center gap-2 text-sm font-black text-blue-500 uppercase tracking-widest">
              <Bot size="16"/> AI Auditor Opinion
            </h3>
            <div class="p-6 rounded-3xl bg-blue-50/50 border border-blue-100 text-blue-800 leading-relaxed shadow-inner relative">
              <div v-if="appeal.status === 'rejected_by_ai'" class="absolute -top-2 -right-2 px-3 py-1 bg-rose-500 text-white text-[10px] font-black rounded-lg shadow-md">
                AI REJECTED
              </div>
              {{ appeal.ai_judgment }}
            </div>
          </div>
          <div v-if="appeal.teacher_remark" class="space-y-4 mt-4 pt-4 border-t border-gray-100">
            <h3 class="flex items-center gap-2 text-sm font-black text-emerald-500 uppercase tracking-widest">
              <CheckCircle2 size="16"/> Teacher's Decision
            </h3>
            <div class="p-6 rounded-3xl bg-emerald-50/50 border border-emerald-100 text-emerald-800 leading-relaxed shadow-inner">
              <p class="text-sm">{{ appeal.teacher_remark }}</p>
              <p v-if="appeal.adjusted_score !== null && appeal.adjusted_score !== undefined" class="text-[10px] font-bold text-emerald-600 mt-2">
                Adjusted Score: {{ appeal.adjusted_score }}
              </p>
            </div>
          </div>
        </div>

        <div class="mt-12 space-y-8 pt-8 border-t border-gray-100">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div class="space-y-3">
              <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Adjust Final Score</label>
              <div class="relative">
                <el-input-number 
                  v-model="form.adjusted_score" 
                  :min="0" :max="100" 
                  class="w-full custom-number-input"
                  controls-position="right"
                />
                <div class="mt-2 text-[10px] font-bold text-gray-400">
                  Original: <span class="text-blue-600">{{ appeal.original_score }}</span>
                </div>
              </div>
            </div>

            <div class="md:col-span-2 space-y-3">
              <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Teacher's Decision (Remark)</label>
              <el-input 
                v-model="form.teacher_remark" 
                type="textarea" 
                :rows="3" 
                placeholder="Explain your final decision to the student..."
                class="custom-textarea"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="p-8 border-t border-gray-100 bg-gray-50/50 flex justify-end gap-4">
        <button @click="$emit('close')" class="px-8 py-3 text-sm font-bold text-gray-500 hover:text-gray-700 transition-colors">
          Dismiss
        </button>
        <button 
          @click="submitResolution" 
          :disabled="isSubmitting"
          class="flex items-center gap-2 px-10 py-3 bg-gray-900 text-white rounded-2xl font-black text-sm hover:bg-blue-600 transition-all shadow-xl active:scale-95 disabled:opacity-50"
        >
          <Loader2 v-if="isSubmitting" class="animate-spin" size="18"/>
          Confirm Resolution
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { X, User, Bot, Loader2 } from 'lucide-vue-next';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';

const props = defineProps({
  appeal: { type: Object, required: true }
});

const emit = defineEmits(['close', 'refresh']);

const isSubmitting = ref(false);
const form = reactive({
  adjusted_score: props.appeal.original_score,
  teacher_remark: ''
});

const submitResolution = async () => {
  if (!form.teacher_remark.trim()) {
    ElMessage.warning('Please provide a remark for the student.');
    return;
  }

  isSubmitting.value = true;
  try {
    // 🚀 对接 TeacherAssignmentViewSet 的 resolve-appeal 接口
    await api.post(`/api/auth/teacher/assignments/${props.appeal.id}/resolve-appeal/`, {
      adjusted_score: form.adjusted_score,
      teacher_remark: form.teacher_remark
    });
    
    ElMessage.success('Appeal resolved successfully!');
    emit('refresh');
    emit('close');
  } catch (e) {
    ElMessage.error(e.response?.data?.error || 'Failed to resolve appeal');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }
:deep(.el-input-number.is-controls-right .el-input-number__decrease),
:deep(.el-input-number.is-controls-right .el-input-number__increase) {
  border-radius: 0 12px 12px 0;
}
:deep(.el-input__wrapper) {
  border-radius: 16px;
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
}
</style>