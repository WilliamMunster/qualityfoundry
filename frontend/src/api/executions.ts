/**
 * 执行管理 API
 */
import apiClient from './client';

export interface Execution {
  id: string;
  testcase_id: string;
  environment_id: string;
  mode: 'dsl' | 'mcp' | 'hybrid';
  status: 'pending' | 'running' | 'success' | 'failed' | 'stopped';
  result?: any;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ExecutionCreate {
  testcase_id: string;
  environment_id: string;
  mode?: 'dsl' | 'mcp' | 'hybrid';
}

export interface ExecutionList {
  total: number;
  items: Execution[];
  page: number;
  page_size: number;
}

export const getExecutions = async (params?: {
  testcase_id?: string;
  environment_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ExecutionList> => {
  return apiClient.get('/api/v1/executions', { params });
};

export const getExecution = async (id: string): Promise<Execution> => {
  return apiClient.get(`/api/v1/executions/${id}`);
};

export const createExecution = async (data: ExecutionCreate): Promise<Execution> => {
  return apiClient.post('/api/v1/executions', data);
};

export const getExecutionStatus = async (id: string): Promise<any> => {
  return apiClient.get(`/api/v1/executions/${id}/status`);
};

export const stopExecution = async (id: string): Promise<Execution> => {
  return apiClient.post(`/api/v1/executions/${id}/stop`);
};

export const getExecutionLogs = async (id: string): Promise<any> => {
  return apiClient.get(`/api/v1/executions/${id}/logs`);
};
