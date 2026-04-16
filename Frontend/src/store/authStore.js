import { defineStore } from 'pinia';
import api from '../utils/request';
import { getToken, setToken, removeToken, getUser, setUser, removeUser } from '../utils/auth';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getToken(),
    user: getUser()
  }),
  actions: {
    /**
     * Log in Action
     * Format for adapting the backend return: Simply lay out access, role, username, and user_id directly.
     */
    async login(credentials) {
      try {
        const res = await api.post('/api/auth/login/', credentials);

        const token = res.access;

        const userData = {
          role: res.role,
          username: res.username,
          user_id: res.user_id,
          student_id: res.student_id
        };

        // Verify and persist
        if (token && userData.role) {
          this.token = token;
          this.user = userData;

          setToken(token);
          setUser(userData);

          console.log('%c[AuthStore] Login successful. The role is identified as: ' + userData.role, 'color: #4CAF50; font-weight: bold;');
          return res;
        } else {
          console.error('[AuthStore] Missing key fields:', res);
          throw new Error('The data returned by the backend is incomplete.');
        }
      } catch (error) {
        console.error('[AuthStore] Login Action Exception:', error);
        throw error;
      }
    },

    /**
     * Logout Action
     */
    logout() {
      this.token = null;
      this.user = null;
      removeToken();
      removeUser();
      localStorage.clear();
      sessionStorage.clear();
      window.location.href = '/login';
    },

    setUser(userData) {
    this.user = userData;
    localStorage.setItem('user', JSON.stringify(userData));
  }
  }
});