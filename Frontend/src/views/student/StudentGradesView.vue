<template>
  <div class="space-y-6 animate-fade-in max-w-6xl mx-auto pt-2 pb-10">
    
    <div class="mb-8">
      <h2 class="text-2xl font-bold text-gray-800 tracking-tight flex items-center gap-2">
        <Award class="text-blue-600" size="24" /> 
        My Gradebook
      </h2>
      <p class="text-sm text-gray-500 mt-1">View your historical course grades and skill evaluations grouped by course.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="frosted-card p-6 rounded-2xl border border-white/60 relative overflow-hidden group hover:-translate-y-1 transition-transform shadow-sm">
        <div class="absolute right-0 top-0 w-32 h-32 bg-gradient-to-br from-blue-400/20 to-indigo-50/20 rounded-bl-full -z-10 group-hover:scale-110 transition-transform duration-500"></div>
        <div class="flex items-start justify-between mb-4">
          <div class="p-3 bg-blue-100/50 text-blue-600 rounded-xl"><TrendingUp size="24" /></div>
          <span class="bg-blue-50 text-blue-600 border border-blue-200 px-2.5 py-1 rounded-lg font-bold text-xs">Real-time</span>
        </div>
        <h3 class="text-3xl font-black text-gray-800 tracking-tight">{{ avgScore }}</h3>
        <p class="text-sm font-bold text-gray-500 mt-1 uppercase tracking-wide">Average Score</p>
      </div>
      <div class="frosted-card p-6 rounded-2xl border border-white/60 relative overflow-hidden group hover:-translate-y-1 transition-transform shadow-sm">
        <div class="absolute right-0 top-0 w-32 h-32 bg-gradient-to-br from-emerald-400/20 to-teal-500/20 rounded-bl-full -z-10 group-hover:scale-110 transition-transform duration-500"></div>
        <div class="flex items-start justify-between mb-4">
          <div class="p-3 bg-emerald-100/50 text-emerald-600 rounded-xl"><CheckCircle2 size="24" /></div>
        </div>
        <h3 class="text-3xl font-black text-gray-800 tracking-tight">{{ submissionCount }} <span class="text-lg text-gray-400 font-medium">Docs</span></h3>
        <p class="text-sm font-bold text-gray-500 mt-1 uppercase tracking-wide">Evaluated Tasks</p>
      </div>
      <div class="frosted-card p-6 rounded-2xl border border-white/60 relative overflow-hidden group hover:-translate-y-1 transition-transform shadow-sm">
        <div class="absolute right-0 top-0 w-32 h-32 bg-gradient-to-br from-orange-400/20 to-rose-500/20 rounded-bl-full -z-10 group-hover:scale-110 transition-transform duration-500"></div>
        <div class="flex items-start justify-between mb-4">
          <div class="p-3 bg-orange-100/50 text-orange-600 rounded-xl"><Star size="24" /></div>
        </div>
        <h3 class="text-3xl font-black text-gray-800 tracking-tight">{{ excellentCount }} <span class="text-lg text-gray-400 font-medium">Times</span></h3>
        <p class="text-sm font-bold text-gray-500 mt-1 uppercase tracking-wide">Above 90</p>
      </div>
    </div>

    <div v-if="loading" class="flex flex-col items-center py-20">
      <Loader2 class="animate-spin text-blue-600 mb-4" size="40" />
      <p class="text-gray-400 text-sm">Fetching grade details...</p>
    </div>

    <div v-else class="space-y-10">
      <div v-for="(records, courseName) in groupedRecords" :key="courseName" class="space-y-4">
        
        <div class="flex items-center gap-3 border-b border-gray-100 pb-2">
          <div class="w-1.5 h-6 bg-blue-500 rounded-full"></div>
          <h3 class="text-xl font-bold text-gray-700">{{ courseName }}</h3>
          <span class="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full font-bold">{{ records.length }}</span>
        </div>

        <div class="grid grid-cols-1 gap-4">
          <div 
            v-for="record in records" 
            :key="record.id"
            class="record-card rounded-2xl border border-gray-100 transition-all bg-white overflow-hidden"
            :class="{'shadow-xl ring-2 ring-blue-500/10 scale-[1.005]': expandedId === record.id, 'hover:shadow-md': record.ai_evaluation}"
          >
            <div 
              class="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer"
              @click="toggleExpand(record)"
            >
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1.5">
                  <span v-if="record.status === 'completed' && !record.ai_evaluation?.is_published" class="px-2 py-0.5 bg-orange-50 text-orange-600 border border-orange-200 rounded text-[10px] font-bold flex items-center gap-1">
                    <Lock size="10"/> Pending Release
                  </span>
                  <span v-else-if="record.status === 'pending' || record.status === 'running'" class="px-2 py-0.5 bg-blue-50 text-blue-600 border border-blue-200 rounded text-[10px] font-bold flex items-center gap-1">
                    <Loader2 size="10" class="animate-spin"/> Grading...
                  </span>
                </div>
                <h3 class="text-lg font-bold text-gray-800 truncate" :class="{'text-blue-600': expandedId === record.id}">
                  {{ record.assignment_info?.title || 'Assignment Details' }}
                </h3>
                <p class="text-xs text-gray-400 mt-1 flex items-center gap-1">
                  <Clock size="12" /> Submitted: {{ formatTime(record.created_at) }}
                </p>
              </div>

              <div v-if="record.ai_evaluation?.is_published" class="flex items-center gap-6">
                <div class="text-right">
                  <div class="flex items-baseline justify-end gap-1">
                    <span class="text-2xl font-black text-blue-600">{{ record.ai_evaluation.total_score }}</span>
                    <span class="text-xs font-bold text-gray-400">/ 100</span>
                  </div>
                  <span class="text-[10px] font-bold text-green-500 mt-0.5 block tracking-widest uppercase">Published</span>
                </div>
                <div class="w-10 h-10 rounded-full flex items-center justify-center bg-gray-50 text-gray-400 transition-transform" :class="{'rotate-180 bg-blue-50 text-blue-600': expandedId === record.id}">
                  <ChevronDown size="20" />
                </div>
              </div>
              <div v-else class="text-gray-400 text-sm italic font-medium">Review in progress...</div>
            </div>

            <transition name="expand">
              <div v-if="expandedId === record.id && record.ai_evaluation?.is_published" class="border-t border-gray-50 bg-gray-50/20 p-5">
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  <div class="lg:col-span-2">
                    <div class="bg-white rounded-xl p-6 shadow-sm border border-blue-100 relative h-full">
                      <h4 class="text-gray-900 font-bold text-base mb-4 flex items-center gap-2.5">
                        <span class="flex items-center justify-center w-7 h-7 bg-blue-600 rounded-lg text-white">
                          <Bot size="16" />
                        </span>
                        Expert Feedback
                      </h4>

                      <div 
                        class="markdown-body feedback-content text-sm leading-relaxed text-gray-600"
                        v-html="renderMarkdown(record.ai_evaluation.feedback)"
                      ></div>

                      <div class="mt-6 flex items-center gap-2 text-[10px] font-bold text-blue-400/80 bg-blue-50/30 w-fit px-2.5 py-1 rounded-md border border-blue-50">
                        <Star size="10" /> AI-Generated Report
                      </div>
                    </div>
                  </div>

                  <div class="space-y-4">
                    <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100 flex flex-col h-full">
                      <h4 class="text-gray-900 font-bold text-xs mb-6 uppercase tracking-widest flex items-center gap-2">
                        <TrendingUp size="14" class="text-blue-500" />
                        Skills Matrix
                      </h4>
                      
                      <div class="flex-grow space-y-5">
                        <div v-for="(val, dim) in record.ai_evaluation.scores" :key="dim">
                          <div class="flex justify-between items-end mb-1.5">
                            <span class="text-[11px] font-bold text-gray-400 uppercase tracking-tighter">{{ dim }}</span>
                            <span class="text-[11px] font-black text-gray-700">{{ val }}%</span>
                          </div>
                          <div class="w-full bg-gray-50 h-1.5 rounded-full overflow-hidden">
                            <div 
                              class="h-full rounded-full transition-all duration-1000 ease-out shadow-[0_0_4px_rgba(0,0,0,0.02)]"
                              :class="{
                                'bg-gradient-to-r from-emerald-400 to-green-500': val >= 85,
                                'bg-gradient-to-r from-blue-400 to-indigo-500': val >= 60 && val < 85,
                                'bg-gradient-to-r from-orange-400 to-rose-500': val < 60
                              }"
                              :style="{ width: val + '%' }"
                            ></div>
                          </div>
                        </div>

                        <div v-if="Object.keys(record.ai_evaluation.kp_scores || {}).length > 0" class="pt-2 border-t border-dashed border-gray-100">
                           <p class="text-[12px] font-bold text-gray-800 uppercase tracking-widest mb-4">Detailed rubric Scores</p>
                           
                           <div class="space-y-4">
                             <div v-for="(val, kpName) in record.ai_evaluation.kp_scores" :key="kpName">
                               <div class="flex justify-between items-center mb-1">
                                 <span class="text-[10px] font-medium text-gray-500 leading-tight pr-4 flex-1">{{ kpName }}</span>
                                 <span class="text-[10px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">{{ val }}</span>
                               </div>
                               <div class="w-full bg-gray-50 h-1 rounded-full overflow-hidden">
                                  <div class="h-full bg-blue-400/60 rounded-full transition-all duration-1000" :style="{ width: val + '%' }"></div>
                               </div>
                             </div>
                           </div>
                        </div>
                      </div>

                      <button 
                        @click="goToDetail(record)" 
                        class="w-full mt-8 py-3 bg-gray-900 hover:bg-blue-600 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-sm active:scale-95"
                      >
                        <FileText size="14"/> View Full Report
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '../../utils/request';
import { 
  Award, TrendingUp, CheckCircle2, Star, Clock, 
  ChevronDown, Lock, Loader2, Bot, FileText
} from 'lucide-vue-next';
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
});

const router = useRouter();
const loading = ref(true);
const expandedId = ref(null);
const allRecords = ref([]);

// Markdown Rendering Function
const renderMarkdown = (content) => {
  if (!content) return '';
  return md.render(content);
};

const fetchGrades = async () => {
  try {
    loading.value = true;
    const res = await api.get('/api/auth/student/submissions/');
    const data = res.data || res;
    if (Array.isArray(data)) {
      allRecords.value = data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    }
  } catch (error) {
    console.error('Failed to fetch gradebook:', error);
  } finally {
    loading.value = false;
  }
};

const groupedRecords = computed(() => {
  const groups = {};
  allRecords.value.forEach(record => {
    const courseName = record.assignment_info?.course_name || 'GENERAL';
    if (!groups[courseName]) groups[courseName] = [];
    groups[courseName].push(record);
  });
  return groups;
});

const publishedGrades = computed(() => 
  allRecords.value.filter(r => r.ai_evaluation?.is_published).map(r => parseFloat(r.ai_evaluation.total_score))
);

const avgScore = computed(() => {
  if (publishedGrades.value.length === 0) return 0;
  const sum = publishedGrades.value.reduce((a, b) => a + b, 0);
  return (sum / publishedGrades.value.length).toFixed(1);
});

const submissionCount = computed(() => publishedGrades.value.length);
const excellentCount = computed(() => publishedGrades.value.filter(s => s >= 90).length);

const toggleExpand = (record) => {
  if (!record.ai_evaluation?.is_published) return;
  expandedId.value = expandedId.value === record.id ? null : record.id;
};

const formatTime = (t) => t ? new Date(t).toLocaleDateString() : '-';
const goToDetail = (record) => router.push(`/student/grades/detail/${record.id}`);

onMounted(fetchGrades);
</script>

<style scoped>
.expand-enter-active, .expand-leave-active { 
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); 
  max-height: 2000px;
  overflow: hidden; 
}
.expand-enter-from, .expand-leave-to { 
  max-height: 0; 
  opacity: 0; 
  transform: translateY(-5px); 
}

.frosted-card {
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.record-card {
  transition: transform 0.2s ease-out;
}

/* Markdown style modification */
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) {
  color: #1e3a8a;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 1.5rem;
  margin-bottom: 1rem;
  list-style: disc;
}

.markdown-body :deep(ol) {
  list-style: decimal;
}

.markdown-body :deep(li) {
  margin-bottom: 0.25rem;
}

.markdown-body :deep(strong) {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.05);
  padding: 0 2px;
  border-radius: 4px;
}

.markdown-body :deep(p) {
  margin-bottom: 0.75rem;
}

.markdown-body :deep(code) {
  background: #f1f5f9;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.85em;
}
</style>