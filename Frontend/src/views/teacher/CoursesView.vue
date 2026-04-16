<template>
  <div class="space-y-6 animate-fade-in max-w-[1400px] mx-auto pt-2 pb-20">
    
    <template v-if="!selectedCourse">
      <div class="flex justify-between items-end mb-6">
        <div>
          <h2 class="text-2xl font-bold text-gray-800 tracking-tight flex items-center gap-2">
            <Library class="text-blue-600" size="24" /> Course & Academic Management
          </h2>
          <p class="text-sm text-gray-500 mt-1">Manage your teaching courses, student lists, as well as publish and manage assignments</p>
        </div>
        <button 
          @click="showCreateCourseModal = true"
          class="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl font-bold shadow-lg hover:bg-blue-700 transition-all active:scale-95 text-sm"
        >
          <PlusCircle size="18" /> Create New Course
        </button>
      </div>

      <div v-if="isLoading" class="text-center py-10"><Loader2 class="animate-spin mx-auto text-blue-500" size="32"/></div>
      
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="course in courses" :key="course.id" class="frosted-card p-0 rounded-2xl overflow-hidden group hover:shadow-xl hover:-translate-y-1 transition-all border border-white/60 flex flex-col h-full cursor-pointer" @click="openCourseManagement(course)">
    <div class="h-3 bg-gradient-to-r from-blue-400 to-indigo-500"></div>
    <div class="p-6 flex-1 flex flex-col">
        <div class="flex justify-between items-start mb-3">
            <div class="flex-1">
                <h3 class="text-xl font-bold text-gray-800 group-hover:text-blue-700 transition-colors">{{ course.name }}</h3>

                <div class="flex items-center gap-2 mt-1.5">
                    <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Invite Code:</span>
                    <span
                        class="text-[11px] font-mono font-black px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded border border-indigo-100 hover:bg-indigo-600 hover:text-white transition-all shadow-sm flex items-center gap-1 group/code"
                        title="Click to copy code"
                        @click.stop="copyInviteCode(course.invite_code)"
                    >
                        {{ course.invite_code }}
                        <Copy size="10" class="opacity-40 group-hover/code:opacity-100" />
                    </span>
                </div>
            </div>

            <div class="flex flex-col items-end gap-1">
                <span class="text-xs font-mono bg-blue-50 text-blue-600 px-2 py-1 rounded border border-blue-100 shrink-0 ml-2">ID:{{ course.id }}</span>
            </div>
        </div>

        <p class="text-sm text-gray-500 line-clamp-2 leading-relaxed mb-6">{{ course.description || 'No course description available' }}</p>

        <div class="mt-auto">
            <div class="flex justify-between text-sm text-gray-600 font-medium bg-gray-50/50 p-3 rounded-xl border border-gray-100 mb-4">
                <span class="flex items-center gap-1.5"><Users size="16" class="text-blue-500"/> {{ course.student_count }} Enrolled</span>
                <span class="flex items-center gap-1.5"><Calendar size="16" class="text-gray-400"/> {{ formatDate(course.created_at) }}</span>
            </div>
            <button class="w-full py-2.5 bg-white border border-gray-200 text-gray-700 font-bold text-sm rounded-xl hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 transition shadow-sm flex justify-center items-center gap-2">
                <Settings2 size="16" /> Manage Course
            </button>
        </div>
    </div>
</div>
      </div>
    </template>

    <template v-else>
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-4">
          <button @click="resetToCourseList" class="p-2.5 frosted-card rounded-xl text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-all shadow-sm">
            <ArrowLeft size="20" />
          </button>
          <div>
            <h2 class="text-2xl font-bold text-gray-800 tracking-tight">{{ selectedCourse.name }}</h2>
          </div>
        </div>
      </div>

      <div class="flex gap-8 mb-6 border-b border-gray-200">
        <button @click="activeTab = 'students'" :class="activeTab === 'students' ? 'text-blue-600 border-b-2 border-blue-600 font-bold' : 'text-gray-500 hover:text-gray-800'" class="pb-3 text-sm flex items-center gap-2 transition-colors">
          <Users size="18"/> Student Management
        </button>
        <button @click="activeTab = 'assignments_list'" :class="activeTab === 'assignments_list' ? 'text-blue-600 border-b-2 border-blue-600 font-bold' : 'text-gray-500 hover:text-gray-800'" class="pb-3 text-sm flex items-center gap-2 transition-colors">
          <CheckSquare size="18"/> Published Assignments
        </button>
        <button @click="enterCreateMode" :class="activeTab === 'publish_assignment' ? 'text-blue-600 border-b-2 border-blue-600 font-bold' : 'text-gray-500 hover:text-gray-800'" class="pb-3 text-sm flex items-center gap-2 transition-colors">
          <FilePlus size="18"/> {{ isEditMode ? 'Editing Assignment' : 'Publish New Assignment' }}
        </button>
      </div>

      <div v-if="activeTab === 'publish_assignment'" class="animate-fade-in pb-20">
        <div class="frosted-card p-4 rounded-2xl border border-white/60 mb-8 flex justify-between items-center relative overflow-hidden">
          <div class="absolute top-1/2 left-10 right-10 h-1 bg-gray-200 -translate-y-1/2 z-0 rounded-full">
            <div class="h-full bg-blue-500 transition-all duration-500" :style="{ width: ((currentStep - 1) / 3) * 100 + '%' }"></div>
          </div>
          <div v-for="step in 4" :key="step" class="relative z-10 flex flex-col items-center w-32 cursor-pointer" @click="jumpToStep(step)">
            <div class="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 shadow-sm"
                 :class="currentStep >= step ? 'bg-blue-600 text-white shadow-blue-500/30' : 'bg-white border-2 border-gray-200 text-gray-400'">
              <Check v-if="currentStep > step" size="18" />
              <span v-else>{{ step }}</span>
            </div>
            <span class="text-xs font-bold mt-2" :class="currentStep >= step ? 'text-blue-800' : 'text-gray-400'">{{ stepTitles[step-1] }}</span>
          </div>
        </div>

        <div class="relative min-h-[400px]">
          <div v-if="currentStep === 1" class="space-y-6">
            <div class="frosted-card p-8 rounded-2xl border border-white/60 space-y-5">
                 <div v-if="isEditMode" class="p-3 bg-amber-50 border border-amber-100 rounded-xl text-xs text-amber-700 font-bold mb-2">
                    Editing Assignment Mode: Changes will overwrite existing data.
                 </div>
                 <div>
                   <label class="block text-xs font-bold text-gray-600 mb-1.5">Assignment Title *</label>
                   <input v-model="form.title" type="text" class="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none">
                 </div>
                 <div>
                   <label class="block text-xs font-bold text-gray-600 mb-1.5">Deadline *</label>
                   <el-date-picker v-model="form.deadline" type="datetime" class="w-full" placeholder="Select deadline" value-format="YYYY-MM-DDTHH:mm:ssZ"/>
                 </div>
                 <div>
                   <label class="block text-xs font-bold text-gray-600 mb-1.5">Programming Language *</label>
                   <el-select v-model="form.category" class="w-full">
                     <el-option label="Python" value="python" />
                     <el-option label="Java" value="java" />
                   </el-select>
                 </div>
                 <div>
                   <label class="block text-xs font-bold text-gray-600 mb-1.5">Assignment Content & Requirements *</label>
                   <textarea v-model="form.content" class="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm h-32 resize-none outline-none"></textarea>
                 </div>
                 <div class="pt-2 border-t border-gray-100">
                    <label class="block text-xs font-bold text-gray-600 mb-1.5">Assignment Attachment (Optional)</label>
                    <el-upload
                      class="attachment-uploader"
                      action="#"
                      :auto-upload="false"
                      :limit="1"
                      :on-change="handleFileChange"
                      :on-remove="handleFileRemove"
                      :file-list="fileList"
                    >
                      <template #trigger>
                        <button class="flex items-center gap-2 px-4 py-2 bg-white border border-dashed border-gray-300 rounded-xl text-xs text-gray-600 hover:border-blue-500 hover:text-blue-600 transition-all">
                          <UploadCloud size="16" /> {{ form.attachment ? 'Replace Reference File' : 'Select Reference File' }}
                        </button>
                      </template>
                    </el-upload>
                 </div>
            </div>
          </div>

          <div v-if="currentStep === 2" class="space-y-6">
            <div class="frosted-card p-8 rounded-2xl border border-white/60">
              <div class="flex justify-between items-center mb-6">
                <div>
                  <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
                    <ClipboardCheck class="text-emerald-500" size="20" /> Performance Standards Matrix
                  </h3>
                </div>
                <div class="text-2xl font-black px-4 py-2 bg-gray-50 rounded-xl border border-gray-100" :class="rubricTotal === 100 ? 'text-green-500' : 'text-red-500'">
                  {{ rubricTotal }}% <span class="text-sm font-normal text-gray-400">/ 100%</span>
                </div>
              </div>

              <div class="space-y-10">
                <div v-for="(item, idx) in form.rubric_config.items" :key="idx" class="relative p-6 bg-white/50 border border-gray-200 rounded-3xl shadow-sm group">
                  <button @click="form.rubric_config.items.splice(idx, 1)" class="absolute -top-3 -right-3 p-2 bg-red-50 text-red-500 rounded-full border border-red-100 hover:bg-red-500 hover:text-white transition-colors z-10">
                    <X size="16" />
                  </button>
                  <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
                    <div class="md:col-span-3">
                      <label class="block text-[10px] font-black text-gray-400 uppercase mb-2 tracking-widest">Dimension Title</label>
                      <input v-model="item.criterion" class="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm font-bold focus:border-blue-500 outline-none">
                    </div>
                    <div>
                      <label class="block text-[10px] font-black text-gray-400 uppercase mb-2 tracking-widest">Weight (%)</label>
                      <el-input-number v-model="item.weight" :min="0" :max="100" class="w-full custom-number-input" controls-position="right" />
                    </div>
                  </div>

                  <div class="grid grid-cols-1 lg:grid-cols-5 gap-3 pt-6 border-t border-dashed border-gray-200">
                    <div v-for="level in gradeLevels" :key="level" class="space-y-2">
                      <div class="flex items-center gap-1.5 px-1">
                        <div class="w-1.5 h-1.5 rounded-full" :class="getLevelColor(level)"></div>
                        <span class="text-[9px] font-black text-gray-500 uppercase truncate">{{ level }}</span>
                      </div>
                      <textarea v-model="item.detailed_rubric[level]" class="w-full bg-gray-50/50 border border-gray-100 rounded-xl p-3 text-[11px] h-36 focus:bg-white outline-none leading-relaxed transition-all"></textarea>
                    </div>
                  </div>
                </div>
                <button @click="addNewCriterion" class="w-full py-8 border-2 border-dashed border-gray-200 text-gray-400 rounded-3xl font-bold hover:bg-blue-50 transition-all flex flex-col items-center justify-center gap-2">
                  <FilePlus size="28" />
                  <span>Add New Dimension</span>
                </button>
              </div>
            </div>
          </div>

          <div v-if="currentStep === 3" class="space-y-6">
            <div class="frosted-card p-8 rounded-2xl border border-white/60">
              <div class="space-y-6">
                <div>
                  <div class="flex justify-between items-end mb-3">
                    <label class="block text-sm font-bold text-blue-800">Knowledge Points Configuration (L1/L2)</label>
                    <div class="flex gap-2">
                        <button
                          @click="showManualKPModal = true"
                          class="flex items-center gap-2 px-4 py-1.5 bg-emerald-50 text-emerald-600 rounded-lg text-xs font-black border border-emerald-100 hover:bg-emerald-600 hover:text-white transition-all shadow-sm"
                        >
                          <PlusCircle size="14" /> Add Manually
                        </button>
                        <button
                          @click="getAIKPSuggestions"
                          :disabled="isGeneratingKP"
                          class="flex items-center gap-2 px-4 py-1.5 bg-indigo-50 text-indigo-600 rounded-lg text-xs font-black hover:bg-indigo-600 hover:text-white transition-all disabled:opacity-50 shadow-sm"
                        >
                          <Sparkles size="14" v-if="!isGeneratingKP" />
                          <Loader2 size="14" class="animate-spin" v-else />
                          AI Suggest Points
                        </button>
                    </div>
                  </div>
                  <el-select v-model="form.knowledge_points" multiple filterable placeholder="Select Knowledge Points" class="w-full">
                    <el-option v-for="item in kpOptions" :key="item.id" :label="item.name" :value="item.id"></el-option>
                  </el-select>
                </div>

                <div v-if="aiSuggestions.length > 0" class="p-6 bg-amber-50/40 border border-amber-200 rounded-2xl animate-fade-in space-y-4">
                  <h4 class="text-xs font-black text-amber-700 uppercase flex items-center gap-2 tracking-widest">
                     <Zap size="16" class="text-amber-500" /> AI Recommended L2 Skills:
                  </h4>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div v-for="(kp, i) in aiSuggestions" :key="i" class="bg-white p-4 rounded-xl border border-amber-100 shadow-sm hover:border-amber-400 transition-all">
                      <div class="flex justify-between items-start mb-2">
                        <span class="font-bold text-gray-800 text-sm">{{ kp.name }}</span>
                        <button @click="addToCourseKPs(kp)" class="text-[10px] bg-amber-600 text-white px-2.5 py-1 rounded-full font-black uppercase tracking-tighter hover:bg-amber-700">Add & Link</button>
                      </div>
                      <p class="text-[11px] text-gray-500 leading-relaxed">{{ kp.description }}</p>
                    </div>
                  </div>
                </div>

                <div class="p-6 bg-indigo-50 rounded-2xl border border-indigo-100 flex items-start gap-4">
                  <div class="p-2 bg-white rounded-xl shadow-sm text-indigo-600"><Check size="20" /></div>
                  <div>
                    <p class="text-md font-bold text-indigo-900 tracking-tight">AI Grading Logic Syncing Enabled</p>
                    <p class="text-sm text-indigo-700 mt-1 leading-relaxed">选中的 L1/L2 知识点将作为 AI 批改的核心参考维度。</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentStep === 4" class="frosted-card p-12 rounded-2xl border border-white/60 text-center">
              <h3 class="text-2xl font-bold mb-6 text-gray-800">{{ isEditMode ? 'Update Assignment' : 'Confirm Publish' }}</h3>
              <div class="flex items-center justify-center gap-4 text-gray-600 mb-8 font-bold">
                  Max Attempts: <el-input-number v-model="form.max_attempts" :min="1" />
              </div>
              <button @click="handleFinalPublish" :disabled="isSubmitting" class="px-12 py-4 bg-blue-600 text-white rounded-2xl font-black flex items-center justify-center gap-2 mx-auto shadow-lg hover:scale-105 transition-all">
                <Loader2 v-if="isSubmitting" class="animate-spin" /> {{ isSubmitting ? 'Processing...' : (isEditMode ? 'Confirm & Update' : 'Confirm & Publish') }}
              </button>
          </div>
        </div>

        <div class="fixed bottom-0 left-64 right-0 p-6 bg-white/80 backdrop-blur-md border-t flex justify-between z-40">
          <button @click="currentStep--" :disabled="currentStep === 1" class="px-8 py-2.5 bg-gray-100 text-gray-600 rounded-xl font-bold disabled:opacity-50">Previous</button>
          <button v-if="currentStep < 4" @click="handleNext" class="px-10 py-2.5 bg-blue-600 text-white rounded-xl font-bold shadow-lg shadow-blue-100">Next Step</button>
        </div>
      </div>

      <div v-if="activeTab === 'students'" class="animate-fade-in space-y-4">
        <div class="flex justify-between items-center mb-2">
          <div class="flex items-center gap-3">
            <div class="relative group w-64">
                <Search size="16" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
                <input v-model="searchQuery" type="text" placeholder="Search..." class="w-full bg-white border border-gray-200 rounded-xl pl-10 pr-4 py-2 text-sm focus:border-blue-400 outline-none transition-all">
            </div>
          </div>
          <button @click="showImportModal = true" class="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl text-sm font-bold shadow-md transition-all flex items-center gap-2 hover:scale-105">
              <UploadCloud size="16" /> Import Students
          </button>
        </div>
        <div v-if="isStudentsLoading" class="text-center py-10"><Loader2 class="animate-spin mx-auto text-blue-500" size="32"/></div>
        <div v-else class="frosted-card rounded-2xl border border-white/60 overflow-hidden bg-white/60">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-gray-50/80 border-b border-gray-100 text-xs font-bold text-gray-500 uppercase tracking-wider">
                  <th class="p-4 w-12 text-center"><input type="checkbox" :checked="isAllSelected" @change="toggleAll" class="w-4 h-4 rounded cursor-pointer"></th>
                  <th class="p-4">Name / ID</th>
                  <th class="p-4 text-center">Class</th>
                  <th class="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="text-sm divide-y divide-gray-100/80">
                <tr v-for="stu in filteredStudents" :key="stu.id" class="hover:bg-blue-50/40 group transition-colors">
                  <td class="p-4 text-center"><input type="checkbox" :value="stu.id" v-model="selectedStudentIds" class="w-4 h-4 rounded cursor-pointer"></td>
                  <td class="p-4">
                    <div class="font-bold text-gray-800">{{ stu.name || stu.username }}</div>
                    <div class="text-xs font-mono text-gray-500">{{ stu.student_id_num || 'N/A' }}</div>
                  </td>
                  <td class="p-4 text-center"><span class="bg-indigo-50 text-indigo-600 px-2 py-1 rounded text-[10px] font-bold">{{ stu.class_name || '--' }}</span></td>
                  <td class="p-4 text-right"><button @click="removeSingleStudent(stu)" class="p-1.5 text-red-400 hover:text-red-600 rounded-lg transition-colors"><UserMinus size="18"/></button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'assignments_list'" class="animate-fade-in space-y-4 pb-20">
        <div v-if="isAssignmentsLoading" class="text-center py-10"><Loader2 class="animate-spin mx-auto text-blue-500" size="32"/></div>
        <div v-else-if="courseAssignments.length === 0" class="p-10 text-center text-gray-400 bg-white/50 rounded-2xl border border-dashed border-gray-200 flex flex-col items-center">
            <Inbox size="48" class="text-gray-300 mb-4" />
            <p>No assignments published yet.</p>
        </div>
        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div v-for="assign in courseAssignments" :key="assign.id"
               class="frosted-card p-6 rounded-2xl border border-white/60 hover:shadow-lg transition-all bg-white flex flex-col justify-between group">
            <div>
              <div class="flex justify-between items-start mb-2">
                <h3 class="text-lg font-bold text-gray-800 group-hover:text-blue-600 transition-colors">{{ assign.title }}</h3>
                <div class="flex gap-2">
                    <button @click="handleEditAssignment(assign)" class="p-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-600 hover:text-white transition-all shadow-sm">
                        <Edit size="14" />
                    </button>
                    <span class="px-2 py-1 bg-gray-100 text-gray-500 text-[10px] font-bold rounded uppercase tracking-wider">{{ assign.category }}</span>
                </div>
              </div>
              <p class="text-sm text-gray-500 line-clamp-2 mb-2 leading-relaxed italic">"{{ assign.content }}"</p>
              <div v-if="assign.attachment" class="flex items-center gap-1.5 text-[10px] text-blue-600 font-bold mb-4 bg-blue-50 w-fit px-2 py-1 rounded">
                <Paperclip size="12" /> Has Attachment
              </div>
            </div>
            <div @click="viewAssignmentDetail(assign)" class="flex items-center justify-between pt-4 border-t border-gray-100 text-sm text-gray-500 font-medium cursor-pointer hover:bg-gray-50 transition-colors">
              <span>Due: {{ formatDate(assign.deadline) }}</span>
              <span class="flex items-center gap-1 text-blue-500 font-bold">Detail <ChevronRight size="14"/></span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <el-dialog v-model="showCreateCourseModal" title="Add New Teaching Course" width="500px" rounded-2xl>
        <div class="space-y-5 p-2 text-left">
            <div>
                <label class="text-[10px] font-black text-gray-400 uppercase mb-2 block tracking-widest ml-1">Course Title *</label>
                <el-input v-model="courseCreateForm.name" placeholder="e.g., Software Engineering 2026" />
            </div>
            <div>
                <label class="text-[10px] font-black text-gray-400 uppercase mb-2 block tracking-widest ml-1">Description</label>
                <el-input v-model="courseCreateForm.description" type="textarea" :rows="4" placeholder="Course objectives..." />
            </div>
            <div class="flex justify-end gap-3 pt-4">
                <el-button @click="showCreateCourseModal = false" class="rounded-xl font-bold">Cancel</el-button>
                <el-button type="primary" color="#2563eb" @click="handleCreateCourse" :loading="isCourseCreating" class="rounded-xl font-bold shadow-lg shadow-blue-100">
                    Create Course
                </el-button>
            </div>
        </div>
    </el-dialog>

    <el-dialog v-model="showManualKPModal" title="Create Knowledge Point (L2)" width="400px" rounded-2xl>
        <div class="space-y-4 p-2 text-left">
            <div>
                <label class="text-[10px] font-bold text-gray-400 uppercase ml-1">Name</label>
                <el-input v-model="kpManualForm.name" placeholder="e.g., Object Oriented Design" />
            </div>
            <div>
                <label class="text-[10px] font-bold text-gray-400 uppercase ml-1">Logic Description</label>
                <el-input v-model="kpManualForm.description" type="textarea" :rows="4" placeholder="Explain the grading logic..." />
            </div>
            <div class="flex justify-end gap-2 pt-2">
                <el-button @click="showManualKPModal = false">Cancel</el-button>
                <el-button type="primary" color="#2563eb" @click="handleManualCreateKP" :loading="isManualKPSaving">Save & Select</el-button>
            </div>
        </div>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="Assignment Performance Matrix" width="85%" destroy-on-close class="assignment-detail-dialog">
      <div v-if="selectedAssignment" class="space-y-6 p-2">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="p-4 bg-blue-50/50 rounded-2xl border border-blue-100">
            <p class="text-[10px] font-black text-blue-400 uppercase mb-1">Title</p>
            <p class="text-sm font-bold text-gray-800">{{ selectedAssignment.title }}</p>
          </div>
          <div class="p-4 bg-purple-50/50 rounded-2xl border border-purple-100">
            <p class="text-[10px] font-black text-purple-400 uppercase mb-1">Deadline</p>
            <p class="text-sm font-bold text-gray-800">{{ formatDate(selectedAssignment.deadline) }}</p>
          </div>
          <div class="p-4 bg-orange-50/50 rounded-2xl border border-orange-100">
            <p class="text-[10px] font-black text-orange-400 uppercase mb-1">Attempts</p>
            <p class="text-sm font-bold text-gray-800">{{ selectedAssignment.max_attempts }} Times</p>
          </div>
        </div>
        <div class="p-5 rounded-2xl bg-gray-50/50 border border-gray-100">
          <h4 class="text-xs font-black text-gray-400 uppercase mb-2 flex items-center gap-2"><FilePlus size="14"/> Requirements</h4>
          <p class="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">{{ selectedAssignment.content }}</p>
        </div>
        <section v-if="matrixData.length > 0">
          <div class="flex items-center gap-2 mb-4 px-1">
            <ClipboardCheck size="18" class="text-emerald-500" />
            <p class="text-[14px] font-black text-gray-800 uppercase tracking-widest">Standards Matrix View</p>
          </div>
          <el-table :data="matrixData" border stripe class="rubric-matrix-table shadow-sm">
            <el-table-column label="Grade Level" width="200" fixed="left">
              <template #default="scope">
                <el-tag :type="getGradeTag(scope.row.grade)" effect="dark" class="font-bold w-full text-center">{{ scope.row.grade }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column v-for="col in matrixColumns" :key="col.prop" :min-width="280">
              <template #header>
                <div class="flex flex-col py-1">
                  <span class="text-gray-800 font-bold leading-tight">{{ col.label }}</span>
                  <span class="text-[10px] text-blue-500 font-black mt-1">WEIGHT: {{ col.weight }}%</span>
                </div>
              </template>
              <template #default="scope">
                <div class="p-1 text-[11px] text-gray-600 whitespace-pre-wrap">{{ scope.row[col.prop] || '--' }}</div>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </div>
    </el-dialog>

    <div v-if="showImportModal" class="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4">
        <div class="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl relative animate-fade-in">
            <button @click="showImportModal = false" class="absolute top-6 right-6 text-gray-400 hover:text-gray-600"><X size="24" /></button>
            <h3 class="text-xl font-bold mb-4 flex items-center gap-3"><FileSpreadsheet class="text-emerald-600" size="28" /> Student Import</h3>

            <div class="bg-gray-50 p-4 rounded-2xl border border-gray-100 mb-6">
              <p class="text-xs text-gray-500 mb-3">Please use the standard template for batch enrollment:</p>
              <button @click="handleDownloadTemplate" class="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-xs font-bold text-gray-700 hover:bg-emerald-50 hover:text-emerald-600 hover:border-emerald-100 transition-all shadow-sm">
                <Download size="14" /> Download Template (.xlsx)
              </button>
            </div>

            <div class="flex justify-end gap-4">
                <button @click="showImportModal = false" class="px-6 py-3 text-gray-500 font-bold">Cancel</button>
                <input type="file" ref="fileInput" @change="handleImportStudents" class="hidden" accept=".xlsx, .xls, .csv" />
                <button @click="$refs.fileInput.click()" :disabled="isImporting" class="px-8 py-3 bg-emerald-500 text-white font-bold rounded-2xl shadow-lg shadow-emerald-100 flex items-center gap-2">
                    <Loader2 v-if="isImporting" size="18" class="animate-spin" />
                    {{ isImporting ? 'Processing...' : 'Select File' }}
                </button>
            </div>
        </div>
    </div>

  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox} from 'element-plus';
import { ref, reactive, computed, onMounted } from 'vue';
import api from '../../utils/request';
import {
  Library, Users, Calendar, Settings2, ArrowLeft, UploadCloud,
  FilePlus, CheckSquare, Check, X, Loader2, Clock, Inbox, Search,
  UserMinus, FileSpreadsheet, ClipboardCheck, Paperclip, Download,
  Sparkles, Zap, Edit, ChevronRight, PlusCircle, Copy
} from 'lucide-vue-next';

const isLoading = ref(false);
const courses = ref([]);
const selectedCourse = ref(null);
const activeTab = ref('students');
const courseStudents = ref([]);
const isStudentsLoading = ref(false);
const searchQuery = ref('');
const selectedStudentIds = ref([]);
const isAssignmentsLoading = ref(false);
const courseAssignments = ref([]);

// Course creation-related status
const showCreateCourseModal = ref(false);
const isCourseCreating = ref(false);
const courseCreateForm = reactive({ name: '', description: '' });

// Core operation mode control
const isEditMode = ref(false);
const editingId = ref(null);

const currentStep = ref(1);
const stepTitles = ['Basic Info', 'Rubric Matrix', 'Knowledge & AI', 'Confirm'];
const kpOptions = ref([]);
const isSubmitting = ref(false);
const fileList = ref([]);
const showImportModal = ref(false);
const isImporting = ref(false);

const isGeneratingKP = ref(false);
const aiSuggestions = ref([]);

// Manually add KP status
const showManualKPModal = ref(false);
const isManualKPSaving = ref(false);
const kpManualForm = reactive({ name: '', description: '' });

const detailVisible = ref(false);
const selectedAssignment = ref(null);
const matrixData = ref([]);
const matrixColumns = ref([]);

const gradeLevels = ["High Distinction (85-100%)", "Distinction (75-84%)", "Credit (65-74%)", "Pass (50-64%)", "Fail (0-49%)"];

const form = reactive({
  title: '',
  content: '',
  course: '',
  deadline: '',
  knowledge_points: [],
  rubric_config: {
    items: [
      {
        criterion: "Algorithm & Logic",
        weight: 100,
        description: "Assess core business logic and efficiency.",
        detailed_rubric: { "High Distinction (85-100%)": "", "Distinction (75-84%)": "", "Credit (65-74%)": "", "Pass (50-64%)": "", "Fail (0-49%)": "" }
      }
    ]
  },
  max_attempts: 3,
  category: 'python',
  attachment: null
});

const copyInviteCode = (code) => {
  if (!code) return;

  navigator.clipboard.writeText(code).then(() => {
    ElMessage({
      message: 'Invite code copied to clipboard!',
      type: 'success',
      plain: true,
      duration: 2000
    });
  }).catch(() => {
    ElMessage.error('Failed to copy code');
  });
};

const rubricTotal = computed(() => {
  if (!form.rubric_config.items) return 0;
  return form.rubric_config.items.reduce((sum, item) => sum + (item.weight || 0), 0);
});

const filteredStudents = computed(() => {
  if (!searchQuery.value) return courseStudents.value;
  return courseStudents.value.filter(s =>
    (s.name || s.username || '').toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    (s.student_id_num || '').includes(searchQuery.value)
  );
});

const isAllSelected = computed(() => filteredStudents.value.length > 0 && selectedStudentIds.value.length === filteredStudents.value.length);


// Handling course creation
const handleCreateCourse = async () => {
    if (!courseCreateForm.name) return ElMessage.warning('Course Title is mandatory');
    isCourseCreating.value = true;
    try {
        await api.post('/api/auth/teacher/courses/', {
            name: courseCreateForm.name,
            description: courseCreateForm.description
        });
        ElMessage.success('Course established successfully!');
        showCreateCourseModal.value = false;
        courseCreateForm.name = ''; courseCreateForm.description = '';
        fetchCourses();
    } catch (e) {
        ElMessage.error('Establishment failed');
    } finally {
        isCourseCreating.value = false;
    }
};

// Download and import template logic
const handleDownloadTemplate = async () => {
  try {
    const response = await api.get('/api/auth/teacher/students/download-template/', { responseType: 'blob' });
    const blob = new Blob([response], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.download = "student_import_template.xlsx";
    link.click();
    window.URL.revokeObjectURL(link.href);
    ElMessage.success('Template download started');
  } catch (e) {
    ElMessage.error('Download failed');
  }
};



// Fill in the data and enter the editing mode
const handleEditAssignment = (assign) => {
  isEditMode.value = true;
  editingId.value = assign.id;
  activeTab.value = 'publish_assignment';
  currentStep.value = 1;
  
  // Echoing basic data
  form.title = assign.title;
  form.content = assign.content;
  form.deadline = assign.deadline;
  form.category = assign.category;
  form.max_attempts = assign.max_attempts;
  form.course = assign.course.id || assign.course;
  
  // Process the list of knowledge point IDs (make sure to extract only the IDs)
  if (assign.knowledge_points) {
      form.knowledge_points = assign.knowledge_points.map(kp => typeof kp === 'object' ? kp.id : kp);
  } else {
      form.knowledge_points = [];
  }
  
  // Echo standard matrix
  if (assign.rubric_config) {
      form.rubric_config = JSON.parse(JSON.stringify(assign.rubric_config));
  }
  
  // The attachment shows the reset operation.
  fileList.value = assign.attachment ? [{ name: assign.attachment_name || 'Current Attachment', url: assign.attachment }] : [];
  // Reset the attachment object in the form, unless the user uploads a new file
  form.attachment = null;
};

// Create mode reset
const enterCreateMode = () => {
    isEditMode.value = false;
    editingId.value = null;
    activeTab.value = 'publish_assignment';
    currentStep.value = 1;
    // Reset the form
    Object.assign(form, {
        title: '', content: '', deadline: '', knowledge_points: [], attachment: null,
        rubric_config: { items: [{ criterion: "Algorithm & Logic", weight: 100, description: "", detailed_rubric: {} }] }
    });
    fileList.value = [];
};

// Manually add KP
const handleManualCreateKP = async () => {
    if (!kpManualForm.name || !kpManualForm.description) return ElMessage.warning('Incomplete form');
    isManualKPSaving.value = true;
    try {
        const res = await api.post('/api/auth/knowledge-points/', {
            name: kpManualForm.name,
            description: kpManualForm.description,
            category: 'L2',
            course: selectedCourse.value.id,
            language: form.category
        });
        kpOptions.value.push(res);
        form.knowledge_points.push(res.id);
        showManualKPModal.value = false;
        kpManualForm.name = ''; kpManualForm.description = '';
        ElMessage.success('KP Created and Linked');
    } catch (e) { ElMessage.error('Create failed'); }
    finally { isManualKPSaving.value = false; }
};

const getAIKPSuggestions = async () => {
  if (!form.content) return ElMessage.warning('Assignment content is required');
  isGeneratingKP.value = true;
  aiSuggestions.value = [];
  try {
    const res = await api.post('/api/auth/teacher/assignments/suggest-kps/', {
      title: form.title, content: form.content, language: form.category,
      course_id: selectedCourse.value.id, rubric_config: form.rubric_config 
    });
    aiSuggestions.value = res.suggested_kps || [];
    ElMessage.success('AI recommendations ready!');
  } catch (e) { ElMessage.error('AI analysis failed.'); }
  finally { isGeneratingKP.value = false; }
};

const addToCourseKPs = async (kp) => {
  if (kp.id) {
    if (!form.knowledge_points.includes(kp.id)) {
        form.knowledge_points.push(kp.id);
        if (!kpOptions.value.find(o => o.id === kp.id)) kpOptions.value.push(kp);
    }
    aiSuggestions.value = aiSuggestions.value.filter(item => item.name !== kp.name);
    return ElMessage.success(`Linked: ${kp.name}`);
  }
};

const handleFinalPublish = async () => {
  if (rubricTotal.value !== 100) return ElMessage.error('Total weight must equal 100%');
  isSubmitting.value = true;
  try {
    const finalRubric = { items: form.rubric_config.items.filter(i => i.criterion.trim() !== '') };
    const formData = new FormData();
    formData.append('title', form.title);
    formData.append('content', form.content);
    formData.append('course', selectedCourse.value.id);
    formData.append('deadline', form.deadline);
    formData.append('max_attempts', form.max_attempts);
    formData.append('category', form.category);
    formData.append('rubric_config', JSON.stringify(finalRubric));
    formData.append('reference_logic', JSON.stringify(finalRubric));
    formData.append('knowledge_points', JSON.stringify(form.knowledge_points));

    if (form.attachment instanceof File) {
      formData.append('attachment', form.attachment);
    }

    const url = isEditMode.value ? `/api/auth/teacher/assignments/${editingId.value}/` : '/api/auth/teacher/assignments/';
    const method = isEditMode.value ? 'patch' : 'post';

    await api[method](url, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    ElMessage.success(isEditMode.value ? 'Assignment updated!' : 'Assignment published!');
    activeTab.value = 'assignments_list';
    fetchCourseAssignments(selectedCourse.value.id);
  } catch (e) { ElMessage.error('Publication/Update failed'); }
  finally { isSubmitting.value = false; }
};

const handleFileChange = (file) => { form.attachment = file.raw; };
const handleFileRemove = () => { form.attachment = null; };
const jumpToStep = (step) => { if (step <= currentStep.value || isEditMode.value) currentStep.value = step; };
const handleNext = () => {
  if (currentStep.value === 1 && (!form.title || !form.deadline || !form.content)) return ElMessage.warning('Required fields missing');
  if (currentStep.value === 2 && rubricTotal.value !== 100) return ElMessage.error('Total weight must equal 100%');
  currentStep.value++;
};
const addNewCriterion = () => {
  form.rubric_config.items.push({
    criterion: "", weight: 0, description: "",
    detailed_rubric: { "High Distinction (85-100%)": "", "Distinction (75-84%)": "", "Credit (65-74%)": "", "Pass (50-64%)": "", "Fail (0-49%)": "" }
  });
};
const resetToCourseList = () => { selectedCourse.value = null; isEditMode.value = false; fetchCourses(); };
const openCourseManagement = (course) => {
  selectedCourse.value = course;
  activeTab.value = 'students'; 
  form.course = course.id; 
  currentStep.value = 1;
  fetchCourseStudents(course.id);
  fetchCourseAssignments(course.id);
};
const fetchCourses = async () => {
  isLoading.value = true;
  try {
    const res = await api.get('/api/auth/teacher/courses/');
    courses.value = res.results || res;
  } catch (error) { ElMessage.error('Failed to load courses'); }
  finally { isLoading.value = false; }
};
const fetchCourseStudents = async (id) => {
  isStudentsLoading.value = true;
  try {
    const res = await api.get(`/api/auth/teacher/courses/${id}/students/`);
    courseStudents.value = res.results || res || [];
  } catch (e) { ElMessage.error('Failed to load students'); }
  finally { isStudentsLoading.value = false; }
};
const fetchCourseAssignments = async (id) => {
  isAssignmentsLoading.value = true;
  try {
    const res = await api.get('/api/auth/teacher/assignments/');
    const allData = res.results || res;
    courseAssignments.value = allData.filter(a => (typeof a.course === 'object' ? a.course.id : a.course) === id);
  } catch (e) { ElMessage.error('Failed to load assignments'); }
  finally { isAssignmentsLoading.value = false; }
};
const fetchGlobalKnowledgePoints = async () => {
  try {
      const kpRes = await api.get('/api/auth/knowledge-points/');
      kpOptions.value = kpRes.results || kpRes;
  } catch (e) {}
};
const handleImportStudents = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  isImporting.value = true;
  const formData = new FormData();
  formData.append('file', file);
  formData.append('course_id', selectedCourse.value.id);
  try {
    const res = await api.post('/api/auth/teacher/students/import-students/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    ElMessageBox.alert(res.message || 'Import Success', 'Result', { confirmButtonText: 'OK', type: 'success' });
    showImportModal.value = false;
    fetchCourseStudents(selectedCourse.value.id);
  } catch (err) { ElMessage.error(err.response?.data?.error || 'Failed'); }
  finally { isImporting.value = false; }
};
const removeSingleStudent = async (stu) => {
  try {
    await ElMessageBox.confirm(`Remove ${stu.name || stu.username}?`, 'Warning', { type: 'warning' });
    await api.post(`/api/auth/teacher/courses/${selectedCourse.value.id}/remove-students/`, { student_ids: [stu.id] });
    ElMessage.success('Removed');
    fetchCourseStudents(selectedCourse.value.id);
  } catch (e) {}
};
const toggleAll = (e) => { selectedStudentIds.value = e.target.checked ? filteredStudents.value.map(s => s.id) : []; };
const viewAssignmentDetail = (assign) => {
  selectedAssignment.value = assign;
  const rubric = assign.rubric_config;
  if (rubric?.items?.length > 0) {
    matrixColumns.value = rubric.items.map((item, index) => ({ label: item.criterion, weight: item.weight, prop: `criterion_${index}` }));
    matrixData.value = gradeLevels.map(level => {
      const row = { grade: level };
      rubric.items.forEach((item, index) => { row[`criterion_${index}`] = item.detailed_rubric?.[level] || ''; });
      return row;
    });
  }
  detailVisible.value = true;
};
const formatDate = (dateStr) => { if (!dateStr) return ''; const d = new Date(dateStr); return d.toLocaleString(); };
const getLevelColor = (level) => level.includes('High') ? 'bg-emerald-500' : level.includes('Distinction') ? 'bg-teal-400' : level.includes('Credit') ? 'bg-blue-400' : level.includes('Pass') ? 'bg-orange-400' : 'bg-red-400';
const getGradeTag = (grade) => grade.includes('High') ? 'success' : grade.includes('Distinction') ? 'primary' : grade.includes('Credit') ? '' : grade.includes('Pass') ? 'warning' : 'danger';

onMounted(() => {
  fetchCourses();
  fetchGlobalKnowledgePoints();
});
</script>

<style scoped>
.frosted-card { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); }
.animate-fade-in { animation: fadeIn 0.4s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.custom-number-input :deep(.el-input__wrapper) { border-radius: 12px; }
.rubric-matrix-table :deep(.el-table__header) { background-color: #f8fafc; }
:deep(.assignment-detail-dialog) { border-radius: 24px; overflow: hidden; backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.9); }
.attachment-uploader :deep(.el-upload-list) { margin-top: 8px; }
</style>