import { defineStore } from 'pinia';
import api from '../utils/request';

export const useAssignmentStore = defineStore('assignment', {
  state: () => ({
    assignmentsList: [],
    currentAssignment: null
  }),
  actions: {
    async fetchAssignments() {
      const res = await api.get('/assignments');
      this.assignmentsList = res.data.results;
    },
    setCurrent(assign) {
      this.currentAssignment = assign;
    }
  }
});