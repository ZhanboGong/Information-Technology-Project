<template>
  <div class="max-w-5xl mx-auto space-y-6 animate-fade-in pt-4 pb-20">
    <div class="flex items-center gap-4">
      <button @click="router.back()" class="p-2.5 frosted-card rounded-xl text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-all shadow-sm">
        <ArrowLeft size="20" />
      </button>
      <div class="flex-1">
        <h2 class="text-2xl font-black text-gray-800">Plagiarism Detection</h2>
        <p class="text-sm text-gray-500 mt-1">Powered by Stanford MOSS — Detect code similarity across student submissions.</p>
      </div>
    </div>

    <!-- 触发查重 -->
    <div class="frosted-card p-6 rounded-2xl border border-white/60 shadow-sm">
      <h3 class="text-sm font-bold text-gray-800 mb-4">Run New Check</h3>
      <div class="flex gap-3 items-end">
        <div class="flex-1">
          <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1 mb-1 block">Course</label>
          <el-select v-model="selectedCourseId" placeholder="Choose course" class="w-full" @change="loadAssignments">
            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </div>
        <div class="flex-1">
          <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1 mb-1 block">Assignment</label>
          <el-select v-model="selectedAssignmentId" placeholder="Choose assignment" class="w-full" :disabled="!selectedCourseId" @change="loadReports">
            <el-option v-for="a in filteredAssignments" :key="a.id" :label="a.title" :value="a.id" />
          </el-select>
        </div>
        <button @click="runCheck" :disabled="!selectedAssignmentId || isStarting"
          class="px-6 py-2.5 bg-blue-600 text-white text-sm font-bold rounded-xl shadow-md flex items-center gap-2 hover:bg-blue-700 transition-all disabled:opacity-50 shrink-0">
          <Loader2 v-if="isStarting" size="16" class="animate-spin" />
          <Search v-else size="16" />
          {{ isStarting ? 'Starting...' : 'Run Check' }}
        </button>
      </div>
    </div>

    <!-- 历史报告列表 -->
    <div v-if="reports.length > 0" class="space-y-3">
      <h3 class="text-sm font-bold text-gray-800">Report History</h3>
      <div v-for="report in reports" :key="report.id" class="frosted-card rounded-2xl border border-white/60 shadow-sm overflow-hidden">

        <!-- 报告头部 -->
        <div class="p-5 flex items-center justify-between cursor-pointer hover:bg-gray-50/50 transition-colors" @click="toggleReport(report.id)">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center"
              :class="report.status === 'completed' ? 'bg-emerald-100 text-emerald-600' : report.status === 'pending' ? 'bg-amber-100 text-amber-600' : 'bg-red-100 text-red-600'">
              <CheckCircle2 v-if="report.status === 'completed'" size="16" />
              <Loader2 v-else-if="report.status === 'pending'" size="16" class="animate-spin" />
              <AlertCircle v-else size="16" />
            </div>
            <div>
              <p class="text-sm font-bold text-gray-800">
                {{ report.status === 'completed' ? 'Scan Complete' : report.status === 'pending' ? 'Scanning...' : 'Error' }}
              </p>
              <p class="text-[10px] text-gray-400 font-bold">{{ formatTime(report.created_at) }} · {{ report.file_count }} files · {{ report.mode || 'unknown' }} mode</p>
            </div>
          </div>
          <div class="flex items-center gap-2" @click.stop>
            <a v-if="report.status === 'completed' && report.report_url" :href="report.report_url" target="_blank"
               class="px-3 py-1.5 bg-emerald-50 text-emerald-600 text-[11px] font-bold rounded-lg border border-emerald-100 hover:bg-emerald-600 hover:text-white transition-all flex items-center gap-1">
              <ExternalLink size="12" /> MOSS
            </a>
            <ChevronDown size="16" class="text-gray-400 transition-transform duration-300" :class="{ 'rotate-180': expandedReports[report.id] }" />
          </div>
        </div>

        <!-- 报告详情 -->
        <div v-show="expandedReports[report.id]" class="px-5 pb-5 border-t border-gray-100">

          <div v-if="report.status === 'error'" class="p-3 bg-red-50 border border-red-100 rounded-xl mt-3">
            <p class="text-xs text-red-600">{{ report.error_message }}</p>
          </div>

          <!-- MOSS 聚合分析 -->
          <div v-if="report.status === 'completed' && report.mode === 'moss' && hasPairs(report)" class="space-y-4 mt-4">
            <!-- 概览 -->
            <div class="grid grid-cols-3 gap-3">
              <div class="p-3 bg-blue-50 border border-blue-100 rounded-xl text-center">
                <p class="text-[10px] font-black text-blue-500 uppercase tracking-widest">Student Pairs</p>
                <p class="text-xl font-black text-blue-700 mt-1">{{ report.matches?.total_pairs || 0 }}</p>
              </div>
              <div class="p-3 bg-red-50 border border-red-100 rounded-xl text-center">
                <p class="text-[10px] font-black text-red-500 uppercase tracking-widest">High Risk</p>
                <p class="text-xl font-black text-red-700 mt-1">{{ report.matches?.high_risk_count || 0 }}</p>
              </div>
              <div class="p-3 bg-amber-50 border border-amber-100 rounded-xl text-center">
                <p class="text-[10px] font-black text-amber-500 uppercase tracking-widest">Medium</p>
                <p class="text-xl font-black text-amber-700 mt-1">{{ report.matches?.medium_risk_count || 0 }}</p>
              </div>
            </div>

            <!-- 风险排名 -->
            <div v-if="report.matches?.risk_summary && report.matches.risk_summary.length > 0" class="p-5 bg-white border border-gray-100 rounded-xl">
              <h4 class="text-sm font-bold text-gray-800 mb-4 flex items-center gap-2">
                <AlertTriangle size="16" class="text-red-500" /> Student Risk Ranking
              </h4>
              <div class="space-y-2">
                <div v-for="(s, idx) in report.matches.risk_summary" :key="idx"
                     class="flex items-center justify-between p-3 rounded-xl"
                     :class="s.risk_level === 'high' ? 'bg-red-50 border border-red-100' : s.risk_level === 'medium' ? 'bg-amber-50 border border-amber-100' : 'bg-gray-50 border border-gray-100'">
                  <div class="flex items-center gap-3">
                    <span class="text-sm font-bold text-gray-500 w-6 text-center">#{{ idx + 1 }}</span>
                    <span class="text-sm font-bold text-gray-800">{{ s.student }}</span>
                  </div>
                  <div class="flex items-center gap-4">
                    <div class="flex gap-3 text-[10px] font-bold">
                      <span v-if="s.high_count > 0" class="text-red-500">{{ s.high_count }} high</span>
                      <span v-if="s.medium_count > 0" class="text-amber-500">{{ s.medium_count }} medium</span>
                      <span class="text-gray-400">{{ s.total_pairs }} pairs</span>
                    </div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase"
                          :class="s.risk_level === 'high' ? 'bg-red-100 text-red-600' : s.risk_level === 'medium' ? 'bg-amber-100 text-amber-600' : 'bg-gray-100 text-gray-500'">
                      {{ s.risk_level }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 学生对 -->
            <div class="p-5 bg-white border border-gray-100 rounded-xl">
              <h4 class="text-sm font-bold text-gray-800 mb-4 flex items-center gap-2">
                <Users size="16" class="text-blue-500" /> Student Pair Analysis
              </h4>
              <div class="space-y-2">
                <div v-for="(m, idx) in (report.matches?.student_pairs || [])" :key="idx"
                     class="p-4 rounded-xl border cursor-pointer transition-all hover:shadow-md"
                     :class="getRiskCardBg(m.max_similarity)"
                     @click="toggleDetail(report.id, idx)">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3 min-w-0">
                      <div class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-black shrink-0"
                           :class="m.max_similarity > 80 ? 'bg-red-500' : m.max_similarity > 50 ? 'bg-amber-500' : 'bg-gray-400'">
                        {{ idx + 1 }}
                      </div>
                      <div class="min-w-0">
                        <div class="flex items-center gap-2">
                          <span class="text-sm font-bold text-gray-800">{{ m.student_a }}</span>
                          <ArrowRight size="12" class="text-gray-400" />
                          <span class="text-sm font-bold text-gray-800">{{ m.student_b }}</span>
                        </div>
                        <p class="text-[10px] text-gray-400 font-bold mt-0.5">{{ m.matched_files }} matched files · avg {{ m.avg_similarity }}%</p>
                      </div>
                    </div>
                    <div class="flex items-center gap-3 shrink-0">
                      <div class="w-24">
                        <div class="flex justify-between mb-1">
                          <span class="text-[9px] font-bold text-gray-400">Max</span>
                          <span class="text-xs font-black" :class="getRiskText(m.max_similarity)">{{ m.max_similarity }}%</span>
                        </div>
                        <div class="w-full bg-gray-200 h-2 rounded-full overflow-hidden">
                          <div class="h-full rounded-full transition-all" :class="getRiskBar(m.max_similarity)" :style="{ width: m.max_similarity + '%' }"></div>
                        </div>
                      </div>
                      <span class="px-2 py-1 rounded-lg text-[10px] font-black uppercase border" :class="getRiskBadge(m.max_similarity)">
                        {{ m.max_similarity > 80 ? 'High' : m.max_similarity > 50 ? 'Med' : 'Low' }}
                      </span>
                      <ChevronDown size="14" class="text-gray-400 transition-transform" :class="{ 'rotate-180': expandedPairs[report.id] === idx }" />
                    </div>
                  </div>

                  <!-- 展开文件详情 -->
                  <div v-if="expandedPairs[report.id] === idx && m.files && m.files.length > 0" class="mt-4 pt-4 border-t border-gray-100">
                    <div class="flex justify-between items-center mb-2">
                      <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Matched Files ({{ m.files.length }})</p>
                      <button @click.stop="openDiffView(report, idx)" class="px-3 py-1 bg-blue-50 text-blue-600 text-[11px] font-bold rounded-lg border border-blue-100 hover:bg-blue-600 hover:text-white transition-all flex items-center gap-1">
                        <Code size="12" /> View Code Diff
                      </button>
                    </div>
                    <div class="space-y-1">
                      <div v-for="(f, fi) in m.files" :key="fi"
                           class="flex items-center justify-between py-2 px-3 rounded-lg"
                           :class="f.similarity > 80 ? 'bg-red-50' : f.similarity > 50 ? 'bg-amber-50' : 'bg-gray-50'">
                        <div class="min-w-0 flex-1">
                          <p class="text-[11px] font-bold text-gray-600 truncate">{{ getFilename(f.file_a) }}</p>
                          <p class="text-[10px] text-gray-400 truncate">↔ {{ getFilename(f.file_b) }}</p>
                        </div>
                        <span class="text-xs font-black ml-3 shrink-0" :class="getRiskText(f.similarity)">{{ f.similarity }}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- MOSS 链接 -->
            <div class="p-4 bg-blue-50/50 border border-blue-100 rounded-xl flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Info size="16" class="text-blue-500" />
                <span class="text-xs text-blue-600 font-bold">Full line-by-line comparison on MOSS</span>
              </div>
              <a :href="report.report_url" target="_blank"
                 class="px-4 py-2 bg-blue-600 text-white text-xs font-bold rounded-lg hover:bg-blue-700 transition-all flex items-center gap-1">
                <ExternalLink size="14" /> Open MOSS
              </a>
            </div>
          </div>

          <div v-if="report.status === 'completed' && report.mode === 'moss' && !hasPairs(report)"
               class="p-4 bg-emerald-50 border border-emerald-100 rounded-xl text-center mt-4">
            <CheckCircle2 size="20" class="mx-auto text-emerald-500 mb-1" />
            <p class="text-xs font-bold text-emerald-600">No high-similarity pairs detected</p>
          </div>

          <div v-if="report.status === 'completed' && report.mode === 'local' && report.matches && report.matches.length > 0" class="mt-4">
            <div class="p-3 bg-blue-50 border border-blue-100 rounded-xl mb-3 flex items-center gap-2">
              <Info size="14" class="text-blue-500" />
              <p class="text-[11px] text-blue-600 font-bold">MOSS unreachable — used local similarity detection</p>
            </div>
            <div class="space-y-2">
              <div v-for="(m, idx) in report.matches.slice(0, 5)" :key="idx"
                   class="flex items-center justify-between p-3 rounded-xl border" :class="getRiskCardBg(m.similarity)">
                <div class="min-w-0 flex-1">
                  <p class="text-xs font-bold text-gray-800 truncate">{{ m.file_a }}</p>
                  <p class="text-[10px] text-gray-400 font-bold">↔ {{ m.file_b }}</p>
                </div>
                <div class="text-right shrink-0 ml-4">
                  <p class="text-lg font-black" :class="getRiskText(m.similarity)">{{ m.similarity }}%</p>
                  <p class="text-[9px] font-bold" :class="getRiskLabel(m.similarity)">
                    {{ m.similarity > 70 ? 'High Risk' : m.similarity > 50 ? 'Medium' : 'Low' }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div v-if="report.status === 'completed' && report.mode === 'local' && (!report.matches || report.matches.length === 0)"
               class="p-4 bg-emerald-50 border border-emerald-100 rounded-xl text-center mt-4">
            <CheckCircle2 size="20" class="mx-auto text-emerald-500 mb-1" />
            <p class="text-xs font-bold text-emerald-600">No high-similarity pairs detected</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="selectedAssignmentId && !loading && reports.length === 0 && !isStarting" class="text-center py-12 bg-white/50 rounded-2xl border border-dashed border-gray-200">
      <Search size="32" class="mx-auto text-gray-300 mb-3" />
      <p class="text-sm font-bold text-gray-400">No plagiarism reports yet</p>
      <p class="text-xs text-gray-400 mt-1">Click "Run Check" to start a new scan</p>
    </div>

    <!-- 代码对比侧边栏 -->
    <transition name="slide-right">
      <div v-if="showDiffView" class="fixed inset-0 z-50 flex justify-end">
        <div class="absolute inset-0 bg-gray-900/30 backdrop-blur-sm" @click="showDiffView = false"></div>
        <div class="relative w-[900px] max-w-full h-full bg-white shadow-2xl flex flex-col">
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
            <div>
              <h3 class="text-sm font-bold text-gray-800">Code Comparison</h3>
              <p class="text-[10px] text-gray-400 font-bold mt-0.5">
                {{ diffData?.files?.[0]?.filename }} ↔ {{ diffData?.files?.[1]?.filename }}
              </p>
            </div>
            <button @click="showDiffView = false" class="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <X size="18" class="text-gray-500" />
            </button>
          </div>

          <!-- 统计栏 -->
          <div v-if="diffData?.files?.length === 2" class="px-6 py-2.5 bg-gray-50 border-b border-gray-100 flex items-center gap-6 text-[11px] font-bold shrink-0">
            <span class="text-gray-500">Lines A: <span class="text-gray-700">{{ diffData.files[0].lines.length }}</span></span>
            <span class="text-gray-500">Lines B: <span class="text-gray-700">{{ diffData.files[1].lines.length }}</span></span>
            <span class="text-red-600">Matched: {{ matchedCount }} lines</span>
          </div>

          <!-- 加载中 -->
          <div v-if="diffLoading" class="flex-1 flex items-center justify-center">
            <Loader2 class="animate-spin text-blue-500" size="32" />
          </div>

          <!-- 代码对比 -->
          <div v-else-if="diffData?.files?.length === 2" class="flex-1 flex overflow-hidden">
            <!-- File A -->
            <div class="flex-1 overflow-auto border-r border-gray-200">
              <div class="sticky top-0 bg-gray-100 px-4 py-2 text-[10px] font-bold text-gray-500 uppercase z-10 border-b border-gray-200">
                {{ diffData.files[0].filename }}
              </div>
              <div class="font-mono text-xs leading-relaxed">
                <div v-for="(line, idx) in diffData.files[0].lines" :key="'a'+idx"
                     class="flex px-4 py-0.5 hover:bg-blue-50 transition-colors"
                     :class="line.matched ? 'bg-red-50 border-l-2 border-red-400' : ''">
                  <span class="w-8 text-right text-gray-400 select-none shrink-0 mr-3 text-[10px]">{{ idx + 1 }}</span>
                  <span class="whitespace-pre" :class="line.matched ? 'text-red-700 font-bold' : 'text-gray-600'">{{ line.code || ' ' }}</span>
                </div>
              </div>
            </div>
            <!-- File B -->
            <div class="flex-1 overflow-auto">
              <div class="sticky top-0 bg-gray-100 px-4 py-2 text-[10px] font-bold text-gray-500 uppercase z-10 border-b border-gray-200">
                {{ diffData.files[1].filename }}
              </div>
              <div class="font-mono text-xs leading-relaxed">
                <div v-for="(line, idx) in diffData.files[1].lines" :key="'b'+idx"
                     class="flex px-4 py-0.5 hover:bg-blue-50 transition-colors"
                     :class="line.matched ? 'bg-red-50 border-l-2 border-red-400' : ''">
                  <span class="w-8 text-right text-gray-400 select-none shrink-0 mr-3 text-[10px]">{{ idx + 1 }}</span>
                  <span class="whitespace-pre" :class="line.matched ? 'text-red-700 font-bold' : 'text-gray-600'">{{ line.code || ' ' }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="flex-1 flex items-center justify-center">
            <p class="text-gray-400 text-sm">No code data available</p>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '../../utils/request';
import { ElMessage } from 'element-plus';
import { ArrowLeft, Search, Loader2, AlertCircle, CheckCircle2, ExternalLink, Info, Clock, ArrowRight, AlertTriangle, Users, ChevronDown, X, Code } from 'lucide-vue-next';

const router = useRouter();
const courses = ref([]);
const assignments = ref([]);
const reports = ref([]);
const selectedCourseId = ref(null);
const selectedAssignmentId = ref(null);
const isStarting = ref(false);
const loading = ref(false);
const expandedPairs = reactive({});
const expandedReports = reactive({});

// 代码对比
const showDiffView = ref(false);
const diffData = ref(null);
const diffLoading = ref(false);

const matchedCount = computed(() => {
  if (!diffData.value?.files) return 0;
  let count = 0;
  for (const file of diffData.value.files) {
    count += file.lines.filter(l => l.matched).length;
  }
  return Math.floor(count / 2);
});

const filteredAssignments = computed(() => {
  return assignments.value.filter(a => {
    const courseId = typeof a.course === 'object' ? a.course.id : a.course;
    return courseId === selectedCourseId.value;
  });
});

const formatTime = (iso) => {
  if (!iso) return '';
  return new Date(iso).toLocaleString();
};

const hasPairs = (report) => {
  if (!report.matches) return false;
  return report.matches.student_pairs && report.matches.student_pairs.length > 0;
};

const getRiskBg = (sim) => {
  if (sim > 80) return 'bg-red-100 text-red-600';
  if (sim > 50) return 'bg-amber-100 text-amber-600';
  return 'bg-gray-100 text-gray-600';
};
const getRiskCardBg = (sim) => {
  if (sim > 80) return 'bg-red-50 border-red-200';
  if (sim > 50) return 'bg-amber-50 border-amber-200';
  return 'bg-gray-50 border-gray-200';
};
const getRiskText = (sim) => {
  if (sim > 80) return 'text-red-600';
  if (sim > 50) return 'text-amber-600';
  return 'text-gray-600';
};
const getRiskBar = (sim) => {
  if (sim > 80) return 'bg-red-500';
  if (sim > 50) return 'bg-amber-500';
  return 'bg-gray-400';
};
const getRiskBadge = (sim) => {
  if (sim > 80) return 'bg-red-100 text-red-600 border-red-200';
  if (sim > 50) return 'bg-amber-100 text-amber-600 border-amber-200';
  return 'bg-gray-100 text-gray-500 border-gray-200';
};
const getRiskLabel = (sim) => {
  if (sim > 70) return 'text-red-500';
  if (sim > 50) return 'text-amber-500';
  return 'text-gray-400';
};

const getFilename = (path) => path.split('/').pop() || path;

const toggleDetail = (reportId, idx) => {
  expandedPairs[reportId] = expandedPairs[reportId] === idx ? null : idx;
};

const toggleReport = (reportId) => {
  expandedReports[reportId] = !expandedReports[reportId];
};

const openDiffView = async (report, pairIdx) => {
  if (!report.report_url) {
    ElMessage.warning('No MOSS report URL available');
    return;
  }

  diffData.value = null;
  diffLoading.value = true;
  showDiffView.value = true;

const pair = report.matches.student_pairs[pairIdx];
const firstFile = pair?.files?.[0];
let detailA, detailB;
if (firstFile?.detail_urls?.file_a) {
  detailA = firstFile.detail_urls.file_a;
  detailB = firstFile.detail_urls.file_b;
} else {
  const baseUrl = report.report_url;
  detailA = `${baseUrl}/match${pairIdx}-0.html`;
  detailB = `${baseUrl}/match${pairIdx}-1.html`;
}

  try {
    const res = await api.post(`/api/auth/teacher/assignments/${selectedAssignmentId.value}/plagiarism-diff/`, {
      url_a: detailA,
      url_b: detailB
    });
    diffData.value = res.data || res;
  } catch (e) {
    ElMessage.error('Failed to load code comparison');
    showDiffView.value = false;
  } finally {
    diffLoading.value = false;
  }
};

const loadCourses = async () => {
  try {
    const res = await api.get('/api/auth/teacher/courses/');
    courses.value = res.results || res;
  } catch (e) { ElMessage.error('Failed to load courses'); }
};

const loadAssignments = async () => {
  selectedAssignmentId.value = null;
  reports.value = [];
  try {
    const res = await api.get('/api/auth/teacher/assignments/');
    assignments.value = res.results || res;
  } catch (e) { ElMessage.error('Failed to load assignments'); }
};

const loadReports = async () => {
  if (!selectedAssignmentId.value) return;
  loading.value = true;
  try {
    const res = await api.get(`/api/auth/teacher/assignments/${selectedAssignmentId.value}/plagiarism-results/`);
    reports.value = res.data || res;
    reports.value.forEach(r => {
      if (r.status === 'pending') pollReport(r.id);
    });
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const runCheck = async () => {
  if (!selectedAssignmentId.value) return;
  isStarting.value = true;
  try {
    const res = await api.post(`/api/auth/teacher/assignments/${selectedAssignmentId.value}/plagiarism-check/`);
    const data = res.data || res;
    ElMessage.success('Plagiarism check started');
    await loadReports();
    if (data.report_id) pollReport(data.report_id);
  } catch (e) {
    ElMessage.error(e.response?.data?.error || 'Failed to start check');
  } finally {
    isStarting.value = false;
  }
};

const pollReport = async (reportId) => {
  const maxAttempts = 60;
  let attempts = 0;
  const poll = async () => {
    attempts++;
    try {
      const res = await api.get(`/api/auth/teacher/assignments/${selectedAssignmentId.value}/plagiarism-results/`);
      const allReports = res.data || res;
      const updated = allReports.find(r => r.id === reportId);
      if (updated && updated.status !== 'pending') {
        reports.value = allReports;
        return;
      }
      if (attempts < maxAttempts) setTimeout(poll, 5000);
    } catch (e) {
      console.error('Poll error:', e);
    }
  };
  setTimeout(poll, 5000);
};

onMounted(loadCourses);
</script>

<style scoped>
.frosted-card { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); }
.slide-right-enter-active, .slide-right-leave-active { transition: opacity 0.3s ease; }
.slide-right-enter-from, .slide-right-leave-to { opacity: 0; }
.slide-right-enter-from .relative:last-child, .slide-right-leave-to .relative:last-child { transform: translateX(100%); transition: transform 0.3s ease; }
</style>