/**
 * API 客户端配置
 */
import axios from 'axios';
import { message } from 'antd';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 401:
          // 未授权，跳转登录
          message.error('未授权，请登录');
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          window.location.href = '/login';
          break;
        case 403:
          message.error('无权限访问');
          break;
        case 404:
          message.error('资源不存在');
          break;
        case 500:
          message.error('服务器错误');
          break;
        default:
          message.error(data?.detail || '请求失败');
      }
    } else {
      message.error('网络错误');
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
