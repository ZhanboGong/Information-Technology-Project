<template>
  <div class="space-y-6 animate-fade-in max-w-6xl mx-auto pt-2">
    <div class="flex items-center gap-4 mb-8">
      <button 
        @click="router.push('/student-assignments')" 
        class="p-2.5 frosted-card rounded-xl text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-all border border-white/60 shadow-sm"
      >
        <ArrowLeft size="20" />
      </button>
      <div>
        <h2 class="text-2xl font-bold text-gray-800 tracking-tight">
          Course Assignments: {{ courseName }}
        </h2>
        <p class="text-sm text-gray-500 mt-1">Please submit before the deadline. The system will grade based on your latest submission.</p>
      </div>
    </div>

    <div v-if="loading" class="flex flex-col justify-center items-center py-20">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4"></div>
      <p class="text-gray-400 text-sm">Fetching assignment list...</p>
    </div>

    <div v-else-if="assignments.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div 
        v-for="assign in assignments" 
        :key="assign.id" 
        class="frosted-card p-6 rounded-2xl border border-white/60 flex flex-col group hover:shadow-xl hover:-translate-y-1 transition-all relative overflow-hidden"
      >
        <div class="absolute -right-4 -top-4 w-20 h-20 bg-blue-500/5 rounded-full blur-2xl"></div>

        <div class="flex justify-between items-start mb-4 relative">
          <h3 
            @click="handleShowDetail(assign)"
            class="text-lg font-bold text-gray-800 group-hover:text-blue-600 transition-colors cursor-pointer flex items-center gap-2 active:scale-95"
          >
            {{ assign.title }}
            <div class="p-1 rounded-full bg-blue-50 text-blue-400 opacity-0 group-hover:opacity-100 transition-all">
              <Maximize2 size="12" />
            </div>
          </h3>
          
          <div class="flex flex-col items-end gap-2">
            <span 
              :class="!assign.is_submitted ? 'bg-amber-50 text-amber-600 border-amber-200' : 'bg-emerald-50 text-emerald-600 border-emerald-200'" 
              class="px-2.5 py-1 rounded-md text-xs font-bold border whitespace-nowrap shadow-sm"
            >
              {{ !assign.is_submitted ? 'Pending' : 'Submitted' }}
            </span>
            <div v-if="assign.attachment" class="flex items-center gap-1 text-[10px] text-blue-500 font-bold bg-blue-50/50 px-1.5 py-0.5 rounded border border-blue-100">
              <Paperclip size="10" /> Attachment
            </div>
          </div>
        </div>

        <div class="space-y-3 mb-8 text-sm text-gray-600">
          <div class="flex items-center gap-2">
            <Clock size="16" class="text-blue-400"/> 
            <span>Deadline: <span class="font-medium text-gray-700">{{ formatTime(assign.deadline) }}</span></span>
          </div>
          <div class="flex items-center gap-2">
            <History size="16" class="text-purple-400"/> 
            <span>Attempts Allowed: <span class="font-bold text-gray-800">{{ assign.max_attempts }} times</span></span>
          </div>
        </div>

        <button 
          @click="router.push(`/student/assignments/submit/${assign.id}`)"
          class="mt-auto w-full py-3 bg-slate-900 hover:bg-black text-white rounded-xl font-bold text-sm shadow-lg shadow-slate-200 transition-all flex items-center justify-center gap-2 group"
        >
          {{ !assign.is_submitted ? 'Start Submission' : 'Submit Again' }}
          <ArrowRight size="16" class="group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>

    <div v-else class="text-center py-20 bg-gray-50/50 rounded-3xl border-2 border-dashed border-gray-200">
      <div class="flex justify-center mb-4 text-gray-300">
        <BookOpen size="48" />
      </div>
      <p class="text-gray-400 font-medium">No assignments published for this course yet.</p>
    </div>

    <el-dialog
      v-model="detailVisible"
      width="1000px"
      align-center
      destroy-on-close
      :show-close="false"
      class="custom-detail-dialog"
    >
      <template #header>
        <div class="flex justify-between items-center w-full pr-4">
          <div class="flex items-center gap-3">
            <div class="p-2.5 bg-blue-600 rounded-xl text-white shadow-lg shadow-blue-100">
              <FileText size="20" />
            </div>
            <h3 class="text-xl font-bold text-gray-800">Assignment Rubric Details</h3>
          </div>
          <button @click="detailVisible = false" class="text-gray-400 hover:text-gray-600 transition-colors">
            <X size="20" />
          </button>
        </div>
      </template>

      <div v-if="selectedAssignment" class="space-y-8 py-2 max-h-[75vh] overflow-y-auto custom-scrollbar pr-2">
        <div class="bg-gradient-to-r from-blue-50 to-transparent p-5 rounded-2xl border border-blue-100/50 shadow-sm flex justify-between items-center">
          <div>
            <p class="text-[10px] font-black text-blue-500 uppercase tracking-[0.2em] mb-1">Overview</p>
            <h4 class="text-2xl font-extrabold text-gray-900 mb-2">{{ selectedAssignment.title }}</h4>
            <div class="flex gap-4 text-sm font-medium text-gray-500">
              <span class="flex items-center gap-1.5"><BookOpen size="14" class="text-blue-500" />{{ courseName }}</span>
              <span class="border-l pl-4 flex items-center gap-1.5"><Calendar size="14" class="text-blue-500" />Due: {{ formatTime(selectedAssignment.deadline) }}</span>
            </div>
          </div>
          
          <div v-if="selectedAssignment.attachment">
            <button 
              @click="handleDownload(selectedAssignment.attachment, selectedAssignment.attachment_name)"
              class="flex items-center gap-2 px-5 py-2.5 bg-white border border-blue-200 text-blue-600 rounded-xl text-sm font-bold shadow-sm hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-all active:scale-95 group"
            >
              <Download size="18" class="group-hover:animate-bounce" />
              Download Reference
            </button>
          </div>
        </div>

        <section>
          <div class="flex items-center gap-2 mb-4 px-1">
            <ClipboardCheck size="18" class="text-emerald-500" />
            <p class="text-[15px] font-black text-gray-800 uppercase tracking-widest">Performance Standards Matrix</p>
          </div>
          
          <el-table 
            :data="matrixData" 
            border 
            stripe 
            class="rubric-matrix-table shadow-sm"
            header-cell-class-name="matrix-header"
          >
            <el-table-column label="Grade Level" width="180" fixed="left">
              <template #default="scope">
                <el-tag :type="getGradeTag(scope.row.grade)" effect="dark" class="font-bold w-full text-center">
                  {{ scope.row.grade }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column 
              v-for="col in matrixColumns" 
              :key="col.prop" 
              :min-width="300"
            >
              <template #header>
                <div class="flex flex-col py-1">
                  <span class="text-gray-800 font-bold leading-tight">{{ col.label }}</span>
                  <span class="text-[10px] text-blue-500 font-black mt-1">WEIGHT: {{ col.weight }}%</span>
                </div>
              </template>
              <template #default="scope">
                <div class="p-1">
                  <p class="text-xs leading-relaxed text-gray-600 whitespace-pre-wrap">
                    {{ scope.row[col.prop] || 'Criteria not specified for this level.' }}
                  </p>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section>
          <div class="flex items-center gap-2 mb-3 px-1">
            <p class="text-[15px] font-black text-gray-800 uppercase tracking-widest">Additional Requirements</p>
          </div>
          <div class="bg-slate-50 rounded-2xl p-5 border border-slate-100 text-sm text-slate-600 leading-relaxed whitespace-pre-wrap italic">
            {{ selectedAssignment.content }}
          </div>
        </section>
      </div>

      <template #footer>
        <div class="flex gap-4 mt-2">
          <button 
            @click="detailVisible = false"
            class="flex-1 py-3.5 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-2xl font-bold transition-all text-sm"
          >
            Cancel
          </button>
          <button 
            @click="router.push(`/student/assignments/submit/${selectedAssignment.id}`)"
            class="flex-[2] py-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold shadow-lg shadow-blue-100 transition-all text-sm flex items-center justify-center gap-2"
          >
            Go to Submission
            <ChevronRight size="18" />
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';
import { 
  ArrowLeft, Clock, History, BookOpen, ArrowRight, Maximize2, X, 
  FileText, Calendar, Zap, ChevronRight, ClipboardCheck, Download, Paperclip 
} from 'lucide-vue-next';

const router = useRouter();
const route = useRoute();
const loading = ref(true);
const assignments = ref([]);
const courseName = ref('Loading...');
const detailVisible = ref(false);
const selectedAssignment = ref(null);

const handleShowDetail = (assign) => {
  selectedAssignment.value = assign;
  detailVisible.value = true;
};

/**
 * 🚀 整合新增：下载附件处理函数
 */
const handleDownload = (fileUrl, fileName) => {
  if (!fileUrl) return;
  try {
    const link = document.createElement('a');
    link.href = fileUrl;
    // 设置下载文件名，若后端没给 attachment_name 则用默认
    link.setAttribute('download', fileName || 'Assignment_Resource');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    ElMessage.success('Download started');
  } catch (err) {
    ElMessage.error('Download failed');
  }
};

/**
 * 矩阵行数据处理逻辑
 */
const matrixData = computed(() => {
  const config = selectedAssignment.value?.rubric_config;
  if (!config || !config.items) return [];

  const standardGrades = [
    "High Distinction (85-100%)",
    "Distinction (75-84%)",
    "Credit (65-74%)",
    "Pass (50-64%)",
    "Fail (0-49%)"
  ];

  return standardGrades.map(gradeLabel => {
    const row = { grade: gradeLabel };
    config.items.forEach((item, index) => {
      let desc = "N/A";
      if (item.detailed_rubric) {
        const shortName = gradeLabel.split(' (')[0];
        const foundKey = Object.keys(item.detailed_rubric).find(key => 
          key.includes(shortName) || (shortName === 'High Distinction' && key.includes('HD'))
        );
        if (foundKey) desc = item.detailed_rubric[foundKey];
      }
      row[`criterion_${index}`] = desc;
    });
    return row;
  });
});

const matrixColumns = computed(() => {
  const config = selectedAssignment.value?.rubric_config;
  if (!config || !config.items) return [];
  return config.items.map((item, index) => ({
    prop: `criterion_${index}`,
    label: item.criterion,
    weight: item.weight
  }));
});

const getGradeTag = (grade) => {
  if (grade.includes('High')) return 'success';
  if (grade.includes('Credit')) return 'warning';
  if (grade.includes('Fail')) return 'danger';
  if (grade.includes('Pass')) return 'info';
  return '';
};

const formatTime = (timeStr) => {
  if (!timeStr) return 'Not Set';
  const date = new Date(timeStr);
  return date.toLocaleString('en-US', { 
    year: 'numeric', month: '2-digit', day: '2-digit', 
    hour: '2-digit', minute: '2-digit' 
  });
};

const fetchAssignments = async () => {
  try {
    loading.value = true;
    const courseId = route.params.courseId;
    const courseRes = await api.get(`/api/auth/student/courses/${courseId}/`);
    courseName.value = courseRes.data?.name || courseRes.name || 'Course Details';

    const [assignRes, subRes] = await Promise.all([
      api.get('/api/auth/student/assignments/'),
      api.get('/api/auth/student/submissions/')
    ]);

    const allData = assignRes.data || assignRes;
    const allSubs = subRes.data || subRes;

    if (Array.isArray(allData)) {
      assignments.value = allData
        .filter(item => String(typeof item.course === 'object' ? item.course.id : item.course) === String(courseId))
        .map(assign => ({ 
          ...assign, 
          is_submitted: Array.isArray(allSubs) && allSubs.some(s => String(s.assignment) === String(assign.id)) 
        }));
    }
  } catch (error) {
    console.error('Failed to fetch:', error);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchAssignments);
</script>

<style scoped>
:deep(.custom-detail-dialog) {
  border-radius: 32px !important;
  padding: 8px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.2) !important;
}

:deep(.el-dialog__header) { padding: 32px 32px 16px; }
:deep(.el-dialog__body) { padding: 8px 32px; }
:deep(.el-dialog__footer) { padding: 16px 32px 32px; border-top: 1px solid #f3f4f6; }

:deep(.rubric-matrix-table) {
  --el-table-border-color: #e5e7eb;
  border-radius: 16px;
  overflow: hidden;
}

:deep(.matrix-header) {
  background-color: #f8fafc !important;
  vertical-align: top;
  padding: 16px 0 !important;
}

:deep(.el-table .cell) {
  word-break: normal;
}

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }

.frosted-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
</style>