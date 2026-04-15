<template>
  <div class="space-y-6 animate-fade-in max-w-6xl mx-auto pt-2">
    <div class="mb-8">
      <h2 class="text-2xl font-bold text-gray-800 tracking-tight flex items-center gap-2">
        <BookOpen class="text-blue-600" size="24" /> My Courses
      </h2>
      <p class="text-sm text-gray-500 mt-1">Showing all enrolled courses and assignment status for this semester.</p>
    </div>

    <div v-if="loading" class="flex flex-col justify-center items-center py-20">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4"></div>
      <p class="text-gray-400 text-sm">Syncing your course schedule...</p>
    </div>

    <div v-else-if="courseList.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div 
        v-for="(course, index) in courseList" :key="course.id" 
        @click="router.push(`/student/assignments/course/${course.id}`)"
        class="frosted-card p-0 rounded-2xl overflow-hidden group border border-white/60 flex flex-col cursor-pointer hover:-translate-y-1 transition-all duration-300 shadow-sm hover:shadow-xl"
      >
        <div :class="['h-28 w-full relative overflow-hidden', colorPresets[index % colorPresets.length]]">
          <div class="absolute inset-0 bg-black/10 group-hover:bg-transparent transition-colors duration-300"></div>
          <div class="absolute bottom-4 left-4">
            <span class="text-xs font-mono font-bold bg-white/20 backdrop-blur-md text-white px-2 py-1 rounded border border-white/30">
              {{ course.code || 'COURSE' }}
            </span>
          </div>
        </div>
        
        <div class="p-6 flex-1 flex flex-col bg-white/40 backdrop-blur-sm">
          <h3 class="text-lg font-bold text-gray-800 leading-tight mb-4 group-hover:text-blue-600 transition-colors">
            {{ course.name }}
          </h3>
          
          <div class="mt-auto flex justify-between items-center text-sm">
            <span class="text-gray-500 flex items-center gap-1.5">
              <User size="14"/> {{ course.teacher_name || course.teacher?.username || 'Instructor' }}
            </span>
            
            <span v-if="course.pending > 0" class="bg-red-50 text-red-600 border border-red-200 px-2.5 py-1 rounded-lg font-bold text-xs flex items-center gap-1">
              <AlertCircle size="12" /> {{ course.pending }} Pending
            </span>
            <span v-else class="text-emerald-500 font-bold text-xs flex items-center gap-1">
              <CheckCircle2 size="14" /> Completed
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-20 bg-gray-50/50 rounded-2xl border-2 border-dashed border-gray-200">
      <div class="flex justify-center mb-4 text-gray-300">
        <BookOpen size="48" />
      </div>
      <p class="text-gray-400 font-medium">No course records found.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '../../utils/request'; 
import { BookOpen, User, AlertCircle, CheckCircle2 } from 'lucide-vue-next';

const router = useRouter();
const loading = ref(true);
const courseList = ref([]);

// Morandi color gradient presets
const colorPresets = [
  'bg-gradient-to-br from-blue-500 to-indigo-600',
  'bg-gradient-to-br from-emerald-500 to-teal-600',
  'bg-gradient-to-br from-orange-400 to-rose-500',
  'bg-gradient-to-br from-purple-500 to-pink-600',
  'bg-gradient-to-br from-cyan-500 to-blue-600'
];

/**
 * Fetch course and assignment data
 */
const fetchCourseData = async () => {
  try {
    loading.value = true;
    
    // Concurrent requests for courses and assignments
    const [coursesRes, assignmentsRes] = await Promise.all([
      api.get('/api/auth/student/courses/'), 
      api.get('/api/auth/student/assignments/')
    ]);

    const courses = coursesRes.data || coursesRes;
    const assignments = assignmentsRes.data || assignmentsRes;

    if (Array.isArray(courses)) {
      // Map pending assignment counts to respective courses
      courseList.value = courses.map(course => {
        const pendingCount = Array.isArray(assignments) 
          ? assignments.filter(a => {
              const aCourseId = (typeof a.course === 'object' && a.course !== null) ? a.course.id : a.course;
              return aCourseId === course.id && !a.is_submitted;
            }).length 
          : 0;

        return {
          ...course,
          pending: pendingCount
        };
      });
    }
  } catch (error) {
    console.error('Failed to fetch course data:', error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchCourseData();
});
</script>