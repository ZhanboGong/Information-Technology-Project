import axios from 'axios';
import { ElMessage } from 'element-plus';
import { getToken } from './auth';

// 1. Set as the backend base domain name
const BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 45000
});

// Request interceptor
api.interceptors.request.use(config => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

// Response interceptor
api.interceptors.response.use(
  response => {
    return response.data;
  },
  error => {
    const status = error.response?.status;
    const data = error.response?.data;

    console.error(`Request Failed [${status}]:`, error.config.url);

    // Error information extraction
    let msg = "Network error";
    if (data) {
      if (typeof data.detail === 'string') msg = data.detail;
      else if (typeof data.error === 'string') msg = data.error;
      else if (typeof data === 'object') {
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