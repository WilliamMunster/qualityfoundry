/**
 * 环境管理 API
 */
import apiClient from './client';

export interface Environment {
  id: string;
  name: string;
  base_url: string;
  variables: Record<string, any>;
  credentials?: string;
  health_check_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EnvironmentCreate {
  name: string;
  base_url: string;
  variables?: Record<string, any>;
  credentials?: string;
  health_check_url?: string;
}

export interface EnvironmentList {
  total: number;
  items: Environment[];
}

export const getEnvironments = async (params?: {
  is_active?: boolean;
}): Promise<EnvironmentList> => {
  return apiClient.get('/api/v1/environments', { params });
};

export const getEnvironment = async (id: string): Promise<Environment> => {
  return apiClient.get(`/api/v1/environments/${id}`);
};

export const createEnvironment = async (data: EnvironmentCreate): Promise<Environment> => {
  return apiClient.post('/api/v1/environments', data);
};

export const updateEnvironment = async (
  id: string,
  data: Partial<EnvironmentCreate>
): Promise<Environment> => {
  return apiClient.put(`/api/v1/environments/${id}`, data);
};

export const deleteEnvironment = async (id: string): Promise<void> => {
  return apiClient.delete(`/api/v1/environments/${id}`);
};

export const healthCheck = async (id: string): Promise<any> => {
  return apiClient.post(`/api/v1/environments/${id}/health-check`);
};
