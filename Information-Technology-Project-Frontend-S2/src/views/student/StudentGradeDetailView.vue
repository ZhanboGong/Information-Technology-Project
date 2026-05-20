<template>
  <div ref="reportContent" class="max-w-7xl mx-auto p-6 space-y-8 animate-fade-in min-h-screen bg-gray-50/30 pb-12">
    
    <div class="flex items-center justify-between print:hidden">
      <button 
        @click="goBack" 
        class="group flex items-center gap-2 px-4 py-2 text-sm font-bold text-gray-500 hover:text-blue-600 transition-all bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md hover:border-blue-200"
      >
        <ArrowLeft size="18" class="group-hover:-translate-x-1 transition-transform"/>
        Back to My gradebook
      </button>

      <div class="flex items-center gap-3">
        <button 
  v-if="evaluation && evaluation.is_published"
  :disabled="submission?.status === 'appealing' || hasAppeal || isAppealing"
  @click="openAppealDialog"
  class="flex items-center gap-2 px-5 py-2.5 text-sm font-black transition-all rounded-xl shadow-lg"
  :class="(submission?.status === 'appealing' || hasAppeal || isAppealing) 
    ? 'text-gray-400 bg-gray-100 border-2 border-gray-200 cursor-not-allowed' 
    : 'text-blue-600 bg-white border-2 border-blue-600 hover:bg-blue-50'"
>
  <MessageSquare size="18"/>
  <span v-if="isAppealing">Sending...</span>
  <span v-else-if="submission?.status === 'appealing'">Under Review</span>
  <span v-else-if="hasAppeal">Appealed</span>
  <span v-else>Grade Appeal</span>
</button>

        <button 
          v-if="evaluation && evaluation.is_published && assignment"
          @click="downloadPDF" 
          :disabled="isDownloading"
          class="flex items-center gap-2 px-6 py-2.5 text-sm font-black text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all rounded-xl shadow-lg hover:shadow-blue-200 active:scale-95"
        >
          <Download v-if="!isDownloading" size="18"/>
          <span v-else class="animate-spin border-2 border-white border-t-transparent rounded-full w-4 h-4 mr-1"></span>
          {{ isDownloading ? 'Preparing PDF...' : 'Download AI Report' }}
        </button>
      </div>
    </div>

    <div class="frosted-card p-10 rounded-[32px] border border-blue-200/60 shadow-xl bg-gradient-to-br from-white via-blue-50/30 to-indigo-50/20 relative overflow-hidden flex items-center">
      <div class="absolute right-0 top-0 w-64 h-64 bg-blue-400/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
      
      <div class="flex flex-col md:flex-row justify-between items-center gap-8 relative z-10 w-full">
        <div class="space-y-4 text-center md:text-left">
          <div class="inline-flex items-center gap-2 px-3 py-1 bg-blue-600/10 border border-blue-600/20 rounded-full text-[10px] font-black tracking-[0.2em] uppercase text-blue-700">
            <Sparkles size="12"/> AI Diagnostic Report
          </div>
          <h1 class="text-4xl font-black tracking-tight leading-tight text-gray-900">
            {{ assignment?.title || 'Assignment Analysis' }}
          </h1>
          
          <div class="flex wrap items-center justify-center md:justify-start gap-4 text-gray-500 font-bold">
            <p class="flex items-center gap-1.5 bg-white/60 px-3 py-1 rounded-lg border border-white shadow-sm">
              <span class="text-blue-600 text-[10px] uppercase tracking-wider font-black">Student ID</span>
              <span class="text-gray-700 font-mono">{{ authStore.user?.username || 'N/A' }}</span>
            </p>
            <p class="flex items-center gap-1.5 bg-white/60 px-3 py-1 rounded-lg border border-white shadow-sm">
              <Calendar size="15" class="text-blue-500"/> 
              <span class="text-gray-400 text-[10px] uppercase tracking-wider font-black">Date</span>
              <span class="text-gray-700">{{ submission?.created_at ? formatDate(submission.created_at) : '-' }}</span>
            </p>
          </div>
        </div>
        
        <div class="flex items-center gap-10 bg-white/80 p-8 rounded-[28px] shadow-sm border border-white">
          <div class="text-center">
            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Total Score</p>
            <div class="text-6xl font-black tracking-tighter text-blue-600">
              {{ evaluation?.total_score || '0' }}
            </div>
          </div>
          <div class="w-px h-14 bg-gray-100 hidden md:block"></div>
          <div class="text-center">
            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Academic Grade</p>
            <div class="text-4xl font-black text-gray-800">
              {{ getGradeLevel(evaluation?.total_score) }}
            </div>
          </div>
        </div>
      </div>
    </div>

<div v-if="hasAppeal && appealData" class="p-6 rounded-[24px] border-2 border-dashed transition-all animate-in slide-in-from-top-4" :class="appealStatusClass">
  <div class="flex items-start gap-5">
    <div class="space-y-2">
      <div class="flex items-center gap-2">
        <h4 class="font-black text-gray-900 uppercase tracking-tighter text-sm">Review Status</h4>
        <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase" :class="appealIconClass + ' bg-white/50'">
          {{ appealData?.status_display || appealData?.status }}
        </span>
      </div>
      
      <p class="text-gray-700 text-[14px] leading-relaxed font-medium italic">
        "{{ appealData?.ai_judgment || 'Waiting for system audit...' }}"
      </p>

      <p v-if="appealData?.status === 'rejected_by_ai'" class="text-[11px] font-bold text-rose-400">
        Note: The AI auditor did not find sufficient evidence in your code to support this appeal.
      </p>
            
      <div v-if="appealData?.teacher_remark" class="mt-3 p-4 bg-emerald-50/50 border border-emerald-100 rounded-xl">
        <p class="text-[10px] font-black text-emerald-500 uppercase tracking-widest mb-1">Teacher's Decision</p>
        <p class="text-sm text-gray-700">{{ appealData.teacher_remark }}</p>
        <p v-if="appealData.adjusted_score" class="text-[10px] font-bold text-emerald-600 mt-1">
          Score adjusted to: {{ appealData.adjusted_score }}
        </p>
      </div>
      <div class="text-[10px] text-gray-400 font-bold uppercase tracking-widest">
        Case Created: {{ formatDate(appealData?.created_at) }}
      </div>
    </div>
  </div>
</div>

    <div v-if="evaluation && evaluation.is_published" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white rounded-[24px] p-8 shadow-sm border border-emerald-100 relative overflow-hidden">
          <div class="absolute top-0 left-0 w-1.5 h-full bg-emerald-500"></div>
          <h3 class="text-emerald-700 font-black text-lg mb-4 flex items-center gap-2">
            <Sparkles size="20"/> Key Strengths
          </h3>
          <div class="text-[15px] text-gray-700 leading-relaxed whitespace-pre-wrap font-medium">
            {{ evaluation.strengths || 'Performance is excellent across all major criteria.' }}
          </div>
        </div>

        <div class="bg-white rounded-[24px] p-8 shadow-sm border border-blue-100 relative">
          <div class="absolute top-0 left-0 w-1.5 h-full bg-blue-600"></div>
          <h3 class="text-gray-900 font-black text-lg mb-8 flex items-center gap-2">
            <Bot size="22" class="text-blue-600"/> Expert Feedback & Guidance
          </h3>
          <div 
            class="markdown-body feedback-container text-[15px] leading-[1.8] text-gray-700" 
            v-html="renderMarkdown(evaluation.feedback)"
          ></div>
        </div>
      </div>

      <div class="lg:col-span-1 space-y-6">
        <div class="frosted-card p-6 rounded-2xl border border-white/60 shadow-sm">
          <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
            <Target size="20" class="text-blue-500"/> Skill Mastery
          </h3>
          
          <div id="studentRadarChart" class="w-full h-80"></div>
          
          <div class="mt-4 space-y-3">
            <div v-for="(score, name) in evaluation.scores" :key="name" class="flex justify-between items-center text-xs">
              <span class="text-gray-500 uppercase tracking-tighter truncate pr-2 w-32" :title="name">{{ name }}</span>
              <div class="flex items-center gap-2">
                <div class="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div class="h-full bg-blue-500 transition-all duration-1000" :style="{ width: score + '%' }"></div>
                </div>
                <span class="font-bold text-gray-700 w-6 text-right">{{ Math.round(score) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="evaluation?.learning_resources?.length > 0" class="bg-white rounded-2xl p-6 shadow-sm border border-indigo-50 relative overflow-hidden">
    <div class="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
    <h3 class="text-sm font-black text-indigo-700 mb-4 flex items-center gap-2 uppercase tracking-tight">
      <BookOpenCheck size="16"/> Personalized Resources
    </h3>
    
    <div class="space-y-4">
      <a 
        v-for="(res, idx) in evaluation.learning_resources" 
        :key="idx" 
        :href="res.url" 
        target="_blank"
        class="group block p-4 rounded-xl border border-gray-50 bg-gray-50/30 hover:bg-white hover:border-indigo-100 hover:shadow-md transition-all"
      >
        <div class="flex justify-between items-start mb-1">
          <h4 class="text-xs font-bold text-gray-800 group-hover:text-indigo-600 transition-colors line-clamp-1">
            {{ res.title }}
          </h4>
          <ExternalLink size="12" class="text-gray-300 group-hover:text-indigo-400" />
        </div>
        <p class="text-[10px] text-gray-500 leading-relaxed line-clamp-2 italic mb-2">
          "{{ res.reason }}"
        </p>
        <p v-if="res.bloom_target" class="text-[9px] text-indigo-500 font-bold uppercase mt-1">
          Target Level: {{ res.bloom_target }}
        </p>
        <div class="text-[9px] font-black text-indigo-500 uppercase tracking-tighter flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          Learn More <ArrowRight size="10"/>
        </div>
      </a>
    </div>
  </div>

        <div v-if="parsedRawFeedback && Object.keys(parsedRawFeedback).length > 0" class="bg-white rounded-2xl p-6 shadow-sm border border-indigo-50 relative overflow-hidden">
          <div class="absolute top-0 left-0 w-1 h-full bg-indigo-400"></div>
          <h3 class="text-sm font-black text-indigo-700 mb-6 flex items-center gap-2">
            <BarChart3 size="16"/> Technical Analysis
          </h3>
          
          <div class="space-y-5">
            <div v-for="(val, key) in parsedRawFeedback" :key="key" class="space-y-1.5">
              <div class="flex justify-between items-center">
                <span class="text-[11px] font-bold text-gray-500 leading-tight pr-4">{{ key }}</span>
                <span class="text-[11px] font-black text-indigo-600">{{ val }}%</span>
              </div>
              <div class="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
                <div 
                  class="h-full bg-indigo-400/80 transition-all duration-1000" 
                  :style="{ width: val + '%' }"
                ></div>
              </div>
            </div>
          </div>

          <div class="mt-6 pt-4 border-t border-gray-50 print:hidden">
            <button @click="showRawJson = !showRawJson" class="text-[10px] font-bold text-gray-400 hover:text-indigo-500 transition-colors uppercase tracking-widest flex items-center gap-1">
              {{ showRawJson ? 'Hide Source' : 'View Source JSON' }}
            </button>
            <pre v-if="showRawJson" class="mt-3 p-3 bg-gray-900 text-indigo-200 text-[10px] rounded-lg overflow-x-auto leading-relaxed"><code>{{ evaluation.ai_raw_feedback }}</code></pre>
          </div>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="appealDialogVisible"
      title="Request Academic Grade Review"
      width="540px"
      class="appeal-dialog rounded-[24px]"
      :show-close="false"
    >
      <div class="space-y-6">
        <div class="flex items-center gap-3 p-4 bg-amber-50 border border-amber-100 rounded-2xl">
          <Info class="text-amber-500 shrink-0" size="20"/>
          <p class="text-xs text-amber-800 leading-normal">
            <strong>AI Auditor Policy:</strong> Your appeal will be audited by the AI system first. Only cases with logical merit will be forwarded to the instructor.
          </p>
        </div>

        <div class="space-y-3">
          <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Why are you appealing?</label>
          <el-input
            v-model="appealReason"
            type="textarea"
            :rows="6"
            placeholder="Describe specific discrepancies between your code and the AI feedback..."
            class="custom-textarea"
          />
        </div>
      </div>
      
      <template #footer>
        <div class="flex items-center justify-end gap-3 pb-2">
          <button @click="appealDialogVisible = false" class="px-6 py-2 text-sm font-bold text-gray-500 hover:bg-gray-100 rounded-xl transition-all">
            Cancel
          </button>
          <button 
            @click="submitAppeal" 
            :disabled="isAppealing || !appealReason.trim()"
            class="flex items-center gap-2 px-8 py-2 text-sm font-black text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-xl transition-all shadow-lg shadow-blue-200"
          >
            <span v-if="isAppealing" class="animate-spin border-2 border-white border-t-transparent rounded-full w-4 h-4 mr-1"></span>
            {{ isAppealing ? 'AI Auditing...' : 'Submit Appeal' }}
          </button>
        </div>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import * as echarts from 'echarts';
import api from '../../utils/request';
import { useAuthStore } from '../../store/authStore';
import { 
  Calendar, Target, Sparkles, Bot, ArrowLeft, BarChart3, Download, 
  MessageSquare, Info, CheckCircle2, Clock, XCircle, BookOpenCheck, ExternalLink, ArrowRight
} from 'lucide-vue-next';
import { ElMessage } from 'element-plus';
import MarkdownIt from 'markdown-it';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

// --- 初始化工具 ---
const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

// --- 基础状态 ---
const submission = ref(null);
const evaluation = ref(null);
const assignment = ref(null);
const showRawJson = ref(false);
const reportContent = ref(null);
const isDownloading = ref(false);

// --- 🚀 申诉相关状态 ---
const appealDialogVisible = ref(false);
const appealReason = ref('');
const isAppealing = ref(false);
const appealData = ref(null);

// --- 🚀 申诉计算属性 ---
const hasAppeal = computed(() => {
  // 如果有 appeal 对象，或者 submission 状态是申诉中，都判定为“已申诉”
  return submission.value?.status === 'appealing' || 
         submission.value?.has_appeal === true || 
         !!appealData.value;
});

const appealStatusClass = computed(() => {
  if (!appealData.value) return ''; // 🚀 关键防御：如果没数据直接返回空字符串
  const s = appealData.value.status;
  if (s === 'pending_teacher') return 'bg-emerald-50 border-emerald-200 text-emerald-700';
  if (s === 'rejected_by_ai') return 'bg-rose-50 border-rose-200 text-rose-700';
  return 'bg-blue-50 border-blue-200 text-blue-700';
});

const appealStatusIcon = computed(() => {
  if (!appealData.value) return Clock; // 🚀 关键防御：默认返回时钟图标
  const s = appealData.value.status;
  if (s === 'pending_teacher') return CheckCircle2;
  if (s === 'rejected_by_ai') return XCircle;
  return Clock;
});

const appealIconClass = computed(() => {
  if (!appealData.value) return 'text-blue-500'; // 🚀 关键防御
  const s = appealData.value.status;
  if (s === 'pending_teacher') return 'text-emerald-500';
  if (s === 'rejected_by_ai') return 'text-rose-500';
  return 'text-blue-500';
});

// --- 基础计算属性 ---
const parsedRawFeedback = computed(() => {
  if (!evaluation.value) return {};
  const raw = evaluation.value.ai_raw_feedback_data || evaluation.value.ai_raw_feedback;
  if (!raw) return {};
  if (typeof raw === 'object') return raw;
  try { return JSON.parse(raw); } catch (e) { return {}; }
});

const allScores = computed(() => evaluation.value ? { ...(evaluation.value.scores || {}), ...(evaluation.value.kp_scores || {}) } : {});

const radarDisplayScores = computed(() => {
  const entries = Object.entries(allScores.value);
  return Object.fromEntries(entries.slice(0, 8));
});

// --- 方法区 ---

const renderMarkdown = (content) => content ? md.render(content) : '';

const goBack = () => router.push('/student/grades');

const formatDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : '-';

const getGradeLevel = (s) => s >= 85 ? 'HD' : s >= 75 ? 'D' : s >= 65 ? 'C' : s >= 50 ? 'P' : 'F';

// 🚀 核心：初始化数据
const initData = async () => {
  try {
    const subId = route.params.id;
    const res = await api.get(`/api/auth/student/submissions/${subId}/`);
    const data = res.data || res;
    submission.value = data;
    evaluation.value = data.ai_evaluation;
    assignment.value = data.assignment;

    // 获取申诉数据 (假设后端已在 evaluation 中嵌套了 appeal)
    appealData.value = data.active_appeal_data || evaluation.value?.appeal || null;
    
    if (evaluation.value?.is_published) {
      nextTick(() => drawRadarChart());
    }
  } catch (e) {
    ElMessage.error('Failed to load detail data');
  }
};

// 🚀 核心：提交申诉
const openAppealDialog = () => {
  appealReason.value = '';
  appealDialogVisible.value = true;
};

const submitAppeal = async () => {
  // 1. 立即拦截逻辑：三重保险，防止任何形式的连点
  if (isAppealing.value || hasAppeal.value || submission.value?.status === 'appealing') {
    return;
  }

  // 获取 Assignment ID
  const assignmentId = assignment.value?.id || submission.value?.assignment?.id || submission.value?.assignment;
  const finalId = (typeof assignmentId === 'object') ? assignmentId.id : assignmentId;

  if (!finalId) {
    ElMessage.error('Assignment ID not found. Please refresh.');
    return;
  }

  if (!appealReason.value.trim()) {
    ElMessage.warning('Reason is required');
    return;
  }
  
  // 🚀 核心：进入“发送中”锁定状态
  isAppealing.value = true;
  appealDialogVisible.value = false; // 立即关闭弹窗，物理隔绝连点机会

  try {
    // 2. 发起 POST 请求
    const res = await api.post(`/api/auth/student/assignments/${finalId}/submit-appeal/`, {
      reason: appealReason.value
    });
    
    // 🚀 【加固补丁】：乐观更新本地状态
    // 不等 initData 返回，直接把本地 submission 状态改为 appealing
    // 这样在 finally 执行完之前，hasAppeal 就能通过 status 判定为 true
    if (submission.value) {
      submission.value.status = 'appealing';
    }

    // 3. 处理结果反馈
    if (res.data.is_reasonable) {
      ElMessage({
        message: 'AI Audit Passed: Your concern has been forwarded to the teacher.',
        type: 'success',
        duration: 5000
      });
    } else {
      ElMessage({
        message: 'AI Audit: Your appeal was reviewed but not recommended for revision.',
        type: 'warning',
        duration: 5000
      });
    }
  } catch (e) {
    // 处理后端占位拦截（如 400 错误）
    const errorMsg = e.response?.data?.error || 'Appeal service is busy, please refresh.';
    ElMessage.error(errorMsg);
    
    // 🚀 即使报错也尝试标记，因为可能后端其实已经“占位”成功但请求超时了
    if (e.response?.status === 400 && submission.value) {
      submission.value.status = 'appealing';
    }
  } finally {
    // 🚀 4. 先拉取后端真实数据，确保状态同步
    await initData(); 
    
    // 🚀 5. 最后才解锁 isAppealing 状态
    // 此时 hasAppeal 已经因为 initData 拿到的新数据变成了 true，
    // 即使解锁了，按钮也会因为 :disabled="hasAppeal" 而保持灰色/隐藏
    isAppealing.value = false;
  }
};

// --- PDF 下载功能 ---
const downloadPDF = async () => {
  if (isDownloading.value || !assignment.value) return;
  isDownloading.value = true;

  const loading = ElMessage({
    message: 'Crafting your report...',
    duration: 0,
    type: 'info'
  });

  try {
    const element = reportContent.value;
    element.classList.add('pdf-rendering');

    const canvas = await html2canvas(element, {
      scale: 3,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
      onclone: (clonedDoc) => {
        const clonedEl = clonedDoc.querySelector('.pdf-rendering');
        if (clonedEl) {
          clonedEl.style.background = '#ffffff';
          const cards = clonedEl.querySelectorAll('.frosted-card');
          cards.forEach(c => {
            c.style.backdropFilter = 'none';
            c.style.webkitBackdropFilter = 'none';
          });
        }
      }
    });

    // Multi-page PDF logic
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    const margin = 10;
    const contentWidth = pdfWidth - (2 * margin);

    // Calculate total content height in mm
    const imgRatio = canvas.width / contentWidth;
    const totalContentHeightMm = canvas.height / imgRatio;

    // How many pixels of canvas fit on one A4 page
    const pageContentHeightMm = pdfHeight - (2 * margin);
    const pageContentHeightPx = pageContentHeightMm * imgRatio;

    let yOffset = 0;
    let pageIndex = 0;

    while (yOffset < canvas.height) {
      if (pageIndex > 0) pdf.addPage();

      // Create a slice of the canvas for this page
      const sliceHeight = Math.min(pageContentHeightPx, canvas.height - yOffset);
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = canvas.width;
      tempCanvas.height = sliceHeight;
      const ctx = tempCanvas.getContext('2d');
      ctx.drawImage(canvas, 0, yOffset, canvas.width, sliceHeight, 0, 0, canvas.width, sliceHeight);

      const sliceData = tempCanvas.toDataURL('image/png', 1.0);
      const sliceHeightMm = sliceHeight / imgRatio;

      pdf.addImage(sliceData, 'PNG', margin, margin, contentWidth, sliceHeightMm);

      yOffset += sliceHeight;
      pageIndex++;
    }

    const studentId = authStore.user?.username || 'Student';
    const safeTitle = assignment.value.title?.replace(/\s+/g, '_') || 'AI_Report';
    pdf.save(`Report_${studentId}_${safeTitle}.pdf`);

    element.classList.remove('pdf-rendering');
    loading.close();
    ElMessage.success('Report downloaded!');
  } catch (error) {
    console.error('PDF Error:', error);
    loading.close();
    ElMessage.error('Download failed.');
  } finally {
    isDownloading.value = false;
  }
};

// --- ECharts 雷达图 ---
let radarChart = null;
const drawRadarChart = () => {
  const chartDom = document.getElementById('studentRadarChart');
  if (!chartDom) return;
  radarChart = echarts.init(chartDom);
  
  const displayData = radarDisplayScores.value;
  const indicator = Object.keys(displayData).map(key => ({ name: key, max: 100 }));
  const fullDataEntries = Object.entries(allScores.value);

  radarChart.setOption({
    animation: false,
    tooltip: {
      show: true,
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      padding: [12, 18],
      borderWidth: 1,
      borderColor: '#3b82f6',
      shadowBlur: 10,
      shadowColor: 'rgba(0,0,0,0.1)',
      textStyle: { color: '#1e293b', fontSize: 12 },
      formatter: () => {
        let res = `<div style="font-weight:900; color:#1e3a8a; border-bottom:1px solid #eee; margin-bottom:8px; padding-bottom:4px;">Complete Skill Analysis</div>`;
        fullDataEntries.forEach(([key, val]) => {
          res += `<div style="display:flex; justify-content:space-between; gap:30px; margin-bottom:3px;">
                    <span style="color:#64748b;">${key}:</span>
                    <span style="font-weight:800; color:#3b82f6;">${Math.round(val)}%</span>
                  </div>`;
        });
        return res;
      }
    },
    radar: {
      indicator: indicator.length > 0 ? indicator : [{ name: 'N/A', max: 100 }],
      shape: 'circle',
      splitNumber: 4,
      axisName: { 
        color: '#64748b', 
        fontWeight: 'bold', 
        fontSize: 9,
        formatter: (value) => value.length > 10 ? value.slice(0, 8) + '...' : value
      },
      splitArea: { areaStyle: { color: ['rgba(255,255,255,0)', 'rgba(203,213,225,0.02)'] } },
      axisLine: { lineStyle: { color: 'rgba(203,213,225,0.2)' } },
      splitLine: { lineStyle: { color: 'rgba(203,213,225,0.2)' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: Object.values(displayData),
        name: 'Capability Distribution',
        itemStyle: { color: '#3b82f6' },
        areaStyle: { 
          color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.1)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.4)' }
          ]) 
        },
        lineStyle: { width: 3, shadowBlur: 10, shadowColor: 'rgba(59, 130, 246, 0.3)' },
        symbol: 'circle',
        symbolSize: 6
      }]
    }]
  });
};

onMounted(initData);
</script>

<style scoped>
.frosted-card { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(16px); }
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #475569; border-radius: 10px; }

/* PDF 渲染专用补丁，强制深色文字以确保清晰 */
.pdf-rendering { color: #000 !important; }
.pdf-rendering :deep(.text-gray-500) { color: #334155 !important; }
.pdf-rendering :deep(.text-gray-400) { color: #475569 !important; }

/* Markdown 样式保持专业 */
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) {
  color: #1e3a8a; margin-top: 1.5rem; margin-bottom: 0.75rem; font-weight: 800;
}
.markdown-body :deep(ul) { list-style: disc; padding-left: 1.5rem; margin-bottom: 1rem; }
.markdown-body :deep(li) { margin-bottom: 0.5rem; }
.markdown-body :deep(strong) {
  color: #1e3a8a; font-weight: 800; background: rgba(59, 130, 246, 0.1); padding: 0 4px; border-radius: 4px;
}
.markdown-body :deep(code) {
  background: #f1f5f9; padding: 0.2rem 0.4rem; border-radius: 4px; color: #ef4444; font-family: monospace;
}
</style>