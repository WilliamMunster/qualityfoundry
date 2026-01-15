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

// 错误消息防抖控制
let lastErrorMessage = '';
let lastErrorTime = 0;
const ERROR_MSG_DURATION = 3000; // 3秒内相同错误不重复提示

const showErrorMessage = (msg: string) => {
  const now = Date.now();
  if (msg === lastErrorMessage && now - lastErrorTime < ERROR_MSG_DURATION) {
    return;
  }
  lastErrorMessage = msg;
  lastErrorTime = now;
  message.error(msg);
};

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
          showErrorMessage('未授权，请登录');
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
          break;
        case 403:
          showErrorMessage('无权限访问此资源');
          break;
        case 404:
          showErrorMessage('请求的资源不存在');
          break;
        case 500:
          showErrorMessage('服务器内部错误，请联系管理员');
          break;
        case 422:
          // 参数验证错误
          const detail = data?.detail;
          if (Array.isArray(detail)) {
            showErrorMessage(`参数错误: ${detail[0]?.msg || '未知错误'}`);
          } else {
            showErrorMessage(detail || '参数验证失败');
          }
          break;
        default:
          showErrorMessage(data?.detail || `请求失败 (${status})`);
      }
    } else if (error.request) {
      // 请求发出但没有收到响应
      showErrorMessage('网络连接失败，请检查网络设置');
    } else {
      // 发送请求时出了点问题
      showErrorMessage('请求配置错误');
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
