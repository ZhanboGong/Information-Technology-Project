import axios from 'axios';
import { ElMessage } from 'element-plus';
import { getToken } from './auth';

// 1. 设置为后端基础域名
// 这里不加 /api/auth/ 是为了在组件中更清晰地控制每一条请求路径
const BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 45000 // AI 相关请求较慢，设置为 45 秒
});

// 请求拦截器
api.interceptors.request.use(config => {
  const token = getToken();
  if (token) {
    // 确保符合 JWT 规范
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

// 响应拦截器
api.interceptors.response.use(
  response => {
    // 直接返回数据主体
    return response.data;
  },
  error => {
    const status = error.response?.status;
    const data = error.response?.data;

    // 调试辅助：在控制台打印最终失败的 URL，方便排查 404
    console.error(`Request Failed [${status}]:`, error.config.url);

    // 错误信息提取
    let msg = "Network error";
    if (data) {
      if (typeof data.detail === 'string') msg = data.detail;
      else if (typeof data.error === 'string') msg = data.error;
      else if (typeof data === 'object') {
        // 处理 Django 验证错误 (如 {"first_name": ["error message"]})
        const firstKey = Object.keys(data)[0];
        msg = Array.isArray(data[firstKey]) ? `${firstKey}: ${data[firstKey][0]}` : "Invalid parameters";
      }
    }

    ElMessage.error({
      message: msg,
      duration: 5000,
      showClose: true
    });

    if (status === 401) {
      localStorage.clear();
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;