<template>
  <div class="space-y-6 animate-fade-in">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="frosted-card p-6 rounded-3xl border border-white/60 shadow-sm">
        <div class="flex items-center gap-4">
          <div class="p-3 bg-blue-50 text-blue-600 rounded-2xl"><Users size="24"/></div>
          <div>
            <p class="text-xs text-gray-500 font-bold uppercase tracking-wider">Students Analyzed (Best)</p>
            <p class="text-2xl font-black text-gray-800">{{ stats.count }} <span class="text-sm font-medium text-gray-400">submissions</span></p>
          </div>
        </div>
      </div>

      <div class="frosted-card p-6 rounded-3xl border border-white/60 shadow-sm">
        <div class="flex items-center gap-4">
          <div class="p-3 bg-emerald-50 text-emerald-600 rounded-2xl"><Trophy size="24"/></div>
          <div>
            <p class="text-xs text-gray-500 font-bold uppercase tracking-wider">Class Average</p>
            <p class="text-2xl font-black text-gray-800">{{ stats.average }} <span class="text-sm font-medium text-gray-400">pts</span></p>
          </div>
        </div>
      </div>

      <div class="frosted-card p-6 rounded-3xl border border-white/60 shadow-sm">
        <div class="flex items-center gap-4">
          <div class="p-3 bg-amber-50 text-amber-600 rounded-2xl"><Target size="24"/></div>
          <div>
            <p class="text-xs text-gray-500 font-bold uppercase tracking-wider">Weakest Knowledge Point</p>
            <p class="text-lg font-black text-amber-700">{{ weakestKp || 'Analyzing...' }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="frosted-card p-8 rounded-[2.5rem] border border-white/60 shadow-sm">
      <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
        <BarChart3 size="20" class="text-indigo-500" />
        Knowledge Point Mastery
      </h3>
      <div class="space-y-5">
        <div v-for="(score, name) in stats.kp_mastery" :key="name" class="space-y-2">
          <div class="flex justify-between items-end">
            <span class="text-sm font-bold text-gray-700">{{ name }}</span>
            <span class="text-xs font-black" :class="score < 60 ? 'text-red-500' : 'text-emerald-500'">{{ score }}%</span>
          </div>
          <el-progress 
            :percentage="score" 
            :stroke-width="12" 
            :color="score < 60 ? '#f87171' : '#10b981'"
            :show-text="false"
            class="custom-progress"
          />
        </div>
      </div>
    </div>

    <div v-if="aiInsights" class="bg-gradient-to-br from-indigo-600 to-blue-700 p-8 rounded-[2.5rem] text-white shadow-xl relative overflow-hidden">
      <div class="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
        <Sparkles size="120" />
      </div>

      <div class="relative z-10 space-y-6">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-white/20 backdrop-blur-md rounded-xl"><Lightbulb size="20"/></div>
          <h3 class="text-lg font-bold">AI Teaching Diagnosis</h3>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div class="space-y-4">
            <div class="bg-white/10 p-5 rounded-2xl border border-white/10">
              <p class="text-[10px] font-black uppercase tracking-widest text-indigo-200 mb-2">Overview</p>
              <p class="text-sm leading-relaxed text-indigo-50">{{ aiInsights.analysis }}</p>
            </div>
            <div class="bg-white/10 p-5 rounded-2xl border border-white/10">
              <p class="text-[10px] font-black uppercase tracking-widest text-emerald-300 mb-2">Strengths</p>
              <ul class="text-sm space-y-2">
                <li v-for="item in aiInsights.strengths" :key="item" class="flex items-start gap-2">
                  <CheckCircle2 size="14" class="mt-0.5 shrink-0 text-emerald-400" /> {{ item }}
                </li>
              </ul>
            </div>
          </div>

          <div class="space-y-4">
            <div class="bg-white/10 p-5 rounded-2xl border border-white/10">
              <p class="text-[10px] font-black uppercase tracking-widest text-rose-300 mb-2">Weaknesses</p>
              <ul class="text-sm space-y-2">
                <li v-for="item in aiInsights.weaknesses" :key="item" class="flex items-start gap-2">
                  <AlertTriangle size="14" class="mt-0.5 shrink-0 text-rose-400" /> {{ item }}
                </li>
              </ul>
            </div>
            <div class="bg-white/10 p-5 rounded-2xl border border-white/10">
              <p class="text-[10px] font-black uppercase tracking-widest text-amber-300 mb-2">Teaching Suggestions</p>
              <ul class="text-sm space-y-2">
                <li v-for="item in aiInsights.suggestions" :key="item" class="flex items-start gap-2">
                  <ArrowRightCircle size="14" class="mt-0.5 shrink-0 text-amber-400" /> {{ item }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { 
  Users, Trophy, Target, BarChart3, Lightbulb, Sparkles, 
  CheckCircle2, AlertTriangle, ArrowRightCircle 
} from 'lucide-vue-next';

// 接收父组件传入的聚合数据
const props = defineProps({
  stats: { type: Object, default: () => ({ count: 0, average: 0, kp_mastery: {} }) },
  aiInsights: { type: Object, default: null }
});

// 计算得分最低的知识点
const weakestKp = computed(() => {
  const mastery = props.stats.kp_mastery;
  const entries = Object.entries(mastery);
  if (entries.length === 0) return '';
  return entries.reduce((prev, curr) => prev[1] < curr[1] ? prev : curr)[0];
});
</script>

<style scoped>
.frosted-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(15px);
}
.custom-progress :deep(.el-progress-bar__outer) {
  background-color: rgba(0, 0, 0, 0.05) !important;
  border-radius: 10px;
}
.animate-fade-in {
  animation: fadeIn 0.6s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>