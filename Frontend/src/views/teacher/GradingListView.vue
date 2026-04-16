<template>
  <div class="space-y-6 animate-fade-in max-w-[1400px] mx-auto pt-2 pb-20">
    
    <template v-if="!selectedCourse">
      <div class="flex justify-between items-end mb-6">
        <div>
          <h2 class="text-2xl font-bold flex items-center gap-2 text-gray-800"><PenTool class="text-blue-600"/> Submit & Grade Workspace</h2>
          <p class="text-sm text-gray-500 mt-1">请选择您要阅卷的课程，查看各个作业的实时提交进度。</p>
        </div>
      </div>
      <div v-if="isLoading" class="text-center py-10"><Loader2 class="animate-spin mx-auto text-blue-500" size="32"/></div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="course in courses" :key="course.id" class="frosted-card p-6 cursor-pointer border border-white/60 hover:shadow-xl rounded-2xl group transition-all hover:-translate-y-1" @click="openCourse(course)">
          <h3 class="text-xl font-bold text-gray-800 group-hover:text-blue-700 transition-colors mb-2">{{ course.name }}</h3>
          <p class="text-sm text-gray-500 mb-6 line-clamp-2">{{ course.description || 'No description available' }}</p>
          <div class="w-full py-2.5 bg-blue-50/50 text-blue-700 font-bold rounded-xl flex justify-center items-center gap-2 group-hover:bg-blue-100 transition-colors border border-blue-100">
            <CheckSquare size="16"/> View Assignments
          </div>
        </div>
      </div>
    </template>

    <template v-else-if="selectedCourse && !selectedAssignment">
      <div class="flex items-center gap-4 mb-6">
        <button @click="selectedCourse = null" class="p-2.5 frosted-card rounded-xl text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-all shadow-sm"><ArrowLeft size="20"/></button>
        <div>
          <div class="text-xs font-bold text-gray-400 mb-1">COURSE ID: {{ selectedCourse.id }}</div>
          <h2 class="text-2xl font-bold text-gray-800">{{ selectedCourse.name }} - Assignment List</h2>
        </div>
      </div>
      <div class="space-y-4">
        <div v-if="isAssignmentsLoading" class="text-center py-10"><Loader2 class="animate-spin mx-auto text-blue-500" size="32"/></div>
        <div v-else v-for="assign in courseAssignments" :key="assign.id" class="frosted-card p-6 rounded-2xl flex justify-between items-center group border border-white/60 hover:shadow-lg bg-white/60 transition-all">
          <div>
            <h3 class="text-lg font-bold text-gray-800 group-hover:text-blue-600 transition-colors mb-2">{{ assign.title }}</h3>
            <span class="text-sm text-gray-500 flex items-center gap-1.5"><Clock size="14"/> Deadline: {{ formatDate(assign.deadline) }}</span>
          </div>
          <button @click="openWorkspace(assign)" class="px-6 py-3 bg-blue-600 text-white font-bold rounded-xl flex items-center gap-2 hover:bg-blue-700 shadow-blue-500/30 shadow-md transition-all">
            <PenTool size="18"/> Enter Grading Workspace
          </button>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-4">
          <button @click="selectedAssignment = null" class="p-2.5 frosted-card rounded-xl text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-all shadow-sm"><ArrowLeft size="20"/></button>
          <div>
            <div class="text-xs font-bold text-gray-400 mb-1">{{ selectedCourse.name }}</div>
            <h2 class="text-xl font-bold text-gray-800 tracking-tight">Grading: {{ selectedAssignment.title }}</h2>
          </div>
        </div>
        <button @click="downloadAllSubmissions" :disabled="isDownloadingAll" class="px-4 py-2 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-xl font-bold text-sm flex items-center gap-2 hover:bg-emerald-100 transition-all disabled:opacity-50">
          <Loader2 v-if="isDownloadingAll" class="animate-spin" size="18"/>
          <Download v-else size="18"/> 
          Package All Best (ZIP)
        </button>
      </div>

      <div class="flex gap-6 h-[calc(100vh-220px)] w-full">
        <div class="w-72 shrink-0 frosted-card rounded-2xl flex flex-col p-3 overflow-y-auto relative border border-white/60">
          <div v-if="isWorkspaceLoading" class="absolute inset-0 bg-white/50 backdrop-blur-sm flex items-center justify-center z-10 rounded-2xl">
            <Loader2 class="animate-spin text-blue-600" size="28"/>
          </div>
          <div v-for="s in wsStudents" :key="s.id" @click="selectStudent(s)" 
               :class="['p-4 rounded-xl cursor-pointer border mb-2 transition-all relative group', currentStudent?.id === s.id ? 'border-blue-300 bg-blue-50 shadow-sm translate-x-1' : 'bg-white hover:bg-gray-50 border-transparent']">
             <div class="flex justify-between items-start">
               <div class="font-bold text-gray-800">{{ s.student_name }}</div>
               <span v-if="s.best_submission" class="text-[9px] px-1.5 py-0.5 rounded font-black uppercase bg-blue-100 text-blue-600">
                 {{ s.best_submission.sub_type }}
               </span>
             </div>
             <div class="text-xs font-mono text-gray-400 mt-1">{{ s.student_id_num }}</div>
             <div class="flex items-center justify-between mt-3">
               <div class="text-[10px] font-bold" :class="s.final_score !== null ? 'text-emerald-600' : 'text-gray-400'">
                 {{ s.final_score !== null ? `Score: ${s.final_score}` : 'Not Graded' }}
               </div>
               <div v-if="s.best_submission" class="text-[9px] text-amber-600 font-bold">Best: #{{ s.best_submission.attempt_number }}</div>
             </div>
          </div>
        </div>

        <div class="flex-1 flex flex-col gap-4 min-w-0">
          <div class="flex-1 frosted-card rounded-2xl p-6 relative bg-gray-50/50 overflow-y-auto border border-white/60">
              <div class="flex justify-between items-center mb-4">
                <h3 class="font-bold text-lg text-purple-700 flex items-center gap-2"><Sparkles size="20"/> AI Diagnosis (Best Attempt)</h3>
                <button v-if="currentStudent?.best_submission" @click="downloadSingle()" class="text-xs font-bold text-blue-600 flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-lg shadow-sm hover:bg-blue-50 transition-all border border-blue-100">
                  <FileDown size="14"/> Download Source
                </button>
              </div>
              <div v-if="currentStudent?.best_submission?.ai_evaluation?.feedback" 
                   class="p-5 bg-white rounded-2xl shadow-sm leading-relaxed text-sm border border-purple-100 text-gray-700 markdown-body"
                   v-html="renderMarkdown(currentStudent.best_submission.ai_evaluation.feedback)">
              </div>
              <div v-else class="text-gray-400 text-sm p-10 text-center border-2 border-dashed border-gray-200 rounded-2xl bg-white/50 h-full flex flex-col justify-center items-center">
                  <Bot size="48" class="mb-3 opacity-20"/>
                  <p>{{ !currentStudent?.best_submission ? '该学生尚未提交作业' : 'AI 诊断报告生成中...' }}</p>
              </div>
          </div>
        </div>

        <div class="w-96 shrink-0 flex flex-col gap-5 overflow-y-auto pr-1">
          <div class="frosted-card p-6 rounded-2xl border border-white/60 shadow-sm space-y-6">
            <div class="flex justify-between items-center">
              <h3 class="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                <ClipboardCheck size="16" class="text-blue-500"/> Rubric Scoring (Snapshot)
              </h3>
              <div class="text-2xl font-black text-blue-600">{{ calculatedTotalScore }} <span class="text-xs text-gray-400 font-normal">/ 100</span></div>
            </div>

            <div class="space-y-5">
              <div v-for="item in gradingRubric" :key="item.criterion" class="p-4 bg-gray-50/50 rounded-2xl border border-gray-100 group hover:border-blue-200 transition-colors">
                <div class="flex justify-between items-center mb-2">
                  <span class="text-xs font-bold text-gray-700">{{ item.criterion }}</span>
                  <span class="text-[10px] font-black bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">{{ item.weight }}%</span>
                </div>
                <div class="flex items-center gap-4">
                  <el-slider v-model="rubricScores[item.criterion]" :min="0" :max="100" class="flex-1" />
                  <input type="number" v-model.number="rubricScores[item.criterion]" 
                         class="w-12 text-center text-xs font-bold bg-white border border-gray-200 rounded-lg py-1.5 focus:border-blue-400 outline-none">
                </div>
              </div>
            </div>
          </div>
          
          <div class="flex-1 frosted-card rounded-2xl p-5 flex flex-col border border-white/60 shadow-sm min-h-[180px]">
            <span class="text-xs font-black text-gray-400 uppercase mb-3 flex items-center gap-2"><MessageSquare size="14"/> Teacher's Remarks</span>
            <textarea v-model="teacherRemarks" class="flex-1 w-full p-4 text-sm bg-white border border-gray-100 rounded-xl outline-none resize-none focus:ring-2 focus:ring-blue-500/10 transition-all" placeholder="输入您的点评意见..."></textarea>
          </div>
          
          <button @click="publishGrade" :disabled="isPublishing || !currentStudent?.best_submission" 
                  class="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold rounded-2xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 flex justify-center items-center gap-2">
            <Loader2 v-if="isPublishing" class="animate-spin" size="20"/> 
            <CheckCircle2 v-else size="20"/> 
            {{ isPublishing ? 'Publishing...' : 'Sync & Save Score' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import api from '../../utils/request';
import MarkdownIt from 'markdown-it';
import { 
  PenTool, CheckSquare, ArrowLeft, Loader2, Clock, Sparkles, 
  Bot, CheckCircle2, Download, FileDown, ClipboardCheck, MessageSquare 
} from 'lucide-vue-next';

// Markdown configuration
const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
const renderMarkdown = (content) => content ? md.render(content) : '';

const isLoading = ref(false);
const courses = ref([]);
const selectedCourse = ref(null);
const selectedAssignment = ref(null);
const isAssignmentsLoading = ref(false);
const courseAssignments = ref([]);
const isWorkspaceLoading = ref(false);
const wsStudents = ref([]);
const currentStudent = ref(null);
const teacherRemarks = ref('');
const isPublishing = ref(false);
const isDownloadingAll = ref(false);

const gradingRubric = ref([]); 
const rubricScores = ref({});  

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
};

// Automatically calculate the total score (based on weights)
const calculatedTotalScore = computed(() => {
  if (!gradingRubric.value.length) return 0;
  let total = 0;
  gradingRubric.value.forEach(item => {
    const s = rubricScores.value[item.criterion] || 0;
    total += (s * (item.weight / 100));
  });
  return Math.round(total);
});

onMounted(async () => {
  isLoading.value = true;
  try {
    const res = await api.get('/api/auth/teacher/courses/');
    courses.value = res.results || res;
  } catch (e) { ElMessage.error('Course list loading failed'); }
  finally { isLoading.value = false; }
});

const openCourse = async (course) => {
  selectedCourse.value = course;
  selectedAssignment.value = null;
  isAssignmentsLoading.value = true;
  try {
    const res = await api.get('/api/auth/teacher/assignments/');
    const all = res.results || res;
    courseAssignments.value = all.filter(a => (typeof a.course === 'object' ? a.course.id : a.course) === course.id);
  } catch(e) { ElMessage.error('The list of assignments failed to load.'); }
  finally { isAssignmentsLoading.value = false; }
};

const openWorkspace = async (assign) => {
  selectedAssignment.value = assign;
  isWorkspaceLoading.value = true;
  try {
    const studentRes = await api.get(`/api/auth/teacher/courses/${selectedCourse.value.id}/students/`);
    const students = studentRes.results || studentRes || [];
    const submissions = await api.get(`/api/auth/teacher/assignments/${assign.id}/submissions/`);

    wsStudents.value = students.map(stu => {
      const studentSubs = (submissions || []).filter(sub => sub.student === stu.id);
      const sortedSubs = [...studentSubs].sort((a, b) => {
        const sA = a.final_score ?? a.ai_evaluation?.total_score ?? 0;
        const sB = b.final_score ?? b.ai_evaluation?.total_score ?? 0;
        return sB !== sA ? sB - sA : b.id - a.id;
      });
      const bestSub = sortedSubs[0] || null;
      return {
        id: stu.id,
        student_name: stu.name || stu.username,
        student_id_num: stu.student_id_num,
        best_submission: bestSub,
        final_score: bestSub ? bestSub.final_score : null,
      };
    });

    if(wsStudents.value.length > 0) selectStudent(wsStudents.value[0]);
  } catch (e) { ElMessage.error('The marking station initialization failed.'); }
  finally { isWorkspaceLoading.value = false; }
};

const selectStudent = (s) => { 
  currentStudent.value = s; 
  const bestEval = s.best_submission?.ai_evaluation;
  
  // 1. Synchronous Rubric Dimensions
  const rubricSource = bestEval?.rubric_snap || selectedAssignment.value?.rubric_config;
  if (rubricSource?.items) {
    gradingRubric.value = JSON.parse(JSON.stringify(rubricSource.items));
  }

  // 2. Deeply extract dimensionality features (parsed from ai_raw_feedback)
  let existingKpScores = bestEval?.kp_scores || {};
  
  if (bestEval?.ai_raw_feedback && typeof bestEval.ai_raw_feedback === 'string') {
    try {
      const rawJson = JSON.parse(bestEval.ai_raw_feedback);
      existingKpScores = rawJson.scores || rawJson.kp_scores || existingKpScores;
    } catch (e) { console.warn("Failed to parse raw feedback JSON"); }
  }
  
  // 3. Force the reconfiguration of the rubricScores object to trigger the UI refresh
  const freshScores = {};
  gradingRubric.value.forEach(item => {
    // Logic: If there are detailed dimension scores in the highest score record, then use them; otherwise, the total score of this occasion will be the default value.
    freshScores[item.criterion] = existingKpScores[item.criterion] ?? (bestEval?.total_score || 0);
  });
  rubricScores.value = freshScores;

  teacherRemarks.value = bestEval?.feedback || '';
};

const downloadSingle = async () => {
  const sub = currentStudent.value?.best_submission;
  const student = currentStudent.value;
  if (!sub || !student) return;
  try {
    const response = await api.get('/api/auth/teacher/assignments/download-submission/', {
      params: { submission_id: sub.id },
      responseType: 'blob' 
    });
    const url = window.URL.createObjectURL(new Blob([response.data || response]));
    const link = document.createElement('a');
    link.href = url;
    // Naming format: Student ID_Name_Atmt_attempt_count.zip
    const fileName = `${student.student_id_num}_${student.student_name}_Atmt${sub.attempt_number}.zip`;
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (e) { ElMessage.error('File retrieval failed'); }
};

const downloadAllSubmissions = async () => {
  if (!selectedAssignment.value) return;
  isDownloadingAll.value = true;
  try {
    const response = await api.get(`/api/auth/teacher/assignments/${selectedAssignment.value.id}/download-all/`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data || response]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${selectedAssignment.value.title}_Highest_Records.zip`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (e) { ElMessage.error('Packaging and downloading failed'); }
  finally { isDownloadingAll.value = false; }
};

const publishGrade = async () => {
  if(!currentStudent.value?.best_submission) return;
  isPublishing.value = true;
  try {
    await api.post('/api/auth/teacher/assignments/update-score/', {
      submission_id: currentStudent.value.best_submission.id, 
      score: calculatedTotalScore.value,
      feedback: teacherRemarks.value,
      kp_scores: rubricScores.value
    });
    ElMessage.success('Detailed ratings have been saved and published.');
    currentStudent.value.final_score = calculatedTotalScore.value;
  } catch (e) { ElMessage.error('Rating release failed'); }
  finally { isPublishing.value = false; }
};
</script>

<style scoped>
.frosted-card { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(14px); }
.animate-fade-in { animation: fadeIn 0.4s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

:deep(.markdown-body) h1 { @apply text-xl font-bold mb-4 border-b pb-2; }
:deep(.markdown-body) h2 { @apply text-lg font-bold mt-4 mb-2; }
:deep(.markdown-body) p { @apply mb-3 leading-6; }
:deep(.markdown-body) ul { @apply list-disc pl-5 mb-3; }
:deep(.markdown-body) code { @apply bg-gray-100 px-1 py-0.5 rounded text-red-500 font-mono text-xs; }
:deep(.markdown-body) pre { @apply bg-gray-900 text-gray-100 p-4 rounded-xl overflow-x-auto mb-3 text-xs; }
:deep(.markdown-body) blockquote { @apply border-l-4 border-purple-300 pl-4 italic my-4 text-gray-600; }
</style>