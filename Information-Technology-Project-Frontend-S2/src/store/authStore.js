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
     * 登录 Action
     * 适配后端返回格式：直接平铺 access, role, username, user_id
     */
    async login(credentials) {
      try {
        const res = await api.post('/api/auth/login/', credentials);

        // 1. 核心修复：直接从响应根部提取字段
        // 截图显示字段名为 access, role, username, user_id
        const token = res.access;

        // 2. 手动构造 user 对象以便在权限守卫中使用
        const userData = {
          role: res.role,
          username: res.username,
          user_id: res.user_id,
          student_id: res.student_id // 截图显示的字段
        };

        // 3. 校验并持久化
        if (token && userData.role) {
          this.token = token;
          this.user = userData;

          setToken(token);
          setUser(userData);

          console.log('%c[AuthStore] 登录成功，角色识别为: ' + userData.role, 'color: #4CAF50; font-weight: bold;');
          return res;
        } else {
          console.error('[AuthStore] 关键字段缺失:', res);
          throw new Error('后端返回的数据不完整');
        }
      } catch (error) {
        console.error('[AuthStore] 登录 Action 异常:', error);
        throw error;
      }
    },

    /**
     * 登出 Action
     */
    logout() {
      this.token = null;
      this.user = null;
      removeToken();
      removeUser();
      // 彻底清理，防止路由守卫残留判断
      localStorage.clear();
      sessionStorage.clear();
      window.location.href = '/login';
    },

    setUser(userData) {
    this.user = userData;
    // 如果需要持久化到 localStorage
    localStorage.setItem('user', JSON.stringify(userData));
  }
  }
});